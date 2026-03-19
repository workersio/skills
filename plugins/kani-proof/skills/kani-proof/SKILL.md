---
name: kani-proof
description: >-
  Writes Kani bounded model checker proofs for Rust programs. Proves conservation,
  isolation, arithmetic safety, and access control properties. Use when the user asks
  for Kani proofs, bounded model checking, or exhaustive formal verification -- or when
  code contains kani::, #[kani::proof], or #[kani::unwind]. Do NOT use for fuzzing
  (proptest, quickcheck, cargo-fuzz), property testing, or Miri.
---

## Prerequisites

Before writing proofs, verify tools are installed:

1. **Kani:** Run `cargo kani --version`. If missing:
   ```
   cargo install --locked kani-verifier
   cargo kani setup
   ```

2. **Linter (optional but recommended):** Requires Node.js. Runs via `npx -p @workersio/klint klint`.

# Kani Formal Verification

Kani is a bounded model checker — it explores ALL possible values of symbolic inputs within bounds, making proofs exhaustive (not sampled like fuzzing).

## Critical Rules

These rules prevent the most common proof failures. Violating any one will likely cause the proof to fail.

1. **No `#[kani::unwind]` or `#[kani::solver]` on first attempt.** Omit both decorators entirely. Only add `#[kani::unwind(N)]` after getting an "unwinding assertion" error, and only add `#[kani::solver(kissat)]` after a timeout. Kani's defaults work better than guessing.

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

### Classify the Proof

Before choosing a workflow, classify the proof:

- **Simple:** Target is a pure function (no `&mut self`), OR pattern is P7 (Arithmetic Safety) / P11 (Concrete Known-Bad) / Safety / Equivalence, AND no loops in the call graph, AND no multi-entity state construction needed.
- **Standard:** Everything else — stateful mutations, P1–P6/P8–P10/P12, loops, multi-entity state.

---

### Simple Track (no agent spawns)

For simple proofs, work inline without spawning sub-agents:

1. **Write the proof** directly from the pattern template. Read the appropriate [references/templates/](references/templates/) file (e.g., `arithmetic-safety.rs` for P7, `safety.rs` for Safety/Equivalence) and adapt it. Start with [references/templates/infrastructure.rs](references/templates/infrastructure.rs) for shared macros.

2. **Lint inline:** Run the linter directly:
   ```bash
   npx -p @workersio/klint klint <file>
   ```
   Fix any errors or warnings before proceeding.

3. **Verify inline:** Run Kani directly:
   ```bash
   cargo kani --harness <harness_name>
   ```
   If it fails, apply the fixes from [Diagnosing Failures](#diagnosing-failures) and re-run.

---

### Standard Track (with agents)

For complex proofs requiring codebase analysis, state construction, or iterative debugging:

#### Step 1 — Analyze the Codebase

Spawn an Explore agent following [references/agents/kani-analyzer-agent.md](references/agents/kani-analyzer-agent.md). It will return loop bounds, existing infrastructure, and state construction patterns. Do not skip this.

#### Step 2 — Write the Proof

Use the agent's output to write a harness. Select a pattern from the [pattern table](#proof-patterns) and see [references/proof-patterns.md](references/proof-patterns.md) for templates. Template files are available in [references/templates/](references/templates/) — read the appropriate template and adapt it. Start with `infrastructure.rs` for shared macros (assert_ok!, assert_err!, snapshot types).

#### Step 3 — Lint the Proof

After writing the proof and **before** running `cargo kani`, spawn a linter agent following [references/agents/kani-linter-agent.md](references/agents/kani-linter-agent.md). The linter statically detects 23 common anti-patterns (contradictory assumes, missing unwind, vacuity risks, over-constrained inputs, etc.) in seconds — far faster than the minutes-long `cargo kani` run.

- **Errors** → must fix before proceeding to verification (contradictory assumes, dead assertions, harness params)
- **Warnings** → should fix to avoid hangs/OOM/vacuity (missing unwind, no symbolic input, large state space)
- **Suggestions** → consider for proof quality (missing cover, assume ordering)

Fix all errors and address warnings, then re-run the linter until clean before proceeding to Step 4.

#### Step 4 — Verify and Iterate

After the linter is clean, spawn a verifier agent following [references/agents/kani-verifier-agent.md](references/agents/kani-verifier-agent.md). It runs `cargo kani`, parses the output, and returns a structured diagnosis.

If the verifier reports FAIL:
- **unwinding assertion** → add `#[kani::unwind(N)]` with N from the error
- **OOM** → reduce symbolic ranges, lower config params, remove Box
- **assertion failed** → check the failing assertion, fix the proof logic
- **timeout** → try `#[kani::solver(kissat)]`, narrow ranges
- **covers UNSATISFIABLE** → assumptions are contradictory, loosen them

Iterate: fix the proof based on the diagnosis, re-run the linter, then re-run the verifier. Do not submit a proof that has not been verified.

See [references/kani-features.md](references/kani-features.md) for the full Kani API (contracts, stubbing, concrete playback, partitioned verification).

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
| Timeout / solver hang | Add `kani::assume()` to narrow ranges, try `#[kani::solver(kissat)]` |
| `VERIFICATION:- FAILED` | Use `cargo kani -Z concrete-playback --concrete-playback=print --harness name` |
| OOM / out of memory | Reduce state size, remove Box, fewer symbolic variables |
| `assume(false)` on all paths | Remove `kani::assume()` constraints — they're contradictory |
| `VERIFICATION:- SUCCESSFUL` | Check `kani::cover!()` statements are SATISFIED (non-vacuity) |

**Iterative approach:** Start SIMPLE (no decorators, unconstrained inputs, API-built state) → add constraints only on timeout/OOM → add unwind only on unwinding errors → switch solver only on timeout.

## When NOT to Use Kani

Kani has real limits. These situations will waste significant time on doomed proofs:

| Situation | Why Kani Struggles | Better Tool |
|-----------|-------------------|-------------|
| Floating-point arithmetic | No symbolic f32/f64 | proptest, bolero |
| Async code | Runtime not modeled | tokio::test + proptest |
| Network/IO | Cannot model syscalls | Integration tests |
| Deep recursion w/o contracts | Unbounded unrolling | Function contracts or proptest |
| Very large state (>1000 elements) | Solver timeout | Narrow with `#[cfg(kani)]` or fuzz |

## Proof Patterns

See [references/proof-patterns.md](references/proof-patterns.md) for full pattern documentation. Template files are available in [references/templates/](references/templates/) — read the appropriate template and adapt it. Start with `infrastructure.rs` for shared macros (assert_ok!, assert_err!, snapshot types).

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
- [references/templates/](references/templates/) — Rust template files for each proof pattern (infrastructure, conservation, frame-isolation, arithmetic-safety, inductive-delta, safety)
- [references/kani-features.md](references/kani-features.md) — Kani API: contracts, stubbing, concrete playback, partitioned verification
- [references/invariant-design.md](references/invariant-design.md) — Layered invariant design methodology
- [references/anchor-verification.md](references/anchor-verification.md) — Anchor program verification with OtterSec annotations
- [references/agents/kani-analyzer-agent.md](references/agents/kani-analyzer-agent.md) — Explore agent for pre-proof codebase analysis
- [references/agents/kani-linter-agent.md](references/agents/kani-linter-agent.md) — Explore agent for static lint checks (run before verification)
- [references/agents/kani-verifier-agent.md](references/agents/kani-verifier-agent.md) — Explore agent for post-proof verification and diagnosis
