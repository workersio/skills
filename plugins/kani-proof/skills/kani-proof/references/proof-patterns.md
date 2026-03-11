# Proof Patterns

A catalog of patterns for writing Kani proofs. Each pattern targets a different class of property. Choose the pattern that matches what you need to verify.

## Contents
- [Shared Infrastructure](#shared-infrastructure) — reusable macros and helpers
- [Proof Ordering](#proof-ordering) — cheapest to most expensive
- [P1: Conservation](#p1-conservation) — accounting equations preserved
- [P2: Frame / Isolation](#p2-frame--isolation) — bystander state unchanged
- [P3: INV Preservation](#p3-inv-preservation) — canonical invariant maintained
- [P4: Error Path](#p4-error-path) — invalid input rejected, state unchanged
- [P5: Monotonicity](#p5-monotonicity) — value only moves in one direction
- [P6: Idempotency](#p6-idempotency) — applying twice = applying once
- [P7: Arithmetic Safety](#p7-arithmetic-safety) — no overflow/underflow/div-by-zero
- [P8: Access Control](#p8-access-control) — unauthorized callers rejected
- [P9: State Machine](#p9-state-machine) — only valid transitions occur
- [P10: Inductive Delta](#p10-inductive-delta) — strongest form, raw primitives
- [P11: Concrete Known-Bad](#p11-concrete-known-bad) — regression tests
- [P12: Lifecycle / Sequence](#p12-lifecycle--sequence) — multi-step operation chains
- [Equivalence Proof](#equivalence-proof) — optimized matches reference
- [Safety Proof](#safety-proof) — function never panics
- [Non-Vacuity Reference](#non-vacuity-reference) — proving proofs prove something

---

## Shared Infrastructure

These helpers are commonly needed across multiple patterns. Adapt them to your codebase's types and fields.

### Result-Forcing Macros

These are critical for preventing vacuous proofs. Use `assert_ok!` in success-path proofs, `assert_err!` in error-path proofs.

```rust
/// Forces the Ok path — fails the proof if the operation returns Err.
/// Use this instead of `let _ = ...` or `if result.is_ok() { ... }`.
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

/// Forces the Err path — fails the proof if the operation returns Ok.
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

### Snapshot Types

For frame and error-path proofs, snapshot state before the operation and compare after.

```rust
/// Snapshot the fields you care about. Include ALL mutable fields —
/// bugs hide in fields you didn't think to check.
struct AccountSnapshot {
    balance: u128,
    // Add all mutable fields from your account type
}

fn snapshot_account(account: &Account) -> AccountSnapshot {
    AccountSnapshot {
        balance: account.balance,
        // snapshot all fields
    }
}

fn assert_snapshot_eq(before: &AccountSnapshot, after: &AccountSnapshot, msg: &str) {
    kani::assert(before.balance == after.balance, msg);
    // compare all fields
}
```

### Populated State Constructor

Fresh/empty state makes invariants trivially true. Always construct state with realistic complexity.

```rust
/// Create state with active entities, non-zero values, and positions.
/// Adapt to your codebase's state structure.
fn create_populated_state() -> ProgramState {
    let mut state = ProgramState::new(test_params());

    // Add multiple active entities (at least 2 for isolation proofs)
    state.add_entity(0).unwrap();
    state.add_entity(1).unwrap();

    // Set symbolic values — NOT concrete ones
    let balance_a: u128 = kani::any();
    kani::assume(balance_a >= 100 && balance_a <= 10_000);
    state.entities[0].balance = balance_a;

    let balance_b: u128 = kani::any();
    kani::assume(balance_b >= 100 && balance_b <= 10_000);
    state.entities[1].balance = balance_b;

    // Recompute any aggregate/derived fields
    state.recompute_aggregates();

    state
}
```

**Why populated state matters:**
- Empty state has all zeros — invariants like `total >= sum(parts)` become `0 >= 0`, trivially true
- Populated state with non-trivial combinations forces invariants to actually work
- Bugs only manifest when state has realistic complexity (e.g., negative values + active positions)

### Integer Safety Helpers

```rust
/// Absolute value of i128 as u128 (handles i128::MIN safely)
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

## Proof Ordering

Write proofs from cheapest to most expensive:

1. **Pure function proofs** — standalone math functions, primitive inputs/outputs. Run in seconds.
2. **Read-only state proofs** — functions that read but don't iterate. Minimal state setup.
3. **Single-entity mutation proofs** — one entity, small state. Benefits from `#[cfg(kani)]` size reduction.
4. **Multi-entity / aggregate proofs** — conservation, isolation, aggregates. Require loop unrolling, most expensive.

**Why this order:** Early proofs catch bugs fast. If infrastructure is incomplete, categories 1-2 still work while 3-4 tell you what's missing. Inductive proofs (P10) bypass loops entirely — try them if category 3-4 proofs are too slow.

---

## P1: Conservation

**When to use:** Any operation that moves, creates, or destroys quantities — deposits, withdrawals, transfers, trades, fee collection.

**Property:** An accounting equation is preserved by the operation.

### Template A — Forces Success, Checks Deltas (preferred)

```rust
#[kani::proof]
// #[kani::unwind(N)]  — add only after unwinding assertion error
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn operation_preserves_conservation() {
    let mut state = create_populated_state();
    kani::assume(invariant(&state));

    let user: usize = kani::any();
    kani::assume(user < MAX_ENTITIES && state.is_active(user));
    let amount: u128 = kani::any();
    kani::assume(amount > 0 && amount < REASONABLE_BOUND);

    // Snapshot before
    let total_before = state.total_value();
    let user_balance_before = state.entities[user].balance;

    // Force success
    assert_ok!(state.operation(user, amount), "operation must succeed");

    // Conservation: accounting equation preserved
    kani::assert(invariant(&state), "invariant after operation");

    // Domain-specific: check the EXACT effect
    kani::assert(
        state.entities[user].balance == user_balance_before + amount,
        "balance must increase by exactly amount"
    );

    kani::cover!(true, "conservation verified");
}
```

### Template B — Universal (Ok or Err)

```rust
#[kani::proof]
// #[kani::unwind(N)]  — add only after unwinding assertion error
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn operation_conservation_regardless() {
    let mut state = create_populated_state();
    kani::assume(invariant(&state));

    let input = kani::any();
    kani::assume(valid_range(&input));

    let _result = state.operation(input);

    // INV holds regardless of success or failure
    kani::assert(invariant(&state), "invariant after operation");
}
```

Use Template A for most proofs — it catches more bugs by forcing the Ok path and checking specific deltas. Use Template B for INV-preservation (P3) where you want to cover both outcomes.

---

## P2: Frame / Isolation

**When to use:** Multi-entity systems where one entity's operation must not affect others.

**Property:** After operating on entity A, all other entities remain completely unchanged.

```rust
#[kani::proof]
// #[kani::unwind(N)]  — add only after unwinding assertion error
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn operation_only_mutates_target() {
    let mut state = create_populated_state();

    let target: usize = kani::any();
    let bystander: usize = kani::any();
    kani::assume(target != bystander);
    kani::assume(target < MAX_ENTITIES && state.is_active(target));
    kani::assume(bystander < MAX_ENTITIES && state.is_active(bystander));

    // Snapshot bystander — ALL fields
    let snap_before = snapshot_account(&state.entities[bystander]);

    // Execute on target
    let amount: u128 = kani::any();
    kani::assume(amount > 0 && amount <= 5_000);
    assert_ok!(state.operation(target, amount), "operation must succeed");

    // Bystander completely unchanged
    let snap_after = snapshot_account(&state.entities[bystander]);
    assert_snapshot_eq(&snap_before, &snap_after, "bystander must be unchanged");

    kani::cover!(true, "isolation verified");
}
```

**Key:** Snapshot ALL mutable fields, not just the obvious ones.

---

## P3: INV Preservation

**When to use:** Every mutation function. The most fundamental pattern.

**Property:** The canonical invariant holds before and after, regardless of success or failure.

```rust
#[kani::proof]
// #[kani::unwind(N)]  — add only after unwinding assertion error
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn operation_preserves_inv() {
    let mut state = create_populated_state();
    kani::assert(invariant(&state), "INV before");

    let input = kani::any();
    kani::assume(valid_range(&input));

    // Don't branch on the result — check INV unconditionally
    let _result = state.operation(input);

    kani::assert(invariant(&state), "INV after operation");
}
```

Write one per mutation function. This is the highest-value pattern because the invariant checks structural, aggregate, and accounting consistency simultaneously.

---

## P4: Error Path

**When to use:** Validating that invalid inputs are rejected and don't corrupt state.

**Property:** Specific error returned + state is completely unchanged.

```rust
#[kani::proof]
// #[kani::unwind(N)]  — add only after unwinding assertion error
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn operation_rejects_invalid_input() {
    let mut state = create_populated_state();
    kani::assume(invariant(&state));

    // Set up invalid input
    let user: usize = kani::any();
    kani::assume(user < MAX_ENTITIES && state.is_active(user));
    let amount: u128 = kani::any();
    kani::assume(amount > state.entities[user].balance);  // exceeds balance

    // Snapshot EVERYTHING before
    let snap_user = snapshot_account(&state.entities[user]);
    let total_before = state.total_value();

    let result = state.operation(user, amount);

    // Assert the SPECIFIC error variant
    match result {
        Err(MyError::InsufficientBalance) => { /* expected */ },
        Err(other) => panic!("wrong error: {:?}", other),
        Ok(_) => panic!("should have failed"),
    }

    // State COMPLETELY unchanged
    let snap_after = snapshot_account(&state.entities[user]);
    assert_snapshot_eq(&snap_user, &snap_after, "user unchanged on error");
    kani::assert(state.total_value() == total_before, "total unchanged on error");
    kani::assert(invariant(&state), "INV preserved on error");

    kani::cover!(true, "error path reached");
}
```

**Two things to verify:** (1) the operation returns the specific Err variant, and (2) NO state was mutated. Use full snapshots to catch partial mutations.

---

## P5: Monotonicity

**When to use:** Values that should only increase (timestamps, nonces, counters) or only decrease (remaining allowance).

```rust
#[kani::proof]
// #[kani::unwind(N)]  — add only after unwinding assertion error
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn counter_only_increases() {
    let mut state = create_populated_state();
    let counter_before = state.counter;

    let input = kani::any();
    kani::assume(valid_range(&input));

    let result = state.advance(input);
    if result.is_ok() {
        kani::assert(state.counter >= counter_before, "counter must not decrease");
    }
}
```

---

## P6: Idempotency

**When to use:** Settlement, synchronization, cache refresh, recompute operations.

**Property:** `f(f(state)) == f(state)`

```rust
#[kani::proof]
// #[kani::unwind(N)]  — add only after unwinding assertion error
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn settlement_is_idempotent() {
    let mut state = create_populated_state();

    // Apply once
    assert_ok!(state.settle(0), "first settle must succeed");
    let snap_first = snapshot_account(&state.entities[0]);

    // Apply again
    assert_ok!(state.settle(0), "second settle must succeed");
    let snap_second = snapshot_account(&state.entities[0]);

    // Same result
    assert_snapshot_eq(&snap_first, &snap_second, "settle must be idempotent");
}
```

---

## P7: Arithmetic Safety

**When to use:** Any function with numeric computation — especially fee calculations, ratios, interest.

**Property:** No overflow, underflow, or division by zero.

```rust
#[kani::proof]
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn arithmetic_no_overflow() {
    let a: u64 = kani::any();
    let b: u64 = kani::any();
    let denominator: u64 = kani::any();

    // Use realistic production ranges
    kani::assume(a > 0 && a <= 10_000_000);
    kani::assume(b > 0 && b <= 10_000_000);
    kani::assume(denominator > 0);

    // Assert the function MUST succeed with realistic inputs
    let result = compute_ratio(a, b, denominator);
    kani::assert(result.is_ok(), "must not overflow with production values");

    kani::cover!(result.is_ok(), "computation succeeded");
}
```

**For large types (u128, i128)**, partition the input space:
```rust
#[kani::proof]
fn arithmetic_near_zero() {
    let a: u128 = kani::any();
    kani::assume(a <= 1000);
    let _ = compute(a);
}

#[kani::proof]
fn arithmetic_near_max() {
    let a: u128 = kani::any();
    kani::assume(a >= u128::MAX - 1000);
    let _ = compute(a);
}
```

**Subtlety:** Don't guard assertions behind `if let Ok(v) = result` — if the function panics on overflow, the guard is never entered and the proof passes vacuously. Assert success first, then check properties.

---

## P8: Access Control

**When to use:** Privileged operations (admin functions, authority changes).

```rust
#[kani::proof]
// #[kani::unwind(N)]  — add only after unwinding assertion error
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn unauthorized_caller_rejected() {
    let mut state = create_populated_state();
    kani::assert(invariant(&state), "INV before");

    let result = state.admin_operation(unauthorized_caller);

    assert_err!(result, "unauthorized call must fail");
    kani::assert(invariant(&state), "INV preserved on rejection");
}
```

---

## P9: State Machine

**When to use:** Programs with lifecycle states (initialized -> active -> paused -> closed).

```rust
#[kani::proof]
// #[kani::unwind(N)]  — add only after unwinding assertion error
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn only_valid_transitions() {
    let mut state = create_populated_state();
    let status_before = state.status;

    let action = kani::any();
    let result = state.transition(action);

    if result.is_ok() {
        kani::assert(
            is_valid_transition(status_before, state.status),
            "invalid state transition"
        );
    } else {
        kani::assert(state.status == status_before, "status unchanged on error");
    }
}
```

---

## P10: Inductive Delta

The strongest form of proof. Proves properties using raw primitives — no data structures, no loops, no `Arbitrary` needed.

### P10a: Mathematical Induction (Primary)

**When to use:** Core accounting operations. Works for any struct size.

```rust
#[kani::proof]
fn inductive_operation_preserves_equation() {
    // Symbolic primitives — NOT a struct
    let total: u128 = kani::any();
    let sum_parts: u128 = kani::any();
    let amount: u128 = kani::any();

    // Pre: equation holds + no overflow
    kani::assume(sum_parts.checked_add(amount).is_some());
    kani::assume(total.checked_add(amount).is_some());
    kani::assume(total >= sum_parts);

    // Model: operation adds amount to both total and sum_parts
    let total_after = total + amount;
    let sum_parts_after = sum_parts + amount;

    // Post: equation preserved
    kani::assert(total_after >= sum_parts_after, "equation preserved");
}
```

Write one per accounting operation. No `#[kani::unwind]` needed — these run in seconds.

### P10b: Fully Symbolic State (Small Structs Only)

Only works for small structs (<100 bytes, no arrays) where `impl kani::Arbitrary` is feasible.

```rust
#[kani::proof]
#[kani::unwind(1)]  // No loops: prevents unnecessary unwinding attempts
fn inductive_small_struct() {
    let mut state: SmallConfig = kani::any();
    kani::assume(state.is_valid());

    state.update(kani::any());
    kani::assert(state.is_valid(), "validity preserved");
}
```

---

## P11: Concrete Known-Bad

**When to use:** Regression tests, reproducing vulnerabilities, boundary value testing.

```rust
#[kani::proof]
fn concrete_regression_test() {
    // Specific values that should trigger (or guard against) the bug
    let input_a: u64 = 5_000_000 * 1_000_000_000;  // 5M tokens
    let input_b: u64 = 10_000_000 * 1_000_000_000;  // 10M pool

    // Document WHY these values matter
    let result = function_under_test(input_a, input_b);
    kani::assert(result.is_ok(), "must handle production-realistic values");
}
```

Fast and targeted. Use to guard against specific known failure modes.

---

## P12: Lifecycle / Sequence

**When to use:** Multi-step user flows where bugs hide in state transitions between operations.

**Property:** Properties hold through chained operations.

```rust
#[kani::proof]
// #[kani::unwind(N)]  — add only after unwinding assertion error
// #[kani::solver(kissat)]  — add only after timeout with default solver
fn lifecycle_deposit_trade_withdraw() {
    let mut state = create_populated_state();

    let user: usize = kani::any();
    kani::assume(user < MAX_ENTITIES && state.is_active(user));

    // Step 1: Deposit
    let deposit_amount: u128 = kani::any();
    kani::assume(deposit_amount >= 1000 && deposit_amount <= 10_000);
    assert_ok!(state.deposit(user, deposit_amount), "deposit");
    kani::assert(invariant(&state), "INV after deposit");

    // Step 2: Trade (uses deposited funds)
    let trade_size: i128 = kani::any();
    kani::assume(trade_size != 0 && trade_size.abs() <= 500);
    assert_ok!(state.open_position(user, trade_size), "trade");
    kani::assert(invariant(&state), "INV after trade");

    // Step 3: Withdraw remainder
    let withdraw_amount: u128 = kani::any();
    kani::assume(withdraw_amount > 0 && withdraw_amount <= state.entities[user].available());
    assert_ok!(state.withdraw(user, withdraw_amount), "withdraw");
    kani::assert(invariant(&state), "INV after withdraw");

    // Properties hold through entire chain
    kani::cover!(true, "full lifecycle completed");
}
```

**These are high-value proofs** — bugs often manifest only after a sequence of operations builds up complex state. Target multiple flows through the program.

---

## Equivalence Proof

**When to use:** Verifying an optimized implementation matches a reference.

```rust
#[kani::proof]
fn optimized_matches_reference() {
    let input = kani::any();
    assert_eq!(
        reference_impl(input),
        optimized_impl(input)
    );
}
```

---

## Safety Proof

**When to use:** Verifying a function doesn't crash for any input — no specific property needed.

```rust
#[kani::proof]
fn function_never_panics() {
    let input = kani::any();
    let _ = function_under_test(input);
}
```

Simple but powerful. Catches panics, overflows, out-of-bounds, and division-by-zero.

---

## Non-Vacuity Reference

A proof is **vacuous** if no execution path reaches the assertions. It passes but proves nothing.

### Detection

```rust
kani::cover!(true, "proof body reached");
kani::cover!(result.is_ok(), "operation succeeded");
```

If Kani reports UNSATISFIABLE for a cover, that path is never taken.

### Prevention

| Pattern | Risk | Fix |
|---------|------|-----|
| `let _ = operation(...)` | Result discarded, no assertions reached | Use `assert_ok!()` or explicit `match` |
| `if result.is_ok() { assert!(...) }` | If operation always fails, assertions skipped | Use `assert_ok!()` to force success |
| `assert!(result.is_err())` | Passes on ANY error, not the specific one | Match specific error variant |
| `State::new()` without population | Invariants trivially true on empty state | Use `create_populated_state()` |
| Contradictory `kani::assume()` | No valid inputs exist | Add `kani::cover!(true, "inputs exist")` |

### Side-by-Side Example

```rust
// VACUOUS
let result = state.withdraw(0, amount);
if result.is_ok() {
    assert!(state.total >= 0);  // never reached on empty state
}

// NON-VACUOUS
let result = state.withdraw(user, amount);
match result {
    Ok(_) => {
        kani::assert(state.total >= 0, "total non-negative");
    },
    Err(_) => {
        kani::assert(false, "withdraw must succeed");
        unreachable!()
    }
};
kani::cover!(true, "withdraw proof reached");
```
