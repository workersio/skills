---
name: kani-proof
description: Writes Kani bounded model checker proofs for Rust programs. Proves conservation, isolation, arithmetic safety, and access control properties. Use when the user asks to write formal verification, Kani proofs, model checking, or when code contains kani::, #[kani::proof], or bounded model checking.
---

# Kani Formal Verification — Methodology Guide

This skill teaches the methodology for writing Kani proofs that actually verify. It provides general guidance — adapt it to your specific codebase.

## Reference Files

Read the relevant reference before writing proofs:

1. [references/proof-patterns.md](references/proof-patterns.md) — 13 proof patterns with templates and shared helper code
2. [references/kani-features.md](references/kani-features.md) — Kani API, solver selection, loop unwinding, stubbing, function contracts

## Step 1: Understand the Target

Before writing any proof:

1. **Read the function** you're proving properties about. Understand what it mutates.
2. **Identify loops** — count maximum iterations. This determines your unwind bound.
3. **Identify state** — what struct fields get modified? What are the invariants?
4. **Check for existing proofs** — look for `tests/kani.rs` or `#[kani::proof]` in the codebase.

## Step 2: Prepare the Codebase (if needed)

Only if the codebase hasn't been prepared for Kani yet:

- **Reduce state space** — For arrays/collections with configurable size, use `#[cfg(kani)]` to reduce bounds during verification:
  ```rust
  #[cfg(kani)] pub const MAX_ITEMS: usize = 4;
  #[cfg(not(kani))] pub const MAX_ITEMS: usize = 64;
  ```
- **Cargo.toml** — Add `[workspace.metadata.kani]` with `flags = { tests = true }` if proofs live in test files
- **Crate root** — Add `#[cfg(kani)] extern crate kani;` if needed

## Step 3: Write the Proof

### Harness Structure

Every Kani proof follows this pattern:

```rust
#[cfg(kani)]
mod kani_proofs {
    use super::*;

    #[kani::proof]
    #[kani::unwind(N)]        // Set based on loop analysis
    #[kani::solver(cadical)]  // Good default for complex proofs
    fn proof_name() {
        // 1. Create state
        // 2. Set up symbolic inputs with bounded ranges
        // 3. Assert precondition (invariant holds before)
        // 4. Call the function under test
        // 5. Assert postcondition (invariant holds after + domain-specific checks)
        // 6. Add kani::cover!() for non-vacuity evidence
    }
}
```

### Determining Unwind Bounds

The `#[kani::unwind(N)]` attribute controls how many loop iterations Kani explores. Getting this wrong is the #1 cause of verification failure.

**How to determine N:**
1. Find all loops in the function AND its callees (including constructors)
2. Determine the maximum number of iterations for each loop
3. Set N to **max_iterations + 1** (Kani needs one extra to confirm termination)
4. If multiple nested loops exist, you may need a higher bound

**If verification fails with "unwinding assertion" errors** → increase the bound.
**If verification times out** → either reduce symbolic ranges or use function contracts to break the problem into smaller pieces.

**If you can't determine the bound**, start with a small value and increase until unwinding assertions disappear. Common starting points:
- No loops: omit the attribute entirely
- Simple loops over small arrays: `unwind(array_size + 1)`
- Nested loops or constructors with initialization: may need 2-4x the array size

### Symbolic Inputs — Keep Ranges Narrow

Use `kani::any()` with `kani::assume()` to test ranges of inputs. **Narrower ranges = faster verification.**

```rust
// Generate symbolic value
let amount: u128 = kani::any();

// Constrain to a reasonable range — prevents solver timeout
kani::assume(amount > 0 && amount <= 10_000);
```

**Guidelines for choosing ranges:**
- Start with the smallest range that exercises the code paths you care about
- If the solver times out, narrow the ranges further
- Use concrete values for inputs that aren't the focus of the proof (e.g., timestamps, indices)
- Never leave large numeric types (u128, i128) fully unconstrained — the solver will timeout
- Avoid `i128::MIN` for signed values (negation overflow)

### Solver Selection

- **`cadical`** — Good default for complex proofs with arithmetic
- **`kissat`** — Try this if cadical is slow; often faster for long-running harnesses
- **`minisat`** — Fast for simple proofs

If a proof takes >30 seconds, try switching solvers before increasing bounds.

### Non-Vacuity — Proving Your Proof Proves Something

A **vacuous proof** passes because no execution path reaches the assertions. This is the most dangerous pitfall.

**How to prevent vacuity:**

1. **Force success when expected** — If the operation should succeed given your setup, use an assertion that fails the proof if it doesn't:
   ```rust
   // If operation should succeed, make the proof FAIL if it doesn't
   match state.my_operation(target, amount) {
       Ok(v) => v,
       Err(_) => { kani::assert(false, "operation must succeed"); unreachable!() }
   };
   ```

