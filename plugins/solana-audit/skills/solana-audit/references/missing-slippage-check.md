# L-2: Missing Slippage Check [HIGH]

Swap, trade, or exchange instructions that lack a minimum output amount parameter (or fail to enforce it) are vulnerable to sandwich attacks. A MEV searcher (or validator) can observe the pending transaction, front-run it with a large trade to move the price unfavorably, let the victim's trade execute at the worse price, then back-run to capture the difference. Without slippage protection, the victim can receive arbitrarily less than expected.

---

## Preconditions

- Program has an instruction that swaps, trades, or exchanges tokens
- The instruction does not accept a `min_amount_out` (or `max_amount_in`) parameter, or accepts it but does not enforce it
- The exchange rate is determined by on-chain state (AMM reserves, order book, oracle price) that can change between transaction submission and execution
- Transactions are visible in the mempool before execution (standard for Solana validators and Jito block engine)

---

## Vulnerable Pattern

### Swap Without Any Slippage Parameter

```rust
pub fn swap(ctx: Context<Swap>, amount_in: u64) -> Result<()> {
    let pool = &mut ctx.accounts.pool;

    // Calculate output using constant product formula
    let amount_out = (amount_in as u128)
        .checked_mul(pool.reserve_out as u128)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(
            (pool.reserve_in as u128)
                .checked_add(amount_in as u128)
                .ok_or(ErrorCode::MathOverflow)?
        )
        .ok_or(ErrorCode::DivisionByZero)?;

    let amount_out: u64 = amount_out.try_into()
        .map_err(|_| ErrorCode::MathOverflow)?;

    // VULNERABLE: no min_amount_out check
    // User gets whatever the pool gives them — could be close to 0
    // after a sandwich attack moves the reserves

    pool.reserve_in = pool.reserve_in.checked_add(amount_in)
        .ok_or(ErrorCode::MathOverflow)?;
    pool.reserve_out = pool.reserve_out.checked_sub(amount_out)
        .ok_or(ErrorCode::MathUnderflow)?;

    // Transfer tokens...
    token::transfer(deposit_ctx, amount_in)?;
    token::transfer(withdraw_ctx, amount_out)?;

    Ok(())
}
```

### Slippage Parameter Accepted but Not Enforced

```rust
pub fn swap_with_unused_slippage(
    ctx: Context<Swap>,
    amount_in: u64,
    min_amount_out: u64, // Parameter exists but is NEVER checked!
) -> Result<()> {
    let pool = &mut ctx.accounts.pool;

    let amount_out = calculate_output(amount_in, pool.reserve_in, pool.reserve_out)?;

    // VULNERABLE: min_amount_out is accepted but never enforced
    // The require! check is missing

    pool.reserve_in = pool.reserve_in.checked_add(amount_in)
        .ok_or(ErrorCode::MathOverflow)?;
    pool.reserve_out = pool.reserve_out.checked_sub(amount_out)
        .ok_or(ErrorCode::MathUnderflow)?;

    token::transfer(deposit_ctx, amount_in)?;
    token::transfer(withdraw_ctx, amount_out)?;

    Ok(())
}
```

### Slippage Check After the Transfer (Useless)

```rust
pub fn swap_late_check(
    ctx: Context<Swap>,
    amount_in: u64,
    min_amount_out: u64,
) -> Result<()> {
    let pool = &mut ctx.accounts.pool;
    let amount_out = calculate_output(amount_in, pool.reserve_in, pool.reserve_out)?;

    // Tokens already transferred!
    token::transfer(deposit_ctx, amount_in)?;
    token::transfer(withdraw_ctx, amount_out)?;

    pool.reserve_in += amount_in;
    pool.reserve_out -= amount_out;

    // VULNERABLE: check after transfer — tx still succeeds because
    // Solana transactions are atomic, BUT if this is a CPI from another program,
    // the caller may have already acted on the intermediate state
    // In practice, this is actually OK for single-instruction txs on Solana
    // (tx is atomic), but it's a code smell and dangerous in CPI chains
    require!(amount_out >= min_amount_out, ErrorCode::SlippageExceeded);

    Ok(())
}
```

### Liquidity Addition Without Slippage

