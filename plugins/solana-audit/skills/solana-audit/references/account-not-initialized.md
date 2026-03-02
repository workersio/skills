# S-1: Account Not Initialized Check [HIGH]

An instruction reads or operates on account data without verifying the account has been properly initialized. This allows an attacker to pass a freshly allocated (all-zeros) or garbage-state account and have the program treat it as valid state.

---

## Preconditions

For this vulnerability to be exploitable, ALL of the following must hold:

1. **The program deserializes account data** from a user-supplied `AccountInfo`
2. **No initialization check** is performed before reading the data (no discriminator verification, no `is_initialized` flag check)
3. **The attacker can create or supply** an account owned by the target program that has never been initialized (e.g., allocated via `create_account` but never populated by an init instruction)
4. **The zero/default state is advantageous** to the attacker (e.g., zero balances pass checks, zero authority matches the system program, default enum variant grants access)

## Vulnerable Pattern

### Native Solana Program (Vulnerable)

```rust
use borsh::BorshDeserialize;
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    program_error::ProgramError,
    pubkey::Pubkey,
};

#[derive(BorshDeserialize)]
pub struct Vault {
    pub authority: Pubkey,
    pub balance: u64,
    pub is_initialized: bool, // exists but never checked!
}

pub fn withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let account_iter = &mut accounts.iter();
    let vault_account = next_account_info(account_iter)?;
    let authority = next_account_info(account_iter)?;

    // VULNERABLE: Deserializes without checking initialization state.
    // A zeroed account will deserialize with:
    //   authority = Pubkey::default() (all zeros = system program)
    //   balance = 0
    //   is_initialized = false
    let vault = Vault::try_from_slice(&vault_account.data.borrow())?;

    // If attacker passes authority = SystemProgram (all zeros), this check passes
    // against the zero-deserialized vault.authority field
    if vault.authority != *authority.key {
        return Err(ProgramError::InvalidAccountData);
    }

    // ... proceeds to withdraw from vault
    Ok(())
}
```

### Anchor Program (Vulnerable via UncheckedAccount)

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct Withdraw<'info> {
    /// CHECK: manual validation below
    #[account(mut)]
    pub vault: UncheckedAccount<'info>,
    pub authority: Signer<'info>,
}

pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
    // VULNERABLE: manually deserializes from UncheckedAccount with no discriminator check.
    // Anchor's 8-byte discriminator is NOT verified because UncheckedAccount is used.
    let data = ctx.accounts.vault.try_borrow_data()?;
    let vault: Vault = Vault::try_from_slice(&data[8..])?; // skips 8 bytes but doesn't verify them

    require!(vault.authority == ctx.accounts.authority.key(), ErrorCode::Unauthorized);

    // ... proceeds with withdrawal on potentially uninitialized account
    Ok(())
}
```

## Detection Heuristics

### Grep Patterns

```bash
# Native: find all borsh deserialization — each hit needs an init check nearby
rg "try_from_slice|deserialize\(" --type rust -n

# Native: find accounts that have is_initialized but may not check it
rg "is_initialized" --type rust -n

# Anchor: find UncheckedAccount or AccountInfo used where Account<T> should be
rg "UncheckedAccount|/// CHECK" --type rust -n

# Anchor: find manual deserialization that bypasses discriminator
rg "try_borrow_data|try_from_slice|from_account_info" --type rust -n
```

### Manual Review Steps

1. **Enumerate all account struct types** in the program. For each, identify whether it has an `is_initialized` field or relies on a discriminator.
2. **Trace every instruction entry point**. For each account parameter that is deserialized:
   - Native: Is `is_initialized == true` checked before reading other fields?
   - Native: Is a discriminator byte/magic number verified before deserialization?
   - Anchor: Is the account typed as `Account<'info, T>` (which auto-checks the 8-byte discriminator)?
3. **Check what zero-state means**. If a zeroed account passes subsequent checks (e.g., authority is `Pubkey::default()`, balance is 0, enum defaults to a privileged variant), the vulnerability is exploitable.

## False Positives

The following patterns are **not vulnerable** and should be excluded:

- **Anchor `Account<'info, T>`**: Automatically verifies the 8-byte discriminator on deserialization. An uninitialized account (all zeros) will fail the discriminator check.
- **Anchor `init` constraint**: The `init` constraint creates and initializes the account in one step, writing the discriminator. Subsequent reads via `Account<T>` are safe.
- **Explicit discriminator verification in native code**:
  ```rust
  let data = vault_account.data.borrow();
  if data[0] != AccountType::Vault as u8 {
      return Err(ProgramError::InvalidAccountData);
  }
  ```
- **Accounts validated by PDA derivation with init**: If the account is created via `create_program_address` within the same init instruction and seeds ensure uniqueness, the account is always freshly initialized by the program itself.
- **System-owned accounts (lamport-only)**: Accounts that are only checked for lamport balance, not deserialized for data, are not affected.

## Remediation

### Native Solana Program (Fixed)

```rust
#[derive(BorshDeserialize, BorshSerialize)]
pub struct Vault {
    pub discriminator: u8,     // 1 = Vault type
    pub is_initialized: bool,
    pub authority: Pubkey,
    pub balance: u64,
}

pub fn withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let account_iter = &mut accounts.iter();
    let vault_account = next_account_info(account_iter)?;
    let authority = next_account_info(account_iter)?;

    // FIX 1: Verify owner
    if vault_account.owner != program_id {
        return Err(ProgramError::IncorrectProgramId);
    }

    let vault = Vault::try_from_slice(&vault_account.data.borrow())?;

    // FIX 2: Verify discriminator (prevents type cosplay too)
    if vault.discriminator != 1 {
        return Err(ProgramError::InvalidAccountData);
    }

    // FIX 3: Verify initialization
    if !vault.is_initialized {
        return Err(ProgramError::UninitializedAccount);
    }

    if vault.authority != *authority.key {
        return Err(ProgramError::InvalidAccountData);
    }

    // ... safe to proceed
    Ok(())
}
```

### Anchor Program (Fixed)

```rust
use anchor_lang::prelude::*;

#[account]
pub struct Vault {
    pub authority: Pubkey,
    pub balance: u64,
}

#[derive(Accounts)]
pub struct Withdraw<'info> {
    // FIX: Use Account<'info, Vault> instead of UncheckedAccount.
    // Anchor automatically:
    //   1. Verifies the 8-byte discriminator (rejects uninitialized accounts)
    //   2. Verifies the account owner == program ID
    //   3. Deserializes the data
    #[account(
        mut,
        has_one = authority,
    )]
    pub vault: Account<'info, Vault>,
    pub authority: Signer<'info>,
}

pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    // Safe: vault is guaranteed to be initialized and owned by this program
    require!(vault.balance >= amount, ErrorCode::InsufficientBalance);
    vault.balance = vault.balance.checked_sub(amount).unwrap();
    // ... transfer lamports/tokens
    Ok(())
}
```

### Key Principle

Every account deserialization must be preceded by verification that the account contains valid, initialized data. In Anchor, use `Account<'info, T>`. In native programs, check a discriminator byte and an `is_initialized` flag before reading any other fields.
