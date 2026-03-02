# A-4: Privilege Escalation

**Severity:** CRITICAL
**Category:** Authentication & Authorization
**Taxonomy ID:** A-4

---

## Preconditions

All of the following must be true for this vulnerability to be exploitable:

1. The program has a **state account** that stores authority, admin, or role fields (e.g., `vault.authority`, `config.admin`, `pool.governance`)
2. An instruction exists that **modifies** one or more of these authority fields
3. The instruction does **not** properly restrict who can invoke the authority change
4. A successful call would grant the attacker **elevated privileges** (admin rights, withdrawal authority, governance control)

---

## Vulnerable Pattern

### Pattern 1: Authority update without access control

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct UpdateAuthority<'info> {
    // VULNERABLE: Any signer can call this -- no check that signer is current authority
    pub new_authority: Signer<'info>,

    #[account(mut)]
    pub vault: Account<'info, Vault>,
}

pub fn update_authority(ctx: Context<UpdateAuthority>) -> Result<()> {
    // VULNERABLE: Overwrites authority without verifying caller is the current authority
    ctx.accounts.vault.authority = ctx.accounts.new_authority.key();
    Ok(())
}

#[account]
pub struct Vault {
    pub authority: Pubkey,
    pub token_account: Pubkey,
    pub total_deposited: u64,
}
```

### Pattern 2: Initialization function callable after first init

```rust
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    program_error::ProgramError,
    pubkey::Pubkey,
};

pub fn process_initialize(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let admin = next_account_info(accounts_iter)?;
    let config_account = next_account_info(accounts_iter)?;

    if !admin.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    // VULNERABLE: No check that config_account is uninitialized.
    // Attacker can call initialize again to overwrite the admin field.
    let mut config = Config::default();
    config.admin = *admin.key;
    config.is_initialized = true;
    config.serialize(&mut &mut config_account.data.borrow_mut()[..])?;

    Ok(())
}
```

### Pattern 3: Role update with insufficient access control

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct SetRole<'info> {
    pub caller: Signer<'info>,

    #[account(mut)]
    pub protocol_config: Account<'info, ProtocolConfig>,
}

pub fn set_role(ctx: Context<SetRole>, target: Pubkey, role: Role) -> Result<()> {
    let config = &mut ctx.accounts.protocol_config;

    // VULNERABLE: Checks if caller is ANY operator, but operators should not
    // be able to grant admin roles or promote themselves.
    require!(
        config.operators.contains(&ctx.accounts.caller.key()),
        ErrorCode::Unauthorized
    );

    // An operator can make themselves an admin
    match role {
        Role::Admin => config.admin = target,       // Operator escalates to admin!
        Role::Operator => config.operators.push(target),
        Role::User => {},
    }

    Ok(())
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq)]
pub enum Role {
    Admin,
    Operator,
    User,
}
```

### Pattern 4: Unprotected admin transfer via two-field pattern

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct TransferAdmin<'info> {
    pub proposer: Signer<'info>,

    #[account(mut)]
    pub config: Account<'info, ProtocolConfig>,
}

pub fn transfer_admin(ctx: Context<TransferAdmin>, new_admin: Pubkey) -> Result<()> {
    // VULNERABLE: Only checks pending_admin == proposer, but pending_admin
    // was never properly set by the current admin -- anyone could have set it.
    require!(
        ctx.accounts.config.pending_admin == ctx.accounts.proposer.key(),
        ErrorCode::Unauthorized
    );

    ctx.accounts.config.admin = new_admin;
    ctx.accounts.config.pending_admin = Pubkey::default();

    Ok(())
}
```

---

## Detection Heuristics

### Step 1: Identify authority/role fields in state accounts

Search for account structs that store authority, admin, owner, or role-related fields.

**Grep patterns:**
```
# Find authority fields in account structs
grep -n "pub authority\|pub admin\|pub owner\|pub governance\|pub operator\|pub role" lib.rs

# Find state account definitions
grep -n "#\[account\]" lib.rs
```

### Step 2: Find instructions that modify authority fields

Search for instructions that write to these authority/role fields.

**Grep patterns:**
```
# Direct field assignment
grep -n "\.authority\s*=\|\.admin\s*=\|\.owner\s*=\|\.governance\s*=" lib.rs

