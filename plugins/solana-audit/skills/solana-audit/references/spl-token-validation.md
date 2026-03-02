# T-1: SPL Token Account Validation [HIGH]

Token accounts passed to an instruction must be validated for the correct **mint** (token type) and **authority** (owner). Without these checks, an attacker can substitute a worthless token where a valuable one is expected, or pass a token account they control where a protocol-owned account should be. This is one of the most common vulnerability classes in Solana programs — any instruction that accepts a `TokenAccount` without verifying its mint and authority is potentially exploitable.

---

## Preconditions

- Program accepts SPL Token accounts (`TokenAccount`) as instruction parameters
- The instruction performs transfers, burns, mints, or reads balances on these accounts
- Token accounts are not validated against expected mint pubkey or expected owner/authority
- The program does not use Anchor's `token::mint` and `token::authority` constraints (or equivalent native checks)

---

## Vulnerable Pattern

### Missing Mint Validation — Wrong Token Accepted

```rust
pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> {
    let user_token = &ctx.accounts.user_token_account;
    let vault_token = &ctx.accounts.vault_token_account;

    // VULNERABLE: no check that user_token.mint == expected_mint
    // Attacker creates a worthless token with the same mint authority structure
    // and deposits it instead of the valuable token

    token::transfer(
        CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: user_token.to_account_info(),
                to: vault_token.to_account_info(),
                authority: ctx.accounts.user.to_account_info(),
            },
        ),
        amount,
    )?;

    // Protocol credits user as if they deposited the real token
    let user_state = &mut ctx.accounts.user_state;
    user_state.deposited_amount = user_state.deposited_amount
        .checked_add(amount)
        .ok_or(ErrorCode::MathOverflow)?;

    Ok(())
}

#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mut)]
    pub user_token_account: Account<'info, TokenAccount>, // No mint check!
    #[account(mut)]
    pub vault_token_account: Account<'info, TokenAccount>, // No mint check!
    #[account(mut)]
    pub user_state: Account<'info, UserState>,
    pub token_program: Program<'info, Token>,
}
```

### Missing Authority Validation — Unauthorized Withdrawal

```rust
pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
    let vault = &ctx.accounts.vault;

    // VULNERABLE: destination token account is not validated
    // Attacker can pass any destination they own
    // The PDA signs the transfer, so no user signature needed on the destination

    let seeds = &[b"vault", &[vault.bump]];
    let signer_seeds = &[&seeds[..]];

    token::transfer(
        CpiContext::new_with_signer(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.vault_token.to_account_info(),
                to: ctx.accounts.destination.to_account_info(), // Not validated!
                authority: ctx.accounts.vault_authority.to_account_info(),
            },
            signer_seeds,
        ),
        amount,
    )?;

    Ok(())
}

#[derive(Accounts)]
pub struct Withdraw<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mut)]
    pub vault: Account<'info, Vault>,
    #[account(mut)]
    pub vault_token: Account<'info, TokenAccount>, // No authority/mint check!
    #[account(mut)]
    pub destination: Account<'info, TokenAccount>, // No owner check!
    /// CHECK: PDA authority
    pub vault_authority: AccountInfo<'info>,
    pub token_program: Program<'info, Token>,
}
```

### Native Program — Raw Deserialization Without Validation

```rust
pub fn process_swap(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let source_token_info = &accounts[0];
    let dest_token_info = &accounts[1];
    let authority = &accounts[2];

    // Deserialize token accounts
    let source = TokenAccount::unpack(&source_token_info.data.borrow())?;
    let dest = TokenAccount::unpack(&dest_token_info.data.borrow())?;

    // VULNERABLE: no mint validation
    // source.mint could be a different token than dest.mint
    // Attacker: deposit worthless token in source, receive valuable token in dest

    // VULNERABLE: no authority validation
    // source.owner could be anyone — not necessarily the signer

    // Perform the swap...
    Ok(())
}
```

