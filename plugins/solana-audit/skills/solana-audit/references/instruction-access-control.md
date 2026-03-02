# A-5: Instruction Access Control

**Severity:** HIGH
**Category:** Authentication & Authorization
**Taxonomy ID:** A-5

---

## Preconditions

All of the following must be true for this vulnerability to be exploitable:

1. The program has **privileged instructions** -- instructions intended for specific roles (admin, governance, operator, emergency multisig)
2. These instructions perform **sensitive operations** (pausing the protocol, updating fee parameters, draining insurance funds, upgrading configurations, freezing accounts)
3. The instruction **lacks proper role-based access control** -- it is callable by anyone, or the access control is insufficient

---

## Vulnerable Pattern

### Pattern 1: Admin instruction with no access control

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct PauseProtocol<'info> {
    // VULNERABLE: Any signer can pause the protocol -- no admin check
    pub caller: Signer<'info>,

    #[account(mut)]
    pub protocol_state: Account<'info, ProtocolState>,
}

pub fn pause_protocol(ctx: Context<PauseProtocol>) -> Result<()> {
    // No check that caller is the admin or has pause authority
    ctx.accounts.protocol_state.is_paused = true;
    Ok(())
}

#[account]
pub struct ProtocolState {
    pub admin: Pubkey,
    pub emergency_admin: Pubkey,
    pub is_paused: bool,
    pub fee_bps: u16,
    pub treasury: Pubkey,
}
```

### Pattern 2: Fee/parameter update without restriction

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct UpdateFees<'info> {
    pub caller: Signer<'info>,

    // VULNERABLE: No has_one or constraint checking admin
    #[account(mut)]
    pub protocol_state: Account<'info, ProtocolState>,
}

pub fn update_fees(ctx: Context<UpdateFees>, new_fee_bps: u16) -> Result<()> {
    // Any signer can set fees to anything -- could set to 10000 bps (100%)
    ctx.accounts.protocol_state.fee_bps = new_fee_bps;
    Ok(())
}
```

### Pattern 3: Emergency withdraw without access control (native)

```rust
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    program_error::ProgramError,
    pubkey::Pubkey,
};

pub fn process_emergency_withdraw(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let caller = next_account_info(accounts_iter)?;
    let treasury = next_account_info(accounts_iter)?;
    let destination = next_account_info(accounts_iter)?;

    if !caller.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    // VULNERABLE: Signer check present, but no check that caller == admin
    // Any signer can drain the treasury via "emergency" withdraw
    let treasury_data = Treasury::try_from_slice(&treasury.data.borrow())?;

    transfer_all_tokens(
        &treasury_data.token_account,
        destination.key,
        treasury_data.balance,
    )?;

    Ok(())
}
```

### Pattern 4: Insufficient role granularity

```rust
use anchor_lang::prelude::*;

#[derive(Accounts)]
pub struct AdminAction<'info> {
    pub operator: Signer<'info>,

    #[account(
        mut,
        // VULNERABLE: Only checks operator role, but some actions require admin
        constraint = protocol.operators.contains(&operator.key())
            @ ErrorCode::Unauthorized,
    )]
    pub protocol: Account<'info, ProtocolState>,
}

pub fn emergency_shutdown(ctx: Context<AdminAction>) -> Result<()> {
    // VULNERABLE: Emergency shutdown should require admin, not just operator.
    // An operator (lower-privilege role) can shut down the entire protocol.
    ctx.accounts.protocol.is_paused = true;
    ctx.accounts.protocol.withdrawals_disabled = true;
    ctx.accounts.protocol.deposits_disabled = true;
    Ok(())
}

pub fn update_oracle(ctx: Context<AdminAction>, new_oracle: Pubkey) -> Result<()> {
    // VULNERABLE: Oracle update should require admin/governance, not operator.
    // A compromised operator key can redirect the oracle to a malicious feed.
    ctx.accounts.protocol.oracle = new_oracle;
    Ok(())
}
```

### Pattern 5: Instruction dispatch without role check (native)

```rust
pub fn process_instruction(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let instruction = ProgramInstruction::try_from_slice(instruction_data)?;

    match instruction {
        ProgramInstruction::Deposit { amount } => process_deposit(program_id, accounts, amount),
        ProgramInstruction::Withdraw { amount } => process_withdraw(program_id, accounts, amount),

        // VULNERABLE: Admin instructions dispatched without any additional
        // access control at the dispatch level. Each handler must implement
        // its own checks -- if any handler forgets, it's exploitable.
        ProgramInstruction::Pause => process_pause(program_id, accounts),
        ProgramInstruction::UpdateFee { fee } => process_update_fee(program_id, accounts, fee),
        ProgramInstruction::EmergencyDrain => process_emergency_drain(program_id, accounts),
    }
}
```

