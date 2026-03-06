---
name: kani-proof
description: Writes Kani bounded model checker proofs for Rust programs. Proves conservation, isolation, arithmetic safety, and access control properties. Use when the user asks to write formal verification, Kani proofs, model checking, or when code contains kani::, #[kani::proof], or bounded model checking. Also use when the user mentions proving properties, verifying invariants, or checking for overflows in Rust code.
---

# Kani Formal Verification

Kani is a bounded model checker — it explores ALL possible values of symbolic inputs within bounds, making proofs exhaustive (not sampled like fuzzing). The solver needs help managing the search space, and proofs must be non-vacuous.

## Workflow

### Step 1 — Analyze the Codebase

Before writing any proof, spawn an Explore agent following [references/agents/kani-analyzer-agent.md](references/agents/kani-analyzer-agent.md). It will return loop bounds, existing infrastructure, and state construction patterns. Do not skip this — wrong unwind bounds and missed helpers are the top causes of proof failure.

### Step 2 — Write the Proof

Use the agent's output to write a harness. Select a pattern from the [pattern table](#proof-patterns) and see [references/proof-patterns.md](references/proof-patterns.md) for templates.

### Step 3 — Verify and Iterate

Run `cargo kani --harness proof_name` and diagnose failures using the [diagnosis table](#diagnosing-failures). See [references/kani-features.md](references/kani-features.md) for the full Kani API (contracts, stubbing, concrete playback, partitioned verification).

## Kani-Specific Concepts

These are the things that differ from normal Rust testing and that you need to get right.

### Loop Unwinding

`#[kani::unwind(N)]` controls how many loop iterations Kani explores. N must be **max_iterations + 1** (the extra confirms termination). If N is too low, Kani reports "unwinding assertion" errors. If too high, it's slower but still correct — err high.

Trace ALL loops in the call graph (target + callees + constructors). Check for `#[cfg(kani)]` constants that reduce collection sizes during verification — these determine your actual loop bounds.

**Parameter-driven loops:** Constructors and init functions often loop over a size parameter (e.g. `for i in 0..capacity`). If your proof passes config/params to a constructor, those values directly control loop iterations. You must ensure every parameter that drives a loop is small enough for your unwind bound. Use `#[cfg(kani)]` constants when they exist, or pass small values (e.g. 4–8) explicitly. Passing production-sized values (64, 1000, etc.) while using a small unwind will cause unwinding assertion failures.

### Non-Vacuity

A proof can report SUCCESS while proving nothing. This happens when no execution path reaches assertions — because the operation always fails for your inputs, assumptions are contradictory, results are discarded, or state is empty/trivial.

**Detect** with `kani::cover!(condition, "message")` — if Kani reports UNSATISFIABLE, that path is never taken.

**Prevent** by handling results explicitly:

```rust
// VACUOUS — if operation always fails, nothing is checked
if result.is_ok() { assert!(invariant); }

// NON-VACUOUS — proof fails if operation can't succeed
match result {
    Ok(_) => { /* assert properties */ },
    Err(_) => { kani::assert(false, "must succeed"); unreachable!() }
};
```

An `assert_ok!` macro is useful — see [references/proof-patterns.md](references/proof-patterns.md) for the template.

**Use populated state** — empty/fresh state makes invariants trivially true (`0 >= 0 + 0`). Construct state with multiple entities, non-zero values, and realistic complexity.

### Solver Selection

`#[kani::solver(cadical)]` is a good default. Try `kissat` if cadical is slow. Try `minisat` for simple proofs. Switching solvers can dramatically affect performance.

### Symbolic Ranges

`kani::assume()` constraints control the search space. Match the codebase's own validation bounds. Never leave large types (`u128`, `i128`) unconstrained — the solver will timeout. If constraints are contradictory, the proof becomes vacuously true.

## Diagnosing Failures

| Kani Output | Fix |
|-------------|-----|
| `unwinding assertion` | Increase `#[kani::unwind(N)]` |
| Timeout / solver hang | Narrow symbolic ranges, switch solver, reduce state complexity |
| `VERIFICATION:- FAILED` | Use `cargo kani -Z concrete-playback --concrete-playback=print --harness name` |
| `UNDETERMINED` | Stub unsupported features |
| OOM / deadline-exceeded | Simplify harness, tighten bounds |
| `VERIFICATION:- SUCCESSFUL` | Verify non-vacuity — check `kani::cover!()` statements are SATISFIED |

**Iterative strengthening:** WEAK (concrete values) → STRONG (symbolic with bounds) → INDUCTIVE (raw primitives, no data structures).

## Proof Patterns

Select the pattern that matches the property you need to verify. See [references/proof-patterns.md](references/proof-patterns.md) for templates and examples.

| Pattern | When to Use | What It Proves |
|---------|-------------|----------------|
| Conservation | Moves, creates, or destroys quantities | Accounting equation preserved |
| Frame / Isolation | Targets one entity in multi-entity system | Bystander entities unchanged |
| INV Preservation | Any state mutation | Canonical invariant holds before and after |
| Error Path | Input validation / preconditions | Specific error + state completely unchanged |
| Monotonicity | Counters, timestamps, accumulators | Value only moves in one direction |
| Idempotency | Settlement, sync, recompute | Applying twice = applying once |
| Arithmetic Safety | Numeric computation | No overflow/underflow/div-by-zero |
| Access Control | Privileged operations | Unauthorized callers rejected |
| State Machine | Lifecycle transitions | Only valid transitions occur |
| Inductive Delta | Core accounting (strongest form) | Equation holds with raw primitives |
| Lifecycle / Sequence | Multi-step user flows | Properties hold through chained operations |

### Harness Skeleton

```rust
#[cfg(kani)]
mod kani_proofs {
    use super::*;

    #[kani::proof]
    #[kani::unwind(N)]        // from loop analysis
    #[kani::solver(cadical)]
    fn proof_name() {
        // 1. Populated state (not empty)
        // 2. Symbolic inputs with kani::assume() bounds
        // 3. Assert precondition
        // 4. Call function, handle result explicitly (no `let _ =`)
        // 5. Assert postcondition + domain-specific deltas
        // 6. kani::cover!() for non-vacuity
    }
}
```

Beyond checking the canonical invariant, always check **domain-specific properties** — the exact delta, monotonicity, frame conditions, or zero-sum equations specific to the operation.

## Codebase Preparation

The Explore agent identifies what's needed. Common preparations:

- `#[cfg(kani)] const MAX_ITEMS: usize = 4;` — reduce collection sizes
- `[workspace.metadata.kani] flags = { tests = true }` in Cargo.toml
- `#[cfg(kani)] extern crate kani;` at crate root

## Reference Files

- [references/proof-patterns.md](references/proof-patterns.md) — Pattern catalog with templates and examples
- [references/kani-features.md](references/kani-features.md) — Kani API: contracts, stubbing, concrete playback, partitioned verification
- [references/invariant-design.md](references/invariant-design.md) — Layered invariant design methodology
- [references/agents/kani-analyzer-agent.md](references/agents/kani-analyzer-agent.md) — Explore agent for pre-proof codebase analysis