### Missing Vault Token Account Validation

```rust
#[derive(Accounts)]
pub struct Stake<'info> {
    #[account(mut)]
    pub user: Signer<'info>,

    #[account(
        mut,
        seeds = [b"pool"],
        bump = pool.bump,
    )]
    pub pool: Account<'info, StakePool>,

    // VULNERABLE: vault_token is not verified to be THE vault for this pool
    // Attacker can pass any token account as the "vault"
    #[account(mut)]
    pub vault_token: Account<'info, TokenAccount>,

    #[account(mut)]
    pub user_token: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}
```

---

## Detection Heuristics

### Grep Patterns

```
# Find token account parameters without constraints
Account<'info, TokenAccount>
token_account
user_token
vault_token
source_token
dest_token

# Find Anchor token constraints (safe patterns)
token::mint
token::authority
has_one = mint

# Find raw token account deserialization (native)
TokenAccount::unpack
spl_token::state::Account::unpack

# Find transfers that might use unvalidated accounts
token::transfer
Transfer {
invoke(
```

### What to Search

1. **Find all `TokenAccount` parameters** in instruction account structs
2. **Check for `token::mint` constraint**: Every token account should validate its mint matches the expected mint
3. **Check for `token::authority` constraint**: Token accounts used as sources should validate authority matches the signer or the expected PDA
4. **Check for `has_one` on parent accounts**: If a vault stores its token account pubkey, check `has_one = token_account`
5. **In native programs**: After `TokenAccount::unpack`, check for `source.mint == expected_mint` and `source.owner == expected_owner`
6. **Check destination accounts**: Even destination token accounts need mint validation (to prevent sending tokens to the wrong mint)
7. **Check associated token account derivation**: If using ATAs, verify they're derived from the correct mint and owner

### Risk Indicators

- `Account<'info, TokenAccount>` without any `token::mint` or `token::authority` constraint
- Token accounts validated only by seeds (PDA) but not by mint
- `/// CHECK:` on token accounts without proper justification
- Native programs that `unpack` token accounts without subsequent mint/owner assertions
- Transfer instructions where the destination is user-supplied without mint validation

---

## False Positives

1. **Anchor `token::mint` and `token::authority` constraints present**:
   ```rust
   #[account(
       mut,
       token::mint = pool.token_mint,
       token::authority = user,
   )]
   pub user_token: Account<'info, TokenAccount>,
   ```

2. **PDA-derived token accounts** (validated by seeds, which implicitly constrains the mint):
   ```rust
   #[account(
       mut,
       seeds = [b"vault", pool.token_mint.as_ref()],
       bump,
       token::mint = pool.token_mint,
       token::authority = vault_authority,
   )]
   pub vault_token: Account<'info, TokenAccount>,
   ```

3. **`has_one` constraint linking token account to parent state**:
   ```rust
   #[account(
       mut,
       has_one = vault_token_account, // Verifies pool.vault_token_account == vault_token_account.key()
   )]
   pub pool: Account<'info, Pool>,
   #[account(mut)]
   pub vault_token_account: Account<'info, TokenAccount>,
   ```

4. **Associated Token Account (ATA) derivation checked**:
   ```rust
   #[account(
       mut,
       associated_token::mint = token_mint,
       associated_token::authority = user,
   )]
   pub user_ata: Account<'info, TokenAccount>,
   ```

5. **Native program with explicit validation after deserialization**:
   ```rust
   let source = TokenAccount::unpack(&source_info.data.borrow())?;
   if source.mint != expected_mint {
       return Err(ProgramError::InvalidArgument);
   }
   if source.owner != *authority.key {
       return Err(ProgramError::InvalidArgument);
   }
   ```

---

## Remediation

### Anchor — Use `token::mint` and `token::authority` Constraints

