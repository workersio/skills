---
name: kani-proof
description: Writes Kani bounded model checker proofs for Solana and Rust programs. Proves conservation, isolation, arithmetic safety, and access control properties. Use when the user asks to write formal verification, Kani proofs, model checking, or when code contains kani::, #[kani::proof], solana_program, or anchor_lang.
---

# Kani Formal Verification

## Progress Checklist

Copy this checklist into your first response and update after each phase.

```
Proof Coverage Progress:
- [ ] Phase 0: Read all reference files
- [ ] Phase 0.5: Check for existing proofs — found N existing harnesses
- [ ] Phase 1: Analyze codebase — found N mutation functions
- [ ] Phase 1.5: Prepare codebase (MAX_ACCOUNTS, transparent types, Cargo.toml, extern crate)
- [ ] Phase 2: Write invariant infrastructure — N lines across 18+ items. STOP — verify >= 250 lines.
- [ ] Phase 2b: Create 3+ RiskParams constructors. STOP — verify count.
- [ ] Phase 3a: Output function enumeration table (N functions). STOP — verify >= 10.
- [ ] Phase 3b: Output coverage matrix. Total x's: N. STOP — verify >= 60.
- [ ] Phase 3c: Inductive proofs — wrote N harnesses.
- [ ] Phase 3d: INV preservation proofs (1 per mutation) — wrote N harnesses.
- [ ] Phase 3e+: Constructive proofs by domain — wrote N harnesses. Running count: N.
- [ ] Phase 3g: Domain-specific invariants (I5/I7/I8/N1) — wrote N harnesses.
- [ ] Phase 3h: Lifecycle/sequence proofs — wrote N harnesses.
- [ ] Phase 3i: Anti-exploit proofs — wrote N harnesses.
- [ ] Phase 4: Run cargo kani, audit, strengthen (WEAK→STRONG→INDUCTIVE)
- [ ] Phase 4.5: Coverage depth verification — per-function depth check, red flags cleared
- [ ] Phase 5: Quality gate — total: N (first session: 80+, incremental: 40+), depth checks pass
```

## Phase 0: Read Reference Files (MANDATORY)

Read ALL of these before proceeding:

1. [references/proof-patterns.md](references/proof-patterns.md) — 13 proof patterns with real code, shared infrastructure code to copy verbatim
2. [references/kani-features.md](references/kani-features.md) — Kani API, codebase preparation, stubbing, solver selection
3. [references/invariant-design.md](references/invariant-design.md) — 5-layer invariant architecture with full implementations
4. [references/coverage-workflow.md](references/coverage-workflow.md) — Enumeration, coverage matrix, batch write protocol

## Phase 0.5: Check for Existing Work

1. Look for `tests/kani.rs` or files containing `#[kani::proof]`
2. If found: count harnesses, build coverage matrix, write only uncovered cells
3. If none found: continue to Phase 1

## Phase 1: Understand the Program

1. Clone the repository if URL provided
2. Identify core mutable state structs (vaults, balances, accounts, positions)
3. Map ALL mutation functions — every state-modifying function is a verification target
4. Determine framework: native `solana_program` vs Anchor

## Phase 1.5: Prepare the Codebase

See [references/kani-features.md](references/kani-features.md) for full details and code. Four preparations:

- **A. State space reduction** — `#[cfg(kani)] pub const MAX_ACCOUNTS: usize = 4;`
- **B. SAT-friendly type wrappers** — `#[repr(transparent)]` I128/U128 under `#[cfg(kani)]`
- **C. Cargo.toml** — `[workspace.metadata.kani]` with `flags = { tests = true }`
- **D. no_std** — `#[cfg(kani)] extern crate kani;` at crate root

## Phase 2: Invariant Infrastructure — STOP GATE

See [references/invariant-design.md](references/invariant-design.md) for layer implementations and [references/proof-patterns.md](references/proof-patterns.md) §Shared Infrastructure for helper code.

**CRITICAL: COPY the shared infrastructure from proof-patterns.md §Shared Infrastructure VERBATIM.** Do not simplify or omit pieces.

You must implement ALL of these before writing proofs:

