# S-5: Type Cosplay / Account Substitution [HIGH]

An instruction deserializes account data without verifying the account's type discriminator, allowing an attacker to pass an account of a different type that has a compatible data layout. Fields from the wrong struct are reinterpreted, potentially granting unauthorized access or corrupting state.

---

## Preconditions

For this vulnerability to be exploitable, ALL of the following must hold:

1. **The program defines multiple account types** (e.g., `Vault`, `UserProfile`, `Config`) that are stored as serialized data in on-chain accounts
2. **Account deserialization does not verify a type discriminator** (no magic number, no Anchor 8-byte discriminator check)
3. **Two or more account types have compatible data layouts** at critical field offsets (e.g., a `Pubkey` at offset 0 in both types, but representing different things: authority in one, beneficiary in another)
4. **The attacker can create or control an account of the "wrong" type** and pass it where the "right" type is expected

## Vulnerable Pattern

### Native Solana Program (Vulnerable)

```rust
use borsh::{BorshDeserialize, BorshSerialize};
use solana_program::pubkey::Pubkey;

// Two account types with compatible layouts at the authority field offset
#[derive(BorshDeserialize, BorshSerialize)]
pub struct Vault {
    pub authority: Pubkey,   // offset 0, 32 bytes
    pub balance: u64,        // offset 32, 8 bytes
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct UserProfile {
    pub wallet: Pubkey,      // offset 0, 32 bytes — same position as Vault::authority!
    pub username_len: u64,   // offset 32, 8 bytes
    pub username: [u8; 32],  // offset 40
}

pub fn withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let vault_account = &accounts[0];
    let authority = &accounts[1];

    // VULNERABLE: Deserializes as Vault without checking the account type.
    // Attacker creates a UserProfile where wallet = attacker's pubkey,
    // then passes it as the "vault" account.
    // vault.authority will read the UserProfile.wallet field (attacker's key).
    let vault = Vault::try_from_slice(&vault_account.data.borrow())?;

    // This check passes because vault.authority is actually UserProfile.wallet
    // which the attacker controls.
    if vault.authority != *authority.key {
        return Err(ProgramError::InvalidAccountData);
    }

    // Attacker now has authority over what the program thinks is a Vault,
    // but is actually their UserProfile account.
    // ... withdraws funds
    Ok(())
}
```

### Multiple Structs Without Discriminator (Vulnerable)

```rust
#[derive(BorshDeserialize, BorshSerialize)]
pub struct StakePool {
    pub admin: Pubkey,         // 32 bytes
    pub total_staked: u64,     // 8 bytes
    pub reward_rate: u64,      // 8 bytes
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct LoanOffer {
    pub lender: Pubkey,        // 32 bytes — same offset as StakePool::admin
    pub principal: u64,        // 8 bytes — same offset as StakePool::total_staked
    pub interest_rate: u64,    // 8 bytes — same offset as StakePool::reward_rate
}

// Identical binary layout! A LoanOffer can be deserialized as a StakePool.
// If attacker creates a LoanOffer with lender = attacker's key, they can
// pass it as a StakePool and the admin check will pass.
```

### Anchor with Manual Deserialization (Vulnerable)

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct AdminAction<'info> {
    /// CHECK: we validate manually below
    #[account(mut)]
    pub config: UncheckedAccount<'info>,  // VULNERABLE: bypasses discriminator check
    pub admin: Signer<'info>,
}

pub fn admin_action(ctx: Context<AdminAction>) -> Result<()> {
    let data = ctx.accounts.config.try_borrow_data()?;
    // VULNERABLE: Skips Anchor discriminator, manually reads fields.
    // An account of ANY type with the right bytes at offset 8 will pass.
    let admin_key = Pubkey::try_from_slice(&data[8..40])?;

    require!(admin_key == ctx.accounts.admin.key(), ErrorCode::Unauthorized);
    // Attacker passes a different account type with their pubkey at bytes 8..40
    Ok(())
}
```

## Detection Heuristics

### Grep Patterns

```bash
# Find all account struct definitions — catalog types and their layouts
rg "pub struct .* \{" --type rust -n

# Find borsh deserialization without prior discriminator checks
rg "try_from_slice|BorshDeserialize|deserialize\(" --type rust -n

# Find UncheckedAccount / AccountInfo used where Account<T> should be
rg "UncheckedAccount|/// CHECK" --type rust -n

# Find manual deserialization that reads raw byte slices
rg "try_borrow_data|data\.borrow\(\)|from_slice" --type rust -n

