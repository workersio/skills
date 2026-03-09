# Kani Linter Agent

Use the Agent tool with `subagent_type: "Explore"` and the following prompt to lint a Kani proof harness before running expensive verification.

The linter statically detects 23 common anti-patterns in Kani harnesses (contradictory assumes, missing unwind, vacuity risks, over-constrained inputs, etc.) and reports structured diagnostics. Running it takes seconds vs minutes for `cargo kani`.

## Agent Prompt

````
You are a Kani proof linting agent. Run the kani-lint static analyzer on a proof file and return a structured diagnosis with fixes.

## Input

- Proof file: [INSERT PATH TO THE RUST FILE CONTAINING THE HARNESS]
- Working directory: [INSERT CRATE ROOT PATH]

## Tasks

### 1. Run the Linter

Run `klint` on the proof file using the Bash tool. The linter is distributed as `@workersio/klint`.

**Install** (if not already installed):
```
npm install @workersio/klint
```

**Run with human-readable output:**
```
klint --format human [FILE_PATH]
```

If `klint` is not in PATH (not yet installed), use:
```
npx -p @workersio/klint klint --format human [FILE_PATH]
```

> **Note:** `npx @workersio/klint` does not work due to a known npm quirk with scoped packages. Use `npx -p @workersio/klint klint` instead.

### 2. Parse Output

The linter emits diagnostics at three severity levels:

| Severity | Meaning |
|----------|---------|
| **ERROR** | Will almost certainly cause verification failure. Must fix before running `cargo kani`. |
| **WARNING** | Likely to cause problems (hangs, state explosion, unsoundness). Should fix. |
| **SUGGESTION** | Best-practice improvement (vacuity prevention, assertion coverage). Consider fixing. |

Each diagnostic includes:
- **rule_id**: Machine-readable rule name (e.g., `contradictory_assumes`, `missing_unwind_with_loop`)
- **message**: What the issue is
- **explanation**: Why it matters
- **help**: How to fix it

### 3. Also Run JSON Output for Structured Data

Run a second pass with JSON output (the default format) for precise counts:

```
klint --format json [FILE_PATH]
```

Extract the `summary` object for error/warning/suggestion counts and `harnesses_analyzed` count.

**Exit codes:**
- `1` — errors found
- `0` — no errors (warnings/suggestions only, or clean)

**Error handling:** Missing or unreadable files are reported cleanly without crashing.

### 4. Return Diagnosis

## Output Format

Return exactly this structure:

```
## Lint Result

### Status: [CLEAN / HAS_ERRORS / HAS_WARNINGS]

- CLEAN: No errors or warnings. Suggestions only (or none).
- HAS_ERRORS: At least one error-level diagnostic. Must fix before verification.
- HAS_WARNINGS: No errors but warnings present. Should fix before verification.

### Summary
- Harnesses analyzed: [N]
- Errors: [N]
- Warnings: [N]
- Suggestions: [N]

### Errors (must fix)
For each error diagnostic:
- **[rule_id]** at line [line]: [message]
  - Explanation: [explanation]
  - Fix: [help]

### Warnings (should fix)
For each warning diagnostic:
- **[rule_id]** at line [line]: [message]
  - Explanation: [explanation]
  - Fix: [help]

### Suggestions (consider)
For each suggestion diagnostic:
- **[rule_id]** at line [line]: [message]
  - Explanation: [explanation]
  - Fix: [help]

### Recommended Actions
- [Prioritized list of changes to make before running cargo kani]
```
````

## Lint Rules Reference

The linter checks for these categories of issues:

### Errors (7 rules)
| Rule | What It Catches |
|------|----------------|
| `contradictory_assumes` | Assumes on same variable create empty range (e.g., `x > 10 && x < 5`) |
| `dead_assertion` | Assertion after unconditional return/panic — never reached |
| `assume_no_symbolic` | Constraining a concrete (non-symbolic) variable |
| `harness_has_parameters` | Harness function has parameters (must be zero-arg) |
| `dead_cover` | Cover statement after unconditional exit — never reached |
| `unsafe_transmute` | Uses `transmute` without `-Z valid-value-checks` |

### Warnings (13 rules)
| Rule | What It Catches |
|------|----------------|
| `missing_unwind_with_loop` | Loop present but no `#[kani::unwind(N)]` — will hang |
| `no_symbolic_input` | No `kani::any()` calls — tests single concrete value |
| `over_constrained_to_single_value` | Assumes narrow variable to exactly one value |
| `large_symbolic_vector` | Vector bound > 32 — state space explosion |
| `low_unwind_bound` | Unwind of 0 or 1 — loop body never executes |
| `large_unwind_bound` | Unwind > 100 — excessive verification time |
| `assume_in_contract_harness` | `assume()` in `proof_for_contract` — makes contract unsound |
| `stub_without_verification` | `#[kani::stub]` without `#[kani::stub_verified]` |
| `assume_assert_same_condition` | Asserts the same condition that was assumed — tautology |
| `large_symbolic_arithmetic` | Symbolic u64/i64/u128/i128 — SAT blowup |
| `symbolic_float` | Symbolic f32/f64 — includes NaN/infinity |
| `large_symbolic_array` | Array > 64 elements — state space explosion |

### Suggestions (4 rules)
| Rule | What It Catches |
|------|----------------|
| `missing_cover` | Has assumes but no `kani::cover!()` — vacuity risk |
| `missing_assertion` | Has symbolic inputs but no assertions |
| `trivial_assume` | `kani::assume(true)` — no-op |
| `assume_after_assert` | Assumes after assertions — wrong ordering |

## Package Details

- **Package**: `@workersio/klint@0.1.1`
- **Install**: `npm install @workersio/klint`
- **Run**: `klint [FILE]` (after install), or `npx -p @workersio/klint klint [FILE]` without installing
- **Formats**: `--format human` (readable diagnostics) or `--format json` (structured, default)
- **Exit codes**: `1` on errors, `0` otherwise
- **Platform**: Resolves the correct platform-specific binary automatically

## Usage

After writing a proof harness and before running the verifier, call:

```
Agent(subagent_type="Explore", prompt="[paste the agent prompt above, filling in the file path and working directory]")
```

Use the returned diagnosis to:
1. Fix all errors before attempting verification
2. Address warnings to avoid hangs/OOM/vacuity
3. Consider suggestions for proof quality
4. Only proceed to the verifier agent once the linter is clean (or warnings are acknowledged)
