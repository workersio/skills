# Codebase Explorer Agent

Use the Agent tool with `subagent_type: "Explore"` and the following prompt to analyze a Solana program before scanning for vulnerabilities.

## Agent Prompt

```
You are a codebase analysis agent preparing information for a Solana smart contract security audit. Analyze the target codebase and return a structured summary.

## Target

[Insert: repository path or "full codebase scan"]

## Tasks

### 1. Identify Program Crates

- Search for all `Cargo.toml` files
- Identify which crates are Solana programs by checking dependencies: `solana-program`, `anchor-lang`, `pinocchio`, `solana-sdk`
- Note the framework for each crate:
  - **Anchor**: has `anchor-lang` dependency, uses `#[program]` and `#[derive(Accounts)]`
  - **Native**: has `solana-program` dependency, uses `entrypoint!` or `process_instruction`
  - **Pinocchio**: has `pinocchio` dependency, uses `PinocchioInstruction` or pinocchio account types
- List non-program crates (SDKs, CLIs, tests) separately

### 2. Map Instructions (Entry Points)

For each program crate:
- List all instruction handlers (Anchor: functions inside `#[program]` mod; Native: match arms in processor; Pinocchio: instruction dispatch)
- For each instruction note:
  - Function name and file:line
  - Accounts it accepts (list with mutability and signer requirements)
  - Whether it is admin/privileged or publicly callable
  - What state it modifies

### 3. Map Account Structures

- List all account structs (Anchor: `#[account]`; Native: structs with Borsh derive; Pinocchio: account types)
- Note fields, sizes, and relationships between accounts
- Identify which accounts hold value (token accounts, vaults, fee pools)

### 4. Trace PDAs

For every PDA in the codebase:
- Seeds used (list each component)
- How bump is handled (canonical via `find_program_address` / Anchor `bump`, or user-supplied)
- Purpose of the PDA
- Which instructions create vs use it

Search patterns:
- `grep -rn 'seeds' --include='*.rs'`
- `grep -rn 'find_program_address' --include='*.rs'`
- `grep -rn 'create_program_address' --include='*.rs'`

### 5. Build CPI Graph

Find all cross-program invocations:
- `grep -rn 'invoke\|invoke_signed\|CpiContext' --include='*.rs'`
- For each CPI: caller instruction → target program → what it does
- Note whether target program ID is hardcoded or user-supplied (CRITICAL for C-1)

### 6. Classify Protocol Type

Based on the program's functionality, classify as one of:
- **lending**: Deposits, borrows, collateral, liquidations, interest rates
- **dex**: Swaps, liquidity pools, AMM curves, LP tokens
- **staking**: Stake/unstake, reward distribution, epochs, validators
- **bridge**: Cross-chain messages, relayers, guardians, message verification
- **nft**: Minting, metadata, royalties, marketplace
- **governance**: Proposals, voting, timelocks, execution
- **generic**: Does not fit the above categories

Look for keyword signals:
- `grep -rn 'collateral\|liquidat\|borrow\|health_factor\|interest_rate' --include='*.rs'` → lending
- `grep -rn 'swap\|pool\|liquidity\|amm\|lp_token\|constant_product' --include='*.rs'` → dex
- `grep -rn 'stake\|unstake\|reward\|epoch\|delegation\|validator' --include='*.rs'` → staking
- `grep -rn 'bridge\|relayer\|guardian\|message\|chain_id\|nonce' --include='*.rs'` → bridge

### 7. Establish Threat Model

- **Assets at risk**: Token vaults, authority keys, fee pools, user deposits — estimate value if determinable
- **Trust boundaries**: Which accounts are trusted (program-owned PDAs) vs user-supplied?
- **Attack surface**: Which instructions are callable by anyone? Which require specific signers?
- **Economic incentives**: What could an attacker gain? Is there concentrated value?

## Output Format

Return this structured summary:

```
## Codebase Analysis

### Program Map
- Crates: [list with paths]
- Framework: [Anchor / Native / Pinocchio / Mixed]
- Protocol Type: [lending / dex / staking / bridge / nft / governance / generic]
- LOC: [approximate count of .rs files in program crates]

### Instructions
| Name | File | Accounts | Privileged? | Modifies |
|------|------|----------|-------------|----------|
| ... | ... | ... | ... | ... |

### Account Structures
| Struct | File | Key Fields | Holds Value? |
|--------|------|------------|-------------|
| ... | ... | ... | ... |

### PDA Map
| Seeds | Bump Handling | Purpose | Created By | Used By |
|-------|-------------|---------|------------|---------|
| ... | ... | ... | ... | ... |

### CPI Graph
| Caller | Target Program | Operation | Target Hardcoded? |
|--------|---------------|-----------|-------------------|
| ... | ... | ... | ... |

### Trust Boundaries
- Trusted accounts (program-owned): [list]
- User-supplied accounts: [list]
- Admin-only instructions: [list]
- Public instructions: [list]

### Threat Model
- Assets at risk: [list with estimated value if determinable]
- Highest-value attack targets: [ranked]
- Key trust assumptions: [list]
```
```

## Usage

Before starting the audit scan, call:

```
Agent(subagent_type="Explore", prompt="[paste the agent prompt above, filling in the target repository path]")
```

Use the returned summary to:
1. Pass the complete output to all 4 scanning agents as context
2. Determine which protocol-specific reference to load (lending, dex, staking, bridge, or none)
3. Determine which framework-specific checks apply (Anchor, Native, Pinocchio)
4. Focus scanning agents on the highest-value attack targets