# Find programs that define multiple account types (more types = higher risk)
rg "#\[account\]|#\[derive.*BorshDeserialize" --type rust -n
```

### Manual Review Steps

1. **List all account struct types** in the program. For each, note the field types and their byte offsets.
2. **Compare layouts pairwise**: Do any two types have a `Pubkey` at the same offset that serves different purposes (e.g., authority vs. beneficiary)? If the layouts are compatible at critical fields, type cosplay is possible.
3. **Check each deserialization point**:
   - Does it verify a type discriminator before reading fields?
   - Native: Is there a `discriminator` or `account_type` field checked against an expected value?
   - Anchor: Is the account typed as `Account<'info, T>` (which auto-verifies the 8-byte discriminator)?
4. **Trace the impact**: If an attacker can substitute one type for another, what fields get reinterpreted? Can they gain authority, inflate balances, or bypass access control?
5. **Single-type programs**: If the program only defines one account type, type cosplay within the program is impossible (but cross-program cosplay via missing owner check is still possible -- see A-2).

## False Positives

The following patterns are **not vulnerable** and should be excluded:

- **Anchor `Account<'info, T>`**: Automatically checks the 8-byte discriminator (SHA256 of `"account:{TypeName}"`). Different types have different discriminators, so substitution is rejected at deserialization:
  ```rust
  // Safe: Anchor verifies the account is actually a Vault, not any other type
  pub vault: Account<'info, Vault>,
  ```
- **Explicit type discriminator in native code**:
  ```rust
  #[derive(BorshDeserialize)]
  pub struct Vault {
      pub account_type: u8,  // 0 = uninitialized, 1 = Vault, 2 = UserProfile
      pub authority: Pubkey,
      pub balance: u64,
  }

  // Verified before use:
  let vault = Vault::try_from_slice(&data)?;
  if vault.account_type != 1 {
      return Err(ProgramError::InvalidAccountData);
  }
  ```
- **Single account type programs**: Programs that define only one account struct cannot be vulnerable to intra-program type cosplay.
- **PDA seeds encode the type**: If different types use different seed prefixes (e.g., `seeds = [b"vault", ...]` vs `seeds = [b"profile", ...]`) and the PDA is validated in the instruction, the type is implicitly enforced.
- **Owner check combined with unique layouts**: If the owner check is present and account types have incompatible sizes (deserialization would fail on length mismatch), cosplay is prevented.

## Remediation

### Native Solana Program (Fixed) -- Enum Discriminator

```rust
use borsh::{BorshDeserialize, BorshSerialize};
use solana_program::pubkey::Pubkey;

#[derive(BorshDeserialize, BorshSerialize, PartialEq)]
pub enum AccountType {
    Uninitialized,
    Vault,
    UserProfile,
    StakePool,
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct Vault {
    pub account_type: AccountType,  // FIX: type discriminator as first field
    pub authority: Pubkey,
    pub balance: u64,
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct UserProfile {
    pub account_type: AccountType,  // FIX: different discriminator value
    pub wallet: Pubkey,
    pub username_len: u64,
    pub username: [u8; 32],
}

pub fn withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let vault_account = &accounts[0];
    let authority = &accounts[1];

    // FIX: Verify owner
    if vault_account.owner != program_id {
        return Err(ProgramError::IncorrectProgramId);
    }

    let vault = Vault::try_from_slice(&vault_account.data.borrow())?;

    // FIX: Verify type discriminator — rejects UserProfile or any other type
    if vault.account_type != AccountType::Vault {
        return Err(ProgramError::InvalidAccountData);
    }

    if vault.authority != *authority.key {
        return Err(ProgramError::InvalidAccountData);
    }

    // Safe: account is verified as an initialized Vault
    Ok(())
}
```

### Anchor Program (Fixed)

```rust
use anchor_lang::prelude::*;

#[account]
pub struct ProgramConfig {
    pub admin: Pubkey,
    pub fee_bps: u16,
}

#[account]
pub struct Vault {
    pub authority: Pubkey,
    pub balance: u64,
}

#[derive(Accounts)]
pub struct AdminAction<'info> {
    // FIX: Use Account<'info, ProgramConfig> instead of UncheckedAccount.
    // Anchor automatically verifies:
    //   1. The 8-byte discriminator matches ProgramConfig (not Vault or anything else)
    //   2. The account owner is this program
    //   3. The data deserializes correctly
    #[account(
        has_one = admin,
    )]
    pub config: Account<'info, ProgramConfig>,
    pub admin: Signer<'info>,
}

pub fn admin_action(ctx: Context<AdminAction>) -> Result<()> {
    // Safe: config is guaranteed to be a ProgramConfig, not a Vault or other type
    let config = &ctx.accounts.config;
    msg!("Admin {} updating config with fee {}", config.admin, config.fee_bps);
    Ok(())
}
```

### Key Principle

Every account deserialization must verify the account's type discriminator before reading any fields. In Anchor, use `Account<'info, T>` which checks an 8-byte discriminator automatically. In native programs, add a type discriminator as the first field of every account struct (using an enum) and verify it immediately after deserialization. Never use `UncheckedAccount` or raw `AccountInfo` for deserialization when `Account<T>` is available.
