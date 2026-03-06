---
name: kani-proof
description: Writes Kani bounded model checker proofs for Rust programs. Proves conservation, isolation, arithmetic safety, and access control properties. Use when the user asks to write formal verification, Kani proofs, model checking, or when code contains kani::, #[kani::proof], or bounded model checking. Also use when the user mentions proving properties, verifying invariants, or checking for overflows in Rust code.
---

# Kani Formal Verification

Kani is a bounded model checker — it explores ALL possible values of symbolic inputs within bounds, making proofs exhaustive (not sampled like fuzzing).

## Critical Rules

These rules prevent the most common proof failures. Violating any one will likely cause the proof to fail.

1. **No `#[kani::unwind]` or `#[kani::solver]` on first attempt.** Omit both decorators entirely. Only add `#[kani::unwind(N)]` after getting an "unwinding assertion" error, and only add `#[kani::solver(cadical)]` after a timeout. Kani's defaults work better than guessing.

2. **Assert the target property inline, not via helper methods.** Do not call methods that check multiple invariants or iterate over collections — they introduce loops, extra assertions, and unrelated failure points. Read the struct fields directly and write the comparison yourself:
   ```rust
   // WRONG — helper checks more than the target property, adds loops
   assert!(engine.check_all_invariants());

   // RIGHT — asserts exactly what you're proving, no extra logic
   assert!(engine.x.get() >= engine.y.get() + engine.z.get());
   ```

3. **Use `kani::any()` without `kani::assume()` bounds first.** Only add assume constraints after a timeout or OOM. Unconstrained symbolic values are often easier for the solver than bounded ranges.

4. **Build state through public API only.** Use constructors, `add_user()`, `deposit()`, etc. Never assign struct fields directly — it creates unreachable states that cause spurious failures. The only exception is `vault` or similar top-level fields with no setter API.

5. **Stack allocation, not Box.** Use `let mut engine = Engine::new(params)` not `Box::new(Engine::new(params))`. Box adds heap tracking overhead to the solver.

6. **Small config parameters.** If the constructor takes a size/capacity parameter that controls a loop (e.g. `max_accounts`), pass a small value (4–8) that matches `#[cfg(kani)]` constants found by the analyzer agent.

## Workflow

### Step 1 — Analyze the Codebase

Before writing any proof, spawn an Explore agent following [references/agents/kani-analyzer-agent.md](references/agents/kani-analyzer-agent.md). It will return loop bounds, existing infrastructure, and state construction patterns. Do not skip this.

### Step 2 — Write the Proof

Use the agent's output to write a harness. Select a pattern from the [pattern table](#proof-patterns) and see [references/proof-patterns.md](references/proof-patterns.md) for templates.

### Step 3 — Verify and Iterate

Run `cargo kani --harness proof_name` and diagnose failures using the [diagnosis table](#diagnosing-failures). See [references/kani-features.md](references/kani-features.md) for the full Kani API (contracts, stubbing, concrete playback, partitioned verification).

## Kani-Specific Concepts

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

**Contradictory assumptions:** If every path hits `assume(false)` or all `kani::cover!()` checks are UNSATISFIABLE, your `kani::assume()` constraints are contradictory — no valid inputs exist. Remove constraints and start unconstrained.

### Loop Unwinding

Only relevant if you get an "unwinding assertion" error. Add `#[kani::unwind(N)]` where N = max_iterations + 1. Trace ALL loops in the call graph (target + callees + constructors). Check for `#[cfg(kani)]` constants that reduce collection sizes.

**Parameter-driven loops:** If a constructor loops over a config param (e.g. `for i in 0..capacity`), that param must be small (4–8). Use `#[cfg(kani)]` constants when they exist.

## Diagnosing Failures

| Kani Output | Fix |
|-------------|-----|
| `unwinding assertion` | Add `#[kani::unwind(N)]` with N = loop_count + 1 |
| Timeout / solver hang | Add `kani::assume()` to narrow ranges, try `#[kani::solver(cadical)]` |
| `VERIFICATION:- FAILED` | Use `cargo kani -Z concrete-playback --concrete-playback=print --harness name` |
| OOM / out of memory | Reduce state size, remove Box, fewer symbolic variables |
| `assume(false)` on all paths | Remove `kani::assume()` constraints — they're contradictory |
| `VERIFICATION:- SUCCESSFUL` | Check `kani::cover!()` statements are SATISFIED (non-vacuity) |

**Iterative approach:** Start SIMPLE (no decorators, unconstrained inputs, API-built state) → add constraints only on timeout/OOM → add unwind only on unwinding errors → switch solver only on timeout.

## Proof Patterns

See [references/proof-patterns.md](references/proof-patterns.md) for templates.

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
    // NO #[kani::unwind] — only add after getting unwinding assertion error
    // NO #[kani::solver] — only add after getting timeout
    fn proof_name() {
        // 1. Build state through public API (NOT field mutation)
        // 2. Symbolic inputs: kani::any() with NO kani::assume() bounds
        // 3. Call function, handle result explicitly (no if result.is_ok())
        // 4. Assert ONLY the target property using raw field access
        //    (NOT check_conservation or other aggregate methods)
        // 5. kani::cover!() for non-vacuity
    }
}
```

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
