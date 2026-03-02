# M-2: Division Precision Loss [MEDIUM]

Integer division in Rust truncates toward zero, discarding the fractional part. When division appears in fee calculations, share computations, or reward distributions, the truncation can systematically favor one party. Dividing before multiplying amplifies precision loss and can cause results to round to zero entirely.

---

## Preconditions

- Program performs integer division (`/`) as part of fee, share, reward, or ratio calculations
- Division operands are derived from on-chain state or user input (not fixed constants)
- The result of the division feeds into a transfer, mint, or balance update
- No use of fixed-point or decimal libraries for the calculation

---

## Vulnerable Pattern

### Division Before Multiplication — Catastrophic Precision Loss

```rust
pub fn calculate_user_share(
    user_deposit: u64,
    total_deposits: u64,
    reward_pool: u64,
) -> Result<u64> {
    // VULNERABLE: division first truncates to 0 for small deposits
    // If user_deposit = 100, total_deposits = 10_000 → 100 / 10_000 = 0
    // Then 0 * reward_pool = 0 regardless of reward_pool size
    let share = user_deposit / total_deposits * reward_pool;

    Ok(share)
}
```

### Fee Calculation With Precision Loss

```rust
pub fn collect_fee(ctx: Context<CollectFee>, amount: u64) -> Result<()> {
    let fee_bps: u64 = 25; // 0.25%

    // VULNERABLE: for amount < 400, fee rounds to 0 → protocol collects nothing
    let fee = amount * fee_bps / 10_000;

    // Even worse — division first:
    // let fee = amount / 10_000 * fee_bps; // Always 0 for amount < 10_000

    let transfer_amount = amount - fee;
    token::transfer(cpi_ctx, transfer_amount)?;

    Ok(())
}
```

### Reward Distribution Precision Loss

```rust
pub fn distribute_rewards(ctx: Context<Distribute>) -> Result<()> {
    let pool = &ctx.accounts.pool;
    let staker = &mut ctx.accounts.staker;

    let elapsed_slots = clock.slot - pool.last_update_slot;

    // VULNERABLE: reward_per_token truncates, compounding over many stakers
    // With reward_rate = 100, total_staked = 1_000_000:
    // reward_per_token_increment = 100 * elapsed / 1_000_000 → 0 if elapsed < 10_000
    let reward_per_token_increment = pool.reward_rate * elapsed_slots / pool.total_staked;

    let pending = staker.amount * reward_per_token_increment;

    Ok(())
}
```

### LP Token Minting — Rounding Favors Depositor

```rust
pub fn add_liquidity(ctx: Context<AddLiquidity>, deposit_amount: u64) -> Result<()> {
    let pool = &ctx.accounts.pool;

    // VULNERABLE: rounding direction matters for economic security
    // Truncation means depositor gets slightly fewer LP tokens (safe direction)
    // BUT if total_supply is very large relative to total_pool, rounding can go wrong
    let lp_tokens_to_mint = deposit_amount * pool.lp_supply / pool.total_pool_value;

    // In withdrawal, truncation means user gets slightly fewer tokens back
    // Both directions should be checked: deposit rounds DOWN, withdraw rounds DOWN
    // This means the pool always keeps a tiny surplus (safe)

    Ok(())
}
```

---

## Detection Heuristics

### Grep Patterns

```
# Find all integer division
/

# Look for division in financial calculations
fee *  /
/ 10_000
/ 10000
/ basis
share *  /
reward *  /
amount *  /
```

### What to Search

1. **Find all `/` division operations** in instruction handlers and helper functions
2. **Check operation order**: Is division performed before multiplication? (`a / b * c` is worse than `a * c / b`)
3. **Identify the context**: Is this a fee, share, reward, ratio, or price calculation?
4. **Check magnitude of operands**: Can the numerator be smaller than the denominator (yielding 0)?
5. **Check rounding direction**: Does truncation consistently favor the protocol or the user?
6. **Look for accumulation**: Does the truncation compound across many operations?

### Risk Indicators

- Division where numerator can be smaller than denominator → result is 0
- Division before multiplication in the same expression
- Division in a loop or accumulator (error compounds per iteration)
- Fee/reward calculations where small amounts should still produce non-zero results
- Share calculations where `total_supply` is much larger than `user_amount`

