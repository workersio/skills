# M-4: Rounding Errors [MEDIUM]

Integer division in share/LP token calculations can round to zero, enabling a class of drain attacks first documented by Neodyme. When a deposit is too small to mint even 1 LP token (result truncates to 0), the deposited tokens enter the pool but no shares are issued. Repeated zero-mint deposits inflate the pool value without diluting shares, allowing the attacker (who holds existing shares) to withdraw more than they deposited.

---

## Preconditions

- Program uses a share-based accounting model (LP tokens, vault shares, staking shares)
- Share calculation involves integer division: `shares = deposit * total_shares / total_pool_value`
- No minimum deposit or minimum share output is enforced
- The pool is in a state where deposits can produce zero shares (e.g., pool value is large relative to share supply, or the pool was seeded with an imbalanced ratio)

---

## Vulnerable Pattern

### Neodyme-Style Zero-Amount LP Token Drain

```rust
pub fn deposit(ctx: Context<Deposit>, deposit_amount: u64) -> Result<()> {
    let pool = &mut ctx.accounts.pool;

    let lp_tokens_to_mint: u64 = if pool.lp_supply == 0 {
        deposit_amount // First deposit: 1:1 ratio
    } else {
        // VULNERABLE: if deposit_amount * lp_supply / total_pool rounds to 0,
        // tokens enter the pool but no LP tokens are minted
        deposit_amount * pool.lp_supply / pool.total_pool_value
    };

    // Deposit is accepted even when lp_tokens_to_mint == 0!
    token::transfer(deposit_cpi_ctx, deposit_amount)?;
    pool.total_pool_value += deposit_amount;

    // Mints 0 LP tokens — depositor gets nothing, pool value increases
    token::mint_to(mint_cpi_ctx, lp_tokens_to_mint)?;
    pool.lp_supply += lp_tokens_to_mint;

    Ok(())
}
```

**Attack scenario:**
1. Attacker deposits a large initial amount, receives LP tokens at 1:1
2. Attacker (or accomplice) makes many small deposits that each produce 0 LP tokens
3. Pool value grows but LP supply stays constant
4. Attacker withdraws — their unchanged share count now represents a larger fraction of the inflated pool

### Withdrawal Rounding in Wrong Direction

```rust
pub fn withdraw(ctx: Context<Withdraw>, shares_to_burn: u64) -> Result<()> {
    let pool = &mut ctx.accounts.pool;

    // VULNERABLE: truncation rounds DOWN — user gets slightly fewer tokens
    // This is actually the SAFE direction for withdrawals
    let tokens_out = shares_to_burn * pool.total_pool_value / pool.lp_supply;

    // BUT if the rounding instead favors the user (rounds UP):
    // DANGEROUS: user extracts more than their proportional share
    // Over many small withdrawals, pool is drained
    let tokens_out_bad = (shares_to_burn * pool.total_pool_value + pool.lp_supply - 1)
        / pool.lp_supply;

    Ok(())
}
```

### First-Depositor Manipulation

```rust
pub fn initialize_and_deposit(ctx: Context<InitPool>, amount: u64) -> Result<()> {
    let pool = &mut ctx.accounts.pool;

    // VULNERABLE: First depositor gets 1:1 LP tokens, then donates tokens
    // directly to the pool (not through deposit instruction) to inflate
    // total_pool_value without increasing lp_supply
    pool.lp_supply = amount;
    pool.total_pool_value = amount;

    // After direct donation of X tokens to pool token account:
    // total_pool_value = amount + X (observed via token account balance)
    // lp_supply = amount (unchanged)
    // Next depositor needs deposit_amount * amount / (amount + X) >= 1
    // If X is large, only very large deposits produce non-zero LP tokens

    Ok(())
}
```

### Reward Distribution Rounding

```rust
pub fn claim_rewards(ctx: Context<ClaimRewards>) -> Result<()> {
    let pool = &ctx.accounts.pool;
    let staker = &mut ctx.accounts.staker;

    // VULNERABLE: if staker.shares * reward_per_share has remainder,
    // truncation loses fractional rewards each claim
    // Attacker claims frequently with small stake to accumulate rounding dust
    let reward = staker.shares * pool.accumulated_reward_per_share
        / PRECISION_FACTOR;
    let pending = reward - staker.reward_debt;

    Ok(())
}
```

---

## Detection Heuristics

### Grep Patterns

```
# Find share/LP token calculations
lp_supply
total_shares
total_supply
shares *
mint_to
lp_tokens

# Find division in share calculations
/ pool
/ total
/ supply
/ lp_

# Find deposit/mint patterns without zero-check
mint_to
deposit_amount *
```

### What to Search

1. **Find all share/LP token minting calculations**: Look for `deposit_amount * total_shares / total_value` patterns
2. **Check for zero-result guard**: After the division, is there a `require!(result > 0)` check?
3. **Check rounding direction**: In deposits, truncation should round DOWN (fewer shares minted — safe). In withdrawals, truncation should also round DOWN (fewer tokens returned — safe for the pool).
4. **Check first-depositor logic**: Is there protection against the first depositor manipulating the initial ratio?
5. **Check for direct token transfers**: Can someone send tokens directly to the pool account (bypassing the deposit instruction) to inflate pool value?
6. **Check minimum deposit/withdrawal amounts**: Are there minimums that prevent zero-result divisions?

### Risk Indicators

