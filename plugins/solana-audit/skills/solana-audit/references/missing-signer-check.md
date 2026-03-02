# A-1: Missing Signer Check

**Severity:** CRITICAL
**Category:** Authentication & Authorization
**Taxonomy ID:** A-1

---

## Preconditions

All of the following must be true for this vulnerability to be exploitable:

1. An account is used as an **authority** for a privileged action (transfer, withdrawal, state mutation, admin operation)
2. The instruction does **not** verify that the account has signed the transaction
3. The account is **not** a PDA (PDAs cannot sign transactions directly; they authorize via `invoke_signed`)

If any of these conditions is false, the finding is either a false positive or a different vulnerability class.

---

## Vulnerable Pattern

### Native Solana (without Anchor)

```rust
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    program::invoke,
    program_error::ProgramError,
    pubkey::Pubkey,
};

pub fn process_withdraw(
    _program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let authority = next_account_info(accounts_iter)?;     // <-- VULNERABLE: no is_signer check
    let vault = next_account_info(accounts_iter)?;
    let destination = next_account_info(accounts_iter)?;
    let token_program = next_account_info(accounts_iter)?;

    // Deserialize vault and check authority matches
    let vault_data = Vault::try_from_slice(&vault.data.borrow())?;
    if authority.key != &vault_data.authority {
        return Err(ProgramError::InvalidAccountData);
    }

    // Proceeds to transfer without verifying authority actually signed
    // Any caller can pass the authority pubkey as an unsigned account
    invoke(
        &spl_token::instruction::transfer(
            token_program.key,
            &vault_data.token_account,
            destination.key,
            authority.key,
            &[],
            amount,
        )?,
        &[vault.clone(), destination.clone(), authority.clone()],
    )?;

    Ok(())
}
```

### Anchor Framework

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct Withdraw<'info> {
    /// VULNERABLE: AccountInfo does not enforce signer verification.
    /// Anyone can pass any pubkey here without signing.
    /// CHECK: authority is not validated as signer
    pub authority: AccountInfo<'info>,

    #[account(
        mut,
        has_one = authority,  // This checks key match but NOT that authority signed
    )]
    pub vault: Account<'info, Vault>,

    #[account(mut)]
    pub destination: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}

pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
    // has_one checks vault.authority == authority.key()
    // But authority could be anyone's pubkey passed unsigned
    token::transfer(
        CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.vault.to_account_info(),
                to: ctx.accounts.destination.to_account_info(),
                authority: ctx.accounts.authority.to_account_info(),
            },
        ),
        amount,
    )?;
    Ok(())
}
```

### Also vulnerable: UncheckedAccount alias

```rust
#[derive(Accounts)]
pub struct Withdraw<'info> {
    /// VULNERABLE: UncheckedAccount is just an alias for AccountInfo
    /// CHECK: This is unchecked and not validated as signer
    pub authority: UncheckedAccount<'info>,

    #[account(mut, has_one = authority)]
    pub vault: Account<'info, Vault>,
}
```

---

## Detection Heuristics

### Step 1: Find authority accounts

Search for accounts that serve as authorities, admins, or owners in instruction handlers.

**Grep patterns:**
```
# Native programs
grep -n "authority\|admin\|owner\|payer\|creator" processor.rs

