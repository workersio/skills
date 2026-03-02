# S-7: Reinitialization [HIGH]

An initialization instruction can be called again on an already-initialized account, resetting its state. An attacker re-initializes a vault, pool, or config account to overwrite the legitimate authority, reset balances to zero, or revert security-critical state to defaults.

---

## Preconditions

For this vulnerability to be exploitable, ALL of the following must hold:

1. **An initialization instruction exists** that sets up account state (writes initial data, sets authority, allocates space)
2. **The init instruction does not check whether the account is already initialized** (no `is_initialized` guard, no discriminator verification, no Anchor `init` constraint)
3. **The attacker can call the init instruction** with an already-initialized account (either they are the signer, or the init instruction has weak access control)
4. **Re-initialization overwrites critical state** that benefits the attacker (e.g., replacing the authority pubkey with their own, resetting a balance, clearing a blocklist)

## Vulnerable Pattern

### Native Solana Program (Vulnerable -- No Init Guard)

```rust
use borsh::{BorshDeserialize, BorshSerialize};
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    program_error::ProgramError,
    pubkey::Pubkey,
};

#[derive(BorshDeserialize, BorshSerialize)]
pub struct Vault {
    pub is_initialized: bool,
    pub authority: Pubkey,
    pub balance: u64,
}

pub fn initialize_vault(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let account_iter = &mut accounts.iter();
    let vault_account = next_account_info(account_iter)?;
    let authority = next_account_info(account_iter)?;

    // VULNERABLE: No check that the vault is NOT already initialized.
    // An attacker can call this on an existing vault to overwrite the authority.
    let mut vault = Vault {
        is_initialized: true,
        authority: *authority.key,  // Attacker sets themselves as authority
        balance: 0,                 // Resets balance to 0 (or any desired value)
    };

    vault.serialize(&mut *vault_account.try_borrow_mut_data()?)?;
    Ok(())
}
```

### Native Solana Program (Vulnerable -- Checks is_initialized but Logic Bug)

```rust
pub fn initialize_vault(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let vault_account = &accounts[0];
    let authority = &accounts[1];

    let vault = Vault::try_from_slice(&vault_account.data.borrow())?;

    // VULNERABLE: Check is inverted! Should be:
    //   if vault.is_initialized { return Err(...); }
    // Instead, this rejects uninitialized accounts and ALLOWS re-init.
    if !vault.is_initialized {
        return Err(ProgramError::AccountAlreadyInitialized);
    }

    let new_vault = Vault {
        is_initialized: true,
        authority: *authority.key,
        balance: 0,
    };
    new_vault.serialize(&mut *vault_account.try_borrow_mut_data()?)?;
    Ok(())
}
```

### Anchor Program (Vulnerable -- init_if_needed Without Authority Check)

```rust
use anchor_lang::prelude::*;

#[account]
pub struct GameState {
    pub admin: Pubkey,
    pub score: u64,
    pub round: u64,
}

#[derive(Accounts)]
pub struct InitGame<'info> {
    // VULNERABLE: init_if_needed allows re-initialization if the account already exists.
    // If the account is already initialized, Anchor skips the init and just deserializes.
    // BUT if an attacker can close the account first (setting it back to uninitialized),
    // init_if_needed will re-create it with attacker-controlled state.
    //
    // Even without closing, init_if_needed on an already-initialized account simply
    // deserializes it -- which is safe. The danger is the NAME suggests it "inits if needed"
    // and developers may add state-overwriting logic in the handler thinking it only runs
    // on first init.
    #[account(
        init_if_needed,
        payer = user,
        space = 8 + 32 + 8 + 8,
        seeds = [b"game", user.key().as_ref()],
        bump,
    )]
    pub game: Account<'info, GameState>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

pub fn init_game(ctx: Context<InitGame>) -> Result<()> {
    let game = &mut ctx.accounts.game;
    // VULNERABLE: This logic runs EVERY time, not just on first init.
    // On re-call, it overwrites the admin to the new caller.
    game.admin = ctx.accounts.user.key();
    game.score = 0;
    game.round = 1;
    Ok(())
}
```

