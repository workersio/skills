# Canonical Proof Patterns

13 patterns for writing Kani proofs, each with a template for verifying Solana and Rust programs.

## Contents
- [Shared Infrastructure](#shared-infrastructure) — macros, snapshots, helpers (COPY VERBATIM)
- [Proof Ordering Strategy](#proof-ordering-strategy) — cheapest to most expensive
- [P1: Conservation](#p1-conservation--accounting-preservation) — fund movement
- [P2: Isolation](#p2-frame-proof-isolation--non-interference) — non-interference
- [P3: INV Preservation](#p3-inv-preservation) — every mutation
- [P4: Error Path](#p4-error-path-correctness) — input validation
- [P5: Monotonicity](#p5-monotonicity--bounded-growth) — only-increase values
- [P6: Idempotency](#p6-idempotency) — settle/sync operations
- [P7: Arithmetic Safety](#p7-arithmetic-safety) — overflow/underflow
- [P8: Access Control](#p8-access-control--authorization) — authorization
- [P9: State Machine](#p9-state-machine-transition-validity) — lifecycle transitions
- [P10: Inductive Delta](#p10-inductive-delta-proof-gold-standard) — strongest form
- [P11: Concrete Known-Bad](#p11-concrete-known-bad-test) — regression tests
- [P12: Lifecycle/Sequence](#p12-lifecyclesequence-proof) — multi-step operation chains
- [P13: Anti-Exploit/Regression](#p13-anti-exploitregression-proof) — teleportation, NEGATIVE, boolean selectors, matchers
- [P14: Liquidation Domain](#p14-liquidation-domain-proofs) — position reduction, insurance, frame property
- [Non-Vacuity: kani::cover!](#non-vacuity-kanicover) — proving proofs are not vacuously true

---

## Shared Infrastructure

These helpers are used across multiple patterns. **COPY ALL of them VERBATIM into your test module.** Do NOT simplify, rename, or omit any piece — proofs depend on the exact API surface.

### Result Macros (CRITICAL — prevents vacuous proofs)

```rust
/// Assert result is Ok, fail proof if Err. Returns the Ok value.
/// EVERY constructive proof calling an engine method MUST use this
/// instead of `let _result = ...` which silently discards errors.
macro_rules! assert_ok {
    ($result:expr, $msg:expr) => {
        match $result {
            Ok(v) => v,
            Err(_) => {
                kani::assert(false, $msg);
                unreachable!()
            }
        }
    };
}

/// Assert result is Err, fail proof if Ok. Returns the Err value.
macro_rules! assert_err {
    ($result:expr, $msg:expr) => {
        match $result {
            Err(e) => e,
            Ok(_) => {
                kani::assert(false, $msg);
                unreachable!()
            }
        }
    };
}
```

### Aggregate Sync

```rust
/// Recompute all aggregate fields from individual accounts.
/// Call after manually setting account fields to ensure aggregates are consistent.
fn sync_engine_aggregates(engine: &mut RiskEngine) {
    engine.recompute_aggregates();
    let mut oi: u128 = 0;
    for idx in 0..MAX_ACCOUNTS {
        if engine.is_used(idx) {
            oi = oi.saturating_add(abs_i128_to_u128(
                engine.accounts[idx].position_size.get()
            ));
        }
    }
    engine.total_open_interest = U128::new(oi);
}
```

### Populated State Constructor (CRITICAL — avoids trivially true proofs)

```rust
/// Create a state with active accounts, non-zero balances, and positions.
/// NEVER use ProgramState::new() directly in proofs — fresh/empty state
/// makes invariants trivially true and catches zero bugs.
///
/// Adapt this template to your program's state structure.
fn create_valid_state() -> ProgramState {
    let mut state = ProgramState::new(test_params());

    // Add multiple active accounts (at least 2 for isolation proofs)
    let user_a = 0usize;
    let user_b = 1usize;
    state.add_account(user_a).unwrap();
    state.add_account(user_b).unwrap();

    // Set symbolic balances — NOT concrete values
    let cap_a: u128 = kani::any();
    kani::assume(cap_a >= 100 && cap_a <= 10_000);
    state.accounts[user_a].capital = cap_a;

    let cap_b: u128 = kani::any();
    kani::assume(cap_b >= 100 && cap_b <= 10_000);
    state.accounts[user_b].capital = cap_b;

    // Set symbolic PnL (can be negative — this is where bugs hide)
    let pnl_a: i128 = kani::any();
    kani::assume(pnl_a > -5_000 && pnl_a < 5_000);
    state.accounts[user_a].pnl = pnl_a;

    // Set non-zero positions (for position-related proofs)
    let pos: i128 = kani::any();
    kani::assume(pos != 0 && pos > -1_000 && pos < 1_000);
    state.accounts[user_a].position_size = pos;

    // Set vault to cover all accounts
    state.vault = cap_a + cap_b + 1_000;  // ensure vault > total capital

    // CRITICAL: recompute aggregates from accounts
    sync_aggregates(&mut state);

    state
}
```

**Why populated state matters:**
- Empty state (`ProgramState::new()`) has all zeros → `vault >= capital + insurance` is `0 >= 0 + 0` → trivially true
- Populated state with negative PnL, open positions, and multiple accounts forces the invariant to actually work
- Bugs only manifest when state has non-trivial combinations (e.g., negative PnL + active position + insufficient capital)

### Snapshot Types (Basic — for frame proofs)

```rust
/// Basic 4-field snapshot for frame proof comparison (P2)
struct AccountSnapshot {
    capital: u128,
    pnl: i128,
    position_size: i128,
    warmup_slope_per_step: u128,
}

fn snapshot_account(a: &Account) -> AccountSnapshot {
    AccountSnapshot {
        capital: a.capital.get(),
        pnl: a.pnl.get(),
        position_size: a.position_size.get(),
        warmup_slope_per_step: a.warmup_slope_per_step.get(),
    }
}

struct GlobalsSnapshot {
    vault: u128,
    insurance_balance: u128,
}

fn snapshot_globals(engine: &RiskEngine) -> GlobalsSnapshot {
    GlobalsSnapshot {
        vault: engine.vault.get(),
        insurance_balance: engine.insurance_fund.balance.get(),
    }
}
```

### Full Account Snapshot (for error-path mutation safety — P4/P13d)

```rust
/// Full 9+ field snapshot capturing ALL mutable account state.
/// Used in error-path proofs to verify NO field was mutated on Err.
struct FullAccountSnapshot {
    capital: u128,
    pnl: i128,
    position_size: i128,
    entry_price: u64,
    warmup_slope_per_step: u128,
    reserved_pnl: u128,
    last_fee_slot: u64,
    fee_credits: u128,
    funding_index: i128,
}

fn snapshot_full_account(a: &Account) -> FullAccountSnapshot {
    FullAccountSnapshot {
        capital: a.capital.get(),
        pnl: a.pnl.get(),
        position_size: a.position_size.get(),
        entry_price: a.entry_price,
        warmup_slope_per_step: a.warmup_slope_per_step.get(),
        reserved_pnl: a.reserved_pnl.get(),
        last_fee_slot: a.last_fee_slot,
        fee_credits: a.fee_credits.get(),
        funding_index: a.funding_index.get(),
    }
}

/// Assert every field of a FullAccountSnapshot matches. Use in error-path proofs
/// to prove the engine made NO state changes when returning Err.
macro_rules! assert_full_snapshot_eq {
    ($before:expr, $after:expr, $msg:expr) => {
        kani::assert($before.capital == $after.capital, concat!($msg, ": capital changed"));
        kani::assert($before.pnl == $after.pnl, concat!($msg, ": pnl changed"));
        kani::assert($before.position_size == $after.position_size, concat!($msg, ": position changed"));
        kani::assert($before.entry_price == $after.entry_price, concat!($msg, ": entry_price changed"));
        kani::assert($before.warmup_slope_per_step == $after.warmup_slope_per_step, concat!($msg, ": warmup changed"));
        kani::assert($before.reserved_pnl == $after.reserved_pnl, concat!($msg, ": reserved_pnl changed"));
        kani::assert($before.last_fee_slot == $after.last_fee_slot, concat!($msg, ": last_fee_slot changed"));
        kani::assert($before.fee_credits == $after.fee_credits, concat!($msg, ": fee_credits changed"));
        kani::assert($before.funding_index == $after.funding_index, concat!($msg, ": funding_index changed"));
    };
}
```

### Totals Struct (for independent aggregate cross-checking)

```rust
/// Independent aggregate recomputation — NOT using engine's own methods.
/// Used to cross-check that engine aggregates are correct.
struct Totals {
    c_tot: u128,
    pnl_pos_tot: u128,
    open_interest: u128,
}

fn recompute_totals(engine: &RiskEngine) -> Totals {
    let mut c_tot: u128 = 0;
    let mut pnl_pos_tot: u128 = 0;
    let mut oi: u128 = 0;
    for idx in 0..MAX_ACCOUNTS {
        if engine.is_used(idx) {
            let a = &engine.accounts[idx];
            c_tot = c_tot.saturating_add(a.capital.get());
            let p = a.pnl.get();
            if p > 0 { pnl_pos_tot = pnl_pos_tot.saturating_add(p as u128); }
            oi = oi.saturating_add(abs_i128_to_u128(a.position_size.get()));
        }
    }
    Totals { c_tot, pnl_pos_tot, open_interest: oi }
}
```

### Non-Vacuity Helpers (CRITICAL — proves operations actually DID something)

```rust
/// Assert a value changed — catches proofs where the operation silently no-ops
fn assert_changed(before: u128, after: u128, msg: &str) {
    kani::assert(before != after, msg);
}

/// Assert a value is nonzero — catches proofs where symbolic setup produces zeros
fn assert_nonzero(val: u128, msg: &str) {
    kani::assert(val > 0, msg);
}

/// Assert an account was freed by GC (slot 0 indicates freed)
fn assert_gc_freed(engine: &RiskEngine, idx: u16) {
    kani::assert(
        !engine.is_used(idx as usize),
        "GC must free the account"
    );
}
```

### N1 Boundary Helper (negative PnL settlement invariant)

```rust
/// N1: Negative PnL must be settled immediately (not time-gated).
/// After any operation that sets negative PnL, the capital must reflect it.
fn n1_boundary_holds(engine: &RiskEngine, idx: usize) -> bool {
    let pnl = engine.accounts[idx].pnl.get();
    if pnl < 0 {
        // Negative PnL should already be reflected in capital reduction
        // or queued for immediate settlement
        true // Specific check depends on program semantics — customize per project
    } else {
        true
    }
}
```

### Integer Safety Helpers

```rust
/// Convert negative i128 to u128 magnitude (handles i128::MIN safely)
fn neg_i128_to_u128(v: i128) -> u128 {
    if v == i128::MIN {
        (i128::MAX as u128) + 1
    } else {
        v.unsigned_abs()
    }
}

/// Clamp u128 to i128 range (saturate at i128::MAX)
fn u128_to_i128_clamped(v: u128) -> i128 {
    if v > i128::MAX as u128 {
        i128::MAX
    } else {
        v as i128
    }
}

/// Absolute value of i128 as u128 (handles i128::MIN)
fn abs_i128_to_u128(v: i128) -> u128 {
    if v == i128::MIN {
        (i128::MAX as u128) + 1
    } else if v < 0 {
        (-v) as u128
    } else {
        v as u128
    }
}
```

### Constants

```rust
/// Default oracle price used across all constructive proofs for consistency.
/// Using a consistent oracle avoids accidental price-dependent divergences.
const DEFAULT_ORACLE: u64 = 1_000_000;
```

---

## Proof Ordering Strategy

When verifying a program with large state structs (like a risk engine with an accounts array), write proofs in this order — from cheapest to most expensive:

1. **Pure function proofs** — Test standalone math functions (fee calculations, ratio computations, mark-to-market) that take primitive inputs and return primitive outputs. These run in seconds regardless of infrastructure setup. Start here to catch arithmetic bugs immediately.

2. **Read-only state proofs** — Test functions that read state fields but don't iterate over arrays (e.g., `is_above_margin()` reads a single account's equity vs margin requirement, `haircut_ratio()` reads global aggregates). Construct minimal state with only the relevant fields set.

3. **Single-account mutation proofs** — Test operations on one account with a small state struct. This is where `#[cfg(kani)]` array size reduction (see `kani-features.md` § "Codebase Preparation") pays off.

4. **Multi-account / aggregate proofs** — Test conservation, isolation, and aggregate coherence across accounts. These require loop unrolling and are the most expensive.

**Why this order matters:**
- If pure function proofs fail, you catch bugs in seconds without solver overhead
- If infrastructure setup (Phase 1.5) is incomplete, categories 1-2 still pass while 3-4 will tell you what's missing
- Inductive delta proofs (P10) with `#[kani::unwind(1)]` bypass loop explosion entirely — try them if category 3-4 proofs are too slow

---

> **Coverage matrix and pattern applicability rules** are in [coverage-workflow.md](coverage-workflow.md). This file focuses on the 10 pattern templates.

---

## P1: Conservation / Accounting Preservation

**When to use:** Any operation that moves funds — deposits, withdrawals, trades, liquidations, fee collection.

**Property:** An accounting equation (e.g., `vault >= total_deposits + insurance`) is preserved by the operation.

**Template A — Constructive conservation (forces success, checks deltas):**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn operation_preserves_conservation() {
    // 1. Create POPULATED state (not empty!)
    let mut state = create_valid_state();  // has active accounts, positions, PnL
    kani::assume(canonical_inv(&state));

    // 2. Symbolic inputs
    let user: usize = kani::any();
    kani::assume(user < MAX_ACCOUNTS && state.is_active(user));
    let amount: u128 = kani::any();
    kani::assume(amount > 0 && amount < REASONABLE_BOUND);

    // 3. Snapshot BEFORE — for delta checks
    let vault_before = state.vault;
    let capital_before = state.accounts[user].capital;

    // 4. Force success — assert_ok! fails the proof if operation can never succeed
    assert_ok!(state.operation(user, amount), "operation must succeed");

    // 5. Conservation holds
    kani::assert(canonical_inv(&state), "INV after operation");

    // 6. Domain-specific delta property — check the EXACT effect
    kani::assert(
        state.accounts[user].capital == capital_before + amount,
        "capital must increase by exactly amount"
    );
    kani::assert(
        state.vault == vault_before + amount,
        "vault must increase by exactly amount"
    );

    kani::cover!(true, "conservation verified on populated state");
}
```

**Template B — Universal conservation (Ok or Err, still holds):**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn operation_conservation_regardless() {
    let mut state = create_valid_state();
    kani::assume(canonical_inv(&state));

    let input: InputType = kani::any();
    kani::assume(valid_input_range(&input));

    // Don't force success — check conservation holds whether Ok or Err
    let _result = state.operation(input);

    kani::assert(canonical_inv(&state), "INV after operation");
}
```

**Use Template A for most proofs** — it catches more bugs because it forces the Ok path and checks specific deltas. Use Template B only for INV-preservation proofs (P3) where you want to cover both outcomes.

**Common mistakes — symbolic vs concrete state setup:**

**WRONG — concrete setup (trivially true):**
```rust
let mut state = ProgramState::new(test_params());
let user = state.add_account(0).unwrap();
state.deposit(user, 10_000).unwrap();  // hard-coded → weak
```

**RIGHT — symbolic setup (tests all valid states):**
```rust
let balance: u128 = kani::any();
kani::assume(balance >= MIN_BALANCE && balance <= MAX_BALANCE);
state.accounts[user].balance = balance;
sync_aggregates(&mut state);  // recompute derived fields from accounts
```

Hard-coded values create trivially simple state where invariants hold vacuously. Always use `kani::any()` with `kani::assume()` to test ALL valid states. Directly assign symbolic values to account fields and recompute aggregates.

---

## P2: Frame Proof (Isolation / Non-Interference)

**When to use:** Multi-user systems where one user's operation must not affect other users' state.

**Property:** After mutating account A, all other accounts remain unchanged.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn operation_only_mutates_target() {
    let mut state = create_valid_state();
    let target = add_account(&mut state);
    let bystander = add_account(&mut state);

    // Snapshot bystander before operation
    let snapshot = snapshot_account(&state.accounts[bystander]);
    let globals_before = snapshot_globals(&state);

    // Execute operation on target only
    state.operation(target);

    // Bystander unchanged
    let after = &state.accounts[bystander];
    assert!(after.capital == snapshot.capital, "capital changed");
    assert!(after.pnl == snapshot.pnl, "pnl changed");
    assert!(after.position_size == snapshot.position_size, "position changed");

    // Global invariants unchanged (if applicable)
    assert!(state.vault == globals_before.vault, "vault changed");
}
```

---

## P3: INV Preservation

**When to use:** Every operation. The most fundamental pattern — the canonical invariant must hold before and after.

**Property:** `canonical_inv(state)` holds after the operation, regardless of whether it succeeded or failed.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn operation_preserves_inv() {
    let mut state = create_valid_state();
    kani::assert(canonical_inv(&state), "INV before");

    let input: InputType = kani::any();
    kani::assume(valid_input_range(&input));

    let _result = state.operation(input);

    // INV preserved regardless of Ok/Err
    kani::assert(canonical_inv(&state), "INV after operation");
}
```

**Key insight:** Don't branch on the result. Assert INV unconditionally. If the operation fails, it should leave state unchanged (or in a valid state).

**You MUST write one `proof_{fn}_preserves_inv` per mutation function.** This is the single highest-value proof pattern — it catches more bugs than any other pattern because `canonical_inv()` checks structural, aggregate, and accounting consistency simultaneously.

---

## P4: Error Path Correctness

**When to use:** Validating that invalid inputs are properly rejected and don't corrupt state.

**Property:** When preconditions are violated, the function returns Err AND the invariant is preserved.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn invalid_input_returns_error() {
    let mut state = create_valid_state();

    let input = kani::any();
    // Assume at least one precondition is violated
    kani::assume(violates_precondition(&input));

    let result = state.operation(input);

    assert!(result.is_err(), "should have failed");
    kani::assert(canonical_inv(&state), "INV preserved on error");
}
```

**Template — Error Path with Full Snapshot (proves NO state mutation on error):**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn proof_deposit_rejects_zero_amount() {
    let mut engine = RiskEngine::new(test_params());
    sync_engine_aggregates(&mut engine);
    kani::assume(canonical_inv(&engine));

    let user = 0u16;
    assert_ok!(engine.add_user(user, DEFAULT_ORACLE), "add user");

    // Snapshot EVERYTHING before the call
    let snap_user = snapshot_account(&engine, user);
    let snap_globals = snapshot_globals(&engine);

    // Invalid input: zero deposit
    let result = engine.deposit(user, 0);

    // Must be rejected
    assert_err!(result, "zero deposit must fail");

    // State must be COMPLETELY unchanged
    let snap_user_after = snapshot_account(&engine, user);
    let snap_globals_after = snapshot_globals(&engine);
    assert_full_snapshot_eq!(snap_user, snap_user_after, "user unchanged on error");
    // Verify globals unchanged too
    kani::assert(snap_globals.vault == snap_globals_after.vault, "vault unchanged");
    kani::assert(snap_globals.insurance == snap_globals_after.insurance, "insurance unchanged");
    kani::assert(canonical_inv(&engine), "INV preserved on error");
    kani::cover!(true, "error path reached");
}
```

**Key principle:** Error path proofs must verify TWO things: (1) the operation returns Err, and (2) NO state was mutated. Use `snapshot_account` + `snapshot_globals` before the call, then `assert_full_snapshot_eq!` after. This catches bugs where invalid input partially mutates state before returning an error.

---

## P5: Monotonicity / Bounded Growth

**When to use:** Values that should only increase (timestamps, nonces, sequence numbers) or only decrease (remaining allowance).

**Property:** `value_after >= value_before` (or `<=` for decreasing).

**Template:**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn slot_advances_monotonically() {
    let mut state = create_valid_state();
    let slot_before = state.current_slot;

    let input = kani::any();
    kani::assume(valid_input(&input));

    let result = state.advance(input);
    if result.is_ok() {
        kani::assert(
            state.current_slot >= slot_before,
            "slot must not go backwards"
        );
    }
}
```

---

## P6: Idempotency

**When to use:** Operations that should produce the same result when applied twice (settlement, synchronization, cache refresh).

**Property:** `f(f(state)) == f(state)` — applying the operation twice gives the same result as applying it once.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn settlement_is_idempotent() {
    let mut state = create_valid_state();

    // Apply once
    state.settle(user_idx).unwrap();
    let after_first = snapshot_account(&state.accounts[user_idx]);

    // Apply again
    state.settle(user_idx).unwrap();
    let after_second = snapshot_account(&state.accounts[user_idx]);

    // Same result
    assert!(after_first.pnl == after_second.pnl);
    assert!(after_first.capital == after_second.capital);
}
```

---

## P7: Arithmetic Safety

**When to use:** Any function with numeric computation — especially token math, fee calculations, exchange rates, interest accrual.

**Property:** No overflow, underflow, or division by zero across the full input range.

**Technique:** For large types (u128, i128), use **partitioned verification** — split the input space into ranges covering near-zero, boundaries, and extremes.

**Template:**
```rust
#[kani::proof]
#[kani::solver(cadical)]
fn arithmetic_no_overflow() {
    let a: u64 = kani::any();
    let b: u64 = kani::any();
    let denominator: u64 = kani::any();

    // Use REALISTIC production values, not arbitrary limits
    // For a DeFi protocol: typical whale = 1-10M tokens
    kani::assume(a >= 1_000_000 * 1_000_000_000);  // >= 1M (with 9 decimals)
    kani::assume(a <= 10_000_000 * 1_000_000_000);  // <= 10M
    kani::assume(b >= 1_000_000 * 1_000_000_000);
    kani::assume(b <= 10_000_000 * 1_000_000_000);
    kani::assume(denominator > 0);

    // Assert the function MUST succeed with realistic inputs
    let result = compute_proportional(a, b, denominator);
    kani::assert(result.is_ok(), "must not overflow with production values");

    kani::cover!(result.is_ok());
}

// For large types, partition the input space:
#[kani::proof]
fn arithmetic_near_zero() {
    let a: u128 = kani::any();
    let b: u128 = kani::any();
    kani::assume(a <= 1000);
    kani::assume(b <= 1000);
    let _result = compute_fee(a, b);
}

#[kani::proof]
fn arithmetic_near_max() {
    let a: u128 = kani::any();
    let b: u128 = kani::any();
    kani::assume(a >= u128::MAX - 1000);
    kani::assume(b >= u128::MAX - 1000);
    let _result = compute_fee(a, b);
}
```

### P7 Subtlety: Assert Success, Not Just Properties

A common false-negative pattern is checking properties of successful results without asserting the function actually succeeds. If the function panics (e.g., on overflow) before returning, the `if let Ok(...)` branch is never taken, and the proof passes vacuously.

**WRONG — misses panics/overflows:**
```rust
#[kani::proof]
fn check_proportional() {
    let amount: u64 = kani::any();
    let total: u64 = kani::any();
    let supply: u64 = kani::any();
    kani::assume(total > 0);

    let result = proportional(amount, total, supply);

    // BUG: if proportional() panics on overflow, this branch is
    // never reached and the proof reports SUCCESSFUL (no assertions fail)
    if let Ok(value) = result {
        kani::assert(value <= supply, "output bounded by supply");
    }
}
```

**CORRECT — catches panics by asserting success:**
```rust
#[kani::proof]
fn check_proportional() {
    let amount: u64 = kani::any();
    let total: u64 = kani::any();
    let supply: u64 = kani::any();
    kani::assume(total > 0);
    kani::assume(amount <= 10_000_000 * 1_000_000_000); // realistic whale deposit

    let result = proportional(amount, total, supply);

    // FIRST: assert the function must succeed with valid inputs
    kani::assert(result.is_ok(), "must not overflow with valid inputs");

    // THEN: check properties of the result
    if let Ok(value) = result {
        kani::assert(value <= supply, "output bounded by supply");
    }
}
```

**When to use each assertion pattern:**

| Pattern | Use When | Example |
|---|---|---|
| `kani::assert(result.is_ok(), ...)` | Function MUST succeed with valid inputs | Token math with production values |
| `kani::cover!(result.is_ok())` | You want to confirm success IS possible (non-vacuity) | General proof coverage |
| `kani::assert(result.is_err(), ...)` | Invalid inputs MUST be rejected | Error path testing (P4) |

---

## P8: Access Control / Authorization

**When to use:** Privileged operations (admin functions, withdrawals, authority changes).

**Property:** Callers without proper authorization receive Err.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn unauthorized_caller_rejected() {
    let mut state = create_valid_state();
    kani::assert(canonical_inv(&state), "INV before");

    // Attempt privileged operation without authorization
    let result = state.admin_operation(unauthorized_caller);

    assert!(result.is_err(), "unauthorized call must fail");
    kani::assert(canonical_inv(&state), "INV preserved on rejection");
}
```

---

## P9: State Machine Transition Validity

**When to use:** Programs with defined lifecycle states (initialized → active → paused → closed).

**Property:** Only valid state transitions occur. Invalid transitions are rejected.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn only_valid_transitions() {
    let mut state = create_valid_state();
    let current = state.status;

    let action = kani::any();
    let result = state.transition(action);

    if result.is_ok() {
        // Verify transition is in the valid set
        kani::assert(
            is_valid_transition(current, state.status),
            "invalid state transition"
        );
    } else {
        // State unchanged on failure
        assert!(state.status == current, "status changed on error");
    }
}
```

---

## P10: Inductive Proofs (Gold Standard)

The strongest form of proof. Proves properties hold for ALL valid states, not just states reachable from a constructor. Two approaches depending on struct size.

### P10a: Mathematical Inductive Proofs (Primary Approach)

**When to use:** Core accounting operations on structs with large arrays (e.g., `[Account; MAX_ACCOUNTS]`). This is the primary approach used in practice.

**Key insight:** Extract the mathematical essence of an operation and prove it with **raw primitive values** (`u128`, `i128`). No struct instantiation, no loops, no `Arbitrary` impl needed.

**How to write one:**
1. Identify the accounting equation: e.g., `vault >= c_tot + insurance`
2. Model the operation as primitive arithmetic: deposit adds `amount` to both `vault` and `c_tot`
3. Use symbolic primitives (NOT struct instances)
4. Assume precondition (equation holds before + no overflow)
5. Model operation effect
6. Assert postcondition (equation holds after)

**Template:**
```rust
#[kani::proof]
fn inductive_operation_preserves_accounting() {
    // Symbolic primitives — NOT a struct
    let vault: u128 = kani::any();
    let c_tot: u128 = kani::any();
    let insurance: u128 = kani::any();
    let amount: u128 = kani::any();

    // Pre: accounting invariant holds
    kani::assume(c_tot.checked_add(insurance).is_some());
    kani::assume(vault >= c_tot + insurance);

    // Pre: no overflow in the operation
    kani::assume(vault.checked_add(amount).is_some());
    kani::assume(c_tot.checked_add(amount).is_some());

    // Model: deposit adds amount to both vault and c_tot
    let vault_after = vault + amount;
    let c_tot_after = c_tot + amount;

    // Post: accounting preserved
    kani::assert(
        vault_after >= c_tot_after + insurance,
        "deposit must preserve vault >= c_tot + insurance",
    );
}
```

**Real example — proving PnL aggregate update is correct:**
```rust
#[kani::proof]
fn inductive_set_pnl_preserves_pnl_pos_tot_delta() {
    let pnl_pos_tot: u128 = kani::any();
    let old_pnl: i128 = kani::any();
    let new_pnl: i128 = kani::any();

    kani::assume(old_pnl != i128::MIN);
    kani::assume(new_pnl != i128::MIN);

    let old_pos: u128 = if old_pnl > 0 { old_pnl as u128 } else { 0 };
    let new_pos: u128 = if new_pnl > 0 { new_pnl as u128 } else { 0 };

    kani::assume(pnl_pos_tot >= old_pos);
    kani::assume(pnl_pos_tot.checked_add(new_pos).is_some());

    // Model: match the function's saturating arithmetic
    let result = pnl_pos_tot.saturating_add(new_pos).saturating_sub(old_pos);
    let expected = pnl_pos_tot - old_pos + new_pos;

    kani::assert(result == expected, "set_pnl delta must correctly update pnl_pos_tot");
}
```

**Write one for each:** deposit, withdraw, settle_loss, settle_profit, fee_transfer, set_capital, set_pnl, top_up_insurance — any operation that modifies accounting state.

### P10b: Fully Symbolic State (Small Structs Only)

> **WARNING:** This approach requires `impl kani::Arbitrary` for the struct. It does NOT work for structs containing large arrays like `[Account; 4096]` or `[u64; 256]`. For those, use P10a above.

**When to use:** Small structs (<100 bytes, no arrays) where implementing `kani::Arbitrary` is feasible: `Duration`, `TokenBucket`, `Config`, simple parameter structs.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(1)]
fn inductive_small_struct_property() {
    let mut state: SmallConfig = kani::any();
    kani::assume(state.is_valid());

    // Execute + assert
    state.update(kani::any());
    kani::assert(state.is_valid(), "validity preserved");
}
```

**Why P10a is preferred:** A mathematical proof with raw primitives covers ALL valid states without needing `Arbitrary`. It's universally applicable — works for any struct size — and runs in seconds with no loop unrolling.

---

## Equivalence Proof (Bonus Pattern)

**When to use:** Verifying that an optimized implementation matches a reference implementation.

**Template:**
```rust
#[kani::proof]
fn optimized_matches_reference() {
    let input: InputType = kani::any();
    assert_eq!(
        reference_implementation(input),
        optimized_implementation(input)
    );
}
```

This pattern caught bugs in ChatGPT-generated code (integer average overflow) and s2n-quic (packet number decoding), finding issues in seconds that fuzzing missed after millions of iterations.

---

## Safety Proof (Bonus Pattern)

**When to use:** When you just want to verify a function doesn't crash/panic/overflow for any input — no specific property needed.

**Template:**
```rust
#[kani::proof]
fn function_never_panics() {
    let input: InputType = kani::any();
    // Just calling it checks for panics, overflows, out-of-bounds, etc.
    let _ = function_under_test(input);
}
```

Simple but powerful. Found 8 boundary bugs in the `hifitime` crate despite 74+ existing integration tests.

---

## P11: Concrete Known-Bad Test

**When to use:** When you suspect a specific bug, want a regression test, or are reproducing a historical vulnerability. Concrete tests use fixed values instead of symbolic inputs, making them fast and targeted.

**Property:** A specific set of inputs triggers the bug (or is proven safe after a fix).

**When to write concrete tests:**
- After a code change that might introduce regressions
- Reproducing a historical or reported vulnerability
- Testing specific boundary values from domain knowledge (whale deposits, max supply, etc.)
- Debugging a symbolic proof failure — extract concrete values to understand the issue
- When symbolic proofs are too slow for a quick smoke test

**Template:**
```rust
#[kani::proof]
fn concrete_known_bad_case() {
    // Use specific values that should trigger the bug
    let input_a: u64 = SPECIFIC_VALUE_A;
    let input_b: u64 = SPECIFIC_VALUE_B;

    // Document WHY these values are interesting
    // e.g., "5M SOL whale deposit into 10M SOL pool"

    let result = function_under_test(input_a, input_b);

    // Assert the expected behavior
    // For bug reproduction: assert it SHOULD succeed but overflows
    kani::assert(result.is_ok(), "must handle this production-realistic case");

    // Optionally verify properties of the result
    if let Ok(value) = result {
        kani::assert(value > 0, "result must be positive");
        kani::assert(value <= input_b, "result bounded by total");
    }
}

// Negative test: verify the bug exists (use before fixing)
#[kani::proof]
#[kani::should_panic]
fn concrete_known_bad_case_panics() {
    let input_a: u64 = SPECIFIC_VALUE_A;
    let input_b: u64 = SPECIFIC_VALUE_B;
    // This SHOULD panic due to the overflow bug
    let _result = function_under_test(input_a, input_b);
}
```

**Real example — Marinade `proportional()` whale deposit overflow:**
```rust
/// Concrete test: 5M SOL whale deposit into a pool with 10M SOL total
/// and matching mSOL supply. The intermediate multiplication
/// `stake_amount * total_supply` overflows u64.
#[kani::proof]
fn proportional_5m_sol_concrete() {
    // Realistic whale deposit scenario
    let stake_amount: u64 = 5_000_000 * 1_000_000_000;   // 5M SOL in lamports
    let total_sol_value: u64 = 10_000_000 * 1_000_000_000; // 10M SOL pool
    let total_msol_supply: u64 = 9_800_000 * 1_000_000_000; // ~9.8M mSOL

    // This should work for any production-realistic deposit
    // BUG: stake_amount * total_msol_supply = 4.9e28 > u64::MAX (1.8e19)
    let result = proportional(stake_amount, total_sol_value, total_msol_supply);

    kani::assert(
        result.is_ok(),
        "5M SOL deposit must not overflow — use u128 intermediate"
    );

    if let Ok(msol_to_mint) = result {
        // Sanity: minted amount should be proportional
        kani::assert(msol_to_mint > 0, "must mint some mSOL");
        kani::assert(
            msol_to_mint <= total_msol_supply,
            "cannot mint more than total supply"
        );
    }
}
```

**Benefits over symbolic proofs:**
- **Fast:** Runs in seconds, no solver overhead
- **Targeted:** Tests the exact scenario you care about
- **Self-documenting:** The values tell a story (5M SOL whale deposit)
- **Debugging-friendly:** Easy to step through and understand failures
- **Regression-proof:** Prevents the same bug from returning after a fix

**Progression:** Start with concrete known-bad tests to confirm the bug exists, then write symbolic proofs (P7) with realistic constraints to prove the fix handles ALL production values, not just the specific case.

---

## P12: Lifecycle/Sequence Proof

**When to use:** Verifying that sequences of 2-4 operations maintain invariants. Many bugs only emerge from operation interaction — e.g., deposit then withdraw, trade then liquidate, or crank then settle. Single-operation proofs miss these.

**Property:** After a realistic sequence of operations, conservation and INV are preserved end-to-end.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn proof_sequence_op1_op2_op3() {
    let mut engine = RiskEngine::new(test_params_with_maintenance_fee());
    engine.current_slot = 100;
    engine.last_crank_slot = 100;
    engine.last_full_sweep_start_slot = 100;
    let user_idx = engine.add_user(0).unwrap();

    // Setup valid initial state
    setup_account_with_capital(&mut engine, user_idx, 1_000);
    sync_engine_aggregates(&mut engine);
    kani::assert(canonical_inv(&engine), "INV at start");

    // Step 1: deposit
    let amount: u128 = kani::any();
    kani::assume(amount > 0 && amount < 5_000);
    let _ = engine.deposit(user_idx, amount, engine.current_slot);
    kani::assert(canonical_inv(&engine), "INV after deposit");

    // Step 2: advance slot and crank
    engine.current_slot += 10;
    let _ = engine.keeper_crank(engine.current_slot);
    kani::assert(canonical_inv(&engine), "INV after crank");

    // Step 3: withdraw
    let withdraw_amt: u128 = kani::any();
    kani::assume(withdraw_amt > 0 && withdraw_amt < 3_000);
    let _ = engine.withdraw(user_idx, withdraw_amt, engine.current_slot);
    kani::assert(canonical_inv(&engine), "INV after withdraw");

    // Final conservation check
    kani::assert(
        conservation_fast_no_funding(&engine),
        "conservation preserved through full sequence"
    );
}
```

**Key patterns to cover:**
- `deposit → crank → withdraw` (basic user lifecycle)
- `deposit → trade → liquidate` (forced closure path)
- `trade → price crash → settle_loss` (loss socialization)
- `trade → warmup → withdraw → top_up` (PnL realization)
- `add_user → deposit → trade → close_account` (full account lifecycle)

**Target: 3-5 lifecycle proofs per program.**

---

## P13: Anti-Exploit / Regression Proof

**When to use:** Proving that known DeFi exploit classes are impossible AND that identified design flaws stay fixed. This pattern covers five sub-categories.

### P13a: Value Teleportation (Two-Engine Comparison)

**Property:** Closing a position in one LP pool and opening in another cannot create or destroy value.

**Key technique:** Use **two independent `RiskEngine` instances** with identical setup. Execute the operation on one engine and compare totals with the untouched engine. This proves value cannot be teleported across independent pools.

```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn exploit_no_value_teleportation_cross_lp() {
    // Engine 1: the "source" LP
    let mut engine1 = RiskEngine::new(test_params());
    engine1.current_slot = 100;
    engine1.last_crank_slot = 100;
    engine1.last_full_sweep_start_slot = 100;
    let a1 = assert_ok!(engine1.add_user(0), "add user1 to engine1");

    // Engine 2: the "destination" LP (independent copy)
    let mut engine2 = RiskEngine::new(test_params());
    engine2.current_slot = 100;
    engine2.last_crank_slot = 100;
    engine2.last_full_sweep_start_slot = 100;
    let a2 = assert_ok!(engine2.add_user(0), "add user1 to engine2");

    // Setup identical capital in both
    let cap: u128 = kani::any();
    kani::assume(cap >= 500 && cap <= 5_000);

    engine1.accounts[a1 as usize].capital = U128::new(cap);
    engine1.vault = U128::new(cap + 1_000);
    engine1.insurance_fund.balance = U128::new(1_000);
    sync_engine_aggregates(&mut engine1);

    engine2.accounts[a2 as usize].capital = U128::new(cap);
    engine2.vault = U128::new(cap + 1_000);
    engine2.insurance_fund.balance = U128::new(1_000);
    sync_engine_aggregates(&mut engine2);

    // Record combined total across both engines
    let total_before = engine1.vault.get() + engine1.insurance_fund.balance.get()
                     + engine2.vault.get() + engine2.insurance_fund.balance.get();

    // Close position in engine1 (withdraw all)
    let _ = engine1.withdraw(a1, cap, 100);

    // Open position in engine2 (deposit)
    let _ = engine2.deposit(a2, cap, 100);

    // Total value across both engines must not increase
    let total_after = engine1.vault.get() + engine1.insurance_fund.balance.get()
                    + engine2.vault.get() + engine2.insurance_fund.balance.get();

    kani::assert(total_after <= total_before, "no cross-LP value teleportation");
}
```

### P13b: Phantom Equity

**Property:** Stale mark/entry prices don't inflate equity after settlement.

```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn proof_flaw2_no_phantom_equity_after_mark_settlement() {
    // Setup account with stale entry price
    // Settle mark to oracle
    // Assert equity doesn't exceed capital + realized_pnl
}
```

### P13c: Flaw Regression

For each identified design flaw, write a proof that the fix holds. Name them `proof_flaw{N}_{description}`:

```rust
proof_flaw1_debt_writeoff_requires_flat_position  // Can't write off debt with open position
proof_flaw1_gc_never_writes_off_with_open_position
proof_flaw2_withdraw_settles_before_margin_check  // Settle mark before checking margin
proof_flaw3_warmup_converts_after_single_slot     // Warmup conversion is time-gated
proof_flaw3_warmup_reset_increases_slope_proportionally
```

### P13d: Gap Proofs (Error Path INV Preservation + No Mutation)

For each error path in critical functions, prove the invariant is preserved AND state is unmutated on error. **Use `FullAccountSnapshot` + `assert_full_snapshot_eq!` macro** to verify ALL account fields are untouched:

```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn error_deposit_to_nonexistent_account() {
    let mut engine = RiskEngine::new(test_params());
    let user_idx = assert_ok!(engine.add_user(0), "add user");

    // Setup valid account state
    engine.accounts[user_idx as usize].capital = U128::new(1_000);
    engine.vault = U128::new(2_000);
    engine.insurance_fund.balance = U128::new(1_000);
    sync_engine_aggregates(&mut engine);

    // Snapshot FULL account state before error
    let snap = snapshot_full_account(&engine.accounts[user_idx as usize]);
    let globals = snapshot_globals(&engine);

    // Attempt operation on INVALID index (should fail)
    let invalid_idx = MAX_ACCOUNTS as u16 + 1;
    let result = engine.deposit(invalid_idx, 500, 100);
    assert_err!(result, "deposit to invalid index must fail");

    // Verify NO field was mutated on error — using full snapshot comparison
    let after = snapshot_full_account(&engine.accounts[user_idx as usize]);
    assert_full_snapshot_eq!(snap, after, "error path must not mutate any account field");

    // Globals also unchanged
    kani::assert(engine.vault.get() == globals.vault, "vault changed on error");
    kani::assert(engine.insurance_fund.balance.get() == globals.insurance_balance, "insurance changed on error");
    kani::assert(canonical_inv(&engine), "INV preserved on error");
}
```

### P13e: Extreme Value / No-Panic

Prove critical functions don't panic at extreme input values:

```rust
#[kani::proof]
#[kani::solver(cadical)]
fn proof_gap4_trade_extreme_price_no_panic() {
    let mut engine = setup_valid_engine();
    let price: u64 = kani::any();
    // No assume — test ALL prices including 0, u64::MAX
    let _ = engine.execute_trade(a, b, 100, price, slot);
    // Just reaching here without panic is the proof
}
```

### P13f: Negative Proofs

Prove that skipping a required step BREAKS the invariant (confirms the step is necessary):

```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn proof_NEGATIVE_bypass_set_pnl_breaks_invariant() {
    let mut engine = setup_valid_engine();
    kani::assert(canonical_inv(&engine), "INV before");

    // Manually change position without calling set_pnl
    // (bypass the proper function)
    engine.accounts[0].position_size = I128::new(kani::any());

    // INV SHOULD be broken — if it's not, the invariant is too weak
    kani::assert(!canonical_inv(&engine), "bypassing set_pnl MUST break INV");
}
```

### P13g: Boolean Selector Proofs (Exponential Path Coverage)

**When to use:** When you want to cover many code paths in a single proof. Use `kani::any::<bool>()` as a symbolic branch selector — Kani explores BOTH branches, giving exponential coverage.

```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn exploit_multi_path_conservation() {
    let mut engine = RiskEngine::new(test_params_with_maintenance_fee());
    engine.current_slot = 100;
    engine.last_crank_slot = 100;
    engine.last_full_sweep_start_slot = 100;
    let user = assert_ok!(engine.add_user(0), "add user");

    let cap: u128 = kani::any();
    kani::assume(cap >= 500 && cap <= 5_000);
    engine.accounts[user as usize].capital = U128::new(cap);
    engine.vault = U128::new(cap + 1_000);
    engine.insurance_fund.balance = U128::new(1_000);
    sync_engine_aggregates(&mut engine);

    kani::assert(canonical_inv(&engine), "INV before");

    // Boolean selectors — Kani explores ALL 2^3 = 8 combinations
    let do_deposit: bool = kani::any();
    let do_advance_slot: bool = kani::any();
    let do_withdraw: bool = kani::any();

    if do_deposit {
        let amt: u128 = kani::any();
        kani::assume(amt > 0 && amt < 3_000);
        let _ = engine.deposit(user, amt, engine.current_slot);
    }

    if do_advance_slot {
        engine.current_slot += 10;
        engine.last_crank_slot = engine.current_slot;
        engine.last_full_sweep_start_slot = engine.current_slot;
    }

    if do_withdraw {
        let amt: u128 = kani::any();
        kani::assume(amt > 0 && amt < 2_000);
        let _ = engine.withdraw(user, amt, engine.current_slot);
    }

    // Conservation must hold across ALL path combinations
    kani::assert(canonical_inv(&engine), "INV after multi-path");
    kani::assert(
        conservation_fast_no_funding(&engine),
        "conservation after multi-path"
    );
}
```

**Why this is powerful:** A single proof with N boolean selectors covers 2^N paths. Three selectors = 8 paths. Five selectors = 32 paths. This catches interaction bugs between operations that single-operation proofs miss.

### P13h: Custom Matching Engine Stubs (Trade Proofs)

**When to use:** Proofs involving `execute_trade()` need controlled matcher behavior. Define custom `MatchingEngine` implementations:

```rust
/// Always fills at the given oracle price with zero fees
struct ZeroFillMatcher;
impl MatchingEngine for ZeroFillMatcher {
    fn fill(&self, _a: u16, _b: u16, size: i128, oracle: u64, _slot: u64) -> FillResult {
        FillResult { fill_size: size, fill_price: oracle, fee_a: 0, fee_b: 0 }
    }
}

/// Always rejects trades — for testing error paths
struct RejectAllMatcher;
impl MatchingEngine for RejectAllMatcher {
    fn fill(&self, _a: u16, _b: u16, _size: i128, _oracle: u64, _slot: u64) -> FillResult {
        FillResult { fill_size: 0, fill_price: 0, fee_a: 0, fee_b: 0 }
    }
}

/// Fills at an exact specified price
struct ExactPriceMatcher(u64);
impl MatchingEngine for ExactPriceMatcher {
    fn fill(&self, _a: u16, _b: u16, size: i128, _oracle: u64, _slot: u64) -> FillResult {
        FillResult { fill_size: size, fill_price: self.0, fee_a: 0, fee_b: 0 }
    }
}
```

Define 5-7 matchers to cover: zero-fill, reject-all, max-size, exact-price, partial-fill, high-fee, and slippage scenarios. Each trade proof should use a specific matcher that targets the code path being tested.

**Target: 15-30 anti-exploit proofs per DeFi program.** Name them with `exploit_`, `proof_flaw{N}_`, `proof_gap{N}_`, `proof_NEGATIVE_`, or descriptive names like `exploit_no_value_teleportation_cross_lp`.

---

## P14: Liquidation Domain Proofs

**When to use:** Programs with liquidation logic — verify liquidation correctly reduces positions, transfers collateral, updates insurance, and preserves invariants.

**Property:** After liquidation:
1. Liquidated account's position is reduced or zeroed
2. Insurance fund receives the correct premium
3. Vault balance and conservation invariant hold
4. Non-liquidated accounts are untouched (frame property)

**Template — Liquidation Reduces Position:**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn proof_liquidate_reduces_position() {
    let mut engine = RiskEngine::new(test_params());
    sync_engine_aggregates(&mut engine);
    kani::assume(canonical_inv(&engine));

    // Setup: add users and put one underwater
    let lp = 0u16;
    assert_ok!(engine.add_lp(lp), "add lp");
    let user = 1u16;
    assert_ok!(engine.add_user(user, DEFAULT_ORACLE), "add user");

    // Give user a position that can be liquidated
    let deposit: u64 = kani::any();
    kani::assume(deposit > 0 && deposit < 1_000_000);
    assert_ok!(engine.deposit(user, deposit), "deposit");

    let snap_before = snapshot_account(&engine, user);

    // Liquidate
    let result = engine.liquidate(user, DEFAULT_ORACLE);
    if result.is_ok() {
        let snap_after = snapshot_account(&engine, user);
        // Position must be reduced or zeroed
        kani::assert(
            snap_after.capital <= snap_before.capital,
            "liquidation must reduce or zero position"
        );
        // INV must hold
        kani::assert(canonical_inv(&engine), "INV after liquidation");
        // Non-vacuity
        kani::cover!(true, "liquidation succeeded");
    }
}
```

**Template — Liquidation Insurance Premium:**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn proof_liquidate_insurance_premium() {
    let mut engine = RiskEngine::new(test_params());
    sync_engine_aggregates(&mut engine);
    kani::assume(canonical_inv(&engine));

    // Setup users
    let lp = 0u16;
    assert_ok!(engine.add_lp(lp), "add lp");
    let user = 1u16;
    assert_ok!(engine.add_user(user, DEFAULT_ORACLE), "add user");

    let deposit: u64 = kani::any();
    kani::assume(deposit > 0 && deposit < 1_000_000);
    assert_ok!(engine.deposit(user, deposit), "deposit");

    let insurance_before = engine.insurance;

    let result = engine.liquidate(user, DEFAULT_ORACLE);
    if result.is_ok() {
        // Insurance must not decrease during liquidation
        kani::assert(
            engine.insurance >= insurance_before,
            "insurance must not decrease during liquidation"
        );
        kani::assert(canonical_inv(&engine), "INV after liquidation");
    }
}
```

**Template — Liquidation Frame (Other Accounts Untouched):**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn proof_liquidate_frame_other_accounts() {
    let mut engine = RiskEngine::new(test_params());
    sync_engine_aggregates(&mut engine);
    kani::assume(canonical_inv(&engine));

    let lp = 0u16;
    assert_ok!(engine.add_lp(lp), "add lp");
    let user_a = 1u16;
    let user_b = 2u16;
    assert_ok!(engine.add_user(user_a, DEFAULT_ORACLE), "add user_a");
    assert_ok!(engine.add_user(user_b, DEFAULT_ORACLE), "add user_b");

    let deposit: u64 = kani::any();
    kani::assume(deposit > 0 && deposit < 500_000);
    assert_ok!(engine.deposit(user_a, deposit), "deposit a");
    assert_ok!(engine.deposit(user_b, deposit), "deposit b");

    let snap_b_before = snapshot_account(&engine, user_b);

    // Liquidate user_a only
    let _ = engine.liquidate(user_a, DEFAULT_ORACLE);

    let snap_b_after = snapshot_account(&engine, user_b);
    assert_full_snapshot_eq!(snap_b_before, snap_b_after, "user_b must be untouched");
}
```

**Target: 6-10 liquidation proofs** covering: position reduction, insurance premium, frame property, error paths (non-liquidatable user rejected), conservation, and sequence (deposit → liquidate → withdraw remaining).

---

## Non-Vacuity: assert_ok! (PRIMARY) + kani::cover! (SUPPLEMENTARY)

**CRITICAL:** Non-vacuity requires TWO mechanisms used together:

1. **`assert_ok!()` — PRIMARY mechanism.** This FORCES the Ok path. If the operation can never succeed under the given constraints, the proof FAILS. This is the actual non-vacuity guarantee.
2. **`kani::cover!(true, "reached")` — SUPPLEMENTARY.** This is instrumentation for Kani's log output. It does NOT fail the proof if unreachable.

**WRONG — vacuous (cover alone doesn't fail the proof):**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn proof_operation_vacuous() {
    let mut state = create_valid_state();
    kani::assume(canonical_inv(&state));

    let amount: u64 = kani::any();
    kani::assume(amount > 0 && amount < 1_000_000);

    let result = state.operation(0, amount);
    kani::cover!(result.is_ok());  // if operation always fails, proof STILL PASSES!
    // ^^^ cover! is just a marker — it does NOT cause proof failure
}
```

**RIGHT — non-vacuous (assert_ok forces success):**
```rust
#[kani::proof]
#[kani::unwind(33)]
#[kani::solver(cadical)]
fn proof_operation_preserves_inv() {
    let mut state = create_valid_state();
    kani::assume(canonical_inv(&state));

    let user: usize = kani::any();
    kani::assume(user < state.num_accounts());
    let amount: u64 = kani::any();
    kani::assume(amount > 0 && amount < 1_000_000);

    // PRIMARY non-vacuity: assert_ok! fails the proof if operation can never succeed
    assert_ok!(state.operation(user, amount), "operation must succeed");
    kani::assert(canonical_inv(&state), "INV after operation");
    // SUPPLEMENTARY: instrumentation for Kani logs
    kani::cover!(true, "operation path reached");
}
```

**Rules:**
- **Every constructive proof MUST use `assert_ok!()`** — this is the primary non-vacuity mechanism
- Add `kani::cover!(true, "branch reached")` as supplementary instrumentation after `assert_ok!()`
- For error path proofs (P4), use `assert_err!()` instead of `assert_ok!()`
- **NEVER rely on `kani::cover!()` alone** — it does not fail the proof if the path is unreachable
- Kani reports cover hits in its output — useful for debugging but not a correctness guarantee