---

## Detection Heuristics

### Step 1: Identify privileged instructions

Search for instructions that perform sensitive operations.

**Grep patterns for function names:**
```
grep -n "pub fn.*pause\|pub fn.*unpause\|pub fn.*freeze\|pub fn.*emergency\|pub fn.*shutdown" lib.rs
grep -n "pub fn.*update_fee\|pub fn.*set_fee\|pub fn.*update_config\|pub fn.*set_param" lib.rs
grep -n "pub fn.*set_oracle\|pub fn.*update_oracle\|pub fn.*set_treasury" lib.rs
grep -n "pub fn.*migrate\|pub fn.*upgrade\|pub fn.*set_authority\|pub fn.*update_admin" lib.rs
grep -n "pub fn.*whitelist\|pub fn.*blacklist\|pub fn.*set_role" lib.rs
```

**Grep patterns for state mutations that indicate admin actions:**
```
grep -n "is_paused\s*=\|fee_bps\s*=\|oracle\s*=\|treasury\s*=" lib.rs
grep -n "withdrawals_disabled\|deposits_disabled\|frozen" lib.rs
```

### Step 2: Verify role-based access control

For each privileged instruction, verify that appropriate access control is in place.

**Anchor -- check for has_one or constraint on the Accounts struct:**
```
# For each admin instruction's Accounts struct, look for:
grep -n "has_one = admin\|has_one = authority\|has_one = governance" lib.rs
grep -n "constraint.*admin\|constraint.*governance\|constraint.*emergency" lib.rs
```

**Native -- check for authority validation in each handler:**
```
grep -n "\.key\s*!=.*admin\|\.key\s*!=.*authority\|\.key\s*!=.*governance" processor.rs
```

### Step 3: Verify role granularity

Check that different privilege levels exist for different severity of operations:

| Operation | Expected minimum role |
|-----------|----------------------|
| Pause/unpause | Admin or emergency multisig |
| Update fees | Admin or governance |
| Update oracle | Admin or governance |
| Emergency drain | Governance or timelock |
| Upgrade config | Governance |
| Manage operators | Admin |
| Routine operations | Operator |

### Step 4: Check for missing access control at dispatch level

In native programs, verify that admin instructions are not just dispatched without any access control wrapper. Each admin handler must independently validate the caller's role.

---

## False Positives

### 1. Intentionally public instructions

Many instructions are designed to be callable by anyone. These do not need admin checks:

```rust
// SAFE — deposit is permissionless by design
pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> { ... }

// SAFE — withdraw is callable by any user (for their own funds)
pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> { ... }

// SAFE — claim rewards is callable by the reward recipient
pub fn claim_rewards(ctx: Context<ClaimRewards>) -> Result<()> { ... }

// SAFE — liquidate is callable by anyone (liquidator receives incentive)
pub fn liquidate(ctx: Context<Liquidate>) -> Result<()> { ... }

// SAFE — crank/keeper functions are permissionless by design
pub fn crank_oracle(ctx: Context<CrankOracle>) -> Result<()> { ... }
```

### 2. Access control via PDA derivation

If the instruction requires accounts derived from specific seeds that include the admin's key, the PDA derivation itself serves as access control.

```rust
// SAFE — admin_config PDA is seeded by admin's key; only the correct
// admin can provide a valid admin_config account
#[derive(Accounts)]
pub struct AdminAction<'info> {
    pub admin: Signer<'info>,

    #[account(
        seeds = [b"admin_config", admin.key().as_ref()],
        bump = admin_config.bump,
    )]
    pub admin_config: Account<'info, AdminConfig>,

    #[account(mut)]
    pub protocol: Account<'info, ProtocolState>,
}
```

### 3. Timelock or governance-gated instructions

Instructions that are gated by an on-chain governance proposal or timelock are properly access-controlled even if they don't have a direct admin signer check.

```rust
// SAFE — requires an executed governance proposal
#[derive(Accounts)]
pub struct ExecuteGovernanceAction<'info> {
    #[account(
        constraint = proposal.status == ProposalStatus::Executed @ ErrorCode::NotExecuted,
        constraint = proposal.expiry > Clock::get()?.unix_timestamp @ ErrorCode::Expired,
    )]
    pub proposal: Account<'info, GovernanceProposal>,

    #[account(mut)]
    pub protocol: Account<'info, ProtocolState>,
}
```

---

## Remediation

### Add authority checks with Anchor `has_one`

