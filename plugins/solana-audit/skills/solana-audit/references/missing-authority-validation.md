# A-3: Missing Authority Validation

**Severity:** HIGH
**Category:** Authentication & Authorization
**Taxonomy ID:** A-3

---

## Preconditions

All of the following must be true for this vulnerability to be exploitable:

1. An account is verified as a **signer** (the `is_signer` check or `Signer<'info>` type is present)
2. The instruction does **not** compare the signer's pubkey to the **expected authority** stored in program state
3. The instruction performs a **privileged action** that should be restricted to a specific authority

This vulnerability is distinct from A-1 (Missing Signer Check). In A-1, no signer check exists at all. In A-3, the signer check exists but it only proves that *someone* signed -- it does not prove that the *correct* entity signed.

---

## Vulnerable Pattern

### Native Solana: Signer check without key comparison

```rust
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    program_error::ProgramError,
    pubkey::Pubkey,
};

pub fn process_withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let authority = next_account_info(accounts_iter)?;
    let vault_account = next_account_info(accounts_iter)?;
    let destination = next_account_info(accounts_iter)?;

    // Signer check is present -- proves SOMEONE signed
    if !authority.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    // Owner check is present
    if vault_account.owner != program_id {
        return Err(ProgramError::IncorrectProgramId);
    }

    let vault_data = Vault::try_from_slice(&vault_account.data.borrow())?;

    // VULNERABLE: Never checks that authority.key == vault_data.authority
    // Any signer can withdraw from any vault!
    transfer_from_vault(&vault_data, destination.key, amount)?;

    Ok(())
}
```

### Anchor: Signer type without has_one or constraint

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct Withdraw<'info> {
    // Signer check is present -- Anchor enforces that authority signed
    pub authority: Signer<'info>,

    // VULNERABLE: No has_one = authority constraint!
    // Any signer can call this on any vault.
    #[account(mut)]
    pub vault: Account<'info, Vault>,

    #[account(mut)]
    pub destination: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}

pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
    // vault.authority is never compared to ctx.accounts.authority
    let vault = &ctx.accounts.vault;

    token::transfer(
        CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: vault.to_account_info(),
                to: ctx.accounts.destination.to_account_info(),
                authority: ctx.accounts.authority.to_account_info(),
            },
        ),
        amount,
    )?;

    Ok(())
}
```

### Vulnerable: Key comparison on wrong field

```rust
pub fn process_update_config(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    new_fee: u64,
) -> ProgramResult {
    let authority = next_account_info(accounts_iter)?;
    let config_account = next_account_info(accounts_iter)?;

    if !authority.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let config = Config::try_from_slice(&config_account.data.borrow())?;

    // VULNERABLE: Compares to the wrong field!
    // Checks against config.fee_recipient instead of config.admin
    if authority.key != &config.fee_recipient {
        return Err(ProgramError::InvalidAccountData);
    }

    // Fee recipient can now change protocol configuration
    let mut config_mut = Config::try_from_slice(&config_account.data.borrow_mut())?;
    config_mut.fee = new_fee;
    config_mut.serialize(&mut &mut config_account.data.borrow_mut()[..])?;

    Ok(())
}
```

---

## Detection Heuristics

### Step 1: Find all signer checks

Locate every instruction that verifies a signer.

**Grep patterns:**
```
# Native
grep -n "is_signer" processor.rs

