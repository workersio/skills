# Solana Vulnerability Cheatsheet

Condensed quick-lookup for all Solana smart contract vulnerability types. Load this first. Consult individual reference files only when validating candidates.

---

## Category A: Authentication & Authorization

### A-1: Missing Signer Check [CRITICAL]
**Keywords:** `is_signer`, `Signer<'info>`, `MissingRequiredSignature`, `authority`
**Grep:** `AccountInfo` params used as authorities without `Signer` type or `.is_signer` check
**Pattern:**
```rust
let authority = &accounts[0]; // No signer check!
// transfers funds using authority
```
**Ref:** [missing-signer-check.md](missing-signer-check.md)

### A-2: Missing Owner/Program Check [HIGH]
**Keywords:** `owner`, `AccountInfo`, `Account<'info`, `program_id`
**Grep:** Raw `AccountInfo` deserialized without `account.owner == expected_program_id`
**Pattern:**
```rust
let vault = Vault::try_from_slice(&account.data.borrow())?;
// No check: account.owner == MY_PROGRAM_ID
```
**Ref:** [missing-owner-check.md](missing-owner-check.md)

### A-3: Missing Authority Validation [HIGH]
**Keywords:** `authority`, `admin`, `is_signer`, `has_one`
**Grep:** Signer verified but not compared to stored authority key
**Pattern:**
```rust
if !authority.is_signer { return Err(...); }
// Missing: authority.key != &vault.authority
```
**Ref:** [missing-authority-validation.md](missing-authority-validation.md)

### A-4: Privilege Escalation [CRITICAL]
**Keywords:** `set_authority`, `update_admin`, `initialize`, `owner`
**Grep:** Instructions that write authority/admin fields — check who can call them
**Pattern:** Admin-update instruction callable by non-admin
**Ref:** [privilege-escalation.md](privilege-escalation.md)

### A-5: Instruction Access Control [HIGH]
**Keywords:** `admin`, `governance`, `pause`, `freeze`, `emergency`
**Grep:** Admin instructions without proper role checks
**Pattern:** Governance-only instruction callable by any signer
**Ref:** [instruction-access-control.md](instruction-access-control.md)

---

## Category S: Account & State Management

### S-1: Account Not Initialized Check [HIGH]
**Keywords:** `is_initialized`, `discriminator`, `AccountInfo`, `try_from_slice`
**Grep:** Account deserialized without checking initialization state/discriminator
**Pattern:**
```rust
let data = MyAccount::try_from_slice(&account.data.borrow())?;
// No check: data.is_initialized == true
```
**Ref:** [account-not-initialized.md](account-not-initialized.md)

### S-2: Duplicate Mutable Accounts [HIGH]
**Keywords:** `key()`, `key !=`, `constraint =`, `source`, `destination`
**Grep:** Two accounts of same type without `a.key() != b.key()` check
**Pattern:**
```rust
pub fn transfer(source: AccountInfo, dest: AccountInfo, amount: u64) {
    source.balance -= amount;
    dest.balance += amount; // If source == dest, state corrupted
}
```
**Ref:** [duplicate-mutable-accounts.md](duplicate-mutable-accounts.md)

### S-3: PDA Seed Collision [HIGH]
**Keywords:** `seeds`, `find_program_address`, `bump`, `Pubkey::create_program_address`
**Grep:** PDA seeds missing user-specific component (just `[b"vault"]` without user key)
**Pattern:**
```rust
seeds = [b"vault"] // All users share one PDA!
// Should be: seeds = [b"vault", user.key().as_ref()]
```
**Ref:** [pda-seed-collision.md](pda-seed-collision.md)

### S-4: Missing Bump Canonicalization [MEDIUM]
**Keywords:** `bump`, `create_program_address`, `find_program_address`, `seeds`
**Grep:** `create_program_address` with user-supplied bump instead of canonical
**Pattern:** User passes arbitrary bump → creates account at non-canonical PDA address
**Ref:** [missing-bump-canonicalization.md](missing-bump-canonicalization.md)

### S-5: Type Cosplay / Account Substitution [HIGH]
**Keywords:** `discriminator`, `AccountInfo`, `try_from_slice`, `Account<'info`
**Grep:** Manual deserialization without type discriminator check; multiple structs with similar layouts
**Pattern:**
```rust
// Vault and TipPool have compatible layouts
// Attacker passes Vault where TipPool expected
let pool = TipPool::try_from_slice(&account.data.borrow())?;
```
**Ref:** [type-cosplay.md](type-cosplay.md)