**5 invariant layers + 2 tiers:**
1. `inv_structural` — freelist acyclicity via bounded walk, cursor bounds including `liq_cursor`
2. `inv_aggregates` — `c_tot`, `pnl_pos_tot`, `total_open_interest` match account sums
3. `inv_accounting` — `vault >= c_tot + insurance` via `signed_residual()`
4. `inv_mode` — parameter validity (margin bps, leverage, fee bounds)
5. `inv_per_account` — PA1: `reserved_pnl <= max(pnl,0)`, PA2-PA4: no sentinels
6. `canonical_inv` — composes all 5 layers
7. `valid_state` — lightweight tier (no loops)
8. `conservation_fast_no_funding` — targeted conservation check only

**Helpers (copy verbatim from proof-patterns.md):**
9. `sync_engine_aggregates` — recompute aggregates from accounts
10. `assert_ok!` / `assert_err!` macros — **MUST use instead of `let _result = ...`**
11. `AccountSnapshot` + `snapshot_account`
12. `FullAccountSnapshot` + `assert_full_snapshot_eq!` macro (9 fields)
13. `GlobalsSnapshot` + `snapshot_globals`
14. `Totals` + `recompute_totals` — independent cross-check
15. Non-vacuity helpers: `assert_changed`, `assert_nonzero`, `assert_gc_freed`
16. `n1_boundary_holds` — negative PnL settlement check
17. Integer helpers: `neg_i128_to_u128`, `u128_to_i128_clamped`, `abs_i128_to_u128`
18. `DEFAULT_ORACLE` constant

> **STOP:** Verify >= 250 lines of infrastructure. Check each item above exists.

**Create 3+ RiskParams constructors:**
- `test_params()` — nonzero trading/liquidation fees
- `test_params_with_maintenance_fee()` — **use for all P3/P1 proofs**
- `test_params_with_floor()` — nonzero risk_reduction_threshold

### Symbolic State Construction (MANDATORY)

Every proof MUST set up state with `kani::any()`, not hard-coded values:

**WRONG — trivially true, catches nothing:**
```rust
let mut state = create_state();
state.deposit(0, 10_000);  // concrete user, concrete amount → weak
```

**RIGHT — tests ALL valid states:**
```rust
let balance: u128 = kani::any();
kani::assume(balance >= MIN_BALANCE && balance <= MAX_BALANCE);
let signed_value: i128 = kani::any();
kani::assume(signed_value > i128::MIN + 1 && signed_value < MAX_VALUE);
// Directly set fields to symbolic values
state.accounts[idx].balance = balance;
state.accounts[idx].signed_field = signed_value;
```

**Rules for symbolic inputs:**
- Indices: `let idx: usize = kani::any(); kani::assume(idx < state.len() && state.is_active(idx));`
- Unsigned amounts: `let amount: u128 = kani::any(); kani::assume(amount > 0 && amount < PROTOCOL_MAX);`
- Signed values: `let val: i128 = kani::any(); kani::assume(val != i128::MIN);` (avoid MIN to prevent negation overflow)
- Prices/rates: `let price: u64 = kani::any(); kani::assume(price > 0 && price <= PRICE_BOUND);`
- **NEVER hard-code amounts/indices in a proof — this is WEAK verification that catches nothing**

## Phase 3: Systematic Proof Writing

See [references/coverage-workflow.md](references/coverage-workflow.md) for the complete process.

### 3a–3b: Enumerate and Matrix (STOP GATES)

Output the function enumeration table, then the coverage matrix. See coverage-workflow.md for templates. Verify >= 10 functions and >= 60 matrix cells before writing code.

### 3c: Inductive Proofs First

One per accounting operation using raw primitives. No `#[kani::unwind]` needed. See proof-patterns.md P10a.

### 3d: INV Preservation (1 per mutation)

Every mutation function gets `proof_{fn}_preserves_inv`. See proof-patterns.md P3.

### 3e–3f: Constructive Proofs by Domain

Work through domains: Capital Flow → Position Mgmt → Settlement → Lifecycle → Risk → GC → Fees → Admin. See coverage-workflow.md for domain grouping and proof variants per operation.

