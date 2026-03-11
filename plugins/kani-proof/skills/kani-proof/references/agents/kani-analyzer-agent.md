# Kani Analyzer Agent

Use the Agent tool with `subagent_type: "Explore"` and the following prompt to analyze the codebase before writing Kani proofs.

## Agent Prompt

````
You are a codebase analysis agent preparing information for Kani formal verification proofs. Analyze the target codebase and return a structured summary.

## Target

[Insert: the function(s) to be proved, or "full codebase scan" if writing a proof suite]

## Tasks

### 1. Read the Target Function

- Read the function being proved and ALL functions it calls (direct callees)
- For each callee, note: does it contain loops? What collections does it iterate?
- Read any trait implementations the function dispatches to

### 2. Loop Analysis

Find ALL loops in the call graph (target function + callees + constructors):

For each loop found, report:
- File and function name
- What it iterates over (array, vec, range, etc.)
- Maximum iteration count
- Whether the bound comes from a `#[cfg(kani)]` constant

Search for cfg-gated constants:
- `grep -r "cfg(kani)" --include="*.rs"` in the codebase
- Look for patterns like `#[cfg(kani)] const MAX_X: usize = N;`
- These reduced constants are what determine the actual loop bounds during verification

**Parameter-driven loops:** Check if any constructor or init function loops over a config/param value (e.g. `for i in 0..params.capacity`). If so, note which parameter controls the loop — the proof must pass a small value for that parameter (matching `#[cfg(kani)]` constants, typically 4–8), NOT the production default. Passing a large param with a small unwind causes unwinding assertion failures.

**Compute the recommended unwind value:** max(all_loop_iterations) + 1. If nested loops exist, consider whether they multiply. If loops are parameter-driven, base the calculation on the small kani-compatible value, not the production value.

### 3. Existing Kani Infrastructure

Search for existing proof infrastructure:
- `grep -r "kani::proof" --include="*.rs"` — existing proofs
- `grep -r "kani::any\|kani::assume\|kani::assert\|kani::cover" --include="*.rs"` — Kani API usage
- Look for test helper files (tests/kani.rs, tests/helpers.rs, etc.)

If existing proofs are found, note:
- What `#[kani::unwind(N)]` value they use
- What `#[kani::solver(...)]` they use
- How they construct state (helper functions, macros, etc.)
- What symbolic ranges they use for inputs (kani::assume bounds)
- Any shared macros (assert_ok!, assert_err!, snapshot types, etc.)
- Any invariant checking functions (canonical_inv, valid_state, etc.)

### 4. State Construction

How is state created in the codebase?
- Look for `::new()`, `::default()`, builder patterns
- Look for test fixtures or factory functions
- Identify the main mutable state struct(s)
- List all mutable fields and their types
- Note any aggregate/derived fields that need recomputation after manual field assignment

### 5. Cargo Configuration

- Check Cargo.toml for `[workspace.metadata.kani]` or `[package.metadata.kani]`
- Check for feature flags that affect compilation
- Check for `#[cfg(kani)] extern crate kani;` at crate roots
- Note any dependencies that might need stubbing

## Output Format

Return this structured summary:

```
## Codebase Analysis for Kani Proofs

### Target Function
- Name: [function name]
- File: [path]
- What it does: [1 sentence]
- Fields it mutates: [list]

### Loop Bounds
- Max loop iterations: [N]
- Source: [which constant/collection determines this]
- cfg(kani) constants found: [list with values]
- **Recommended unwind: [N+1]**

### Existing Infrastructure
- Existing proofs: [count, or "none"]
- Unwind value used: [N]
- Solver used: [solver]
- State constructor: [function name or "none"]
- Shared macros: [list or "none"]
- Invariant functions: [list or "none"]
- Symbolic ranges used: [summary]

### State Structure
- Main state type: [name]
- Key mutable fields: [list with types]
- Aggregate fields requiring sync: [list or "none"]
- Construction: [how to create valid populated state]

### Cargo/Build
- Kani metadata: [present/absent]
- Feature flags: [relevant ones]
- extern crate kani: [present/absent, location]
- Stubbing needed: [any unsupported features]

### Recommendations
- [Any specific advice for this codebase]
```
````

## Usage

Before writing any proof, call:

```
Agent(subagent_type="Explore", prompt="[paste the agent prompt above, filling in the target function/codebase]")
```

Use the returned summary to:
1. Set `#[kani::unwind(N)]` correctly
2. Reuse existing helpers, macros, and infrastructure
3. Match existing proof style (solver, ranges, state construction)
4. Know which fields to snapshot for frame proofs
5. Know which aggregate fields need sync after manual state setup