```rust
#[derive(Accounts)]
pub struct PauseProtocol<'info> {
    // FIX: Require admin or emergency_admin to sign
    pub admin: Signer<'info>,

    #[account(
        mut,
        // FIX: has_one ensures protocol_state.admin == admin.key()
        has_one = admin @ ErrorCode::Unauthorized,
    )]
    pub protocol_state: Account<'info, ProtocolState>,
}

pub fn pause_protocol(ctx: Context<PauseProtocol>) -> Result<()> {
    ctx.accounts.protocol_state.is_paused = true;
    emit!(ProtocolPaused {
        admin: ctx.accounts.admin.key(),
        timestamp: Clock::get()?.unix_timestamp,
    });
    Ok(())
}
```

### Implement role-based access with granular permissions

```rust
#[account]
pub struct ProtocolState {
    pub governance: Pubkey,      // Highest authority: protocol upgrades, parameter changes
    pub admin: Pubkey,           // Day-to-day admin: pause, operator management
    pub emergency_admin: Pubkey, // Emergency-only: pause, emergency drain
    pub operators: Vec<Pubkey>,  // Routine operations: crank, rebalance
    pub is_paused: bool,
    pub fee_bps: u16,
    pub oracle: Pubkey,
    pub treasury: Pubkey,
}

// Governance-only actions
#[derive(Accounts)]
pub struct GovernanceAction<'info> {
    pub governance: Signer<'info>,
    #[account(mut, has_one = governance @ ErrorCode::GovernanceOnly)]
    pub protocol: Account<'info, ProtocolState>,
}

pub fn update_oracle(ctx: Context<GovernanceAction>, new_oracle: Pubkey) -> Result<()> {
    ctx.accounts.protocol.oracle = new_oracle;
    Ok(())
}

pub fn update_fees(ctx: Context<GovernanceAction>, new_fee_bps: u16) -> Result<()> {
    require!(new_fee_bps <= 1000, ErrorCode::FeeTooHigh); // Max 10%
    ctx.accounts.protocol.fee_bps = new_fee_bps;
    Ok(())
}

// Admin actions (admin OR governance)
#[derive(Accounts)]
pub struct AdminAction<'info> {
    pub caller: Signer<'info>,
    #[account(
        mut,
        constraint = protocol.admin == caller.key()
            || protocol.governance == caller.key()
            @ ErrorCode::AdminOrGovernanceOnly,
    )]
    pub protocol: Account<'info, ProtocolState>,
}

pub fn pause(ctx: Context<AdminAction>) -> Result<()> {
    ctx.accounts.protocol.is_paused = true;
    Ok(())
}

// Emergency actions (emergency_admin, admin, OR governance)
#[derive(Accounts)]
pub struct EmergencyAction<'info> {
    pub caller: Signer<'info>,
    #[account(
        mut,
        constraint = protocol.emergency_admin == caller.key()
            || protocol.admin == caller.key()
            || protocol.governance == caller.key()
            @ ErrorCode::EmergencyAccessOnly,
    )]
    pub protocol: Account<'info, ProtocolState>,
}
```

### Native Solana: Add explicit checks in each handler

```rust
pub fn process_pause(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let caller = next_account_info(accounts_iter)?;
    let state_account = next_account_info(accounts_iter)?;

    if !caller.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    if state_account.owner != program_id {
        return Err(ProgramError::IncorrectProgramId);
    }

    let mut state = ProtocolState::try_from_slice(&state_account.data.borrow())?;

    // FIX: Verify caller is admin or emergency_admin
    if caller.key != &state.admin && caller.key != &state.emergency_admin {
        return Err(ProgramError::InvalidAccountData);
    }

    state.is_paused = true;
    state.serialize(&mut &mut state_account.data.borrow_mut()[..])?;

    Ok(())
}
```

### Add parameter bounds validation

Even with proper access control, admin instructions should validate parameter bounds:

```rust
pub fn update_fees(ctx: Context<GovernanceAction>, new_fee_bps: u16) -> Result<()> {
    // FIX: Bound fee to reasonable range even for governance
    require!(new_fee_bps <= MAX_FEE_BPS, ErrorCode::FeeTooHigh);
    require!(new_fee_bps >= MIN_FEE_BPS, ErrorCode::FeeTooLow);

    ctx.accounts.protocol.fee_bps = new_fee_bps;
    emit!(FeeUpdated { new_fee_bps });
    Ok(())
}

pub fn update_oracle(ctx: Context<GovernanceAction>, new_oracle: Pubkey) -> Result<()> {
    // FIX: Validate oracle is not the zero address
    require!(new_oracle != Pubkey::default(), ErrorCode::InvalidOracle);

    ctx.accounts.protocol.oracle = new_oracle;
    emit!(OracleUpdated { new_oracle });
    Ok(())
}
```

---

## References

- Taxonomy: A-5 in `vulnerability-taxonomy.md`
- Related: A-3 (Missing Authority Validation) -- signer not matched to stored authority
- Related: A-4 (Privilege Escalation) -- authority fields being modified without control
- [Anchor Constraints Reference](https://www.anchor-lang.com/docs/account-constraints)
