# L-1: Oracle Manipulation [CRITICAL]

Programs that read on-chain price data without proper validation are vulnerable to oracle manipulation. An attacker can distort prices within a single transaction (or block) — via flash loans, large swaps, or thin-liquidity AMMs — to trigger favorable liquidations, borrow at distorted collateral ratios, or extract value from lending/trading protocols. This was the root cause of the **Mango Markets exploit ($114M, October 2022)** and contributed to **Solend's near-insolvency crisis (June 2022)**.

---

## Preconditions

- Program reads price data from an oracle (Pyth, Switchboard, on-chain AMM pool)
- The price data influences an economic decision: collateral valuation, liquidation threshold, swap rate, or position pricing
- The oracle data is not validated for staleness, confidence, or source integrity
- The price source can be influenced within a single transaction or block (e.g., spot AMM price)

---

## Vulnerable Pattern

### Direct AMM Spot Price Read

```rust
pub fn calculate_collateral_value(ctx: Context<Borrow>) -> Result<u64> {
    let pool = &ctx.accounts.amm_pool;

    // VULNERABLE: spot price from AMM is trivially manipulable via flash loan
    // Attacker: flash-borrow → swap to skew price → borrow against inflated collateral → repay
    let price = pool.token_a_reserve
        .checked_div(pool.token_b_reserve)
        .ok_or(ErrorCode::DivisionByZero)?;

    let collateral_value = ctx.accounts.user_collateral.amount
        .checked_mul(price)
        .ok_or(ErrorCode::MathOverflow)?;

    Ok(collateral_value)
}
```

### Pyth Oracle Without Staleness Check

```rust
pub fn liquidate(ctx: Context<Liquidate>) -> Result<()> {
    let price_feed = &ctx.accounts.pyth_price_feed;
    let price_data = price_feed.get_price_unchecked(); // Gets price without any validation

    // VULNERABLE: price could be hours old (stale)
    // During volatile markets, stale prices create arbitrage opportunities
    let price = price_data.price; // No staleness check!
    let confidence = price_data.conf; // Confidence interval ignored!

    let collateral_value = (ctx.accounts.position.collateral as i128)
        .checked_mul(price as i128)
        .ok_or(ErrorCode::MathOverflow)?;

    // Liquidation proceeds using potentially stale/manipulated price
    if collateral_value < ctx.accounts.position.debt as i128 {
        // Execute liquidation...
    }

    Ok(())
}
```

### Switchboard Oracle Without Confidence Check

```rust
pub fn get_asset_price(ctx: Context<GetPrice>) -> Result<u64> {
    let feed = &ctx.accounts.switchboard_feed;
    let result = feed.get_result()?;

    // VULNERABLE: no confidence interval check
    // If the oracle reports price = $100 with confidence ± $50,
    // the actual price could be anywhere from $50 to $150
    let price: u64 = result.try_into()
        .map_err(|_| ErrorCode::InvalidPrice)?;

    // No staleness check — result.round_open_timestamp not verified

    Ok(price)
}
```

### Mango Markets Pattern — Thin Market Manipulation

```rust
pub fn update_perp_position(ctx: Context<UpdatePosition>) -> Result<()> {
    let oracle = &ctx.accounts.oracle_account;
    let price = read_oracle_price(oracle)?;

    // VULNERABLE: Mango's oracle was based on a thin-liquidity perp market
    // Attacker placed large perp orders to move the oracle price,
    // then borrowed against the inflated mark-to-market value

    let position = &mut ctx.accounts.user_position;
    position.value = position.base_amount
        .checked_mul(price)
        .ok_or(ErrorCode::MathOverflow)?;

    // User can now borrow against this inflated position.value
    let max_borrow = position.value * COLLATERAL_FACTOR / PRECISION;

    Ok(())
}
```

### Single Oracle Source Without Fallback