### Anchor Program (Vulnerable -- Manual Init Without Discriminator)

```rust
#[derive(Accounts)]
pub struct InitConfig<'info> {
    /// CHECK: manual validation
    #[account(mut)]
    pub config: UncheckedAccount<'info>,
    pub admin: Signer<'info>,
}

pub fn init_config(ctx: Context<InitConfig>) -> Result<()> {
    let config_info = &ctx.accounts.config;

    // VULNERABLE: Manually writes data without checking if the account already
    // has valid data. Any signer can overwrite the config.
    let mut data = config_info.try_borrow_mut_data()?;
    let config = Config {
        admin: ctx.accounts.admin.key(),
        fee_bps: 100,
        paused: false,
    };
    config.serialize(&mut &mut data[..])?;
    Ok(())
}
```

## Detection Heuristics

### Grep Patterns

```bash
# Find initialization functions/instructions
rg "init|initialize|create|setup" --type rust -n

# Find is_initialized checks (verify they are present and correct direction)
rg "is_initialized" --type rust -n

# Find init_if_needed usage (potential re-init vector)
rg "init_if_needed" --type rust -n

# Find Anchor init constraint (safe pattern)
rg "#\[account\(.*init[^_]" --type rust -n

# Find manual account creation without Anchor
rg "create_account|CreateAccount" --type rust -n

# Find serialization in init functions (should have guard before it)
rg "serialize\(&mut" --type rust -n
```

### Manual Review Steps

1. **Identify all initialization instructions**: Search for functions named `init*`, `initialize*`, `create*`, `setup*`, or any instruction that writes initial account state.
2. **For each init instruction, check the guard**:
   - **Native**: Is `is_initialized` checked and is the logic correct? (`if vault.is_initialized { return Err(...) }` -- NOT inverted)
   - **Anchor `init`**: Uses the discriminator as an implicit guard. If the account already has data, `init` will fail because the account already exists. This is safe.
   - **Anchor `init_if_needed`**: Does NOT prevent re-init. If the handler overwrites state unconditionally, any caller can re-trigger the handler on an existing account.
3. **Check access control on init**: Even if re-init is prevented, verify that the FIRST init is properly gated. Can anyone call init, or only a specific authority?
4. **Check interaction with close**: If the program has a close instruction, can an attacker close an account and then call init again to re-create it with new state? Especially dangerous with `init_if_needed`.
5. **Verify discriminator handling**: In native programs, does the init instruction write a discriminator? Do subsequent instructions check it?

## False Positives

The following patterns are **not vulnerable** and should be excluded:

- **Anchor `init` constraint (without `_if_needed`)**: The `init` constraint creates the account via a CPI to the System Program. If the account already exists (has data/lamports), the System Program's `CreateAccount` instruction will fail. This makes double-init impossible:
  ```rust
  #[account(
      init,
      payer = user,
      space = 8 + std::mem::size_of::<Vault>(),
      seeds = [b"vault", user.key().as_ref()],
      bump,
  )]
  pub vault: Account<'info, Vault>,
  ```

- **Correct `is_initialized` guard in native code**:
  ```rust
  let vault = Vault::try_from_slice(&data)?;
  if vault.is_initialized {
      return Err(ProgramError::AccountAlreadyInitialized);
  }
  // Only reaches here on first init
  ```

- **Discriminator check before init in native code**:
  ```rust
  let data = account.data.borrow();
  if data[0] != 0 {  // Non-zero discriminator means already initialized
      return Err(ProgramError::AccountAlreadyInitialized);
  }
  ```

- **`init_if_needed` with idempotent handler**: If the handler only writes state on first init (checks a flag) and is a no-op on subsequent calls:
  ```rust
  pub fn init_game(ctx: Context<InitGame>) -> Result<()> {
      let game = &mut ctx.accounts.game;
      if game.admin != Pubkey::default() {
          // Already initialized, skip
          return Ok(());
      }
      game.admin = ctx.accounts.user.key();
      Ok(())
  }
  ```

- **Admin-only init with verified authority**: If init can only be called by a hardcoded or governance-controlled authority, the attack surface is minimal (only the admin can re-init, which may be intentional for upgrades).