2. **Add coverage witnesses** — `kani::cover!()` checks if a condition CAN be satisfied:
   ```rust
   kani::cover!(true, "proof body was reached");
   kani::cover!(result > 0, "non-trivial result produced");
   ```
   If Kani reports these as UNSATISFIABLE, your proof may be vacuous.

3. **Be cautious with `if result.is_ok()` guards** — If the operation always fails for your symbolic inputs, guarded assertions are silently skipped and the proof becomes vacuous:
   ```rust
   // Risky — if operation always fails, nothing is checked
   if result.is_ok() {
       assert!(invariant_holds());  // never reached!
   }
   ```
   If you use this pattern (e.g., when the operation legitimately may fail for some inputs), add `kani::cover!(result.is_ok(), "operation succeeded")` and verify Kani reports it as SATISFIED.

### Error Path Proofs

When testing that an operation correctly rejects invalid inputs:

1. **Check the specific error variant**, not just that any error occurred:
   ```rust
   match result {
       Err(MyError::InsufficientBalance) => { /* expected */ },
       Err(other) => panic!("wrong error: {:?}", other),
       Ok(_) => panic!("should have failed"),
   }
   ```

2. **Verify state wasn't corrupted** — snapshot state before the call, assert it's unchanged after:
   ```rust
   let state_before = snapshot(&state);
   let result = state.operation(bad_input);
   match result {
       Err(MyError::ExpectedError) => { /* expected */ },
       Err(other) => panic!("wrong error: {:?}", other),
       Ok(_) => panic!("operation should have failed"),
   }
   let state_after = snapshot(&state);
   assert_eq!(state_before, state_after, "state unchanged on error");
   ```

### Domain-Specific Checks

Don't just check that an invariant holds — check the **exact effect** of the operation:

| Check Type | Example |
|-----------|---------|
| Delta/exact effect | `field_after == field_before + amount` |
| Monotonicity | `counter_after >= counter_before` |
| Idempotency | `f(f(state)) == f(state)` |
| Frame/isolation | Bystander fields unchanged after operation on different entity |
| Zero-sum | `total_credits + total_debits == 0` |
| Boundary | Field stays within valid range after operation |

### Frame / Isolation Proofs

To prove an operation only mutates specific fields:

1. Snapshot ALL mutable fields of bystander entities before the operation
2. Execute the operation on the target entity
3. Assert every bystander field is unchanged

**Tip:** For operations with side effects (fee collection, etc.), consider using zero-fee parameters to isolate the mutation you're testing.

## Step 4: Run and Iterate

```bash
# Run a single proof
cargo kani --harness proof_name

# Run all proofs
cargo kani --tests
```

**If verification fails:**
- Check for "unwinding assertion" → increase unwind bound
- Check for UNDETERMINED → may need to stub unsupported features
- Check for timeout → narrow symbolic ranges or switch solver
- Check for counterexample → use concrete playback to debug:
  ```bash
  cargo kani -Z concrete-playback --concrete-playback=print --harness proof_name
  ```

**Strengthen proofs iteratively:**
- WEAK (concrete values) → STRONG (symbolic with bounds) → INDUCTIVE (raw primitives, no data structures)

## Common Pitfalls

1. **Insufficient unwind** — The #1 failure cause. Always check for loops in constructors and callees, not just the function itself.
2. **Unbounded symbolic values** — Large types (u128, i128) without `kani::assume()` constraints will timeout.
3. **Vacuous proofs** — All assertions guarded behind `if result.is_ok()` when the operation always fails.
4. **Generic error checks** — `assert!(result.is_err())` passes on ANY error, not the one you're testing.
5. **Missing aggregate sync** — After manually setting struct fields, recompute any derived/aggregate fields before asserting invariants.
6. **Testing empty state** — Invariants on empty/fresh state are trivially true. Use populated state with multiple entities, non-zero balances, and active positions.

## Proof Patterns Quick Reference

See [references/proof-patterns.md](references/proof-patterns.md) for full templates.

| Pattern | Use When | Key Idea |
|---------|----------|----------|
| P1: Conservation | Quantity-moving operations | Accounting equation preserved |
| P2: Frame/Isolation | Multi-entity systems | Bystander state unchanged |
| P3: INV Preservation | Every mutation | Canonical invariant holds after |
| P4: Error Path | Input validation | Specific error + state unchanged |
| P5: Monotonicity | Timestamps, counters | Value only increases/decreases |
| P6: Idempotency | Sync, settlement | Applying twice = applying once |
| P7: Arithmetic Safety | Any numeric code | No overflow/underflow |
| P8: Access Control | Privileged operations | Unauthorized callers rejected |
| P9: State Machine | Lifecycle states | Only valid transitions occur |
| P10: Inductive Delta | Accounting operations | Raw primitives, strongest form |
| P11: Concrete Known-Bad | Specific bugs | Fixed inputs, regression test |
| P12: Lifecycle | Multi-step flows | Chain operations, check at each step |
| P13: Anti-Exploit | Critical operations | Multi-path, negative, regression |