```rust
pub fn execute_trade(ctx: Context<Trade>, amount: u64) -> Result<()> {
    let pyth_feed = &ctx.accounts.price_feed;

    // VULNERABLE: single oracle source — if Pyth goes down or is manipulated,
    // there's no fallback or circuit breaker
    let price = pyth_feed.get_price_no_older_than(
        &Clock::get()?,
        60, // 60 second staleness — but no confidence or fallback
    ).ok_or(ErrorCode::StalePrice)?;

    let trade_value = amount
        .checked_mul(price.price as u64)
        .ok_or(ErrorCode::MathOverflow)?;

    // No circuit breaker: if price moves 50% in one block, trade still executes

    Ok(())
}
```

---

## Detection Heuristics

### Grep Patterns

```
# Find oracle/price reading patterns
pyth
switchboard
oracle
price_feed
get_price
get_result
price_data
spot_price

# Find AMM pool reads used as price sources
reserve_a / reserve_b
token_a_reserve
token_b_reserve
pool.amount

# Find staleness-related checks (or lack thereof)
get_price_unchecked
get_price_no_older_than
unix_timestamp
staleness
confidence
conf
```

### What to Search

1. **Find all price/oracle reads**: Search for Pyth, Switchboard, or AMM pool balance reads
2. **Check the price source**: Is it a TWAP (safer) or spot price (manipulable)?
3. **Check staleness validation**: Is `get_price_no_older_than` used? Is the max age reasonable (< 60 seconds for volatile assets)?
4. **Check confidence interval**: Is `price.conf` checked against a threshold? A wide confidence interval means the price is unreliable.
5. **Check for circuit breakers**: Is there a max price deviation check between consecutive updates?
6. **Check for multi-oracle fallback**: Does the protocol use multiple independent oracle sources?
7. **Trace price usage**: Where does the price flow? Collateral valuation, liquidation, swap pricing?

### Risk Indicators

- `get_price_unchecked()` or any oracle read without staleness validation
- AMM spot price (`reserve_a / reserve_b`) used for collateral valuation or liquidation
- No confidence interval check on Pyth/Switchboard data
- Single oracle source with no fallback
- No circuit breaker for extreme price movements
- Price used for high-value operations (liquidation, large borrows)

---

## False Positives

1. **TWAP with sufficient time window** (30+ minutes for most assets):
   ```rust
   // TWAP averages price over a window, resisting single-block manipulation
   let twap_price = oracle.get_twap(1800)?; // 30-minute TWAP
   ```

2. **Multi-oracle with median selection**:
   ```rust
   let price_a = pyth_feed.get_price()?;
   let price_b = switchboard_feed.get_result()?;
   let price_c = chainlink_feed.get_price()?;
   let median_price = median(price_a, price_b, price_c); // Manipulation requires corrupting 2/3
   ```

3. **Circuit breakers in place**:
   ```rust
   let new_price = oracle.get_price()?;
   let deviation = abs_diff(new_price, cached_price) * 10000 / cached_price;
   require!(deviation <= MAX_PRICE_DEVIATION_BPS, ErrorCode::PriceDeviationTooHigh);
   // Rejects updates that move price more than X% in one update
   ```

4. **Staleness + confidence checks present**:
   ```rust
   let price = pyth_feed.get_price_no_older_than(&clock, MAX_ORACLE_AGE)?;
   require!(
       price.conf as u64 * 100 <= price.price.unsigned_abs() * MAX_CONFIDENCE_PCT,
       ErrorCode::OracleConfidenceTooWide
   );
   ```

5. **Oracle used only for non-critical display or informational purposes** (not economic decisions):
   ```rust
   // Price used for UI display only, not for transfers/liquidations
   emit!(PriceUpdate { price: oracle.get_price()? });
   ```

---

## Remediation

### Use TWAP Instead of Spot Price

```rust
pub fn get_safe_price(oracle: &AccountInfo) -> Result<u64> {
    let price_feed = load_pyth_feed(oracle)?;

    // Use TWAP — resistant to single-transaction manipulation
    let twap = price_feed.get_twap_no_older_than(
        &Clock::get()?,
        MAX_ORACLE_AGE,
    ).ok_or(ErrorCode::StaleOracle)?;

    Ok(twap.price as u64)
}

const MAX_ORACLE_AGE: u64 = 60; // 60 seconds max staleness
```