```rust
#[derive(Accounts)]
pub struct SafeDeposit<'info> {
    #[account(mut)]
    pub user: Signer<'info>,

    #[account(
        mut,
        seeds = [b"pool"],
        bump = pool.bump,
    )]
    pub pool: Account<'info, StakePool>,

    // SAFE: validates mint matches pool's expected mint
    // SAFE: validates authority is the user (signer)
    #[account(
        mut,
        token::mint = pool.token_mint,
        token::authority = user,
    )]
    pub user_token: Account<'info, TokenAccount>,

    // SAFE: vault validated by has_one + mint constraint
    #[account(
        mut,
        constraint = vault_token.key() == pool.vault_token @ ErrorCode::InvalidVault,
        token::mint = pool.token_mint,
    )]
    pub vault_token: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}
```

### Anchor — Use Associated Token Account Constraints

```rust
#[derive(Accounts)]
pub struct SafeTransfer<'info> {
    #[account(mut)]
    pub user: Signer<'info>,

    pub token_mint: Account<'info, Mint>,

    // SAFE: ATA is deterministically derived from mint + owner
    // Anchor verifies derivation automatically
    #[account(
        mut,
        associated_token::mint = token_mint,
        associated_token::authority = user,
    )]
    pub user_ata: Account<'info, TokenAccount>,

    // SAFE: vault ATA derived from mint + PDA authority
    #[account(
        mut,
        associated_token::mint = token_mint,
        associated_token::authority = vault_authority,
    )]
    pub vault_ata: Account<'info, TokenAccount>,

    /// CHECK: PDA authority for vault
    #[account(seeds = [b"vault_authority"], bump)]
    pub vault_authority: AccountInfo<'info>,

    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
}
```

### Native Solana — Explicit Mint and Owner Checks

```rust
pub fn process_deposit(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let source_info = &accounts[0];
    let vault_info = &accounts[1];
    let authority_info = &accounts[2];
    let token_program_info = &accounts[3];

    // Validate token program
    if token_program_info.key != &spl_token::ID {
        return Err(ProgramError::IncorrectProgramId);
    }

    // Validate source token account
    let source = TokenAccount::unpack(&source_info.data.borrow())?;

    // SAFE: check mint matches expected
    if source.mint != EXPECTED_MINT {
        return Err(ProgramError::InvalidArgument);
    }

    // SAFE: check authority is the signer
    if source.owner != *authority_info.key {
        return Err(ProgramError::InvalidArgument);
    }
    if !authority_info.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    // Validate vault token account
    let vault = TokenAccount::unpack(&vault_info.data.borrow())?;

    // SAFE: check vault mint matches
    if vault.mint != EXPECTED_MINT {
        return Err(ProgramError::InvalidArgument);
    }

    // SAFE: check vault is owned by the program's PDA
    if vault.owner != expected_vault_authority {
        return Err(ProgramError::InvalidArgument);
    }

    // Now safe to transfer
    let ix = spl_token::instruction::transfer(
        &spl_token::ID,
        source_info.key,
        vault_info.key,
        authority_info.key,
        &[],
        amount,
    )?;

    invoke(&ix, &[
        source_info.clone(),
        vault_info.clone(),
        authority_info.clone(),
        token_program_info.clone(),
    ])?;

    Ok(())
}
```

### Validate Mint Account Itself

```rust
#[derive(Accounts)]
pub struct MintTokens<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,

    // Validate the mint is the correct one
    #[account(
        mut,
        constraint = token_mint.key() == pool.token_mint @ ErrorCode::InvalidMint,
    )]
    pub token_mint: Account<'info, Mint>,

    // Validate destination is for the correct mint
    #[account(
        mut,
        token::mint = token_mint,
    )]
    pub destination: Account<'info, TokenAccount>,

    #[account(
        has_one = authority,
        has_one = token_mint,
    )]
    pub pool: Account<'info, Pool>,

    pub token_program: Program<'info, Token>,
}
```
