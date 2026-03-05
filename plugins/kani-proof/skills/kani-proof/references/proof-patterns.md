# Canonical Proof Patterns

13 proof patterns for Kani verification. Adapt struct types, field names, method names, and domain logic to your specific codebase.

## Contents
- [Shared Infrastructure](#shared-infrastructure) — macros, snapshots, helpers
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
- [P13: Anti-Exploit/Regression](#p13-anti-exploitregression-proof) — multi-path, negative, regression
- [Non-Vacuity](#non-vacuity-scenario-aware-strategy--kanicover) — proving proofs are not vacuously true

---

## Shared Infrastructure

These helpers are used across multiple patterns. The macros (`assert_ok!`, `assert_err!`) are universal. Snapshot types and field names should match your program's state structure. Only include helpers that your proofs actually need.

### Result Macros (prevents vacuous proofs)

```rust
/// Assert result is Ok, fail proof if Err. Returns the Ok value.
/// Use this in proofs where the operation is expected to succeed —
/// it prevents vacuity by failing the proof if the operation errors.
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

### Snapshot Pattern (for frame and error-path proofs)

Snapshot all mutable fields of an entity before an operation, then compare after. Adapt the struct to match your program's state.

```rust
/// Snapshot all mutable fields of an entity.
/// Adapt: add every field from your struct that could be mutated.
struct EntitySnapshot {
    field_a: u128,
    field_b: i128,
    // ... add all mutable fields of your entity
}

fn snapshot_entity(state: &MyState, idx: usize) -> EntitySnapshot {
    let e = &state.entities[idx];
    EntitySnapshot {
        field_a: e.field_a,
        field_b: e.field_b,
    }
}

/// Assert every field of two snapshots matches.
/// Use in error-path proofs to prove no state changes on Err.
macro_rules! assert_snapshot_eq {
    ($before:expr, $after:expr, $msg:expr) => {
        kani::assert($before.field_a == $after.field_a, concat!($msg, ": field_a changed"));
        kani::assert($before.field_b == $after.field_b, concat!($msg, ": field_b changed"));
        // ... add one line per field
    };
}
```

**For frame proofs (P2):** snapshot bystander entities before, compare after.
**For error-path proofs (P4):** snapshot ALL entities + globals before, compare after to prove no mutation on Err.

### Aggregate Sync (recompute derived fields)

After manually setting entity fields via `kani::any()`, recompute any derived/aggregate fields to keep state consistent before asserting invariants.

```rust
/// Recompute aggregate fields from individual entities.
/// Adapt: replace with your program's aggregate fields.
fn sync_aggregates(state: &mut MyState) {
    let mut total = 0u128;
    for idx in 0..MAX_ENTITIES {
        if state.is_active(idx) {
            total += state.entities[idx].field_a;
        }
    }
    state.aggregate_total = total;
}
```

### Populated State (avoids trivially true proofs)

When writing proofs, prefer populated state over fresh/empty state:
- Create multiple active entities with non-zero, symbolic values
- Set derived/aggregate fields consistently (call your sync function)
- Empty state makes invariants trivially true — e.g., `total >= 0` when total is 0

```rust
/// Create a state with active entities and non-trivial values.
/// Adapt: use your program's constructor and setup methods.
fn create_populated_state() -> MyState {
    let mut state = MyState::new(test_params());

    // Add multiple entities (at least 2 for isolation proofs)
    state.add_entity(0).unwrap();
    state.add_entity(1).unwrap();

    // Set symbolic values — NOT concrete
    let val_a: u128 = kani::any();
    kani::assume(val_a >= 100 && val_a <= 10_000);
    state.entities[0].field_a = val_a;

    let val_b: u128 = kani::any();
    kani::assume(val_b >= 100 && val_b <= 10_000);
    state.entities[1].field_a = val_b;

    // Recompute aggregates
    sync_aggregates(&mut state);

    state
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

---

## Proof Ordering Strategy

When verifying a program with large state structs (e.g., a struct containing an array of entities), write proofs in this order — from cheapest to most expensive:

1. **Pure function proofs** — Test standalone math functions (fee calculations, ratio computations) that take primitive inputs and return primitive outputs. These run in seconds regardless of infrastructure setup. Start here to catch arithmetic bugs immediately.

2. **Read-only state proofs** — Test functions that read state fields but don't iterate over arrays (e.g., checking a single entity's eligibility). Construct minimal state with only the relevant fields set.

3. **Single-entity mutation proofs** — Test operations on one entity with a small state struct. This is where `#[cfg(kani)]` array size reduction (see `kani-features.md`) pays off.

4. **Multi-entity / aggregate proofs** — Test conservation, isolation, and aggregate coherence across entities. These require loop unrolling and are the most expensive.

**Why this order matters:**
- If pure function proofs fail, you catch bugs in seconds without solver overhead
- If infrastructure setup (helpers, snapshots, invariant function) is incomplete, categories 1-2 still pass while 3-4 will tell you what's missing
- Inductive delta proofs (P10) with `#[kani::unwind(1)]` bypass loop explosion entirely — try them if category 3-4 proofs are too slow

---

## P1: Conservation / Accounting Preservation

**When to use:** Any operation that moves or transforms quantities — transfers, deposits, withdrawals, fee collection.

**Property:** A conservation equation (e.g., `total_in >= total_out + reserves`) is preserved by the operation.

**Template A — Constructive conservation (forces success, checks deltas):**
```rust
#[kani::proof]
#[kani::unwind(N)]  // adapt: set based on loop analysis
#[kani::solver(cadical)]
fn operation_preserves_conservation() {
    // 1. Create POPULATED state (not empty!)
    let mut state = create_populated_state();
    kani::assume(invariant(&state));

    // 2. Symbolic inputs
    let target: usize = kani::any();
    kani::assume(target < MAX_ENTITIES && state.is_active(target));
    let amount: u128 = kani::any();
    kani::assume(amount > 0 && amount <= 10_000);

    // 3. Snapshot BEFORE — for delta checks
    let total_before = state.global_total;
    let entity_val_before = state.entities[target].field_a;

    // 4. Force success — assert_ok! fails the proof if operation can never succeed
    assert_ok!(state.my_operation(target, amount), "operation must succeed");

    // 5. Conservation holds
    kani::assert(invariant(&state), "invariant after operation");

    // 6. Domain-specific delta property — check the EXACT effect
    kani::assert(
        state.entities[target].field_a == entity_val_before + amount,
        "field_a must increase by exactly amount"
    );

    kani::cover!(true, "conservation verified on populated state");
}
```

**Template B — Universal conservation (Ok or Err, still holds):**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn operation_conservation_regardless() {
    let mut state = create_populated_state();
    kani::assume(invariant(&state));

    let input: u128 = kani::any();
    kani::assume(input > 0 && input <= 10_000);

    // Don't force success — check conservation holds whether Ok or Err
    let _result = state.my_operation(input);

    kani::assert(invariant(&state), "invariant after operation");
}
```

**Use Template A for most proofs** — it catches more bugs because it forces the Ok path and checks specific deltas. Use Template B only for INV-preservation proofs (P3) where you want to cover both outcomes.

**Common mistakes — symbolic vs concrete state setup:**

**WEAK — fully concrete setup:**
```rust
let mut state = MyState::new(params());
state.add_entity(0).unwrap();
state.my_operation(0, 10_000).unwrap();  // hard-coded → weak coverage
```

**STRONGER — symbolic setup (tests all valid states):**
```rust
let val: u128 = kani::any();
kani::assume(val >= 100 && val <= 10_000);
state.entities[target].field_a = val;
sync_aggregates(&mut state);  // recompute derived fields
```

Hard-coded values create trivially simple state. Using `kani::any()` with `kani::assume()` for key fields under test gives broader coverage. Use concrete values for fields that aren't the focus of the proof to reduce solver load. Recompute aggregates after assigning fields.

**Combining patterns:** Complex operations (like liquidation or settlement) often need both conservation (P1) and isolation (P2). Write separate proofs for each property, or combine them in a single proof if the solver can handle it.

---

## P2: Frame Proof (Isolation / Non-Interference)

**When to use:** Multi-entity systems where one entity's operation must not affect other entities' state.

**Property:** After mutating entity A, all other entities remain unchanged.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn operation_only_mutates_target() {
    let mut state = create_populated_state();
    let target: usize = 0;
    let bystander: usize = 1;

    // Snapshot bystander before operation
    let snap_before = snapshot_entity(&state, bystander);

    // Execute operation on target only
    let _ = state.my_operation(target, kani::any());

    // Bystander unchanged
    let snap_after = snapshot_entity(&state, bystander);
    assert_snapshot_eq!(snap_before, snap_after, "bystander mutated");

    kani::cover!(true, "isolation verified");
}
```

**Tips:**
- For operations with side effects (fee collection, etc.), consider using zero-fee parameters to isolate the mutation you're testing
- Snapshot ALL mutable fields — missing one field can hide a bug
- Test with both success and failure paths if the operation can fail

---

## P3: INV Preservation

**When to use:** Every operation. The most fundamental pattern — the canonical invariant must hold before and after.

**Property:** `invariant(state)` holds after the operation, regardless of whether it succeeded or failed.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn operation_preserves_inv() {
    let mut state = create_populated_state();
    kani::assert(invariant(&state), "invariant before");

    let input: u128 = kani::any();
    kani::assume(input > 0 && input <= 10_000);

    let _result = state.my_operation(input);

    // Invariant preserved regardless of Ok/Err
    kani::assert(invariant(&state), "invariant after operation");
}
```

**Key insight:** Don't branch on the result. Assert the invariant unconditionally. If the operation fails, it should leave state unchanged (or in a valid state).

**Writing `proof_{fn}_preserves_inv` for each mutation function is high value.** This pattern catches more bugs than most others because `invariant()` checks structural, aggregate, and accounting consistency simultaneously.

---

## P4: Error Path Correctness

**When to use:** Validating that invalid inputs are properly rejected and don't corrupt state.

**Property:** When preconditions are violated, the function returns Err AND the invariant is preserved AND no state was mutated.

**Template — Basic error path:**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn invalid_input_returns_error() {
    let mut state = create_populated_state();

    let input = kani::any();
    // Assume at least one precondition is violated
    kani::assume(violates_precondition(&input));

    let result = state.my_operation(input);

    // Use assert_err! — NOT assert!(result.is_err()) which is too generic
    assert_err!(result, "operation should have rejected invalid input");
    kani::assert(invariant(&state), "invariant preserved on error");
}
```

**Template — Error path with full snapshot (proves NO state mutation on error):**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn error_path_no_mutation() {
    let mut state = create_populated_state();
    kani::assume(invariant(&state));

    // Snapshot all mutable state before the call
    let snap = snapshot_entity(&state, 0);
    let global_before = state.global_total;

    // Attempt operation with invalid input
    let result = state.my_operation(INVALID_INPUT);
    assert_err!(result, "should fail with invalid input");

    // Verify no field was mutated
    let snap_after = snapshot_entity(&state, 0);
    assert_snapshot_eq!(snap, snap_after, "entity state should be unchanged on error");
    kani::assert(state.global_total == global_before, "globals unchanged on error");
    kani::assert(invariant(&state), "invariant preserved on error");
    kani::cover!(true, "error path reached");
}
```

**Key principle:** Error path proofs verify two things: (1) the operation returns Err, and (2) no state was mutated. Use full snapshots before the call, then compare after. This catches bugs where invalid input partially mutates state before returning an error.

---

## P5: Monotonicity / Bounded Growth

**When to use:** Values that should only increase (timestamps, nonces, sequence numbers) or only decrease (remaining allowance).

**Property:** `value_after >= value_before` (or `<=` for decreasing).

**Template:**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn counter_advances_monotonically() {
    let mut state = create_populated_state();
    let counter_before = state.counter;

    let input = kani::any();
    kani::assume(input > 0 && input <= 10_000);

    let result = state.advance(input);
    // Both branches assert something so the proof is never vacuous.
    if result.is_ok() {
        kani::assert(
            state.counter >= counter_before,
            "counter must not go backwards"
        );
    } else {
        // On failure: counter must be unchanged
        kani::assert(
            state.counter == counter_before,
            "counter unchanged on failed advance"
        );
    }
    kani::cover!(result.is_ok(), "advance succeeded");
}
```

---

## P6: Idempotency

**When to use:** Operations that should produce the same result when applied twice (settlement, synchronization, cache refresh).

**Property:** `f(f(state)) == f(state)` — applying the operation twice gives the same result as applying it once.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn operation_is_idempotent() {
    let mut state = create_populated_state();
    let target: usize = 0;

    // Apply once
    state.sync_operation(target).unwrap();
    let after_first = snapshot_entity(&state, target);

    // Apply again
    state.sync_operation(target).unwrap();
    let after_second = snapshot_entity(&state, target);

    // Same result
    assert_snapshot_eq!(after_first, after_second, "second application changed state");
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

    // Constrain to realistic production values
    kani::assume(a >= 1_000 && a <= 10_000_000);
    kani::assume(b >= 1_000 && b <= 10_000_000);
    kani::assume(denominator > 0);

    // Assert the function succeeds with realistic inputs
    let result = compute_ratio(a, b, denominator);
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
fn check_ratio() {
    let amount: u64 = kani::any();
    let total: u64 = kani::any();
    let supply: u64 = kani::any();
    kani::assume(total > 0);

    let result = compute_ratio(amount, total, supply);

    // BUG: if compute_ratio() panics on overflow, this branch is
    // never reached and the proof reports SUCCESSFUL (no assertions fail)
    if let Ok(value) = result {
        kani::assert(value <= supply, "output bounded by supply");
    }
}
```

**CORRECT — catches panics by asserting success:**
```rust
#[kani::proof]
fn check_ratio() {
    let amount: u64 = kani::any();
    let total: u64 = kani::any();
    let supply: u64 = kani::any();
    kani::assume(total > 0);
    kani::assume(amount <= 10_000_000);  // realistic bound

    let result = compute_ratio(amount, total, supply);

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
| `kani::assert(result.is_ok(), ...)` | Function should succeed with valid inputs | Math with production values |
| `kani::cover!(result.is_ok())` | You want to confirm success IS possible (non-vacuity) | General proof coverage |
| `kani::assert(result.is_err(), ...)` | Invalid inputs should be rejected | Error path testing (P4) |

---

## P8: Access Control / Authorization

**When to use:** Privileged operations (admin functions, authority changes, restricted mutations).

**Property:** Callers without proper authorization receive Err.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn unauthorized_caller_rejected() {
    let mut state = create_populated_state();
    kani::assert(invariant(&state), "invariant before");

    // Attempt privileged operation without authorization
    let result = state.admin_operation(UNAUTHORIZED_CALLER);

    // Use assert_err! — NOT assert!(result.is_err()) which is too generic
    assert_err!(result, "unauthorized call must fail");
    kani::assert(invariant(&state), "invariant preserved on rejection");
}
```

---

## P9: State Machine Transition Validity

**When to use:** Programs with defined lifecycle states (initialized -> active -> paused -> closed).

**Property:** Only valid state transitions occur. Invalid transitions are rejected.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn only_valid_transitions() {
    let mut state = create_populated_state();
    let current = state.status;

    let action = kani::any();
    let result = state.transition(action);

    // Both branches assert something so the proof is never vacuous.
    if result.is_ok() {
        kani::assert(
            is_valid_transition(current, state.status),
            "invalid state transition"
        );
    } else {
        // State unchanged on failure
        kani::assert(state.status == current, "status changed on error");
    }
    kani::cover!(result.is_ok(), "transition succeeded");
}
```

---

## P10: Inductive Proofs (Gold Standard)

The strongest form of proof. Proves properties hold for ALL valid states, not just states reachable from a constructor. Two approaches depending on struct size.

### P10a: Mathematical Inductive Proofs (Primary Approach)

**When to use:** Core operations on structs with large arrays. This is the primary approach used in practice.

**Key insight:** Extract the mathematical essence of an operation and prove it with **raw primitive values** (`u128`, `i128`). No struct instantiation, no loops, no `Arbitrary` impl needed.

**How to write one:**
1. Identify the accounting equation: e.g., `total_in >= sum_of_parts + reserves`
2. Model the operation as primitive arithmetic: adding `amount` to both `total_in` and one part
3. Use symbolic primitives (NOT struct instances)
4. Assume precondition (equation holds before + no overflow)
5. Model operation effect
6. Assert postcondition (equation holds after)

**Template:**
```rust
#[kani::proof]
fn inductive_operation_preserves_equation() {
    // Symbolic primitives — NOT a struct
    let total: u128 = kani::any();
    let sum_parts: u128 = kani::any();
    let reserves: u128 = kani::any();
    let amount: u128 = kani::any();

    // Pre: accounting equation holds
    kani::assume(sum_parts.checked_add(reserves).is_some());
    kani::assume(total >= sum_parts + reserves);

    // Pre: no overflow in the operation
    kani::assume(total.checked_add(amount).is_some());
    kani::assume(sum_parts.checked_add(amount).is_some());

    // Model: operation adds amount to both total and sum_parts
    let total_after = total + amount;
    let sum_parts_after = sum_parts + amount;

    // Post: equation preserved
    kani::assert(
        total_after >= sum_parts_after + reserves,
        "operation must preserve total >= sum_parts + reserves",
    );
}
```

**Write one for each:** any operation that modifies the quantities in your accounting equation.

### P10b: Fully Symbolic State (Small Structs Only)

> **WARNING:** This approach requires `impl kani::Arbitrary` for the struct. It does NOT work for structs containing large arrays. For those, use P10a above.

**When to use:** Small structs (<100 bytes, no arrays) where implementing `kani::Arbitrary` is feasible.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(1)]
fn inductive_small_struct_property() {
    let mut state: SmallConfig = kani::any();
    kani::assume(state.is_valid());

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

---

## Safety Proof (Bonus Pattern)

**When to use:** When you want to verify a function doesn't crash/panic/overflow for any input — no specific property needed.

**Template:**
```rust
#[kani::proof]
fn function_never_panics() {
    let input: InputType = kani::any();
    // Just calling it checks for panics, overflows, out-of-bounds, etc.
    let _ = function_under_test(input);
}
```

---

## P11: Concrete Known-Bad Test

**When to use:** When you suspect a specific bug, want a regression test, or are reproducing a historical vulnerability. Concrete tests use fixed values instead of symbolic inputs, making them fast and targeted.

**Property:** A specific set of inputs triggers the bug (or is proven safe after a fix).

**When to write concrete tests:**
- After a code change that might introduce regressions
- Reproducing a historical or reported vulnerability
- Testing specific boundary values from domain knowledge
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
    // e.g., "large input that causes intermediate overflow"

    let result = function_under_test(input_a, input_b);

    // Assert the expected behavior
    kani::assert(result.is_ok(), "must handle this realistic case");

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

**Benefits over symbolic proofs:**
- **Fast:** Runs in seconds, no solver overhead
- **Targeted:** Tests the exact scenario you care about
- **Self-documenting:** The values tell a story
- **Debugging-friendly:** Easy to step through and understand failures
- **Regression-proof:** Prevents the same bug from returning after a fix

**Progression:** Start with concrete known-bad tests to confirm the bug exists, then write symbolic proofs (P7) with realistic constraints to prove the fix handles ALL valid inputs, not just the specific case.

---

## P12: Lifecycle/Sequence Proof

**When to use:** Verifying that sequences of 2-4 operations maintain invariants. Many bugs only emerge from operation interaction — e.g., create then delete, add then remove, or process then settle. Single-operation proofs miss these.

**Property:** After a realistic sequence of operations, the invariant is preserved end-to-end.

**Template:**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn proof_sequence_op_a_op_b_op_c() {
    let mut state = MyState::new(test_params());
    let target: usize = 0;
    state.add_entity(target).unwrap();

    // Setup valid initial state
    state.entities[target].field_a = 1_000;
    sync_aggregates(&mut state);
    kani::assert(invariant(&state), "invariant at start");

    // Step 1: first operation
    let amount: u128 = kani::any();
    kani::assume(amount > 0 && amount <= 5_000);
    let _ = state.operation_a(target, amount);
    kani::assert(invariant(&state), "invariant after step 1");

    // Step 2: second operation
    let _ = state.operation_b(target);
    kani::assert(invariant(&state), "invariant after step 2");

    // Step 3: third operation
    let remove_amt: u128 = kani::any();
    kani::assume(remove_amt > 0 && remove_amt <= 3_000);
    let _ = state.operation_c(target, remove_amt);
    kani::assert(invariant(&state), "invariant after step 3");

    kani::cover!(true, "full sequence completed");
}
```

**Target: 3-5 lifecycle proofs per program** covering the most common operation sequences.

---

## P13: Anti-Exploit / Regression Proof

**When to use:** Proving that known exploit classes are impossible AND that identified design flaws stay fixed.

### P13a: Cross-Instance Comparison

**Property:** Operating on two independent state instances with identical setup cannot create or destroy value.

```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn no_value_creation_across_instances() {
    // Instance 1
    let mut state1 = MyState::new(test_params());
    state1.add_entity(0).unwrap();
    // Instance 2 (independent copy)
    let mut state2 = MyState::new(test_params());
    state2.add_entity(0).unwrap();

    // Setup identical state
    let val: u128 = kani::any();
    kani::assume(val >= 100 && val <= 5_000);
    state1.entities[0].field_a = val;
    state2.entities[0].field_a = val;
    sync_aggregates(&mut state1);
    sync_aggregates(&mut state2);

    let total_before = state1.global_total + state2.global_total;

    // Remove from instance 1, add to instance 2
    let _ = state1.remove(0, val);
    let _ = state2.add(0, val);

    let total_after = state1.global_total + state2.global_total;
    kani::assert(total_after <= total_before, "no value creation across instances");
}
```

### P13b: Flaw Regression

For each identified design flaw, write a proof that the fix holds:

```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn proof_flaw1_fix_holds() {
    // Setup state that would trigger the old bug
    // Assert the fix prevents it
}
```

### P13c: Gap Proofs (Error Path INV + No Mutation)

For each error path in critical functions, prove the invariant is preserved AND state is unmutated on error. Use the full snapshot pattern from P4.

### P13d: Extreme Value / No-Panic

Prove critical functions don't panic at extreme input values:

```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn extreme_input_no_panic() {
    let mut state = create_populated_state();
    let input: u64 = kani::any();
    // No assume — test ALL values including 0, u64::MAX
    let _ = state.critical_operation(input);
    // Just reaching here without panic is the proof
}
```

### P13e: Negative Proofs

Prove that skipping a required step BREAKS the invariant (confirms the step is necessary):

```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn proof_NEGATIVE_bypass_breaks_invariant() {
    let mut state = create_populated_state();
    kani::assert(invariant(&state), "invariant before");

    // Manually change state without going through the proper function
    state.entities[0].field_a = kani::any();

    // Invariant SHOULD be broken — if not, the invariant is too weak
    kani::assert(!invariant(&state), "bypassing proper function should break invariant");
}
```

### P13f: Boolean Selector Proofs (Exponential Path Coverage)

**When to use:** When you want to cover many code paths in a single proof. Use `kani::any::<bool>()` as a symbolic branch selector — Kani explores BOTH branches, giving exponential coverage.

```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn multi_path_invariant() {
    let mut state = create_populated_state();
    kani::assert(invariant(&state), "invariant before");

    // Boolean selectors — Kani explores ALL 2^3 = 8 combinations
    let do_op_a: bool = kani::any();
    let do_op_b: bool = kani::any();
    let do_op_c: bool = kani::any();

    if do_op_a {
        let amt: u128 = kani::any();
        kani::assume(amt > 0 && amt <= 3_000);
        let _ = state.operation_a(0, amt);
    }

    if do_op_b {
        let _ = state.operation_b(0);
    }

    if do_op_c {
        let amt: u128 = kani::any();
        kani::assume(amt > 0 && amt <= 2_000);
        let _ = state.operation_c(0, amt);
    }

    // Invariant must hold across ALL path combinations
    kani::assert(invariant(&state), "invariant after multi-path");
}
```

**Why this is powerful:** A single proof with N boolean selectors covers 2^N paths. Three selectors = 8 paths. Five selectors = 32 paths. This catches interaction bugs between operations that single-operation proofs miss.

---

## Non-Vacuity: Scenario-Aware Strategy + kani::cover!

Non-vacuity strategy depends on the scenario:

1. **Success-required scenario:** use `assert_ok!()` (or equivalent) to force the meaningful path.
2. **May-fail scenario:** do not force success; assert required invariants/properties on the correct path(s).
3. **`kani::cover!(...)` is supplementary instrumentation** and does NOT replace assertions.

**WRONG — vacuous (cover alone doesn't fail the proof):**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn proof_operation_vacuous() {
    let mut state = create_populated_state();
    kani::assume(invariant(&state));

    let amount: u64 = kani::any();
    kani::assume(amount > 0 && amount <= 10_000);

    let result = state.my_operation(0, amount);
    kani::cover!(result.is_ok());  // if operation always fails, proof STILL PASSES!
    // ^^^ cover! is just a marker — it does NOT cause proof failure
}
```

**RIGHT — non-vacuous (success-required scenario):**
```rust
#[kani::proof]
#[kani::unwind(N)]
#[kani::solver(cadical)]
fn proof_operation_preserves_inv() {
    let mut state = create_populated_state();
    kani::assume(invariant(&state));

    let target: usize = kani::any();
    kani::assume(target < MAX_ENTITIES && state.is_active(target));
    let amount: u64 = kani::any();
    kani::assume(amount > 0 && amount <= 10_000);

    // PRIMARY non-vacuity: assert_ok! fails the proof if operation can never succeed
    assert_ok!(state.my_operation(target, amount), "operation must succeed");
    kani::assert(invariant(&state), "invariant after operation");
    // SUPPLEMENTARY: instrumentation for Kani logs
    kani::cover!(true, "operation path reached");
}
```

**Guidelines:**
- Use `assert_ok!()` when the scenario requires success; do not force success when failure is legitimate
- Add `kani::cover!(...)` as supplementary instrumentation to confirm important branches are explored
- For error path proofs (P4), use `assert_err!()` instead of `assert_ok!()`
- Avoid relying on `kani::cover!()` alone — it does not fail the proof if the path is unreachable
- Kani reports cover hits in its output — useful for debugging but not a correctness guarantee