---

## False Positives

1. **Division on small bounded values where truncation is negligible**:
   ```rust
   // total_items is always < 100, and we only need approximate split
   let per_user = total_items / num_users;
   ```

2. **Intentional truncation with correct rounding direction**:
   ```rust
   // Fee rounds DOWN — user pays less fee. Protocol accepts this.
   let fee = amount * fee_bps / 10_000;
   // Explicitly documented: "Fees round in favor of the user"
   ```

3. **Division on constants or very large numerators where loss is < 1 lamport**:
   ```rust
   // total_rewards is always > 1_000_000_000 (1B lamports), total_stakers < 10_000
   // Precision loss is < 1 lamport per staker — negligible
   let per_staker = total_rewards / total_stakers;
   ```

4. **u128 intermediates already in use**:
   ```rust
   // Promoted to u128 to preserve precision in the intermediate product
   let shares = (amount as u128) * (total_shares as u128) / (total_deposits as u128);
   ```

5. **Result is explicitly checked for zero and handled**:
   ```rust
   let lp_tokens = deposit * lp_supply / pool_value;
   require!(lp_tokens > 0, ErrorCode::DepositTooSmall);
   ```

---

## Remediation

### Multiply Before Divide

```rust
pub fn calculate_user_share(
    user_deposit: u64,
    total_deposits: u64,
    reward_pool: u64,
) -> Result<u64> {
    // SAFE: multiply first to preserve precision
    // user_deposit * reward_pool could overflow u64, so use u128
    let share: u64 = (user_deposit as u128)
        .checked_mul(reward_pool as u128)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(total_deposits as u128)
        .ok_or(ErrorCode::DivisionByZero)?
        .try_into()
        .map_err(|_| ErrorCode::MathOverflow)?;

    Ok(share)
}
```

### Use u128 Intermediates

```rust
pub fn calculate_fee(amount: u64, fee_bps: u64) -> Result<u64> {
    // SAFE: u64 * u64 fits in u128, then divide
    let fee: u64 = (amount as u128)
        .checked_mul(fee_bps as u128)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(10_000u128)
        .ok_or(ErrorCode::DivisionByZero)?
        .try_into()
        .map_err(|_| ErrorCode::MathOverflow)?;

    Ok(fee)
}
```

### Check Rounding Direction Explicitly

```rust
/// Rounds UP (ceiling division) — use when rounding should favor the protocol
pub fn ceil_div(numerator: u128, denominator: u128) -> Result<u128> {
    require!(denominator > 0, ErrorCode::DivisionByZero);
    // (a + b - 1) / b is the standard ceiling division formula
    Ok(numerator
        .checked_add(denominator)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_sub(1)
        .ok_or(ErrorCode::MathUnderflow)?
        .checked_div(denominator)
        .ok_or(ErrorCode::DivisionByZero)?)
}

/// Rounds DOWN (floor division) — use when rounding should favor the user
pub fn floor_div(numerator: u128, denominator: u128) -> Result<u128> {
    require!(denominator > 0, ErrorCode::DivisionByZero);
    Ok(numerator / denominator) // Default Rust integer division floors
}
```

### Accumulator Pattern for Reward Distribution

```rust
pub fn update_reward_per_token(pool: &mut Pool, clock: &Clock) -> Result<()> {
    let elapsed = clock.slot.checked_sub(pool.last_update_slot)
        .ok_or(ErrorCode::MathUnderflow)?;

    if pool.total_staked > 0 {
        // SAFE: use u128 accumulator scaled by 1e12 to preserve precision
        let reward_increment: u128 = (pool.reward_rate as u128)
            .checked_mul(elapsed as u128)
            .ok_or(ErrorCode::MathOverflow)?
            .checked_mul(1_000_000_000_000u128) // scale factor
            .ok_or(ErrorCode::MathOverflow)?
            .checked_div(pool.total_staked as u128)
            .ok_or(ErrorCode::DivisionByZero)?;

        pool.reward_per_token_accumulated = pool.reward_per_token_accumulated
            .checked_add(reward_increment)
            .ok_or(ErrorCode::MathOverflow)?;
    }

    pool.last_update_slot = clock.slot;
    Ok(())
}
```
