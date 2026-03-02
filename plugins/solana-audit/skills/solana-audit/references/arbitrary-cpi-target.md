# C-1: Arbitrary CPI Target [CRITICAL]

A Cross-Program Invocation (CPI) uses a user-supplied program ID without validating it against a known constant. An attacker substitutes a malicious program that mimics the expected interface but performs a different action — such as approving a token transfer to the attacker instead of the intended recipient. This was the root cause of the **Wormhole bridge exploit ($326M, February 2022)** and the **Crema Finance exploit ($8.8M, July 2022)**.

---

## Preconditions

- Program makes a CPI call using `invoke` or `invoke_signed`
- The target program's `AccountInfo` is passed by the caller (not hardcoded in the program)
- The program does not validate that the target program's key matches a known, expected program ID
- The CPI call involves transferring value, minting tokens, or modifying critical state

---

## Vulnerable Pattern

### Native Solana — User-Supplied Program in `invoke`

```rust
pub fn process_instruction(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let token_program = &accounts[0];  // User-supplied!
    let source = &accounts[1];
    let destination = &accounts[2];
    let authority = &accounts[3];
    let amount = u64::from_le_bytes(instruction_data[..8].try_into().unwrap());

    // VULNERABLE: token_program is whatever the caller passed
    // Attacker deploys a fake program that accepts this instruction
    // and transfers tokens to the attacker instead
    let ix = spl_token::instruction::transfer(
        token_program.key, // Attacker's malicious program ID
        source.key,
        destination.key,
        authority.key,
        &[],
        amount,
    )?;

    invoke(&ix, &[
        source.clone(),
        destination.clone(),
        authority.clone(),
        token_program.clone(),
    ])?;

    Ok(())
}
```

### Wormhole Pattern — Unverified System Program in CPI

```rust
pub fn complete_transfer(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    vaa_data: &[u8],
) -> ProgramResult {
    let system_program = &accounts[5]; // User-supplied!

    // Verify the VAA signature (guardian signature check)
    // ... signature verification passes ...

    // VULNERABLE: system_program is not validated
    // Attacker passes a fake system_program that pretends to create an account
    // but doesn't actually verify signatures or do anything
    let create_ix = system_instruction::create_account(
        payer.key,
        new_account.key,
        lamports,
        space,
        owner,
    );

    invoke(&create_ix, &[
        payer.clone(),
        new_account.clone(),
        system_program.clone(), // Could be attacker's program!
    ])?;

    Ok(())
}
```

### Crema Pattern — Unverified Swap Program

```rust
pub fn harvest_fees(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let swap_program = &accounts[0]; // User-supplied!
    let pool = &accounts[1];
    let fee_account = &accounts[2];

    // VULNERABLE: swap_program is not validated
    // Attacker passes a program that returns fake swap results
    // allowing them to claim fees they didn't earn
    let swap_ix = Instruction {
        program_id: *swap_program.key,
        accounts: vec![
            AccountMeta::new(*pool.key, false),
            AccountMeta::new(*fee_account.key, false),
        ],
        data: swap_data,
    };

    invoke(&swap_ix, &[
        pool.clone(),
        fee_account.clone(),
        swap_program.clone(),
    ])?;

    Ok(())
}
```

### Anchor — Untyped Program Account

```rust
#[derive(Accounts)]
pub struct SwapTokens<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mut)]
    pub source_token: Account<'info, TokenAccount>,
    #[account(mut)]
    pub dest_token: Account<'info, TokenAccount>,

    // VULNERABLE: no constraint verifying this is the real token program
    /// CHECK: token program
    pub token_program: AccountInfo<'info>,
}

pub fn swap_tokens(ctx: Context<SwapTokens>, amount: u64) -> Result<()> {
    // CPI using unverified token_program
    let cpi_ctx = CpiContext::new(
        ctx.accounts.token_program.to_account_info(), // Could be malicious!
        Transfer {
            from: ctx.accounts.source_token.to_account_info(),
            to: ctx.accounts.dest_token.to_account_info(),
            authority: ctx.accounts.user.to_account_info(),
        },
    );
    token::transfer(cpi_ctx, amount)?;
    Ok(())
}
```

---

## Detection Heuristics

### Grep Patterns

```
# Find all CPI calls
invoke(
invoke_signed(
CpiContext::new(
CpiContext::new_with_signer(

# Find program accounts that might be user-supplied
/// CHECK
AccountInfo<'info>
UncheckedAccount<'info>
program_id:
token_program
system_program
associated_token_program
```

### What to Search

1. **Find all `invoke` and `invoke_signed` calls**: These are CPI entry points
2. **Trace the program ID**: Where does the `program_id` field of the instruction come from?
   - If it's a constant (`spl_token::ID`, `system_program::ID`) — safe
   - If it's from an `AccountInfo` passed by the caller — **potentially vulnerable**
3. **Check for program ID validation**: Before the CPI, is there a check like `require!(program.key() == spl_token::ID)`?
4. **In Anchor**: Look for `AccountInfo<'info>` or `UncheckedAccount<'info>` used as program accounts. Safe alternatives are `Program<'info, Token>`, `Program<'info, System>`, etc.
5. **Check `/// CHECK:` comments**: Anchor requires these for unchecked accounts — the justification should include program ID validation