# Set/update/transfer function names
grep -n "update_authority\|set_admin\|transfer_ownership\|set_role\|change_admin" lib.rs
```

### Step 3: Verify access control on authority-modifying instructions

For each instruction that modifies an authority field, verify:

1. **The caller is the current authority** -- the instruction must check that the signer matches the existing authority stored in state
2. **The role hierarchy is enforced** -- lower-privilege roles cannot grant higher-privilege roles
3. **Initialization is one-time** -- `initialize` instructions cannot be called on already-initialized accounts

**Anchor patterns to look for:**
```rust
// SAFE: has_one ensures only current authority can change it
#[account(mut, has_one = authority)]
pub vault: Account<'info, Vault>,

// SAFE: constraint restricts to admin only
#[account(mut, constraint = config.admin == caller.key())]
pub config: Account<'info, ProtocolConfig>,
```

### Step 4: Check for reinitialization vectors

Even if authority-update instructions are properly guarded, check if `initialize` can be called again to reset the authority.

```
# Find initialization instructions
grep -n "pub fn initialize\|pub fn init\|process_initialize" lib.rs processor.rs

# Check for init constraint (Anchor prevents re-init)
grep -n "init," lib.rs
```

---

## False Positives

### 1. Proper two-step authority transfer

A two-step (propose/accept) transfer pattern is a security best practice, not a vulnerability:

```rust
// Step 1: Current admin proposes new admin (only current admin can call)
pub fn propose_new_admin(ctx: Context<ProposeAdmin>, new_admin: Pubkey) -> Result<()> {
    let config = &mut ctx.accounts.config;
    // has_one = admin ensures only current admin can propose
    config.pending_admin = new_admin;
    Ok(())
}

// Step 2: Proposed admin accepts (only pending admin can call)
pub fn accept_admin(ctx: Context<AcceptAdmin>) -> Result<()> {
    let config = &mut ctx.accounts.config;
    require!(
        config.pending_admin == ctx.accounts.new_admin.key(),
        ErrorCode::Unauthorized
    );
    config.admin = config.pending_admin;
    config.pending_admin = Pubkey::default();
    Ok(())
}

#[derive(Accounts)]
pub struct ProposeAdmin<'info> {
    pub admin: Signer<'info>,
    #[account(mut, has_one = admin)]  // Only current admin can propose
    pub config: Account<'info, ProtocolConfig>,
}

#[derive(Accounts)]
pub struct AcceptAdmin<'info> {
    pub new_admin: Signer<'info>,
    #[account(mut)]
    pub config: Account<'info, ProtocolConfig>,
}
```

### 2. Governance-controlled updates

Authority updates that go through an on-chain governance process (DAO vote, multisig threshold) are intentionally designed to allow authority changes.

```rust
// SAFE — update requires governance proposal to have passed
#[derive(Accounts)]
pub struct GovernanceUpdate<'info> {
    #[account(
        constraint = proposal.status == ProposalStatus::Executed,
        constraint = proposal.governance == config.governance,
    )]
    pub proposal: Account<'info, Proposal>,

    #[account(mut)]
    pub config: Account<'info, ProtocolConfig>,
}
```

### 3. Factory/deployer patterns

Some protocols have a factory that initializes new instances. The factory sets the initial authority as part of deployment. This is safe if the factory itself is properly access-controlled.

```rust
// SAFE — factory pattern; deployer becomes authority for their own pool
pub fn create_pool(ctx: Context<CreatePool>) -> Result<()> {
    let pool = &mut ctx.accounts.pool;
    pool.authority = ctx.accounts.deployer.key(); // Deployer sets their own authority
    pool.is_initialized = true;
    Ok(())
}
```

### 4. Self-referential authority (user manages own account)

If each user has their own account and can only modify their own authority, this is typically by design.

```rust
// SAFE — user can only change authority on their own account (PDA seeded by user)
#[derive(Accounts)]
pub struct UpdateMyAuthority<'info> {
    pub current_authority: Signer<'info>,

    #[account(
        mut,
        has_one = current_authority,
        seeds = [b"user_vault", current_authority.key().as_ref()],
        bump,
    )]
    pub user_vault: Account<'info, UserVault>,
}
```

---

## Remediation

### Restrict authority updates to the current authority

```rust
#[derive(Accounts)]
pub struct UpdateAuthority<'info> {
    // FIX: Current authority must sign the transaction
    pub authority: Signer<'info>,

    // FIX: has_one ensures vault.authority == authority.key()
    #[account(
        mut,
        has_one = authority @ ErrorCode::Unauthorized,
    )]
    pub vault: Account<'info, Vault>,
}