**CRITICAL: Every constructive proof MUST:**
1. Start from populated state (use `create_valid_state()` with multiple accounts, positions, PnL)
2. Use `assert_ok!()` to force the Ok path (non-vacuity)
3. Check domain-specific properties beyond `canonical_inv` (see Domain-Specific Property Checks below)
4. Include `kani::cover!(true, ...)` as supplementary instrumentation

**DO NOT** write proofs that: create empty state → call one function → check only canonical_inv. These are trivially true and worthless.

### 3g: Domain-Specific Invariants

I5 (warmup), I7 (isolation), I8 (equity/margin), N1 (negative PnL), Funding. See proof-patterns.md.

### 3h: Lifecycle/Sequence Proofs (HIGH PRIORITY — TARGET 10-15)

Chain 2-4 operations to build rich state and test realistic flows. **These are the highest-value proofs** because bugs hide in state transitions between operations, not in single operations on empty state.

**Multi-step state construction pattern:**
```rust
// Step 1: Create base state and add accounts
// Step 2: Deposit / set up balances (with assert_ok!)
// Step 3: Open positions / create complex state (with assert_ok!)
// Step 4: NOW test the interesting operation on rich state
// Step 5: Check domain-specific properties, not just canonical_inv
```

**Target 10-15 multi-step proofs.** Each should exercise a different realistic flow through the program. See proof-patterns.md P12.

### 3i: Anti-Exploit Proofs

Teleportation (two-engine comparison), phantom equity, NEGATIVE proofs, gap proofs (FullAccountSnapshot), boolean selectors, extreme values. Target 15-30 proofs. See proof-patterns.md P13a-P13h.

### Critical Rules for All Proofs

**Annotations:** Every constructive proof MUST have `#[kani::unwind(33)]` and `#[kani::solver(cadical)]`. Only loop-free inductive proofs (P10a) may omit them. See [references/kani-features.md](references/kani-features.md).

**Batch writes:** Maximum 15-20 proofs per Write/Edit call. Verify count after each write with `grep -c '#\[kani::proof\]'`. See coverage-workflow.md §Batch Write Enforcement.

**Custom matchers:** Position management proofs require custom `MatchingEngine` implementations. See proof-patterns.md P13h.

**Harness structure:** 15-40 lines each, one property per harness. Use `assert_ok!`/`assert_err!`, assert `canonical_inv` before and after.

**Non-vacuity (MANDATORY — TWO mechanisms together):**
1. `assert_ok!()` — PRIMARY. Forces the Ok path. If the operation can't succeed, the proof FAILS.
2. `kani::cover!(true, "reached")` — SUPPLEMENTARY. Instrumentation for Kani logs.