# Anchor — find Signer type accounts
grep -n "Signer<'info>" lib.rs
```

### Step 2: Verify key comparison to stored state

For each signer, verify that its public key is compared to the expected authority stored in the relevant program account.

**Native — look for key comparison:**
```
grep -n "\.key\s*!=\|\.key\s*==" processor.rs
```

Expected safe pattern:
```rust
if !authority.is_signer {
    return Err(ProgramError::MissingRequiredSignature);
}
if authority.key != &vault_data.authority {
    return Err(ProgramError::InvalidAccountData);
}
```

**Anchor — look for has_one or constraint:**
```
grep -n "has_one\|constraint.*authority\|constraint.*admin\|constraint.*owner" lib.rs
```

Expected safe pattern:
```rust
#[account(mut, has_one = authority)]
pub vault: Account<'info, Vault>,
```

### Step 3: Verify the correct field is compared

Even when a key comparison exists, verify it compares against the **correct authority field** on the correct account. Common mistakes:
- Comparing to the wrong field (e.g., `fee_recipient` instead of `admin`)
- Comparing to the wrong account (e.g., checking authority against Pool A when operating on Pool B)
- Comparing to an uninitialized or attacker-controllable field

---

## False Positives

### 1. Open/permissionless instructions

Some instructions are intentionally callable by anyone. No authority validation is needed.

```rust
// SAFE — deposit is permissionless; anyone can deposit their own tokens
#[derive(Accounts)]
pub struct Deposit<'info> {
    pub depositor: Signer<'info>,  // Signer is the depositor, not a privileged authority

    #[account(
        mut,
        token::authority = depositor,  // Depositor must own the source tokens
    )]
    pub user_token_account: Account<'info, TokenAccount>,

    #[account(mut)]
    pub vault_token_account: Account<'info, TokenAccount>,
}
```

### 2. PDA-derived authority validated by seeds

If the authority is a PDA derived from specific seeds, and the PDA derivation is validated, the authority is implicitly validated by the seed constraints.

```rust
// SAFE — authority is validated by PDA derivation, not by key comparison
#[derive(Accounts)]
pub struct VaultAction<'info> {
    #[account(
        seeds = [b"vault_authority", vault.key().as_ref()],
        bump = vault.authority_bump,
    )]
    /// CHECK: PDA derivation validates this is the correct authority
    pub authority: AccountInfo<'info>,

    #[account(mut)]
    pub vault: Account<'info, Vault>,
}
```

### 3. Authority validated through a different mechanism

The authority may be validated through a mechanism other than direct key comparison -- for example, through a governance vote, multisig threshold, or time-locked proposal.

```rust
// SAFE — authority is validated via governance proposal execution
pub fn execute_proposal(ctx: Context<ExecuteProposal>) -> Result<()> {
    let proposal = &ctx.accounts.proposal;
    require!(proposal.status == ProposalStatus::Approved, ErrorCode::NotApproved);
    require!(proposal.executor == ctx.accounts.executor.key(), ErrorCode::WrongExecutor);
    // ...
}
```

### 4. Signer used only for paying transaction fees

If a `Signer` account is used solely as a `payer` for account creation and does not authorize any privileged action, no authority validation is needed.

```rust
// SAFE — payer is just paying for account creation, not authorizing anything
#[derive(Accounts)]
pub struct CreateAccount<'info> {
    #[account(mut)]
    pub payer: Signer<'info>,

    #[account(
        init,
        payer = payer,
        space = 8 + MyAccount::INIT_SPACE,
    )]
    pub new_account: Account<'info, MyAccount>,

    pub system_program: Program<'info, System>,
}
```

---

## Remediation

### Native Solana

Add a key comparison after the signer check:

```rust
pub fn process_withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let authority = next_account_info(accounts_iter)?;
    let vault_account = next_account_info(accounts_iter)?;
    let destination = next_account_info(accounts_iter)?;

    // Step 1: Verify signer (A-1 check)
    if !authority.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    // Step 2: Verify owner (A-2 check)
    if vault_account.owner != program_id {
        return Err(ProgramError::IncorrectProgramId);
    }

    let vault_data = Vault::try_from_slice(&vault_account.data.borrow())?;

    // FIX Step 3: Verify authority matches stored authority (A-3 check)
    if authority.key != &vault_data.authority {
        return Err(ProgramError::InvalidAccountData);
    }

    transfer_from_vault(&vault_data, destination.key, amount)?;
    Ok(())
}
```

### Anchor Framework

Add `has_one` constraint to the account that stores the authority:

```rust
#[derive(Accounts)]
pub struct Withdraw<'info> {
    pub authority: Signer<'info>,

    // FIX: has_one = authority checks vault.authority == authority.key()
    #[account(
        mut,
        has_one = authority @ ErrorCode::Unauthorized,
    )]
    pub vault: Account<'info, Vault>,

    #[account(mut)]
    pub destination: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}
```

Alternative using `constraint`:

```rust
#[derive(Accounts)]
pub struct Withdraw<'info> {
    pub authority: Signer<'info>,

    #[account(
        mut,
        constraint = vault.authority == authority.key() @ ErrorCode::Unauthorized,
    )]
    pub vault: Account<'info, Vault>,
}
```

### Key principle

A complete authorization check requires three layers (A-1, A-2, A-3 together):

| Check | What it proves | Vulnerability if missing |
|-------|---------------|------------------------|
| **Signer** (`is_signer` / `Signer<'info>`) | Someone signed | A-1: Anyone can impersonate |
| **Owner** (`account.owner` / `Account<T>`) | Data is from expected program | A-2: Fake account substitution |
| **Authority** (`key == stored_key` / `has_one`) | The RIGHT entity signed | A-3: Wrong signer authorized |

All three are required for a complete authorization model.

---

## References

- Taxonomy: A-3 in `vulnerability-taxonomy.md`
- Related: A-1 (Missing Signer Check) -- missing signer entirely
- Related: A-4 (Privilege Escalation) -- authority field itself can be overwritten
- [Anchor has_one constraint](https://www.anchor-lang.com/docs/account-constraints)
