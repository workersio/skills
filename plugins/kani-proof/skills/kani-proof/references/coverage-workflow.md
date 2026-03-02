# Coverage Workflow — Systematic Proof Enumeration

This file contains the detailed process for building a comprehensive coverage matrix and writing granular proof harnesses. Load this file at the start of Phase 3.

## Contents
- [Step 1: Enumerate ALL Mutation Functions](#step-1-enumerate-all-mutation-functions)
- [Step 2: Build Coverage Matrix](#step-2-build-coverage-matrix)
- [Step 3: Write Proofs by Domain Group](#step-3-write-proofs-by-domain-group)
- [Resume Protocol](#resume-protocol)
- [Example Harness](#example-harness)

---

## Step 1: Enumerate ALL Mutation Functions

List EVERY public function/instruction that modifies state. Don't pick "key" ones — list ALL of them. **Output this table in your chat response** (not as a code comment — the user must see it):

```
## Mutation Function Enumeration

| # | Category    | Function                 | Moves Funds? | Has Validation? | Has Math? | Per-Account? | Monotonic? | Lifecycle? |
|---|-------------|--------------------------|--------------|-----------------|-----------|--------------|------------|------------|
| 1 | Lifecycle   | add_user                 | No           | Yes             | No        | Yes          | No         | Yes        |
| 2 | Lifecycle   | close_account            | No           | Yes             | No        | No           | No         | Yes        |
| 3 | Capital     | deposit                  | Yes          | Yes             | Yes       | Yes          | No         | No         |
| 4 | Capital     | withdraw                 | Yes          | Yes             | Yes       | Yes          | No         | No         |
...
```

The boolean columns map directly to pattern applicability in Step 2:
- Moves Funds -> P1 Conservation
- Has Validation -> P4 Error Path
- Has Math -> P7 Arithmetic Safety
- Per-Account -> P2 Isolation
- Monotonic -> P5 Monotonicity
- Lifecycle -> P9 State Machine

### STOP GATE — Step 1

**You MUST output this enumeration table before writing any code.** After outputting it:
1. Count the functions. A DeFi program typically has 10-25 mutation functions. Fewer than 8 means you missed some.
2. Update your Progress Checklist: `Phase 3a: Output function enumeration table (N functions listed).`
3. Only THEN proceed to Step 2.

---

## Step 2: Build Coverage Matrix

Using the enumeration from Step 1, mark which of the 10 patterns apply to each function. **Output this exact matrix format in your chat response:**

```
## Coverage Matrix

                         P1    P2    P3    P4    P5    P6    P7    P8    P9    P10
                         Cons  Isol  INV   Err   Mono  Idem  Arith Auth  SM    Delta
add_user                 -     -     x     x     -     -     -     -     x     -
close_account            -     -     x     x     -     -     -     -     x     -
deposit                  x     x     x     x     -     -     x     -     -     x
withdraw                 x     x     x     x     -     -     x     -     -     x
set_position             x     x     x     x     -     -     x     -     -     -
mark_pnl                 -     x     x     -     -     -     x     -     -     -
crank                    x     -     x     x     x     x     x     -     -     x
liquidate                x     x     x     x     -     -     x     -     -     -
accrue_funding           x     -     x     x     x     -     x     -     -     -
update_warmup            -     x     x     -     x     -     x     -     -     -
update_params            -     -     x     -     -     -     -     x     -     -

Total proof harnesses: [count each 'x' — this is your OVERALL TARGET]
```

### Pattern Applicability Rules

| Pattern | Question to Ask | Applies To |
|---|---|---|
| P1 Conservation | Does it move, create, or destroy value? | deposit, withdraw, trade, liquidate, fees |
| P2 Isolation | Does it target one entity in a multi-entity system? | Any per-account operation |
| P3 INV Preservation | Is it a mutation function? | **YES -> P3 ALWAYS applies to EVERY mutation** |
| P4 Error Path | Does it have input validation or preconditions? | Functions with require!/if-checks |
| P5 Monotonicity | Does it update a value that only increases/decreases? | Slot advances, nonce increments |
| P6 Idempotency | Is it a settle/sync/recompute operation? | recompute_aggregates, settle_funding |
| P7 Arithmetic Safety | Does it perform numeric computation? | ALL math functions |
| P8 Access Control | Does it check authorization? | Admin operations |
| P9 State Machine | Does it transition between lifecycle states? | open->active->closed transitions |
| P10 Inductive Delta | Is this a critical invariant needing max confidence? | Conservation, aggregate coherence |

### STOP GATE — Step 2

1. Count the total `x`'s in your matrix. This number is your **matrix proof target** (not overall — lifecycle, anti-exploit, and domain-specific proofs add 30-50 more).
2. For a typical DeFi program with 10-20 mutation functions, expect **60-100+ cells** marked.
3. **If you have fewer than 60 x's:** You are missing functions or applicable patterns. Go back to Step 1 and re-check.
4. Update your Progress Checklist: `Phase 3b: Output coverage matrix. Total x's: N.`
5. **Do NOT write any proof code until this matrix is complete and the count is verified.**

---

## Step 3: Write Proofs by Domain Group

The coverage matrix is your PLANNING tool. For execution, group related operations into **domain batches** and write all applicable patterns for each group before moving on.

### Domain-Based Organization

Group your enumerated functions by domain (related operations together):

```
Domain groups (example for a perpetuals engine):

1. Capital Flow:      deposit, withdraw
2. Position Mgmt:     set_position, mark_pnl, execute_trade  ← REQUIRES custom matchers (see below)
3. Settlement/Crank:  keeper_crank, accrue_funding, settle_warmup, settle_mark, touch_account
4. Lifecycle:         add_user, add_lp, close_account
5. Risk:              liquidate, update_warmup
6. GC/Dust:           garbage_collect_dust, dust predicate checks
7. Fee Credits:       settle_maintenance_fee, trading fee crediting, fee_credit deposit
8. Admin:             update_params, set_owner, set_risk_reduction_threshold
```

**Position Management Domain — Custom Matcher Prerequisite:**
Before writing proofs for Domain 2 (Position Mgmt), you MUST define 5-7 custom `MatchingEngine` implementations. Without them, `execute_trade()` proofs either fail or are vacuous because the default matcher behavior is unpredictable under symbolic inputs.

Required matchers:
- `ZeroFillMatcher` — fills at oracle price, zero fees (baseline)
- `RejectAllMatcher` — always rejects trades (error path testing)
- `MaxSizeMatcher` — fills maximum allowed size (boundary testing)
- `ExactPriceMatcher(u64)` — fills at specific price (PnL testing)
- `PartialFillMatcher` — fills half the requested size (partial fill testing)

See proof-patterns.md §P13h for implementation templates.

For each domain group, write multiple proof variants per operation. For example, "Capital Flow" (deposit + withdraw) would produce:
- `inductive_deposit_preserves_accounting` — mathematical proof (Track 1)
- `fast_i2_deposit_preserves_conservation` — fast conservation check
- `fast_frame_deposit_only_mutates_one_account` — isolation/frame proof
- `fast_valid_preserved_by_deposit` — INV preservation
- `error_deposit_zero_amount` — error path
- Same variants for withdraw
- `slow_i2_deposit_with_funding_and_fees` — comprehensive (for critical paths)

### Per-Batch Protocol

After writing each domain group:
1. Compile: `cargo build --tests`
2. Count: `grep -c '#\[kani::proof\]' tests/kani.rs`
3. Update your Progress Checklist with the running count
4. Move to next domain group

### BATCH WRITE ENFORCEMENT (MANDATORY)

**Maximum 15-20 proof harnesses per Write/Edit call.** This is a hard limit.

| Session total target | Number of Write calls needed |
|---|---|
| 60 proofs | 4-5 writes |
| 100 proofs | 6-7 writes |
| 150 proofs | 8-10 writes |

**Why:** A single Write call with 100+ proofs (3000+ lines) causes:
- Context window overflow → silent truncation of later proofs
- Lost proofs that never make it to the file
- Inability to verify intermediate state

**Protocol:**
1. Write infrastructure first (invariants, macros, helpers) — 1 Write call
2. Write inductive proofs (P10a) — 1 Write call (~10-15 proofs)
3. Write constructive proofs domain-by-domain — 1 Write call per domain (~10-20 proofs each)
4. After EACH write, immediately `grep -c '#\[kani::proof\]'` to verify count
5. If count doesn't match expected, re-read the file and investigate before proceeding

### Session Targets

- **First session:** Target 80+ proofs. The matrix typically yields 60-100+ cells, and you should also write lifecycle, anti-exploit, and domain-specific invariant proofs beyond the matrix.
- **Incremental session (existing proofs found):** Target 40+ new proofs covering uncovered matrix cells and missing categories.
- **Overall target:** All matrix `x` cells covered PLUS lifecycle, anti-exploit, and domain-specific invariant proofs. A production DeFi engine should have 120-160 proofs.
- **Hard minimum per session:** 60 harnesses. Below this, continue writing.

### Required Proof Categories Checklist

Before declaring completion, verify you have proofs in ALL of these categories:

```
- [ ] Inductive accounting proofs (P10a) — 1 per accounting operation, ~10-15 proofs
- [ ] INV preservation proofs (P3) — 1 per mutation function, ~10-20 proofs
- [ ] Conservation proofs (P1) — 1 per fund-moving operation, ~5-10 proofs
- [ ] Frame/isolation proofs (P2) — 1 per per-account operation, ~5-10 proofs
- [ ] Error path proofs (P4) — 1 per error condition, ~5-10 proofs
- [ ] Domain-specific invariants (I5/I7/I8/N1/Funding) — ~10-15 proofs
- [ ] Lifecycle/sequence proofs (P12) — multi-step chains, ~3-5 proofs
- [ ] Anti-exploit/regression proofs (P13) — teleportation, phantom equity, flaw/gap, ~15-30 proofs
- [ ] GC/Dust proofs — if program has GC, ~3-5 proofs
- [ ] Fee credit proofs — if program has fees, ~5-10 proofs
- [ ] Extreme value / no-panic proofs — ~5-10 proofs
```

If any category is empty and the program has the corresponding feature, go back and add proofs.

### Required Proof Families by Domain

Beyond per-function/per-pattern proofs, identify the program's **domain-specific proof families**. For each domain the program implements, you MUST write a dedicated family of proofs.

**How to identify required families (DO THIS STEP — don't skip it):**
1. Read every function in the program. Group them by subsystem (e.g., settlement, collateral, matching, fees, funding, liquidation)
2. For each subsystem, identify the key safety properties from the table below
3. Write 3-6 proofs per subsystem, each testing a DIFFERENT property
4. Each proof should use **multi-step state construction** — set up state through a chain of operations, then test the target property
5. **Output a "Domain Families" table** listing each subsystem and its planned proofs BEFORE writing code

**Discovery template — output this for each subsystem you find:**
```
Subsystem: [name]
Functions: [list of functions in this subsystem]
Properties to prove:
  - [ ] [property 1] → proof name: [name]
  - [ ] [property 2] → proof name: [name]
  - [ ] [property 3] → proof name: [name]
State setup: [what multi-step setup is needed to reach interesting states]
```

**Common domain families (write proofs for each that applies):**

**Settlement/Periodic Computation:**
- Idempotency — re-running settlement is a no-op
- Monotonicity — values only move forward (e.g., accruals, timestamps)
- Aggregate correctness — totals match sum of individual values
- Symmetry — balanced operations net to zero (e.g., long/short, debit/credit)

**Collateral/Risk Management:**
- Floor enforcement — minimums are never violated
- Conservation under loss — value isn't created during loss events
- Ordering constraints — operations happen in required sequence
- Insurance/reserve monotonicity — safety buffers don't decrease unexpectedly

**External Input Trust Boundary:**
- Outputs bounded by inputs — external calls can't produce more than requested
- Default/fallback correctness — missing external data uses safe defaults
- Fee bounds — extracted fees never exceed available balance
- Reject-all path — total rejection produces clean error, not corrupt state

**Credit/Token/Balance Tracking:**
- Credits not fungible with principal — tracked values can't be mixed
- Transfer completeness — all tracked values move on account close
- Accumulation correctness — values aggregate from all sources

**Frame/Bystander Proofs (with FullAccountSnapshot):**
- Every per-account operation gets a frame proof using `snapshot_full_account` + `assert_full_snapshot_eq!`
- Verify ALL account fields unchanged, not just the obvious ones (balance, position)

If the program doesn't have a subsystem (e.g., no settlement), skip that family.
If it DOES have the subsystem and you skip the proofs, coverage is incomplete.

### Naming Convention

Use `{speed}_{invariant}_{function}_{variant}`:

```
fast_i2_deposit_preserves_conservation        // Fast conservation check
fast_frame_deposit_only_mutates_one_account   // Isolation/frame proof
inductive_deposit_preserves_accounting        // Mathematical proof (Track 1)
slow_i2_deposit_with_funding_and_fees         // Comprehensive
i5_warmup_monotonicity                        // Specific invariant property
i7_user_isolation_deposit                     // User isolation
error_deposit_zero_amount                     // Error path
```

Naming key:
- `fast_` = tight constraints, quick verification (seconds)
- `slow_` = wide constraints, comprehensive (minutes)
- `frame_` = isolation/non-interference (bystander unchanged)
- `inductive_` = mathematical primitive-level proof (Track 1)
- `exploit_` = anti-exploit proof (teleportation, extraction, phantom equity)
- `error_` = error path proof (invalid input rejected)
- `extreme_` = extreme value / no-panic proof
- `i2_`, `i5_`, `i7_`, `i8_` = specific invariant numbers (document these per project)

**Solver/Unwind Annotations (MANDATORY):**
Every constructive proof (P1-P9, P12-P13) MUST have `#[kani::unwind(33)]` and `#[kani::solver(cadical)]`. Only loop-free inductive proofs (P10a) and pure type-safety proofs may omit them. See SKILL.md §Solver and Unwind Annotation Table.

### Proof Variants Per Operation

For each public mutation function, write these variants:

| Variant | Naming Pattern | Purpose |
|---|---|---|
| Mathematical proof | `inductive_{fn}_preserves_accounting` | Prove accounting equation with raw primitives |
| Fast basic | `fast_i2_{fn}_preserves_conservation` | Quick conservation check, tight constraints |
| Frame proof | `fast_frame_{fn}_only_mutates_one_account` | Verify bystander accounts unchanged |
| INV preservation | `fast_valid_preserved_by_{fn}` | Check invariant maintained |
| Error paths | `error_{fn}_{condition}` | One per error condition |
| Edge variants | `fast_i2_{fn}_with_fees` | With fees, funding, warmup, near_max |
| Slow comprehensive | `slow_i2_{fn}_with_funding_and_fees` | Full invariant, wide constraints |

This produces ~8-12 proofs per function, yielding **100-150+ total** for a 15-function program.

### Beyond the Matrix: Additional Required Proof Categories

The matrix covers per-function per-pattern proofs. You MUST also write proofs in these categories that don't fit neatly into the matrix:

**Lifecycle/Sequence Proofs (P12)** — chain 2-4 operations in realistic user flows:
```rust
proof_sequence_deposit_crank_withdraw         // deposit → crank → withdraw
proof_sequence_deposit_trade_liquidate        // deposit → trade → price crash → liquidate
proof_lifecycle_trade_crash_settle_loss       // trade → price crash → settle loss
proof_lifecycle_trade_warmup_withdraw_topup   // trade → warmup → withdraw → top_up
```

**Anti-Exploit Proofs (P13)** — target known DeFi attack vectors:
```rust
proof_variation_margin_no_pnl_teleport        // cross-LP close cannot create value
proof_flaw2_no_phantom_equity_after_mark      // stale prices don't inflate equity
proof_NEGATIVE_bypass_set_pnl_breaks_inv      // negative proof: skipping step breaks INV
proof_gap2_execute_trade_err_preserves_inv    // error paths preserve invariant
proof_gap4_trade_extreme_price_no_panic       // extreme values don't panic
```

**Domain-Specific Invariant Proofs** — named invariants specific to the business domain:
```rust
i5_warmup_monotonicity                        // warmup only increases
i7_user_isolation_deposit                     // one user's deposit doesn't affect another
i8_equity_with_negative_pnl                   // margin uses equity, not capital
neg_pnl_is_realized_immediately_by_settle     // negative PnL isn't time-gated
funding_p1_settlement_idempotent              // re-settling funding is a no-op
```

### Granular vs Composite

**WRONG — composite proof testing multiple patterns at once:**
```rust
fn deposit_comprehensive_proof() { ... } // 80+ lines, hard to debug
```

**CORRECT — one proof per (function, property) pair:**
```rust
// Separate, focused, 15-40 lines each
fn inductive_deposit_preserves_accounting() { ... }   // Track 1
fn fast_i2_deposit_preserves_conservation() { ... }   // Track 2
fn fast_frame_deposit_only_mutates_one_account() { ... }
fn error_deposit_zero_amount() { ... }
```

### Constraint Guidance

Use realistic production constraints, not conservative ones. `kani::assume(amount <= u64::MAX / 1000)` hides overflow bugs — use actual protocol limits instead. Check the code's own `require!()` bounds for reference.

---

## Resume Protocol

If existing proofs are found (Phase 0.5), follow this protocol:

1. Count existing harnesses: `grep -c '#\[kani::proof\]' tests/kani.rs`
2. List existing proof names: `grep '#\[kani::proof\]' -A1 tests/kani.rs`
3. Build the coverage matrix (Step 2) and mark which cells are already covered
4. Write proofs ONLY for uncovered cells
5. Check if existing proofs need strengthening (WEAK→STRONG→INDUCTIVE)

---

## Example Harness

A conservation proof (assumes Phase 1.5 infrastructure is in place):

```rust
#[kani::proof]
#[kani::unwind(33)]
fn deposit_preserves_conservation() {
    let mut engine = setup_valid_state();
    kani::assert(canonical_inv(&engine), "INV before deposit");

    let amount: u128 = kani::any();
    kani::assume(amount > 0 && amount < 10_000);

    let user_idx: u16 = kani::any();
    kani::assume(engine.is_valid_user(user_idx));

    let result = engine.deposit(user_idx, amount);

    // INV preserved regardless of success or failure
    kani::assert(canonical_inv(&engine), "INV after deposit");

    // Conservation: vault >= total_deposits + insurance
    kani::assert(
        engine.vault >= engine.total_deposits + engine.insurance,
        "conservation violated"
    );

    // Non-vacuity: this path is actually reachable
    kani::cover!(result.is_ok());
}
```

See [proof-patterns.md](proof-patterns.md) for all pattern templates.
