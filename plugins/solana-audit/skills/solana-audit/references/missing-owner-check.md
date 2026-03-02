# A-2: Missing Owner/Program Check

**Severity:** HIGH
**Category:** Authentication & Authorization
**Taxonomy ID:** A-2

---

## Preconditions

All of the following must be true for this vulnerability to be exploitable:

1. An account is **deserialized** and its data is used to make trust decisions (balances, authority keys, configuration values)
2. The instruction does **not** verify that the account is owned by the expected program
3. The attacker can create an account with a **compatible data layout** owned by a different program (e.g., their own deployed program or the System Program)

If the account's address is derived via PDA and the PDA derivation is validated, the owner check may be implicit (see False Positives).

---

## Vulnerable Pattern

### Native Solana: Raw deserialization without owner check

```rust
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    program_error::ProgramError,
    pubkey::Pubkey,
};
use borsh::BorshDeserialize;

pub fn process_withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let authority = next_account_info(accounts_iter)?;
    let vault_account = next_account_info(accounts_iter)?;

    if !authority.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    // VULNERABLE: Deserializes vault data without checking who owns the account.
    // An attacker can deploy their own program, create an account with a Vault-compatible
    // data layout where vault_data.authority == attacker's pubkey, and pass it here.
    let vault_data = Vault::try_from_slice(&vault_account.data.borrow())?;

    if authority.key != &vault_data.authority {
        return Err(ProgramError::InvalidAccountData);
    }

    // Attacker passes authority check because they control the fake vault's data
    // Now they can withdraw from the REAL token accounts
    transfer_tokens(vault_data.token_account, amount)?;

    Ok(())
}
```

### Anchor: AccountInfo where Account<T> should be used

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct Withdraw<'info> {
    pub authority: Signer<'info>,

    /// VULNERABLE: AccountInfo does not verify owner or deserialize with type safety.
    /// Attacker can pass any account with matching data layout.
    /// CHECK: vault is not validated
    #[account(mut)]
    pub vault: AccountInfo<'info>,

    #[account(mut)]
    pub destination: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}

pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
    // Manual deserialization without owner check
    let vault_data = Vault::try_from_slice(
        &ctx.accounts.vault.data.borrow()
    )?;

    require!(
        ctx.accounts.authority.key() == vault_data.authority,
        ErrorCode::Unauthorized
    );

    // Attacker-controlled vault data passes the authority check
    // ...
    Ok(())
}
```

### Vulnerable trust-chain pattern (Cashio-style)

```rust
pub fn process_redeem(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let bank_account = next_account_info(accounts_iter)?;
    let collateral_account = next_account_info(accounts_iter)?;

    let bank = Bank::try_from_slice(&bank_account.data.borrow())?;
    let collateral = Collateral::try_from_slice(&collateral_account.data.borrow())?;

    // Checks that collateral belongs to the bank (relational check)
    if collateral.bank != *bank_account.key {
        return Err(ProgramError::InvalidAccountData);
    }

    // VULNERABLE: Never checks that bank_account.owner == program_id
    // Attacker creates a fake bank with their own program, crafts collateral
    // that references it. The entire trust chain is attacker-controlled.
    mint_tokens(bank.mint, collateral.amount)?;

    Ok(())
}
```

---

## Detection Heuristics

### Step 1: Find all account deserialization points

Search for every location where account data is read and interpreted.

**Grep patterns:**
```
# Native — borsh/manual deserialization
grep -n "try_from_slice\|deserialize\|unpack\|from_bytes" processor.rs

# Anchor — look for AccountInfo or UncheckedAccount with manual deserialization
grep -n "AccountInfo<'info>\|UncheckedAccount<'info>" lib.rs
grep -n "try_from_slice\|data.borrow()" lib.rs
```

### Step 2: Check owner validation

For each deserialized account, verify that `account.owner` is checked before or during deserialization.

**Native — look for explicit owner check:**
```
grep -n "\.owner\s*==\|\.owner\s*!=" processor.rs
```

Expected safe pattern:
```rust
if vault_account.owner != program_id {
    return Err(ProgramError::IncorrectProgramId);
}
let vault_data = Vault::try_from_slice(&vault_account.data.borrow())?;
```

**Anchor — check account type:**
```
# Account<'info, T> automatically checks owner == T::owner()
# AccountInfo<'info> and UncheckedAccount<'info> do NOT check owner
grep -n "Account<'info" lib.rs  # Safe
grep -n "AccountInfo<'info>\|UncheckedAccount<'info>" lib.rs  # Needs manual check
```

### Step 3: Trace account origin

Determine where each account comes from:
- **User-supplied** (passed in transaction accounts list) -- MUST have owner check
- **PDA-derived with validated seeds** -- owner check may be implicit (see False Positives)
- **Hardcoded/known address** -- may not need owner check if address itself is sufficient

For user-supplied accounts, an attacker fully controls which account is passed. Without an owner check, they can substitute any account with a compatible data layout.

---

## False Positives

### 1. Anchor `Account<'info, T>` auto-checks owner