### S-6: Account Closure Vulnerability [MEDIUM]
**Keywords:** `close`, `lamports`, `fill(0)`, `zero`, `close =`
**Grep:** Account closure without zeroing data; revival in same transaction
**Pattern:**
```rust
**dest.lamports.borrow_mut() += source.lamports();
**source.lamports.borrow_mut() = 0;
// Data NOT zeroed — can be reused before slot ends
```
**Ref:** [account-closure-vulnerability.md](account-closure-vulnerability.md)

### S-7: Reinitialization [HIGH]
**Keywords:** `init`, `init_if_needed`, `initialize`, `is_initialized`
**Grep:** Init instruction without checking account already initialized
**Pattern:** `initialize()` callable twice — resets account state
**Ref:** [reinitialization.md](reinitialization.md)

### S-8: Missing Rent Exemption Check [LOW]
**Keywords:** `rent`, `is_exempt`, `rent_epoch`, `lamports`
**Grep:** Account creation without rent exemption check
**Pattern:** Account created with insufficient lamports for rent exemption
**Ref:** Part of account-not-initialized checks. Low severity.

---

## Category C: Cross-Program Invocation

### C-1: Arbitrary CPI Target [CRITICAL]
**Keywords:** `invoke`, `invoke_signed`, `program_id`, `CpiContext`
**Grep:** `invoke`/`invoke_signed` where program account is user-supplied, not hardcoded
**Pattern:**
```rust
let program = &accounts[3]; // User-supplied program!
invoke(&Instruction { program_id: *program.key, .. }, &[...])?;
```
**Ref:** [arbitrary-cpi-target.md](arbitrary-cpi-target.md)

### C-2: CPI Signer Privilege Escalation [HIGH]
**Keywords:** `invoke_signed`, `seeds`, `signer_seeds`, `PDA`
**Grep:** `invoke_signed` that passes PDA authority broader than needed
**Pattern:** PDA signs for operations beyond the intended instruction scope
**Ref:** Part of arbitrary-cpi-target checks.

### C-3: Unvalidated `remaining_accounts` [MEDIUM]
**Keywords:** `remaining_accounts`, `ctx.remaining_accounts`, `iter()`
**Grep:** `remaining_accounts` used without owner/type validation per account
**Pattern:**
```rust
for account in ctx.remaining_accounts.iter() {
    let data = MyStruct::try_from_slice(&account.data.borrow())?; // No validation!
}
```
**Ref:** Covered in [anchor-specific.md](anchor-specific.md) §2.

---

## Category M: Arithmetic & Math

### M-1: Integer Overflow / Underflow [HIGH]
**Keywords:** `checked_add`, `checked_sub`, `checked_mul`, `saturating`, `overflow`
**Grep:** Raw `+`, `-`, `*` on integer types without `checked_*` or `saturating_*`
**Pattern:**
```rust
let total = amount_a + amount_b; // Wraps in release mode!
// Should be: amount_a.checked_add(amount_b).ok_or(ErrorCode::Overflow)?
```
**Ref:** [integer-overflow-underflow.md](integer-overflow-underflow.md)

### M-2: Division Precision Loss [MEDIUM]
**Keywords:** `/`, `checked_div`, `shares`, `ratio`, `fee`, `reward`
**Grep:** Integer division in fee/reward/share calculations; division before multiplication
**Pattern:**
```rust
let shares = deposit * total_shares / total_deposits; // Truncation risk
// Worse: deposit / total_deposits * total_shares (almost always 0)
```
**Ref:** [division-precision-loss.md](division-precision-loss.md)

### M-3: Unsafe Casting [MEDIUM]
**Keywords:** `as u64`, `as u32`, `as u128`, `as i64`, `try_into`, `TryFrom`
**Grep:** `as` casts between integer types that could silently truncate
**Pattern:**
```rust
let truncated = large_u128_value as u64; // Silent truncation!
```
**Ref:** [unsafe-casting.md](unsafe-casting.md)

### M-4: Rounding Errors [MEDIUM]
**Keywords:** `shares`, `pool`, `mint`, `redeem`, `deposit`, `withdraw`, `/`
**Grep:** Division in share/LP token calculations without zero-amount guard
**Pattern:**
```rust
let lp_tokens = deposit_amount * total_supply / total_pool;
// If result rounds to 0, deposit is accepted but no tokens minted → drain attack
```
**Ref:** [rounding-errors.md](rounding-errors.md)