## Remediation

### Native Solana Program (Fixed)

```rust
use borsh::{BorshDeserialize, BorshSerialize};
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    program_error::ProgramError,
    pubkey::Pubkey,
};

#[derive(BorshDeserialize, BorshSerialize)]
pub struct Vault {
    pub discriminator: u8,     // 1 = Vault type, 0 = uninitialized
    pub is_initialized: bool,
    pub authority: Pubkey,
    pub balance: u64,
}

pub fn initialize_vault(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let account_iter = &mut accounts.iter();
    let vault_account = next_account_info(account_iter)?;
    let authority = next_account_info(account_iter)?;

    // FIX: Verify owner
    if vault_account.owner != program_id {
        return Err(ProgramError::IncorrectProgramId);
    }

    // FIX: Check if already initialized BEFORE writing anything
    let existing_data = vault_account.try_borrow_data()?;
    if existing_data.len() > 0 && existing_data[0] != 0 {
        // Non-zero discriminator means account already has data
        return Err(ProgramError::AccountAlreadyInitialized);
    }
    drop(existing_data);

    // Safe: account is uninitialized, proceed with first-time setup
    let vault = Vault {
        discriminator: 1,       // Mark as Vault type
        is_initialized: true,   // Mark as initialized
        authority: *authority.key,
        balance: 0,
    };

    vault.serialize(&mut *vault_account.try_borrow_mut_data()?)?;
    Ok(())
}
```

### Anchor Program (Fixed -- Use init, Not init_if_needed)

```rust
use anchor_lang::prelude::*;

#[account]
pub struct GameState {
    pub admin: Pubkey,
    pub score: u64,
    pub round: u64,
    pub bump: u8,
}

#[derive(Accounts)]
pub struct InitGame<'info> {
    // FIX: Use `init` instead of `init_if_needed`.
    // `init` calls System Program CreateAccount, which fails if the account
    // already exists. This makes re-initialization impossible.
    #[account(
        init,
        payer = user,
        space = 8 + 32 + 8 + 8 + 1,
        seeds = [b"game", user.key().as_ref()],
        bump,
    )]
    pub game: Account<'info, GameState>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

pub fn init_game(ctx: Context<InitGame>) -> Result<()> {
    let game = &mut ctx.accounts.game;
    game.admin = ctx.accounts.user.key();
    game.score = 0;
    game.round = 1;
    game.bump = ctx.bumps.game;
    // Safe: this handler can only run once per unique PDA.
    // Calling it again will fail at account creation.
    Ok(())
}
```

### Anchor Program (Fixed -- init_if_needed with Guard)

If `init_if_needed` is genuinely required (e.g., lazy initialization), add an explicit guard:

```rust
#[derive(Accounts)]
pub struct InitOrUseVault<'info> {
    #[account(
        init_if_needed,
        payer = user,
        space = 8 + std::mem::size_of::<Vault>(),
        seeds = [b"vault", user.key().as_ref()],
        bump,
    )]
    pub vault: Account<'info, Vault>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

pub fn init_or_use_vault(ctx: Context<InitOrUseVault>) -> Result<()> {
    let vault = &mut ctx.accounts.vault;

    // FIX: Only set authority on first init (when authority is default/zero).
    // On subsequent calls, the authority is already set and cannot be changed.
    if vault.authority == Pubkey::default() {
        // First initialization
        vault.authority = ctx.accounts.user.key();
        vault.balance = 0;
        vault.bump = ctx.bumps.vault;
    } else {
        // Already initialized -- verify the caller is the original authority.
        // Do NOT overwrite any state.
        require!(
            vault.authority == ctx.accounts.user.key(),
            ErrorCode::Unauthorized
        );
    }

    Ok(())
}
```

### Key Principle

Initialization instructions must be idempotent-safe: they either reject already-initialized accounts outright, or they detect the initialized state and refuse to overwrite critical fields. In Anchor, prefer `init` (which prevents re-init by construction) over `init_if_needed` (which requires careful handler logic). In native programs, check the discriminator or `is_initialized` flag before writing any state, and ensure the check logic is not inverted.
