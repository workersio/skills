# M-3: Unsafe Casting [MEDIUM]

Using Rust's `as` keyword to cast between integer types performs a **silent truncation** when the source value exceeds the target type's range. For example, casting a u128 value greater than `u64::MAX` to u64 silently discards the upper bits. This produces an incorrect, much smaller value with no error or warning at runtime.

---

## Preconditions

- Program uses `as` to cast between integer types of different sizes (e.g., u128 to u64, u64 to u32, i64 to u64)
- The source value is derived from arithmetic, user input, or on-chain state (not a compile-time constant within range)
- The result of the cast is used in a transfer, balance update, or logic comparison
- No preceding bounds check ensures the source fits in the target type

---

## Vulnerable Pattern

### u128 to u64 Truncation in Share Calculation

```rust
pub fn calculate_withdrawal(ctx: Context<Withdraw>, shares: u64) -> Result<()> {
    let pool = &ctx.accounts.pool;

    // Intermediate calculation in u128 for precision
    let withdrawal_amount_u128: u128 = (shares as u128)
        .checked_mul(pool.total_value as u128)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(pool.total_shares as u128)
        .ok_or(ErrorCode::DivisionByZero)?;

    // VULNERABLE: silent truncation if result > u64::MAX
    // Attacker with enough shares could get a tiny amount instead of a huge payout
    let withdrawal_amount = withdrawal_amount_u128 as u64;

    token::transfer(cpi_ctx, withdrawal_amount)?;
    Ok(())
}
```

### i64 to u64 Sign Loss

```rust
pub fn process_oracle_price(ctx: Context<UpdatePrice>) -> Result<()> {
    let price_feed = &ctx.accounts.price_feed;

    // Pyth oracle returns price as i64
    let price: i64 = price_feed.get_price().price;

    // VULNERABLE: if oracle returns negative price (error or extreme condition),
    // this casts to a very large u64 value
    let price_u64 = price as u64;
    // e.g., -1_i64 as u64 = 18_446_744_073_709_551_615

    ctx.accounts.vault.cached_price = price_u64;
    Ok(())
}
```

### u64 to u32 Truncation in Token Amount

```rust
pub fn create_order(ctx: Context<CreateOrder>, amount: u64) -> Result<()> {
    let order = &mut ctx.accounts.order;

    // VULNERABLE: order book stores amount as u32 to save space
    // Any amount > 4_294_967_295 silently truncates
    order.amount = amount as u32;
    // e.g., 5_000_000_000_u64 as u32 = 705_032_704

    Ok(())
}
```

### Timestamp / Clock Casting

```rust
pub fn check_lockup(ctx: Context<CheckLockup>) -> Result<()> {
    let clock = Clock::get()?;
    let stake = &ctx.accounts.stake;

    // Clock::unix_timestamp is i64
    let now: i64 = clock.unix_timestamp;

    // VULNERABLE: converting to u64 without checking sign
    // Theoretically safe today (timestamp is positive), but defensive coding required
    let elapsed = (now as u64) - stake.start_time;

    // ALSO VULNERABLE: casting elapsed seconds to u32
    // Overflows after ~136 years from epoch — unlikely but shows the pattern
    let elapsed_u32 = elapsed as u32;

    Ok(())
}
```

### Casting in Constant Product AMM

```rust
pub fn swap(ctx: Context<Swap>, amount_in: u64) -> Result<()> {
    let pool = &mut ctx.accounts.pool;

    // Calculate output using u128 intermediate
    let numerator: u128 = (amount_in as u128)
        .checked_mul(pool.reserve_out as u128)
        .ok_or(ErrorCode::MathOverflow)?;
    let denominator: u128 = (pool.reserve_in as u128)
        .checked_add(amount_in as u128)
        .ok_or(ErrorCode::MathOverflow)?;
    let amount_out_u128 = numerator / denominator;

    // VULNERABLE: if pool has very large reserves (e.g., wrapped BTC with
    // many decimals), result could exceed u64::MAX
    let amount_out = amount_out_u128 as u64;

    Ok(())
}
```

---

## Detection Heuristics

### Grep Patterns

```
# Find all `as` casts between integer types
as u8
as u16
as u32
as u64
as u128
as i8
as i16
as i32
as i64
as i128
as usize
```

### What to Search

1. **Find all `as` casts** on integer types in the codebase
2. **Categorize by direction**:
   - **Narrowing** (larger to smaller type): `u128 as u64`, `u64 as u32`, `i64 as u64` — **potentially dangerous**
   - **Widening** (smaller to larger type): `u32 as u64`, `u64 as u128` — **always safe**
   - **Sign change**: `i64 as u64`, `u64 as i64` — **dangerous if value can be negative or > i64::MAX**