# Anchor — find AccountInfo or UncheckedAccount used in Accounts structs
grep -n "AccountInfo<'info>\|UncheckedAccount<'info>" lib.rs
```

### Step 2: Check signer verification

For each authority account found, verify it is validated as a signer.

**Native — look for is_signer check:**
```
# Must find a corresponding is_signer check for every authority
grep -n "is_signer" processor.rs
```

Expected safe pattern:
```rust
if !authority.is_signer {
    return Err(ProgramError::MissingRequiredSignature);
}
```

**Anchor — check account type in the Accounts struct:**
```
# Safe: Signer<'info> enforces signer automatically
# Unsafe: AccountInfo<'info> or UncheckedAccount<'info> used for authority
grep -n "pub authority.*Signer\|pub admin.*Signer" lib.rs
```

### Step 3: Trace usage of the authority account

Follow the authority account through the instruction handler. Determine if it is used to:
- Authorize a token transfer (passed as `authority` to SPL Token CPI)
- Gate access to a privileged operation (state mutation, parameter update)
- Sign a CPI call (passed in `invoke_signed` signer seeds)

If the authority is used for any privileged action without signer verification, flag it.

### Step 4: Check CPI context

If the authority is passed into a CPI call, check if the CPI itself enforces the signer requirement. SPL Token's `transfer` instruction requires the authority to be a signer, so the CPI will fail at runtime. However, if the program uses `invoke_signed` with PDA seeds that include the authority, the signer check may be bypassed at the CPI level.

```rust
// This CPI will fail if authority is not a signer — SPL Token enforces it
// But the error message is confusing and the check should be explicit
invoke(
    &spl_token::instruction::transfer(..., authority.key, ...)?,
    &[...],
)?;
```

---

## False Positives

### 1. PDA accounts used as authority

PDAs cannot sign transactions directly. They authorize via `invoke_signed` with seeds. A PDA authority does not need an `is_signer` check on the account itself.

```rust
// This is SAFE — PDA authority signs via invoke_signed, not is_signer
let seeds = &[b"vault", vault.mint.as_ref(), &[vault.bump]];
invoke_signed(
    &spl_token::instruction::transfer(
        token_program.key,
        &vault.token_account,
        destination.key,
        &vault_pda.key(),  // PDA as authority
        &[],
        amount,
    )?,
    &[vault_token.clone(), destination.clone(), vault_pda.clone()],
    &[seeds],
)?;
```

### 2. Read-only public data accounts

Accounts that serve as read-only data sources (price feeds, configuration, public metadata) do not need signer checks because they do not authorize any action.

```rust
// SAFE — oracle is read-only, not authorizing anything
/// CHECK: Oracle account is only read, not used as authority
pub oracle: AccountInfo<'info>,
```

### 3. Signer verified in a separate preceding instruction

Some protocols use a two-instruction pattern where the first instruction verifies the signer and writes a temporary "authorization" state, and the second instruction reads that state. In this case, the second instruction does not need a direct signer check if it validates the authorization state.

```rust
// Instruction 1: verify_signer — checks is_signer, writes AuthRecord
// Instruction 2: execute_action — reads AuthRecord, no direct signer check needed
// This is SAFE if AuthRecord is properly scoped (per-transaction, time-limited)
```

### 4. Anchor `Signer<'info>` already applied

If the account type is `Signer<'info>`, Anchor enforces the signer check automatically at deserialization time. No additional check is needed.

```rust
// SAFE — Anchor enforces signer check
pub authority: Signer<'info>,
```

---

## Remediation

### Native Solana

Add an explicit `is_signer` check immediately after obtaining the authority account:

```rust
pub fn process_withdraw(
    _program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let authority = next_account_info(accounts_iter)?;
    let vault = next_account_info(accounts_iter)?;
    let destination = next_account_info(accounts_iter)?;
    let token_program = next_account_info(accounts_iter)?;

    // FIX: Verify authority has signed the transaction
    if !authority.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let vault_data = Vault::try_from_slice(&vault.data.borrow())?;
    if authority.key != &vault_data.authority {
        return Err(ProgramError::InvalidAccountData);
    }

    invoke(
        &spl_token::instruction::transfer(
            token_program.key,
            &vault_data.token_account,
            destination.key,
            authority.key,
            &[],
            amount,
        )?,
        &[vault.clone(), destination.clone(), authority.clone()],
    )?;

    Ok(())
}
```

### Anchor Framework

Change the account type from `AccountInfo<'info>` or `UncheckedAccount<'info>` to `Signer<'info>`:

```rust
#[derive(Accounts)]
pub struct Withdraw<'info> {
    // FIX: Signer<'info> enforces that authority must sign the transaction
    pub authority: Signer<'info>,

    #[account(
        mut,
        has_one = authority,  // Now checks BOTH key match AND signer status
    )]
    pub vault: Account<'info, Vault>,

    #[account(mut)]
    pub destination: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}
```

### Key principle

Every account that authorizes a privileged action must satisfy **two** checks:
1. **Signer check** — the account has signed the transaction (`is_signer` or `Signer<'info>`)
2. **Key comparison** — the account's pubkey matches the expected authority stored in program state (`has_one` or manual key comparison)

Missing either check is a distinct vulnerability: missing signer = A-1, missing key comparison = A-3.

---

## References

- [Solana Documentation: Signers](https://solana.com/docs/core/transactions#signatures)
- [Anchor Signer type](https://docs.rs/anchor-lang/latest/anchor_lang/accounts/signer/struct.Signer.html)
- Taxonomy: A-1 in `vulnerability-taxonomy.md`
- Related: A-3 (Missing Authority Validation) is the complementary check