- Share minting formula with no zero-check on the result
- Withdrawal formula that rounds UP (favoring the withdrawer)
- No minimum deposit amount enforced
- Pool allows direct token transfers (anyone can call SPL transfer to the pool's token account)
- First depositor receives LP tokens at a fixed ratio without dead-share mechanism

---

## False Positives

1. **Zero-amount check exists after calculation**:
   ```rust
   let lp_tokens = deposit_amount * pool.lp_supply / pool.total_value;
   require!(lp_tokens > 0, ErrorCode::DepositTooSmall); // Protected
   ```

2. **Rounding always against the user (safe direction)**:
   ```rust
   // Deposits: user receives fewer shares (floor division) — safe
   let shares = deposit * total_shares / total_deposits; // rounds DOWN

   // Withdrawals: user receives fewer tokens (floor division) — safe
   let tokens = shares * total_deposits / total_shares; // rounds DOWN
   ```

3. **Dead shares / minimum liquidity mechanism**:
   ```rust
   // First deposit permanently locks a minimum number of LP tokens
   // Prevents first-depositor manipulation
   if pool.lp_supply == 0 {
       let lp_tokens = amount;
       let dead_shares = 1000; // Permanently locked
       pool.lp_supply = lp_tokens;
       token::burn(burn_ctx, dead_shares)?; // or send to dead address
   }
   ```

4. **Minimum deposit/withdrawal amount is enforced**:
   ```rust
   require!(deposit_amount >= MIN_DEPOSIT, ErrorCode::BelowMinimum);
   // MIN_DEPOSIT is large enough that zero-share-mint is impossible
   ```

5. **Fixed-point math library used for share calculations**:
   ```rust
   // Using a fixed-point library that handles rounding explicitly
   let shares = FixedPoint::from(deposit)
       .checked_mul(total_shares)?
       .checked_div(total_value)?
       .floor(); // Explicit rounding direction
   ```

---

## Remediation

### Require Non-Zero Share Output

```rust
pub fn deposit(ctx: Context<Deposit>, deposit_amount: u64) -> Result<()> {
    let pool = &mut ctx.accounts.pool;

    let lp_tokens_to_mint: u64 = if pool.lp_supply == 0 {
        deposit_amount
    } else {
        (deposit_amount as u128)
            .checked_mul(pool.lp_supply as u128)
            .ok_or(ErrorCode::MathOverflow)?
            .checked_div(pool.total_pool_value as u128)
            .ok_or(ErrorCode::DivisionByZero)?
            .try_into()
            .map_err(|_| ErrorCode::MathOverflow)?
    };

    // SAFE: reject deposits that produce zero LP tokens
    require!(lp_tokens_to_mint > 0, ErrorCode::DepositTooSmall);

    token::transfer(deposit_cpi_ctx, deposit_amount)?;
    pool.total_pool_value = pool.total_pool_value
        .checked_add(deposit_amount)
        .ok_or(ErrorCode::MathOverflow)?;
    token::mint_to(mint_cpi_ctx, lp_tokens_to_mint)?;
    pool.lp_supply = pool.lp_supply
        .checked_add(lp_tokens_to_mint)
        .ok_or(ErrorCode::MathOverflow)?;

    Ok(())
}
```

### Round Against the User in Both Directions

```rust
/// Deposit: round DOWN shares minted (user gets fewer shares)
pub fn shares_for_deposit(deposit: u64, total_value: u64, total_shares: u64) -> Result<u64> {
    if total_shares == 0 {
        return Ok(deposit);
    }
    // Floor division — rounds down, fewer shares for depositor (safe)
    let shares: u64 = (deposit as u128)
        .checked_mul(total_shares as u128)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(total_value as u128)
        .ok_or(ErrorCode::DivisionByZero)?
        .try_into()
        .map_err(|_| ErrorCode::MathOverflow)?;

    require!(shares > 0, ErrorCode::DepositTooSmall);
    Ok(shares)
}

/// Withdraw: round DOWN tokens returned (user gets fewer tokens)
pub fn tokens_for_withdrawal(shares: u64, total_value: u64, total_shares: u64) -> Result<u64> {
    // Floor division — rounds down, fewer tokens for withdrawer (safe)
    let tokens: u64 = (shares as u128)
        .checked_mul(total_value as u128)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(total_shares as u128)
        .ok_or(ErrorCode::DivisionByZero)?
        .try_into()
        .map_err(|_| ErrorCode::MathOverflow)?;

    require!(tokens > 0, ErrorCode::WithdrawalTooSmall);
    Ok(tokens)
}
```

### Dead Shares for First Deposit Protection

```rust
pub fn initialize_pool(ctx: Context<InitPool>, initial_deposit: u64) -> Result<()> {
    let pool = &mut ctx.accounts.pool;

    require!(initial_deposit >= MINIMUM_LIQUIDITY, ErrorCode::InsufficientInitialDeposit);

    // Lock MINIMUM_LIQUIDITY shares permanently to prevent first-depositor attacks
    let dead_shares: u64 = 1_000; // Permanently unclaimable
    let user_shares = initial_deposit
        .checked_sub(dead_shares)
        .ok_or(ErrorCode::MathUnderflow)?;

    pool.total_pool_value = initial_deposit;
    pool.lp_supply = initial_deposit; // total includes dead shares
    // dead_shares are "owned" by address(0) or burned — never redeemable

    // Mint user_shares to the depositor
    token::mint_to(mint_cpi_ctx, user_shares)?;

    Ok(())
}

const MINIMUM_LIQUIDITY: u64 = 10_000;
```

### Enforce Minimum Deposit Amount

```rust
pub fn deposit(ctx: Context<Deposit>, deposit_amount: u64) -> Result<()> {
    require!(deposit_amount >= MIN_DEPOSIT_AMOUNT, ErrorCode::BelowMinDeposit);
    // ... rest of deposit logic
    Ok(())
}

// Set high enough that deposit_amount * lp_supply / total_value >= 1
// for any reasonable pool state
const MIN_DEPOSIT_AMOUNT: u64 = 1_000;
```