pub fn update_authority(ctx: Context<UpdateAuthority>, new_authority: Pubkey) -> Result<()> {
    ctx.accounts.vault.authority = new_authority;
    Ok(())
}
```

### Implement two-step transfer (recommended for high-value authorities)

```rust
#[account]
pub struct ProtocolConfig {
    pub admin: Pubkey,
    pub pending_admin: Pubkey,
    // ... other fields
}

// Step 1: Current admin proposes
#[derive(Accounts)]
pub struct ProposeAdmin<'info> {
    pub admin: Signer<'info>,
    #[account(mut, has_one = admin)]
    pub config: Account<'info, ProtocolConfig>,
}

pub fn propose_admin(ctx: Context<ProposeAdmin>, new_admin: Pubkey) -> Result<()> {
    ctx.accounts.config.pending_admin = new_admin;
    emit!(AdminProposed { new_admin });
    Ok(())
}

// Step 2: New admin accepts
#[derive(Accounts)]
pub struct AcceptAdmin<'info> {
    pub new_admin: Signer<'info>,
    #[account(
        mut,
        constraint = config.pending_admin == new_admin.key() @ ErrorCode::NotPendingAdmin,
    )]
    pub config: Account<'info, ProtocolConfig>,
}

pub fn accept_admin(ctx: Context<AcceptAdmin>) -> Result<()> {
    let config = &mut ctx.accounts.config;
    config.admin = config.pending_admin;
    config.pending_admin = Pubkey::default();
    emit!(AdminTransferred { new_admin: config.admin });
    Ok(())
}
```

### Prevent reinitialization

**Native:**
```rust
pub fn process_initialize(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let config_account = next_account_info(accounts_iter)?;

    // FIX: Check that account is not already initialized
    let existing_data = config_account.data.borrow();
    if existing_data[0] != 0 {
        return Err(ProgramError::AccountAlreadyInitialized);
    }
    drop(existing_data);

    // Safe to initialize
    let mut config = Config::default();
    config.is_initialized = true;
    config.admin = *admin.key;
    config.serialize(&mut &mut config_account.data.borrow_mut()[..])?;
    Ok(())
}
```

**Anchor:**
```rust
// SAFE — Anchor's init constraint checks discriminator to prevent re-init
#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,

    #[account(
        init,  // Anchor will reject if account already has a valid discriminator
        payer = admin,
        space = 8 + ProtocolConfig::INIT_SPACE,
    )]
    pub config: Account<'info, ProtocolConfig>,

    pub system_program: Program<'info, System>,
}
```

### Enforce role hierarchy

```rust
pub fn set_role(ctx: Context<SetRole>, target: Pubkey, role: Role) -> Result<()> {
    let config = &mut ctx.accounts.protocol_config;
    let caller_key = ctx.accounts.caller.key();

    // FIX: Enforce role hierarchy
    match role {
        Role::Admin => {
            // Only current admin can grant admin role
            require!(config.admin == caller_key, ErrorCode::AdminOnly);
            config.admin = target;
        },
        Role::Operator => {
            // Only admin can add operators
            require!(config.admin == caller_key, ErrorCode::AdminOnly);
            config.operators.push(target);
        },
        Role::User => {
            // Operators or admin can manage users
            require!(
                config.admin == caller_key
                    || config.operators.contains(&caller_key),
                ErrorCode::InsufficientRole
            );
        },
    }

    Ok(())
}
```

---

## References

- Taxonomy: A-4 in `vulnerability-taxonomy.md`
- Related: A-1 (Missing Signer Check) -- no signer at all
- Related: A-3 (Missing Authority Validation) -- signer not matched to stored authority
- Related: A-5 (Instruction Access Control) -- broader access control failures
- Related: S-7 (Reinitialization) -- re-init as an escalation vector
