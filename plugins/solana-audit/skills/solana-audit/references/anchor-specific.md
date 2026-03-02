# Anchor Framework-Specific Vulnerabilities

Gotchas and pitfalls specific to programs built with the Anchor framework. Based on research by Zellic, Neodyme, and common audit findings.

---

## 1. PDA Seed Collisions in Anchor

**Risk:** Two logically different accounts derive to the same PDA because seeds aren't sufficiently unique.

**Common pattern:**
```rust
#[account(
    seeds = [b"user_stats"],
    bump
)]
pub user_stats: Account<'info, UserStats>,
```
This creates ONE global PDA. All users share it.

**Fix:**
```rust
#[account(
    seeds = [b"user_stats", user.key().as_ref()],
    bump
)]
pub user_stats: Account<'info, UserStats>,
```

**What to check:**
- Every `seeds = [...]` constraint includes enough discriminating components
- Multi-entity PDAs include the entity's unique identifier in seeds
- Seeds don't use user-controlled data that could collide (e.g., truncated strings)

---

## 2. `ctx.remaining_accounts` Misuse

**Risk:** `remaining_accounts` bypass Anchor's account validation. Any account can be injected.

**Common pattern:**
```rust
pub fn process_batch(ctx: Context<ProcessBatch>) -> Result<()> {
    for account in ctx.remaining_accounts.iter() {
        // DANGEROUS: no type/owner/signer validation
        let data = MyStruct::try_from_slice(&account.data.borrow())?;
        // ... operates on unvalidated data
    }
}
```

**Fix:**
```rust
for account in ctx.remaining_accounts.iter() {
    // Validate owner
    require!(account.owner == &MY_PROGRAM_ID, MyError::InvalidOwner);
    // Validate discriminator
    let data = Account::<MyStruct>::try_from(account)?;
    // ... now safe to use
}
```

**What to check:**
- Every use of `remaining_accounts` validates owner, type, and relevant constraints
- Consider whether the variable-length pattern is necessary or if fixed accounts suffice

---

## 3. Confused Deputy via CPI

**Risk:** Your program (the "deputy") makes a CPI call on behalf of a user, but the call does something the user didn't intend because accounts are swapped.

**Common pattern:**
```rust
// User wants to transfer from their account A to vault B
// Attacker passes: source = victim's account, dest = attacker's account
token::transfer(
    CpiContext::new(
        token_program.to_account_info(),
        Transfer {
            from: source.to_account_info(),  // user-controlled
            to: destination.to_account_info(), // user-controlled!
            authority: program_pda.to_account_info(),
        },
    ),
    amount,
)?;
```

**Fix:**
```rust
#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(
        mut,
        token::mint = vault.mint,
        token::authority = user,  // source must be user-owned
    )]
    pub user_token: Account<'info, TokenAccount>,
    #[account(
        mut,
        seeds = [b"vault", vault.mint.as_ref()],
        bump,
    )]
    pub vault_token: Account<'info, TokenAccount>, // dest is program-controlled PDA
}
```

**What to check:**
- CPI destination accounts are PDA-derived or hardcoded, not user-supplied
- Token transfer sources are validated to be owned by the signer
- CPI authority matches the intended scope of the operation

---

## 4. Account Reloading After CPI

**Risk:** After a CPI call, account data may have changed, but Anchor's deserialized struct still holds stale values.

**Common pattern:**
```rust
pub fn swap(ctx: Context<Swap>) -> Result<()> {
    let balance_before = ctx.accounts.vault.amount; // Read before CPI

    // CPI: transfer tokens into vault
    token::transfer(cpi_ctx, deposit_amount)?;

    // BUG: vault.amount is stale — still shows balance_before
    let balance_after = ctx.accounts.vault.amount;
    let received = balance_after - balance_before; // Always 0!
}
```

**Fix:**
```rust
// Reload account data after CPI
ctx.accounts.vault.reload()?;
let balance_after = ctx.accounts.vault.amount; // Now reflects CPI changes
```

