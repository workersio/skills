# S-2: Duplicate Mutable Accounts [HIGH]

An instruction accepts two or more accounts of the same type (e.g., source and destination token accounts) without verifying they are distinct. An attacker passes the same account for both parameters, causing double-counting, self-referential state corruption, or bypass of balance checks.

---

## Preconditions

For this vulnerability to be exploitable, ALL of the following must hold:

1. **The instruction takes 2+ accounts of the same type** (e.g., two `TokenAccount`s, two `Vault` accounts, two `AccountInfo`s used as similar roles)
2. **Both accounts are mutable** (at least one write occurs to each)
3. **No key comparison** is performed between the accounts (`source.key() != dest.key()`)
4. **The operation produces a different outcome** when `source == dest` than intended (e.g., a transfer from an account to itself, double-credit, or bypassed invariant)

## Vulnerable Pattern

### Native Solana Program (Vulnerable)

```rust
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    program_error::ProgramError,
    pubkey::Pubkey,
};

pub fn transfer(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let account_iter = &mut accounts.iter();
    let source = next_account_info(account_iter)?;
    let destination = next_account_info(account_iter)?;
    let authority = next_account_info(account_iter)?;

    // VULNERABLE: No check that source != destination.
    // If attacker passes the same account for both:
    //   source and destination point to the SAME underlying data.

    let mut source_data = source.try_borrow_mut_data()?;
    let mut source_vault = Vault::try_from_slice(&source_data)?;

    let mut dest_data = destination.try_borrow_mut_data()?;
    let mut dest_vault = Vault::try_from_slice(&dest_data)?;

    // When source == destination, source_vault and dest_vault are deserialized
    // from the same bytes. After this block:
    //   source_vault.balance -= amount  (written back first)
    //   dest_vault.balance += amount    (written back second, OVERWRITES source write)
    // Net effect: balance INCREASES by amount (free money)
    source_vault.balance = source_vault.balance.checked_sub(amount)
        .ok_or(ProgramError::InsufficientFunds)?;
    dest_vault.balance = dest_vault.balance.checked_add(amount)
        .ok_or(ProgramError::InvalidArgument)?;

    source_vault.serialize(&mut *source_data)?;
    dest_vault.serialize(&mut *dest_data)?;  // overwrites the subtract!

    Ok(())
}
```

### Anchor Program (Vulnerable)

```rust
use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};

#[derive(Accounts)]
pub struct TransferTokens<'info> {
    #[account(mut)]
    pub source: Account<'info, TokenAccount>,
    #[account(mut)]
    pub destination: Account<'info, TokenAccount>,
    pub authority: Signer<'info>,
    pub token_program: Program<'info, Token>,
}

// VULNERABLE: No constraint ensuring source.key() != destination.key()
// Anchor will NOT reject duplicate keys automatically for Account<T> types.
pub fn transfer_tokens(ctx: Context<TransferTokens>, amount: u64) -> Result<()> {
    let cpi_accounts = Transfer {
        from: ctx.accounts.source.to_account_info(),
        to: ctx.accounts.destination.to_account_info(),
        authority: ctx.accounts.authority.to_account_info(),
    };
    let cpi_ctx = CpiContext::new(
        ctx.accounts.token_program.to_account_info(),
        cpi_accounts,
    );
    // SPL token program will handle self-transfer gracefully (no-op),
    // but custom vault logic around this may double-count rewards or shares.
    token::transfer(cpi_ctx, amount)?;

    // Custom accounting on top of the transfer is where the bug bites:
    ctx.accounts.source.reload()?;
    ctx.accounts.destination.reload()?;
    // If source == destination, both reload to the same state.
    // Any bookkeeping based on "delta" will be wrong.

    Ok(())
}
```

### Reward Claim Double-Count Pattern (Vulnerable)

```rust
#[derive(Accounts)]
pub struct ClaimRewards<'info> {
    #[account(mut)]
    pub user_stake_a: Account<'info, StakeAccount>,
    #[account(mut)]
    pub user_stake_b: Account<'info, StakeAccount>,
    #[account(mut)]
    pub reward_pool: Account<'info, RewardPool>,
    pub authority: Signer<'info>,
}

// VULNERABLE: Allows claiming rewards for stake_a and stake_b in one instruction.
// If attacker passes the same account for both, they claim rewards twice.
pub fn claim_rewards(ctx: Context<ClaimRewards>) -> Result<()> {
    let reward_a = calculate_reward(&ctx.accounts.user_stake_a)?;
    let reward_b = calculate_reward(&ctx.accounts.user_stake_b)?;

    let total_reward = reward_a.checked_add(reward_b).unwrap();
    // Double reward if user_stake_a == user_stake_b
    distribute_reward(&mut ctx.accounts.reward_pool, total_reward)?;
    Ok(())
}
```