### Risk Indicators

- `invoke` where the first argument's `program_id` comes from `accounts[N].key`
- `CpiContext::new(some_account_info, ...)` where `some_account_info` is an `AccountInfo` not a `Program<'info, T>`
- `/// CHECK: token program` without an accompanying `constraint = token_program.key() == spl_token::ID`
- Missing `Program<'info, Token>` in Anchor account structs where token CPI happens
- Any CPI to a "configurable" program address stored in state without validation

---

## False Positives

1. **Program ID validated against a known constant**:
   ```rust
   // Native check — safe
   if token_program.key != &spl_token::ID {
       return Err(ProgramError::IncorrectProgramId);
   }
   invoke(&ix, &[...])?;
   ```

2. **Anchor `Program<'info, T>` type constraint** — automatically validates:
   ```rust
   #[derive(Accounts)]
   pub struct SafeTransfer<'info> {
       // Anchor verifies this is the real SPL Token program
       pub token_program: Program<'info, Token>,
   }
   ```

3. **Anchor `CpiContext` with typed program from `Program<'info, T>`**:
   ```rust
   let cpi_ctx = CpiContext::new(
       ctx.accounts.token_program.to_account_info(), // Safe: token_program is Program<'info, Token>
       Transfer { from, to, authority },
   );
   ```

4. **Explicit constraint on the account**:
   ```rust
   #[derive(Accounts)]
   pub struct MyInstruction<'info> {
       /// CHECK: validated below
       #[account(constraint = token_program.key() == spl_token::ID)]
       pub token_program: AccountInfo<'info>,
   }
   ```

5. **CPI to the program's own ID** (self-CPI with hardcoded `program_id`):
   ```rust
   invoke(
       &Instruction { program_id: *program_id, .. }, // program_id is the current program
       &[...],
   )?;
   ```

---

## Remediation

### Native Solana — Validate Program ID Before CPI

```rust
pub fn process_instruction(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let token_program = &accounts[0];

    // SAFE: validate the program ID is the expected SPL Token program
    if token_program.key != &spl_token::ID {
        return Err(ProgramError::IncorrectProgramId);
    }

    let ix = spl_token::instruction::transfer(
        token_program.key,
        source.key,
        destination.key,
        authority.key,
        &[],
        amount,
    )?;

    invoke(&ix, &[
        source.clone(),
        destination.clone(),
        authority.clone(),
        token_program.clone(),
    ])?;

    Ok(())
}
```

### Anchor — Use `Program<'info, T>` Type

```rust
use anchor_spl::token::{self, Token, Transfer};

#[derive(Accounts)]
pub struct SafeSwap<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mut)]
    pub source_token: Account<'info, TokenAccount>,
    #[account(mut)]
    pub dest_token: Account<'info, TokenAccount>,

    // SAFE: Program<'info, Token> verifies key == spl_token::ID
    pub token_program: Program<'info, Token>,

    // SAFE: Program<'info, System> verifies key == system_program::ID
    pub system_program: Program<'info, System>,
}

pub fn safe_swap(ctx: Context<SafeSwap>, amount: u64) -> Result<()> {
    let cpi_ctx = CpiContext::new(
        ctx.accounts.token_program.to_account_info(),
        Transfer {
            from: ctx.accounts.source_token.to_account_info(),
            to: ctx.accounts.dest_token.to_account_info(),
            authority: ctx.accounts.user.to_account_info(),
        },
    );
    token::transfer(cpi_ctx, amount)?;
    Ok(())
}
```

### Hardcode Program IDs as Constants

```rust
use solana_program::pubkey;

// Hardcode known program IDs
pub const TOKEN_PROGRAM_ID: Pubkey = pubkey!("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
pub const ASSOCIATED_TOKEN_PROGRAM_ID: Pubkey = pubkey!("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL");
pub const SYSTEM_PROGRAM_ID: Pubkey = pubkey!("11111111111111111111111111111111");

pub fn process_cpi(accounts: &[AccountInfo]) -> ProgramResult {
    let token_program = &accounts[0];

    // SAFE: compare against hardcoded constant
    if token_program.key != &TOKEN_PROGRAM_ID {
        return Err(ProgramError::IncorrectProgramId);
    }

    // ... proceed with CPI
    Ok(())
}
```

### For Configurable Programs (Governance-Controlled)

```rust
#[derive(Accounts)]
pub struct ConfigurableCpi<'info> {
    #[account(
        seeds = [b"config"],
        bump = config.bump,
    )]
    pub config: Account<'info, ProgramConfig>,

    /// CHECK: validated against stored config
    #[account(constraint = target_program.key() == config.approved_program_id
              @ ErrorCode::InvalidProgramId)]
    pub target_program: AccountInfo<'info>,
}

#[account]
pub struct ProgramConfig {
    pub approved_program_id: Pubkey, // Set by governance/admin
    pub bump: u8,
}
```