**What to check:**
- After every CPI that modifies a shared account, the account is reloaded
- Business logic that depends on pre/post CPI state uses reloaded values
- This is especially critical for balance-tracking patterns (deposit/swap)

---

## 5. `init_if_needed` Pitfalls

**Risk:** `init_if_needed` will initialize an account if it doesn't exist. This can be exploited if an attacker can front-run to initialize with malicious parameters.

**Common pattern:**
```rust
#[account(
    init_if_needed,
    payer = user,
    space = 8 + UserStats::INIT_SPACE,
    seeds = [b"stats", user.key().as_ref()],
    bump,
)]
pub user_stats: Account<'info, UserStats>,
```

**Risks:**
- Attacker initializes the account before the intended user, setting different initial values
- Re-initialization vectors if discriminator check has edge cases

**Fix:**
- Prefer separate `initialize` instructions with explicit access control
- If using `init_if_needed`, ensure all initialized fields are deterministic (derived from seeds/context, not user input)

---

## 6. False Sense of Security from Anchor Constraints

**Risk:** Developers assume Anchor handles all security. In reality, Anchor only validates what's declared.

**Missing checks that Anchor does NOT auto-add:**
- Business logic validation (amount > 0, valid state transitions)
- Cross-account relationships (source.owner == destination.owner)
- Time-based constraints (lockup periods, cooldowns)
- Economic constraints (slippage, min/max amounts)

**What to check:**
- Don't assume "Anchor handles it" — verify each constraint is explicitly declared
- Check that `constraint = ...` or `require!()` covers all business rules
- Look for instructions that seem "simple" — they often miss edge cases

---

## 7. Anchor Account Discriminator Limitations

**Risk:** Anchor's 8-byte discriminator prevents type cosplay between accounts within the same program but not cross-program.

**Attack scenario:**
1. Attacker deploys a malicious program with account type `FakeVault`
2. `FakeVault` has same 8-byte discriminator (SHA256("account:Vault")[:8]) as target program's `Vault`
3. Attacker passes their `FakeVault` account where `Vault` is expected

**Defense:** Anchor's `Account<'info, T>` checks both discriminator AND owner. The owner check prevents cross-program type cosplay. This is only a risk when using raw `AccountInfo` with manual deserialization.

**What to check:**
- Every deserialized account uses `Account<'info, T>` (not raw `AccountInfo`)
- If `AccountInfo` is used, both discriminator AND owner are manually verified

---

## 8. `close` Constraint and Account Revival

**Risk:** Anchor's `close = target` zeroes data and transfers lamports, but in the same transaction, a later instruction could re-fund and re-initialize the account.

**Defense:**
```rust
#[account(
    mut,
    close = recipient,
    has_one = authority,
)]
pub account_to_close: Account<'info, MyAccount>,
```

Anchor sets the discriminator to a "closed" marker. Any attempt to re-use the account in the same program will fail the discriminator check.

**What to check:**
- Closed accounts can't be re-initialized by a different program in the same transaction
- If custom closure logic is used (not Anchor's `close`), verify data is zeroed and discriminator is invalidated

---

## Summary Checklist for Anchor Programs

| Check | What to look for |
|-------|-----------------|
| PDA seeds unique? | Every `seeds` includes enough discriminating components |
| `remaining_accounts` validated? | Owner, type, and constraints checked for each |
| CPI destinations constrained? | Dest accounts are PDAs or validated, not user-supplied |
| Post-CPI reload? | `account.reload()` after any CPI that modifies shared state |
| No `init_if_needed` abuse? | Prefer explicit init instructions |
| Business logic validated? | Don't rely solely on Anchor constraints |
| No raw `AccountInfo` deserialization? | Use `Account<'info, T>` for type + owner safety |
| Account closure safe? | Use Anchor `close` constraint, check revival vectors |