3. **Trace the source value**: Can it exceed the target type's range?
4. **Check for preceding bounds validation**: Is there a `require!` or `if` check before the cast?
5. **Check the usage context**: Is the cast result used in a transfer, balance, or critical comparison?

### Risk Indicators

- `as u64` after u128 arithmetic (share/reward calculations)
- `as u64` on an `i64` from oracle price feeds or timestamps
- `as u32` on any u64 amount (token amounts are typically u64)
- Cast result immediately used in `token::transfer` or balance mutation
- No `try_into()` or explicit bounds check anywhere near the cast

---

## False Positives

1. **Widening casts (smaller to larger type)** — always safe:
   ```rust
   let wide = amount_u32 as u64;   // u32 always fits in u64
   let wider = amount_u64 as u128; // u64 always fits in u128
   ```

2. **Value already bounds-checked before the cast**:
   ```rust
   require!(value_u128 <= u64::MAX as u128, ErrorCode::ValueTooLarge);
   let safe_value = value_u128 as u64; // Safe: validated above
   ```

3. **Casting constants or literals within range**:
   ```rust
   let fee_bps = 30u128 as u64; // 30 obviously fits in u64
   ```

4. **Known bounded results** (e.g., the division result is mathematically guaranteed to fit):
   ```rust
   // percentage is always 0-100 because numerator <= denominator
   let percentage = (part as u128 * 100 / total as u128) as u64;
   // Result is 0-100, always fits in u64
   ```

5. **`Clock::unix_timestamp as u64`** — currently safe because Unix timestamps are positive and fit in u64 for the foreseeable future. Low risk but still worth noting in an audit.

---

## Remediation

### Use `try_into()` with Error Handling

```rust
pub fn calculate_withdrawal(ctx: Context<Withdraw>, shares: u64) -> Result<()> {
    let pool = &ctx.accounts.pool;

    let withdrawal_amount_u128: u128 = (shares as u128)
        .checked_mul(pool.total_value as u128)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(pool.total_shares as u128)
        .ok_or(ErrorCode::DivisionByZero)?;

    // SAFE: try_into() returns Err if value doesn't fit
    let withdrawal_amount: u64 = withdrawal_amount_u128
        .try_into()
        .map_err(|_| ErrorCode::CastOverflow)?;

    token::transfer(cpi_ctx, withdrawal_amount)?;
    Ok(())
}
```

### Use `TryFrom` for Sign-Changing Casts

```rust
pub fn process_oracle_price(ctx: Context<UpdatePrice>) -> Result<()> {
    let price_feed = &ctx.accounts.price_feed;
    let price: i64 = price_feed.get_price().price;

    // SAFE: explicit error if price is negative
    let price_u64: u64 = u64::try_from(price)
        .map_err(|_| ErrorCode::NegativePrice)?;

    ctx.accounts.vault.cached_price = price_u64;
    Ok(())
}
```

### Explicit Bounds Check Before Cast (Alternative)

```rust
pub fn create_order(ctx: Context<CreateOrder>, amount: u64) -> Result<()> {
    let order = &mut ctx.accounts.order;

    // SAFE: explicit bounds check
    require!(amount <= u32::MAX as u64, ErrorCode::AmountExceedsU32);
    order.amount = amount as u32;

    Ok(())
}
```

### Helper Function for Safe Casting

```rust
/// Safely cast u128 to u64, returning an error on overflow
pub fn to_u64(value: u128) -> Result<u64> {
    u64::try_from(value).map_err(|_| error!(ErrorCode::CastOverflow))
}

/// Safely cast i64 to u64, returning an error on negative values
pub fn i64_to_u64(value: i64) -> Result<u64> {
    u64::try_from(value).map_err(|_| error!(ErrorCode::NegativeValue))
}

/// Safely cast u64 to u32, returning an error on overflow
pub fn to_u32(value: u64) -> Result<u32> {
    u32::try_from(value).map_err(|_| error!(ErrorCode::CastOverflow))
}
```

### Anchor Error Codes

```rust
#[error_code]
pub enum ErrorCode {
    #[msg("Cast would overflow target type")]
    CastOverflow,
    #[msg("Unexpected negative value")]
    NegativeValue,
    #[msg("Negative price from oracle")]
    NegativePrice,
    #[msg("Amount exceeds u32 maximum")]
    AmountExceedsU32,
}
```