---

## Category L: Logic & Economic

### L-1: Oracle Manipulation [CRITICAL]
**Keywords:** `oracle`, `price`, `pyth`, `switchboard`, `TWAP`, `spot`, `pool`
**Grep:** Price reads from on-chain AMMs or oracles; missing staleness/confidence checks
**Pattern:**
```rust
let price = pool.token_a / pool.token_b; // Spot price — trivially manipulable!
```
**Ref:** [oracle-manipulation.md](oracle-manipulation.md)

### L-2: Missing Slippage Check [HIGH]
**Keywords:** `min_amount_out`, `max_amount_in`, `slippage`, `swap`, `trade`
**Grep:** Swap/trade instructions without min output or max input parameters
**Pattern:** Swap has no `min_amount_out` → sandwich attack possible
**Ref:** [missing-slippage-check.md](missing-slippage-check.md)

### L-3: Flash Loan Vulnerability [HIGH]
**Keywords:** `flash`, `borrow`, `repay`, `same transaction`, `slot`
**Grep:** State reads influencing economic decisions that can be manipulated in same tx
**Pattern:** Collateral value readable + manipulable within single transaction
**Ref:** Part of oracle-manipulation and economic analysis.

### L-4: Front-Running Susceptibility [MEDIUM]
**Keywords:** `MEV`, `sandwich`, `commit`, `reveal`, `frontrun`
**Grep:** Operations where knowing pending tx allows profitable counter-trades
**Pattern:** AMM trades without slippage, liquidations, NFT mints
**Ref:** Part of missing-slippage-check analysis.

---

## Category T: Token-Specific

### T-1: SPL Token Account Validation [HIGH]
**Keywords:** `mint`, `token::mint`, `token::authority`, `TokenAccount`, `Mint`
**Grep:** Token accounts accepted without verifying `.mint == expected_mint`
**Pattern:**
```rust
let user_token = Account::<TokenAccount>::try_from(account)?;
// Missing: assert!(user_token.mint == expected_mint.key());
```
**Ref:** [spl-token-validation.md](spl-token-validation.md)

### T-2: Token-2022 Extension Handling [MEDIUM]
**Keywords:** `token-2022`, `spl-token-2022`, `transfer_fee`, `permanent_delegate`, `transfer_hook`
**Grep:** Programs interacting with Token-2022 without handling extensions
**Pattern:** Transfer fee means amount_received != amount_sent
**Ref:** Part of spl-token-validation analysis.

### T-3: Missing Token Freeze Check [LOW]
**Keywords:** `is_frozen`, `freeze`, `FreezeAccount`
**Grep:** Token operations without `token_account.is_frozen()` check
**Pattern:** Operations on frozen accounts may fail or lock funds
**Ref:** Low severity. Check only if program explicitly handles frozen states.

---

## Category R: Runtime & Deployment

### R-1: Upgrade Authority Risk [MEDIUM]
**Keywords:** `upgrade_authority`, `set_authority`, `BPFUpgradeableLoader`, `programdata`
**Grep:** Check if program is upgradeable and who holds authority
**Pattern:** Single-key upgrade authority on high-TVL program — compromised key = full program takeover
**Ref:** Check `solana program show <program_id>` for upgrade authority. Should be multisig, governance, or revoked.

### R-2: Missing Rent Exemption [LOW]
**Keywords:** `rent`, `is_exempt`, `minimum_balance`, `Rent::get`
**Grep:** `grep -rn 'system_instruction::create_account' --include='*.rs'` — check lamports parameter
**Pattern:** Account created with insufficient lamports for rent exemption — will be garbage collected
**Ref:** Low severity. Modern Solana enforces rent exemption on account creation.

### R-3: Unverified Build [INFORMATIONAL]
**Keywords:** `verifiable`, `anchor-build`, `solana-verify`, `checksum`
**Grep:** Check for `Anchor.toml` with `[programs.verifiable]` or CI scripts running `solana-verify`
**Pattern:** Deployed bytecode cannot be verified against source — users cannot confirm program behavior
**Ref:** Informational. Recommend Anchor Verifiable Build or `solana-verify` for mainnet deployments.