WRONG (vacuous — cover doesn't fail the proof):
```rust
let result = state.operation(user, amount);
kani::cover!(result.is_ok());  // if operation always fails, proof still passes!
```

RIGHT (non-vacuous — assert_ok forces success):
```rust
assert_ok!(state.operation(user, amount), "operation must succeed");
kani::cover!(true, "operation path reached");
```

For error path proofs: use `assert_err!()` instead of `assert_ok!()`. See proof-patterns.md §Non-Vacuity.

**Liquidation proofs:** Target 6-10 proofs covering position reduction, insurance premium, frame property, error paths, conservation, and sequences. See proof-patterns.md P14.

**Error path proofs:** Use full snapshot comparison (snapshot before → call → assert_err → assert snapshot unchanged). See proof-patterns.md P4.

### Domain-Specific Property Checks (MANDATORY — go beyond canonical_inv)

`canonical_inv` is necessary but NOT sufficient. Every proof should also check **domain-specific properties** — the exact effect of the operation on specific fields.

**For EVERY proof, check at least one domain-specific property from this list:**

| Property Type | What to Assert | Example |
|---|---|---|
| **Delta/exact effect** | Field changed by exactly the expected amount | `capital_after == capital_before + deposit_amount` |
| **Equity formula** | equity = capital + unrealized_pnl | `assert!(equity(&account) == account.capital as i128 + account.pnl)` |
| **Boundary conditions** | Fields stay within valid ranges | `assert!(pnl < 0 implies capital > 0 OR position == 0)` |
| **Monotonicity** | Values only move in one direction | `assert!(insurance_after >= insurance_before)` |
| **Symmetry/zero-sum** | Balanced operations net to zero | `assert!(total_long_funding + total_short_funding == 0)` |
| **Idempotency** | Re-running is a no-op | `settle(); let snap = snapshot(); settle(); assert_eq!(snap, snapshot())` |
| **Cross-field consistency** | Related fields stay in sync | `assert!(aggregate_total == sum_of_individual_accounts)` |

**WRONG — only checks canonical_inv (too generic, misses specific bugs):**
```rust
assert_ok!(state.deposit(user, amount), "deposit");
kani::assert(canonical_inv(&state), "INV after");  // ← this is ALL you check? Too weak.
```

**RIGHT — checks canonical_inv PLUS domain-specific deltas:**
```rust
let capital_before = state.accounts[user].capital;
let vault_before = state.vault;
assert_ok!(state.deposit(user, amount), "deposit");
kani::assert(canonical_inv(&state), "INV after");
// Domain-specific: verify EXACT effect
kani::assert(state.accounts[user].capital == capital_before + amount, "capital delta");
kani::assert(state.vault == vault_before + amount, "vault delta");
kani::cover!(true, "deposit deltas verified");
```

Read the codebase to identify which domain-specific properties apply to each function. Check the function's implementation — what fields does it modify? Assert the exact expected modification.

## Phase 4: Run, Audit & Strengthen

```bash
cargo kani --harness <name>    # Single proof
cargo kani                      # All proofs
```

Upgrade proofs: WEAK (concrete) → STRONG (symbolic) → INDUCTIVE (raw primitives).

## Phase 4.5: Coverage Depth Verification

Before declaring completion, verify DEEP coverage — not just proof count.

### Per-Function Depth Check

For each core mutation function, you MUST have at least 5 of these:

| Pattern | Required For |
|---------|-------------|
| P10a Inductive (raw primitives) | Every accounting operation |
| P1 Conservation | Every fund-moving operation |
| P3 INV Preservation | EVERY mutation (mandatory) |
| P2 Frame/Isolation | Every per-account operation |
| P4 Error Path (with FullAccountSnapshot) | Every function with validation |
| P7 Arithmetic Safety | Every function with math |
| Anti-exploit variant | Critical functions (value-moving, state-destroying) |

**RED FLAGS — go back and add proofs if:**
- Any core function has fewer than 5 proof patterns
- Zero P10a inductive proofs (these are highest confidence)
- Zero frame proofs with FullAccountSnapshot
- Zero anti-exploit proofs (P13 family)
- More than 30% of proofs test the same pattern (e.g., all INV preservation, no conservation)
- Zero multi-step lifecycle proofs (proofs that chain 2+ operations before checking properties)

## Phase 5: Quality Gate

Count proofs: `grep -c '#\[kani::proof\]' tests/kani.rs`

- First session: 80+. Incremental: 40+. Hard minimum: 60.

**Depth check (MANDATORY):**
- `grep -c 'assert_ok!'` — should appear in 50%+ of proofs (non-vacuity)
- `grep -c 'kani::any()'` — should appear in 80%+ of proofs (symbolic state)
- `grep -c 'snapshot_full_account'` — should appear in 10%+ of proofs (frame proofs)
- `grep -c 'inductive_'` — should have 8+ inductive proofs
- Count proofs that check domain-specific properties (not just canonical_inv) — should be 40%+
- Count proofs with multi-step setup (2+ assert_ok! calls building state) — should be 15%+

**Proof QUALITY check — read 5 random proofs and verify each one:**
1. Does NOT start from empty/fresh state (must have populated accounts)
2. Uses assert_ok! (not `let _result`)
3. Checks at least one domain-specific property beyond canonical_inv
4. Would actually catch a bug if the function had a logic error

If any check fails, return to Phase 3 and strengthen weak areas.
If below count minimum, return to Phase 3 and fill gaps using the Required Proof Categories Checklist in coverage-workflow.md.