## Detection Heuristics

### Grep Patterns

```bash
# Find instructions that take 2+ mutable accounts of the same type
rg "#\[account\(mut" --type rust -n

# Find Account<'info, TokenAccount> appearing multiple times in one struct
rg "Account<'info, TokenAccount>" --type rust -n

# Check for key comparison constraints (remediation pattern)
rg "key\(\) != |\.key != " --type rust -n

# Find AccountInfo pairs that might be same type
rg "next_account_info" --type rust -n
```

### Manual Review Steps

1. **For each instruction context struct** (Anchor `#[derive(Accounts)]` or native account list):
   - Count how many accounts share the same type (`Account<'info, TokenAccount>`, `Account<'info, Vault>`, etc.)
   - For each pair of same-typed mutable accounts, check if a key inequality constraint exists.
2. **For native programs**: Look at the instruction handler. If two `AccountInfo` parameters are used for the same role (source/dest, user_a/user_b), check for `a.key != b.key`.
3. **Analyze the consequence**: What happens if both accounts point to the same data? Does the instruction produce a different result than intended? If self-transfer is a no-op, it may be low risk. If it duplicates rewards, inflates balances, or corrupts state, it is high severity.

## False Positives

The following patterns are **not vulnerable** and should be excluded:

- **Accounts of different types**: `Account<'info, Vault>` and `Account<'info, UserProfile>` cannot be the same account because Anchor verifies the discriminator (different types have different 8-byte discriminators).
- **Immutable accounts**: If both accounts are read-only (`#[account()]` without `mut`), duplicates cannot corrupt state. The result is at worst a logical no-op.
- **SPL Token self-transfers**: The SPL Token program handles `source == destination` as a successful no-op. Only vulnerable if the program has custom accounting on top.
- **Intentionally allowed self-transfer**: Some designs explicitly permit `source == dest` (e.g., a "refresh" or "compound" operation).
- **PDA-derived accounts with different seeds**: If both accounts are PDAs with different seed derivations enforced via `seeds = [...]`, they cannot have the same address by construction.
- **Anchor `constraint` already present**:
  ```rust
  #[account(mut, constraint = source.key() != destination.key())]
  pub source: Account<'info, TokenAccount>,
  ```

## Remediation

### Anchor Program (Fixed)

```rust
#[derive(Accounts)]
pub struct TransferTokens<'info> {
    #[account(
        mut,
        // FIX: Explicit constraint preventing duplicate accounts
        constraint = source.key() != destination.key() @ ErrorCode::DuplicateAccounts,
    )]
    pub source: Account<'info, TokenAccount>,
    #[account(mut)]
    pub destination: Account<'info, TokenAccount>,
    pub authority: Signer<'info>,
    pub token_program: Program<'info, Token>,
}

#[error_code]
pub enum ErrorCode {
    #[msg("Source and destination accounts must be different")]
    DuplicateAccounts,
}
```

### Native Solana Program (Fixed)

```rust
pub fn transfer(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let account_iter = &mut accounts.iter();
    let source = next_account_info(account_iter)?;
    let destination = next_account_info(account_iter)?;
    let authority = next_account_info(account_iter)?;

    // FIX: Reject duplicate accounts
    if source.key == destination.key {
        return Err(ProgramError::InvalidArgument);
    }

    // ... safe to proceed with transfer logic
    Ok(())
}
```

### Reward Claim (Fixed)

```rust
#[derive(Accounts)]
pub struct ClaimRewards<'info> {
    #[account(
        mut,
        constraint = user_stake_a.key() != user_stake_b.key() @ ErrorCode::DuplicateAccounts,
    )]
    pub user_stake_a: Account<'info, StakeAccount>,
    #[account(mut)]
    pub user_stake_b: Account<'info, StakeAccount>,
    #[account(mut)]
    pub reward_pool: Account<'info, RewardPool>,
    pub authority: Signer<'info>,
}
```

### Key Principle

Whenever an instruction accepts two or more mutable accounts of the same type, explicitly verify that their keys differ. In Anchor, use a `constraint` on the accounts struct. In native programs, compare `.key` fields early in the handler before any state reads.