```rust
pub fn add_liquidity(
    ctx: Context<AddLiquidity>,
    amount_a: u64,
    amount_b: u64,
) -> Result<()> {
    let pool = &mut ctx.accounts.pool;

    // VULNERABLE: no minimum LP tokens parameter
    // Pool ratio can change between submission and execution
    // User may receive far fewer LP tokens than expected
    let lp_tokens = calculate_lp_tokens(amount_a, amount_b, pool)?;

    token::transfer(deposit_a_ctx, amount_a)?;
    token::transfer(deposit_b_ctx, amount_b)?;
    token::mint_to(mint_ctx, lp_tokens)?;

    Ok(())
}
```

### CPI Swap Without Forwarding Slippage

```rust
pub fn route_swap(ctx: Context<RouteSwap>, amount_in: u64) -> Result<()> {
    // VULNERABLE: calling an AMM's swap via CPI without passing min_amount_out
    // Even if the AMM supports slippage, the router doesn't use it
    let swap_ix = create_swap_instruction(
        ctx.accounts.amm_program.key(),
        amount_in,
        0, // min_amount_out = 0 — no protection!
    );

    invoke(&swap_ix, &[...])?;

    Ok(())
}
```

---

## Detection Heuristics

### Grep Patterns

```
# Find swap/trade/exchange instructions
fn swap
fn trade
fn exchange
fn buy
fn sell
fn add_liquidity
fn remove_liquidity
fn route

# Find slippage parameters (or lack thereof)
min_amount_out
max_amount_in
min_out
max_in
slippage
minimum_received

# Find amount output calculations
amount_out
output_amount
tokens_out
received_amount
```

### What to Search

1. **Find all swap/trade instructions**: Any instruction that exchanges one token for another
2. **Check for `min_amount_out` parameter**: Does the instruction signature include a minimum output parameter?
3. **Verify enforcement**: Is there a `require!(amount_out >= min_amount_out)` check?
4. **Check placement**: Is the enforcement check before any irreversible state changes?
5. **Check CPI calls to AMMs**: When the program calls another swap program, does it pass a non-zero `min_amount_out`?
6. **Check liquidity operations**: Add/remove liquidity also needs slippage protection (min LP tokens / min tokens returned)
7. **Check for hardcoded zero slippage**: `min_amount_out: 0` passed in a CPI effectively disables slippage protection

### Risk Indicators

- Swap instruction with no `min_amount_out` in the function signature
- `min_amount_out` parameter present but no `require!` check against it
- CPI to an AMM with `min_amount_out: 0` or missing parameter
- Liquidity operations without min LP token / min token output checks
- SDK or client code that sets `min_amount_out = 0` by default

---

## False Positives

1. **Parameter exists and is properly enforced**:
   ```rust
   pub fn swap(ctx: Context<Swap>, amount_in: u64, min_amount_out: u64) -> Result<()> {
       let amount_out = calculate_output(...)?;
       require!(amount_out >= min_amount_out, ErrorCode::SlippageExceeded); // Enforced
       // ... proceed with swap
       Ok(())
   }
   ```

2. **Limit orders with inherent slippage protection**:
   ```rust
   pub fn fill_limit_order(ctx: Context<FillOrder>) -> Result<()> {
       let order = &ctx.accounts.order;
       // Limit order has a fixed price — inherently slippage-protected
       // It either fills at the limit price or doesn't fill at all
       require!(current_price <= order.limit_price, ErrorCode::PriceTooHigh);
       // ...
       Ok(())
   }
   ```

3. **Private/permissioned swaps** (only callable by trusted parties, e.g., a rebalancer controlled by governance):
   ```rust
   pub fn rebalance(ctx: Context<Rebalance>) -> Result<()> {
       // Only callable by the protocol's governance multisig
       require!(ctx.accounts.authority.key() == GOVERNANCE_KEY, ErrorCode::Unauthorized);
       // Governance can accept any slippage — they set the parameters
       // ...
       Ok(())
   }
   ```

4. **Atomic multi-hop routes with overall slippage check**:
   ```rust
   pub fn multi_hop_swap(ctx: Context<MultiHop>, amount_in: u64, min_final_out: u64) -> Result<()> {
       // Individual hops don't need slippage — final output is checked
       let mid = swap_a_to_b(amount_in)?;    // No slippage check needed here
       let out = swap_b_to_c(mid)?;           // No slippage check needed here
       require!(out >= min_final_out, ErrorCode::SlippageExceeded); // Overall check
       Ok(())
   }
   ```

---

## Remediation

### Add `min_amount_out` Parameter and Enforce It

