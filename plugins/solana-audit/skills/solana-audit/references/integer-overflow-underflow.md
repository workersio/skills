# M-1: Integer Overflow / Underflow [HIGH]

Arithmetic operations on unsigned integers wrap around silently in Rust release builds, producing incorrect values. Rust panics on overflow in debug mode but **wraps in release mode** (the mode used for on-chain programs). This can lead to massive value discrepancies — e.g., a subtraction that wraps a u64 from 0 to `u64::MAX`.

---

## Preconditions

- Program performs arithmetic (`+`, `-`, `*`) on integer types (u8, u16, u32, u64, u128, i64, etc.)
- At least one operand is derived from user input, account state, or on-chain data (not a compile-time constant)
- The program is compiled in release mode (all deployed Solana programs are)
- No `overflow-checks = true` in `Cargo.toml` `[profile.release]` section (most projects do not set this)

---

## Vulnerable Pattern

### Native Solana Program — Raw Arithmetic

```rust
pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> {
    let vault = &mut ctx.accounts.vault;

    // VULNERABLE: wraps to a small number if vault.total_deposits + amount > u64::MAX
    vault.total_deposits = vault.total_deposits + amount;

    // VULNERABLE: wraps to u64::MAX if user.balance < fee
    let net_amount = amount - vault.fee;

    // VULNERABLE: wraps if amount * price overflows u64
    let value = amount * vault.price_per_token;

    Ok(())
}
```

### Anchor Program — Arithmetic in Business Logic

```rust
pub fn calculate_rewards(ctx: Context<ClaimRewards>) -> Result<()> {
    let pool = &ctx.accounts.pool;
    let user = &mut ctx.accounts.user_stake;

    // VULNERABLE: multiplication can overflow u64 with large staked amounts and high reward rates
    let pending_reward = user.staked_amount * pool.reward_rate * elapsed_time;

    // VULNERABLE: subtraction wraps if user already claimed more than total
    let claimable = pending_reward - user.claimed_amount;

    token::transfer(cpi_ctx, claimable)?;
    Ok(())
}
```

### Compound Overflow in Fee Calculations

```rust
pub fn swap(ctx: Context<Swap>, amount_in: u64) -> Result<()> {
    let fee_bps: u64 = 30; // 0.3%

    // VULNERABLE: amount_in * fee_bps can overflow if amount_in > u64::MAX / 30
    let fee = amount_in * fee_bps / 10_000;
    let amount_after_fee = amount_in - fee;

    // VULNERABLE: amount_after_fee * reserve_out can overflow
    let amount_out = amount_after_fee * reserve_out / (reserve_in + amount_after_fee);

    Ok(())
}
```

---

## Detection Heuristics

### Grep Patterns

```
# Find raw arithmetic operators on likely integer variables
+, -, * operators used on u64/u128/i64 variables without checked_ prefix

# Specific patterns to search for:
# 1. Addition without checked_add
amount +
total +
balance +
supply +

# 2. Subtraction without checked_sub
amount -
balance -
total -
remaining -

# 3. Multiplication without checked_mul
amount *
price *
rate *
```

### What to Search

1. **Find all arithmetic operations**: Search for `+`, `-`, `*` operators on integer types
2. **Exclude checked operations**: Filter out `checked_add`, `checked_sub`, `checked_mul`, `checked_div`, `saturating_add`, `saturating_sub`, `saturating_mul`
3. **Check if `overflow-checks = true`** is set in `Cargo.toml` under `[profile.release]`
4. **Trace operand sources**: Determine if operands can be attacker-controlled or grow unbounded
5. **Check Anchor `require!` guards**: Look for bounds checks before the arithmetic

### Risk Indicators

- Arithmetic on user-supplied `amount` parameters
- Multiplication of two u64 values (easily overflows)
- Subtraction where the subtrahend could exceed the minuend
- Loop-accumulated arithmetic (totals computed across iterations)
- Timestamp arithmetic (slot numbers, Unix timestamps)

---

## False Positives

1. **Compile-time constants / literals**: Operations on constants known at compile time cannot overflow at runtime
   ```rust
   let fee_denominator: u64 = 10_000; // constant, safe
   let seconds_per_day: u64 = 86_400; // constant, safe
   ```

2. **u128 with bounded u64 inputs**: If both operands are u64, their product fits in u128
   ```rust
   let product = (amount as u128) * (price as u128); // u64 * u64 always fits in u128
   ```

3. **Anchor `require!` / bounds check before arithmetic**: If the inputs are validated to be within safe ranges before the operation
   ```rust
   require!(amount <= MAX_DEPOSIT, ErrorCode::ExceedsMax);
   require!(pool.total + amount <= u64::MAX, ErrorCode::Overflow);
   let new_total = pool.total + amount; // Safe: guarded above
   ```

4. **`overflow-checks = true` in release profile**: If the project's `Cargo.toml` includes:
   ```toml
   [profile.release]
   overflow-checks = true
   ```
   Then all arithmetic panics on overflow (still a DoS risk, but not a silent wrap).

5. **Small bounded enums or counters**: A u8 counter that can only reach a known small maximum (e.g., number of signers in a multisig, capped at 11).

---

## Remediation

### Use `checked_*` Methods with Error Propagation

```rust
pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> {
    let vault = &mut ctx.accounts.vault;

    // SAFE: returns error instead of wrapping
    vault.total_deposits = vault.total_deposits
        .checked_add(amount)
        .ok_or(ErrorCode::MathOverflow)?;

    // SAFE: returns error if fee > amount
    let net_amount = amount
        .checked_sub(vault.fee)
        .ok_or(ErrorCode::MathUnderflow)?;

    // SAFE: returns error if product overflows
    let value = amount
        .checked_mul(vault.price_per_token)
        .ok_or(ErrorCode::MathOverflow)?;

    Ok(())
}
```

### Use `saturating_*` When Capping is Acceptable

```rust
// Saturating is appropriate when capping at max/min is the desired behavior
let capped_reward = base_reward.saturating_mul(multiplier);
// If overflow, returns u64::MAX instead of wrapping — acceptable for display/cap scenarios
```

### Use u128 Intermediates for Products

```rust
pub fn calculate_share(amount: u64, total_shares: u64, total_deposits: u64) -> Result<u64> {
    // Promote to u128 for the intermediate multiplication
    let shares: u64 = (amount as u128)
        .checked_mul(total_shares as u128)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(total_deposits as u128)
        .ok_or(ErrorCode::DivisionByZero)?
        .try_into()
        .map_err(|_| ErrorCode::MathOverflow)?;

    Ok(shares)
}
```

### Enable Overflow Checks Globally (Defense in Depth)

```toml
# Cargo.toml — enables panic-on-overflow even in release builds
# Note: This causes panics (DoS) rather than silent corruption
# Still use checked_* for proper error handling
[profile.release]
overflow-checks = true
```

### Anchor Error Code Definition

```rust
#[error_code]
pub enum ErrorCode {
    #[msg("Math overflow")]
    MathOverflow,
    #[msg("Math underflow")]
    MathUnderflow,
    #[msg("Division by zero")]
    DivisionByZero,
}
```
