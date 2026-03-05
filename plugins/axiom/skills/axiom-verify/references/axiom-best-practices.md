# Axiom Best Practices

## Understanding Response Messages

Every response includes two distinct message types:

**Lean Messages** (`lean_messages`): Direct output from the Lean compiler. Errors here indicate problems with the Lean code itself -- type mismatches, tactic failures, unknown identifiers, etc. These are the same messages you'd see running `lean` locally.

**Tool Messages** (`tool_messages`): Axle-specific diagnostics. Errors here indicate the tool itself had issues processing the request -- import mismatches, unsupported constructs, internal timeouts, etc.

**Severity levels:**
- **Errors**: Result may be unusable
- **Warnings**: Suspicious but non-fatal
- **Infos**: Timing/debug output

Check both when debugging failures. A `tool_messages` error about imports is different from a `lean_messages` error about a tactic failure -- they have different fixes.

## Checking Results

**For transformation tools** (normalize, rename, simplify, repair, etc.): Inspect `lean_messages.errors` first. Rule of thumb: if the input compiles, the output should compile.

**For evaluation tools** (verify_proof, check): Non-empty `lean_messages.errors` is expected diagnostic output. Check `result.okay` for compilation success AND `result.failed_declarations` for verification-level issues. `okay: true` means the code compiles, but `failed_declarations` may still list theorems using `sorry`. A fully valid proof has `okay: true` and `failed_declarations: []`.

## Import Handling

All requests assume the Lean code's imports match the environment's default header. When they don't:

- **Default behavior**: Axle raises an error about mismatched imports
- **With `ignore_imports: true`**: Axle auto-replaces the file's imports with the environment defaults

Use `ignore_imports: true` when:
- Working with code snippets that don't have import statements
- Code was written for a different Lean/Mathlib version
- You're getting import-related errors and just want to check the proof logic

## Common Pitfalls

**Mathlib `autoImplicit` is off.** The standard Mathlib environments set `autoImplicit := false`. Always declare type variables explicitly (e.g., `variable {α : Type*}` before using `List α`). Implicit variables that work in standalone Lean will fail in Mathlib environments.

**Mathlib name shadowing.** Theorems named `add_zero`, `add_comm`, `mul_comm`, etc. conflict with existing Mathlib declarations, causing "already declared" errors. This silently blocks all transformation tools (they return unchanged content with zero stats). Use the `rename` endpoint to give theorems unique names, or wrap them in a custom namespace.

**Custom project attributes and constructs.** Files from Lean projects often use custom attributes (e.g., `@[category research open, AMS 11]`) and helper constructs (e.g., `answer(sorry)`) defined in project-specific imports. When `ignore_imports: true` replaces those imports with standard Mathlib, these become unresolvable and cause compilation errors. Strip custom attributes and project-specific constructs before submission. Note: attributes containing the word `open` (e.g., `@[category research open, ...]`) trigger a misleading "Candidate uses banned 'open private' command" error -- this is a false positive from the parser misinterpreting `open`.

**Silent failures from compilation errors.** Any compilation error -- not just name shadowing -- causes transformation tools (`simplify_theorems`, `repair_proofs`, `normalize`, etc.) to silently return unchanged content with all stats at zero and no `tool_messages` errors. The only signal is non-empty `lean_messages.errors`. Always inspect `lean_messages.errors` even when `tool_messages` looks clean and stats are zero.

**`normalize` may miss references in theorem bodies.** When flattening namespaces, `normalize` fully qualifies declaration names (e.g., `p` becomes `Namespace.p`) but may not update all references inside theorem bodies. Always `check` the normalized output and fix any unresolved references manually.

## Scope and Limitations

Axle works best with straightforward Lean code: imports, theorem/lemma declarations, and definitions.

**Well supported:**
- Standard `import` statements
- `theorem`, `lemma`, `def`, `instance` declarations
- Common Mathlib tactics and structures
- Multiple declarations in a single file

**Not guaranteed to work with:**
- Custom declaration types or macros
- `open` commands (may confuse some tools)
- `section` / `namespace` blocks (use `normalize` first)
- Complex mutual recursion
- Exotic Lean 4 metaprogramming

If a file uses `section`, `namespace`, or `open`, run `normalize` first to flatten these constructs before using other tools.

## Recommended Workflows

### Quick verification
1. `check` to see if code compiles
2. If clean: `verify_proof` to confirm it proves the intended statement

### Fixing broken proofs (after version upgrade)
1. `check` to identify which proofs broke
2. `repair_proofs` with all three repair strategies
3. `check` again to see what's still broken
4. Manually fix remaining issues
5. `verify_proof` for final confirmation

### Understanding unfamiliar code
1. `normalize` to clean up formatting
2. `extract_theorems` to see the structure
3. Review individual theorems and their dependencies

### Cleaning up proofs
1. `repair_proofs` with `remove_extraneous_tactics` to remove tactics after proof is already complete
2. `simplify_theorems` to remove no-op tactics and unused haves
3. `check` to confirm cleanup didn't break anything
4. `have2lemma` to extract reusable pieces

**Note:** `simplify_theorems` removes tactics that don't change the proof state (no-ops mid-proof). `repair_proofs` with `remove_extraneous_tactics` removes tactics that appear after the proof goal is already solved. For cleaning up redundant tactics, you typically need both -- repair first, then simplify.

### Testing a conjecture
1. `disprove` to look for counterexamples first
2. If no counterexample found: attempt the proof
3. `check` incrementally as you build the proof
4. `verify_proof` when complete

### Proof scaffolding
1. Write all theorem statements
2. `theorem2sorry` to create a compilable scaffold
3. Fill in proofs one at a time
4. `check` after each proof to verify progress
5. `sorry2lemma` to track remaining obligations

## Performance Tips

- Per-request `timeout_seconds` defaults to 120s; increase for complex proofs
- Use `names` or `indices` parameters to target specific declarations rather than processing the entire file
- For large files, `extract_theorems` first and work with individual theorem blocks
- The `check` endpoint is the fastest way to validate code -- use it for iteration
- Negative indices work (e.g., `-1` for the last declaration)

## Three Interfaces

Axiom offers three equivalent interfaces. Choose based on context:

| Interface | Best for | Install |
|---|---|---|
| **HTTP API** (curl) | Claude Code, scripts, CI/CD | None needed |
| **CLI** (`axle`) | Interactive terminal use | `pip install axiom-axle` |
| **Python client** | Python scripts, notebooks | `pip install axiom-axle` |

In Claude Code, prefer the HTTP API via curl since it requires no installation and gives direct access to the full response JSON.