```rust
pub fn swap(
    ctx: Context<Swap>,
    amount_in: u64,
    min_amount_out: u64, // Caller specifies minimum acceptable output
) -> Result<()> {
    let pool = &mut ctx.accounts.pool;

    let amount_out = (amount_in as u128)
        .checked_mul(pool.reserve_out as u128)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(
            (pool.reserve_in as u128)
                .checked_add(amount_in as u128)
                .ok_or(ErrorCode::MathOverflow)?
        )
        .ok_or(ErrorCode::DivisionByZero)?;

    let amount_out: u64 = amount_out.try_into()
        .map_err(|_| ErrorCode::MathOverflow)?;

    // SAFE: enforce minimum output — fails if sandwiched
    require!(amount_out >= min_amount_out, ErrorCode::SlippageExceeded);

    pool.reserve_in = pool.reserve_in.checked_add(amount_in)
        .ok_or(ErrorCode::MathOverflow)?;
    pool.reserve_out = pool.reserve_out.checked_sub(amount_out)
        .ok_or(ErrorCode::MathUnderflow)?;

    token::transfer(deposit_ctx, amount_in)?;
    token::transfer(withdraw_ctx, amount_out)?;

    Ok(())
}
```

### Slippage for Liquidity Operations

```rust
pub fn add_liquidity(
    ctx: Context<AddLiquidity>,
    amount_a: u64,
    amount_b: u64,
    min_lp_tokens: u64, // Minimum LP tokens to receive
) -> Result<()> {
    let pool = &mut ctx.accounts.pool;
    let lp_tokens = calculate_lp_tokens(amount_a, amount_b, pool)?;

    // SAFE: enforce minimum LP tokens minted
    require!(lp_tokens >= min_lp_tokens, ErrorCode::SlippageExceeded);

    token::transfer(deposit_a_ctx, amount_a)?;
    token::transfer(deposit_b_ctx, amount_b)?;
    token::mint_to(mint_ctx, lp_tokens)?;

    Ok(())
}

pub fn remove_liquidity(
    ctx: Context<RemoveLiquidity>,
    lp_tokens: u64,
    min_amount_a: u64, // Minimum token A to receive
    min_amount_b: u64, // Minimum token B to receive
) -> Result<()> {
    let pool = &mut ctx.accounts.pool;
    let (amount_a, amount_b) = calculate_withdrawal(lp_tokens, pool)?;

    // SAFE: enforce minimum tokens returned for both assets
    require!(amount_a >= min_amount_a, ErrorCode::SlippageExceededTokenA);
    require!(amount_b >= min_amount_b, ErrorCode::SlippageExceededTokenB);

    token::burn(burn_ctx, lp_tokens)?;
    token::transfer(withdraw_a_ctx, amount_a)?;
    token::transfer(withdraw_b_ctx, amount_b)?;

    Ok(())
}
```

### Forward Slippage in CPI Calls

```rust
pub fn route_swap(
    ctx: Context<RouteSwap>,
    amount_in: u64,
    min_amount_out: u64, // Accept from caller and forward to AMM
) -> Result<()> {
    // SAFE: forward the caller's slippage protection to the underlying AMM
    let swap_ix = create_swap_instruction(
        ctx.accounts.amm_program.key(),
        amount_in,
        min_amount_out, // Forwarded — AMM enforces it
    );

    invoke(&swap_ix, &[...])?;

    Ok(())
}
```

### Deadline Parameter (Additional Protection)

```rust
pub fn swap_with_deadline(
    ctx: Context<Swap>,
    amount_in: u64,
    min_amount_out: u64,
    deadline: i64, // Unix timestamp — tx fails if executed after deadline
) -> Result<()> {
    let clock = Clock::get()?;

    // SAFE: reject if transaction was delayed (e.g., held by validator for MEV)
    require!(clock.unix_timestamp <= deadline, ErrorCode::TransactionExpired);

    let amount_out = calculate_output(amount_in, &ctx.accounts.pool)?;
    require!(amount_out >= min_amount_out, ErrorCode::SlippageExceeded);

    // ... execute swap
    Ok(())
}
```

### Error Codes

```rust
#[error_code]
pub enum ErrorCode {
    #[msg("Output amount below minimum — slippage exceeded")]
    SlippageExceeded,
    #[msg("Token A output below minimum")]
    SlippageExceededTokenA,
    #[msg("Token B output below minimum")]
    SlippageExceededTokenB,
    #[msg("Transaction deadline exceeded")]
    TransactionExpired,
}
```
