# S-4: Missing Bump Canonicalization [MEDIUM]

Program Derived Addresses (PDAs) are found using `find_program_address`, which returns the **canonical bump** — the highest valid bump (255 down to 0) that produces a valid off-curve point. However, `create_program_address` accepts any bump value. If a program uses a user-supplied bump instead of the stored canonical bump, an attacker can create accounts at non-canonical PDA addresses (using lower bump values). This can lead to duplicate accounts for the same logical entity, bypassing uniqueness assumptions.

---

## Preconditions

- Program uses `create_program_address` (not `find_program_address`) for PDA validation
- The bump value is supplied by the user (passed as instruction data or stored in an account without verification)
- The program does not store the canonical bump from `find_program_address` and re-verify it on subsequent uses
- The program relies on PDA uniqueness for security (e.g., one vault per user, one config per pool)

---

## Vulnerable Pattern

### User-Supplied Bump in `create_program_address`

```rust
pub fn process_instruction(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let user = &accounts[0];
    let pda_account = &accounts[1];
    let bump = instruction_data[0]; // User-supplied bump!

    // VULNERABLE: accepts any bump value from the user
    // For seeds [b"vault", user_key], there are multiple valid bumps (255, 254, 253, ...)
    // Each produces a different PDA address
    let expected_pda = Pubkey::create_program_address(
        &[b"vault", user.key.as_ref(), &[bump]],
        program_id,
    )?;

    if expected_pda != *pda_account.key {
        return Err(ProgramError::InvalidSeeds);
    }

    // Attacker can create multiple "vaults" for the same user by using different bumps
    // Each is a valid PDA but at a different address

    Ok(())
}
```

### Initialization Without Storing Canonical Bump

```rust
pub fn initialize_vault(ctx: Context<InitializeVault>) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    vault.owner = ctx.accounts.user.key();
    vault.balance = 0;

    // VULNERABLE: bump is not stored
    // On subsequent access, the program has no way to verify canonical bump was used
    // (unless it calls find_program_address every time, which costs CU)

    Ok(())
}

#[derive(Accounts)]
pub struct InitializeVault<'info> {
    #[account(mut)]
    pub user: Signer<'info>,

    #[account(
        init,
        payer = user,
        space = 8 + Vault::INIT_SPACE,
        seeds = [b"vault", user.key().as_ref()],
        bump, // Anchor finds canonical bump — but doesn't store it automatically
    )]
    pub vault: Account<'info, Vault>,

    pub system_program: Program<'info, System>,
}

#[account]
pub struct Vault {
    pub owner: Pubkey,
    pub balance: u64,
    // Missing: pub bump: u8,
}
```

### Re-verification With User-Supplied Bump (Native)

```rust
pub fn withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let vault_info = &accounts[0];
    let user = &accounts[1];
    let amount = u64::from_le_bytes(instruction_data[0..8].try_into().unwrap());
    let bump = instruction_data[8]; // User-supplied bump again!

    // VULNERABLE: re-using user-supplied bump for PDA signing
    // If attacker initialized with a non-canonical bump, they can sign with it here
    let seeds = &[b"vault", user.key.as_ref(), &[bump]];

    invoke_signed(
        &transfer_ix,
        &[vault_info.clone(), user.clone()],
        &[seeds],
    )?;

    Ok(())
}
```

### Multiple Valid PDAs Exploited for Double-Init

```rust
pub fn create_user_profile(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    bump: u8, // User supplies the bump
    username: String,
) -> ProgramResult {
    let user = &accounts[0];
    let profile_account = &accounts[1];

    let pda = Pubkey::create_program_address(
        &[b"profile", user.key.as_ref(), &[bump]],
        program_id,
    )?;

    if pda != *profile_account.key {
        return Err(ProgramError::InvalidSeeds);
    }

    // VULNERABLE: attacker creates profile with bump=254 (non-canonical)
    // Then creates ANOTHER profile with bump=253
    // Program thinks each is unique because the PDA addresses differ
    // But logically they represent the same user's profile

    // Create and initialize the account at this PDA...

    Ok(())
}
```

---

## Detection Heuristics

### Grep Patterns

```
# Find create_program_address usage (potentially vulnerable)
create_program_address

# Find find_program_address (canonical — safe)
find_program_address

# Find bump as instruction data or user input
bump: u8
instruction_data
bump_seed

# Find invoke_signed with PDA seeds
invoke_signed
signer_seeds
```

### What to Search

1. **Find all `create_program_address` calls**: These accept arbitrary bumps — check where the bump comes from
2. **Check if bump is user-supplied**: Is the bump read from instruction data, function parameters, or a user-supplied account?
3. **Check if bump is stored in account state**: After `find_program_address`, is the canonical bump saved in the PDA's data?
4. **Check re-verification on subsequent instructions**: When the PDA is accessed again, is the stored canonical bump used (not a user-supplied one)?
5. **In Anchor**: Check if `bump = account.bump` is used in seeds constraints for subsequent instructions (not just `bump`)
6. **Check `invoke_signed` calls**: Where do the seeds (including bump) come from?

### Risk Indicators

- `create_program_address` with bump from `instruction_data` or function parameter
- PDA account struct without a `bump: u8` field
- `invoke_signed` where the bump in signer seeds is user-supplied
- `seeds` constraint in Anchor without `bump = account.bump` (just `bump` alone re-derives, which is safe but costs more CU)
- Native programs that never call `find_program_address`

---

## False Positives

1. **Anchor `bump` constraint auto-handles canonicalization**:
   ```rust
   #[account(
       seeds = [b"vault", user.key().as_ref()],
       bump, // Anchor calls find_program_address and verifies canonical bump
   )]
   pub vault: Account<'info, Vault>,
   ```
   When Anchor sees `bump` without a value, it calls `find_program_address` to derive and verify the canonical bump. This is always safe but costs extra CU.