Anchor's `Account<'info, T>` type automatically verifies:
- The account owner matches the program that defines type `T`
- The account's 8-byte discriminator matches the expected type

```rust
// SAFE — Account<'info, Vault> checks owner == declaring_program_id automatically
#[account(mut, has_one = authority)]
pub vault: Account<'info, Vault>,
```

### 2. System-owned accounts (rent, clock, etc.)

System program accounts like `Rent`, `Clock`, and the system program itself are inherently trusted. They are typically accessed via Anchor's `Sysvar<'info, Rent>` or `Program<'info, System>`, which validate the expected program/sysvar address.

```rust
// SAFE — Sysvar type validates the account is the real rent sysvar
pub rent: Sysvar<'info, Rent>,
pub system_program: Program<'info, System>,
```

### 3. PDA-derived accounts with validated seeds

If an account's address is derived from `Pubkey::find_program_address` using seeds that include the program ID, and the derivation is validated, then the owner check is implicit. Only the correct program can create a PDA at that address.

```rust
// SAFE — if the PDA derivation is verified, only this program could have
// created the account at this address, so owner is implicitly this program.
#[account(
    seeds = [b"vault", authority.key().as_ref()],
    bump = vault.bump,
)]
pub vault: Account<'info, Vault>,
```

However, note that PDA derivation alone is not sufficient if you use raw `AccountInfo` -- the PDA check only validates the address, not the owner. An attacker could theoretically create an account at a PDA address owned by a different program using `create_account` before the real program does.

### 4. Accounts validated by known address

If the account's pubkey is compared against a hardcoded or stored known-good address, the owner check adds defense-in-depth but is not strictly required for exploitability (the address comparison is sufficient).

```rust
// SAFE — even without owner check, only the correct account can match
if config_account.key != &KNOWN_CONFIG_PUBKEY {
    return Err(ProgramError::InvalidAccountData);
}
```

---

## Remediation

### Native Solana

Add an explicit owner check before deserializing account data:

```rust
pub fn process_withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let authority = next_account_info(accounts_iter)?;
    let vault_account = next_account_info(accounts_iter)?;

    if !authority.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    // FIX: Verify the vault account is owned by this program
    if vault_account.owner != program_id {
        return Err(ProgramError::IncorrectProgramId);
    }

    let vault_data = Vault::try_from_slice(&vault_account.data.borrow())?;

    if authority.key != &vault_data.authority {
        return Err(ProgramError::InvalidAccountData);
    }

    transfer_tokens(vault_data.token_account, amount)?;
    Ok(())
}
```

For trust chains, validate the root account's owner:

```rust
// FIX: Validate root of trust chain
if bank_account.owner != program_id {
    return Err(ProgramError::IncorrectProgramId);
}
let bank = Bank::try_from_slice(&bank_account.data.borrow())?;

// Now relational checks (collateral.bank == bank.key) are meaningful
// because the bank account is guaranteed to be from this program
```

### Anchor Framework

Replace `AccountInfo<'info>` with `Account<'info, T>` for any account that is deserialized:

```rust
#[derive(Accounts)]
pub struct Withdraw<'info> {
    pub authority: Signer<'info>,

    // FIX: Account<'info, Vault> verifies owner and deserializes with type safety
    #[account(
        mut,
        has_one = authority,
    )]
    pub vault: Account<'info, Vault>,

    #[account(mut)]
    pub destination: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}
```

If `AccountInfo` is truly needed (e.g., for dynamic account types), add manual owner validation:

```rust
/// CHECK: Owner is manually validated below
pub dynamic_account: AccountInfo<'info>,

// In handler:
require!(
    dynamic_account.owner == &expected_program::ID,
    ErrorCode::InvalidAccountOwner
);
```

### Key principle

Every account whose data is read and used for trust decisions must have its **owner** verified. The owner check ensures the data was written by the expected program, not by an attacker-deployed program with a compatible data layout.

---

## Real-World Exploits

- **Wormhole ($326M):** `verify_signatures` accepted a user-supplied "secp256k1 program" account without validating it was the real secp256k1 program. Attacker passed a fake program that always returned "verified."
- **Cashio ($52M):** `Bank` account at the root of a trust chain was not owner-checked. Attacker created a fake `Bank` owned by their program, then built a fake collateral chain on top of it.
- **Crema Finance ($8.8M):** Tick account program was user-supplied and unvalidated. Attacker passed a fake program returning manipulated price data.

---

## References

- [Solana Documentation: Account Model](https://solana.com/docs/core/accounts)
- [Anchor Account type](https://docs.rs/anchor-lang/latest/anchor_lang/accounts/account/struct.Account.html)
- Taxonomy: A-2 in `vulnerability-taxonomy.md`
- Case studies: Wormhole, Cashio, Crema in `exploit-case-studies.md`
- Related: S-5 (Type Cosplay) -- similar attack vector using type confusion instead of owner confusion