### Add Staleness Checks

```rust
pub fn get_validated_price(ctx: &Context<MyInstruction>) -> Result<i64> {
    let price_feed = &ctx.accounts.pyth_price_feed;
    let clock = Clock::get()?;

    // SAFE: rejects prices older than MAX_ORACLE_AGE seconds
    let price = price_feed
        .get_price_no_older_than(&clock, MAX_ORACLE_AGE)
        .ok_or(ErrorCode::OracleStale)?;

    // Verify the price is positive (sanity check)
    require!(price.price > 0, ErrorCode::InvalidOraclePrice);

    Ok(price.price)
}
```

### Add Confidence Interval Validation

```rust
pub fn get_price_with_confidence(ctx: &Context<MyInstruction>) -> Result<(i64, u64)> {
    let price_feed = &ctx.accounts.pyth_price_feed;
    let clock = Clock::get()?;

    let price = price_feed
        .get_price_no_older_than(&clock, MAX_ORACLE_AGE)
        .ok_or(ErrorCode::OracleStale)?;

    // SAFE: reject if confidence interval is too wide relative to price
    // confidence / price > 2.5% means oracle is unreliable
    let max_confidence: u64 = (price.price.unsigned_abs() as u64)
        .checked_mul(MAX_CONFIDENCE_BPS)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(10_000)
        .ok_or(ErrorCode::DivisionByZero)?;

    require!(price.conf <= max_confidence, ErrorCode::OracleConfidenceTooWide);

    Ok((price.price, price.conf))
}

const MAX_CONFIDENCE_BPS: u64 = 250; // 2.5% max confidence interval
```

### Add Circuit Breakers

```rust
pub fn update_cached_price(ctx: Context<UpdatePrice>) -> Result<()> {
    let config = &mut ctx.accounts.price_config;
    let new_price = get_validated_price(&ctx)?;

    // Circuit breaker: reject price updates that deviate too much from last known price
    if config.last_price > 0 {
        let deviation = if new_price > config.last_price {
            new_price - config.last_price
        } else {
            config.last_price - new_price
        };

        let max_deviation = config.last_price
            .checked_mul(MAX_PRICE_CHANGE_BPS)
            .ok_or(ErrorCode::MathOverflow)?
            .checked_div(10_000)
            .ok_or(ErrorCode::DivisionByZero)?;

        require!(deviation <= max_deviation, ErrorCode::PriceDeviationExceeded);
    }

    config.last_price = new_price;
    config.last_update_slot = Clock::get()?.slot;

    Ok(())
}

const MAX_PRICE_CHANGE_BPS: i64 = 1_000; // 10% max change per update
```

### Multi-Oracle with Fallback

```rust
pub fn get_robust_price(ctx: &Context<MultiOracle>) -> Result<i64> {
    // Try primary oracle (Pyth)
    let pyth_result = get_pyth_price(&ctx.accounts.pyth_feed);

    // Try secondary oracle (Switchboard)
    let switchboard_result = get_switchboard_price(&ctx.accounts.switchboard_feed);

    match (pyth_result, switchboard_result) {
        (Ok(p), Ok(s)) => {
            // Both available — use median / check they agree within tolerance
            let diff = (p - s).unsigned_abs();
            let avg = ((p + s) / 2).unsigned_abs();
            require!(
                diff * 10_000 / avg <= MAX_ORACLE_DIVERGENCE_BPS as u64,
                ErrorCode::OraclesDiverge
            );
            Ok((p + s) / 2) // Average of both
        },
        (Ok(p), Err(_)) => Ok(p),  // Fallback to Pyth
        (Err(_), Ok(s)) => Ok(s),  // Fallback to Switchboard
        (Err(_), Err(_)) => Err(error!(ErrorCode::AllOraclesUnavailable)),
    }
}

const MAX_ORACLE_DIVERGENCE_BPS: i64 = 500; // 5% max divergence between oracles
```