2. **Anchor `bump = vault.bump` with stored canonical bump**:
   ```rust
   #[account(
       seeds = [b"vault", user.key().as_ref()],
       bump = vault.bump, // Uses stored canonical bump — safe and efficient
   )]
   pub vault: Account<'info, Vault>,
   ```

3. **`find_program_address` always returns canonical bump**:
   ```rust
   // This always returns the highest valid bump (canonical)
   let (pda, canonical_bump) = Pubkey::find_program_address(
       &[b"vault", user.key.as_ref()],
       program_id,
   );
   // canonical_bump is guaranteed to be the highest valid bump
   ```

4. **Program stores and re-uses the canonical bump consistently**:
   ```rust
   // Initialization: store canonical bump
   let (_, bump) = Pubkey::find_program_address(&seeds, program_id);
   vault.bump = bump; // Stored

   // Later: use stored bump, not user-supplied
   let seeds = &[b"vault", user.key.as_ref(), &[vault.bump]]; // From stored state
   invoke_signed(&ix, &accounts, &[seeds])?;
   ```

5. **Bump is only used for CPI signing, and the PDA address is validated via seeds** (the Anchor account validation already confirms the PDA is canonical before the instruction body runs).

---

## Remediation

### Store Canonical Bump at Initialization

```rust
#[derive(Accounts)]
pub struct InitializeVault<'info> {
    #[account(mut)]
    pub user: Signer<'info>,

    #[account(
        init,
        payer = user,
        space = 8 + Vault::INIT_SPACE,
        seeds = [b"vault", user.key().as_ref()],
        bump,
    )]
    pub vault: Account<'info, Vault>,

    pub system_program: Program<'info, System>,
}

pub fn initialize_vault(ctx: Context<InitializeVault>) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    vault.owner = ctx.accounts.user.key();
    vault.balance = 0;

    // SAFE: store the canonical bump for future use
    vault.bump = ctx.bumps.vault;

    Ok(())
}

#[account]
pub struct Vault {
    pub owner: Pubkey,
    pub balance: u64,
    pub bump: u8, // Store canonical bump
}
```

### Re-Verify Using Stored Canonical Bump

```rust
#[derive(Accounts)]
pub struct WithdrawFromVault<'info> {
    #[account(mut)]
    pub user: Signer<'info>,

    #[account(
        mut,
        seeds = [b"vault", user.key().as_ref()],
        bump = vault.bump, // SAFE: uses stored canonical bump, not user-supplied
        has_one = owner @ ErrorCode::InvalidOwner,
    )]
    pub vault: Account<'info, Vault>,

    #[account(mut)]
    pub vault_token: Account<'info, TokenAccount>,

    #[account(mut)]
    pub user_token: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}

pub fn withdraw(ctx: Context<WithdrawFromVault>, amount: u64) -> Result<()> {
    let vault = &ctx.accounts.vault;

    // SAFE: signer seeds use stored canonical bump
    let seeds = &[
        b"vault",
        ctx.accounts.user.key.as_ref(),
        &[vault.bump],
    ];
    let signer_seeds = &[&seeds[..]];

    token::transfer(
        CpiContext::new_with_signer(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.vault_token.to_account_info(),
                to: ctx.accounts.user_token.to_account_info(),
                authority: ctx.accounts.vault.to_account_info(),
            },
            signer_seeds,
        ),
        amount,
    )?;

    Ok(())
}
```

### Native Solana — Use `find_program_address` and Store

```rust
pub fn initialize(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let user = &accounts[0];
    let vault_info = &accounts[1];

    // SAFE: always derive canonical bump
    let (expected_pda, canonical_bump) = Pubkey::find_program_address(
        &[b"vault", user.key.as_ref()],
        program_id,
    );

    if expected_pda != *vault_info.key {
        return Err(ProgramError::InvalidSeeds);
    }

    // Create the account at the canonical PDA
    let seeds = &[b"vault", user.key.as_ref(), &[canonical_bump]];
    invoke_signed(
        &create_account_ix,
        &[user.clone(), vault_info.clone()],
        &[seeds],
    )?;

    // Store the canonical bump in account data
    let mut vault_data = vault_info.data.borrow_mut();
    vault_data[0] = canonical_bump; // First byte: canonical bump

    Ok(())
}

pub fn withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let vault_info = &accounts[0];
    let user = &accounts[1];

    // SAFE: read stored canonical bump, not user-supplied
    let vault_data = vault_info.data.borrow();
    let stored_bump = vault_data[0];

    // Verify PDA matches
    let expected_pda = Pubkey::create_program_address(
        &[b"vault", user.key.as_ref(), &[stored_bump]],
        program_id,
    )?;

    if expected_pda != *vault_info.key {
        return Err(ProgramError::InvalidSeeds);
    }

    // Sign CPI with stored canonical bump
    let seeds = &[b"vault", user.key.as_ref(), &[stored_bump]];
    invoke_signed(
        &transfer_ix,
        &[vault_info.clone(), user.clone()],
        &[seeds],
    )?;

    Ok(())
}
```

### Summary of Safe Patterns

| Pattern | Safe? | Notes |
|---------|-------|-------|
| `bump` in Anchor `seeds` constraint | Yes | Re-derives canonical bump (costs CU) |
| `bump = account.bump` in Anchor | Yes | Uses stored canonical bump (efficient) |
| `find_program_address` + store bump | Yes | Canonical by definition |
| `create_program_address` with user bump | **No** | User can supply non-canonical bump |
| `create_program_address` with stored bump | Yes | If stored bump was from `find_program_address` |
