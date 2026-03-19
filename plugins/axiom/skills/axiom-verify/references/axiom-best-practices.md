# Axiom Best Practices

## Understanding Response Messages

Every response includes two distinct message types:

**Lean Messages** (`lean_messages`): Direct output from the Lean compiler. Errors here indicate problems with the Lean code itself -- type mismatches, tactic failures, unknown identifiers, etc. These are the same messages you'd see running `lean` locally.

**Tool Messages** (`tool_messages`): Axle-specific diagnostics. Errors here indicate the tool itself had issues processing the request -- import mismatches, unsupported constructs, internal timeouts, etc. The `tool_messages.infos` field often contains **unsolved goals** when a proof fails -- always check this for debugging context.

**Severity levels:**
- **Errors**: Result may be unusable
- **Warnings**: Suspicious but non-fatal
- **Infos**: Timing/debug output, unsolved goals

Check both when debugging failures. A `tool_messages` error about imports is different from a `lean_messages.errors` error about a tactic failure -- they have different fixes.

## Checking Results by Endpoint

### `check`

Returns `okay` (boolean) and `failed_declarations` (list). The `okay` flag reflects **compilation success only** -- `true` if the code compiles without errors (warnings like `sorry` don't affect it). `failed_declarations` is empty when `okay` is `true`. The `check` endpoint does **not** detect sorry usage or other verification-level issues -- it only checks that code compiles. Use `verify_proof` to validate that proofs are complete.

### `verify_proof`

Returns `okay` (boolean) and `failed_declarations` (list). The `okay` flag reflects **proof validity** -- `true` only if the code compiles **and** passes all verification checks (no sorry, signatures match, no disallowed axioms). Note the distinction:
- **Compilation errors** (tactic failures, syntax errors, name collisions): `okay` is `false`, `failed_declarations` is empty. The errors appear in `lean_messages.errors`.
- **Verification failures** (sorry usage, signature mismatch, disallowed axioms): `okay` is `false`, and the offending names appear in `failed_declarations` with details in `tool_messages.errors`.
- **Fully valid proof**: `okay` is `true` and `failed_declarations` is empty. This is the only state that means the proof is both compilable and complete.

### Transformation tools (`repair_proofs`, `simplify_theorems`, `normalize`, etc.)

These do not return `okay` or `failed_declarations`. Check that `lean_messages.errors` is empty and inspect the `content` field for the transformed result. Transformation tools can "succeed" (return content with zero `tool_messages` errors) while the underlying code has compilation errors visible only in `lean_messages.errors`.

### `disprove`

Check `disproved_theorems` (list of refuted names) and `results` (dict mapping each theorem name to a human-readable outcome string). If a counterexample is found, the name appears in `disproved_theorems` and the `results` entry contains the counterexample. If disprove fails (the theorem may be true), `disproved_theorems` is empty and the `results` entry describes why the negation could not be proven.

### `user_error` responses

Several error conditions return `{"user_error": "...", "info": {...}}` instead of the standard response format. This includes import mismatches (when `ignore_imports` is false), unrecognized declaration names in `rename`, and other request-level validation failures. Always check for a `user_error` field before parsing `lean_messages`/`tool_messages`.

## Import Handling

All requests assume the Lean code's imports match the environment's default header. When they don't:

- **Default behavior**: Axle raises an error about mismatched imports
- **With `ignore_imports: true`**: Axle auto-replaces the file's imports with the environment defaults

**Always use `--ignore-imports` (CLI) or `"ignore_imports": true` (API)** unless you have a specific reason not to (e.g., testing that exact imports are correct). Without this flag, import mismatches return a `user_error` string instead of the standard response format, which breaks JSON parsing and hides the actual verification result. Code snippets, code from different Lean/Mathlib versions, and proof-logic checks all require this flag.

Use `ignore_imports: true` when:
- Working with code snippets that don't have import statements
- Code was written for a different Lean/Mathlib version
- You're getting import-related errors and just want to check the proof logic

## Pre-submission Checklist

Before sending code to any Axle endpoint, verify:

1. **Strip custom attributes**: `sed 's/@\[category [^]]*\]//' file.lean` removes `@[category ...]` blocks. Also strip other project-specific attributes that won't resolve under standard Mathlib imports.
2. **Strip project-specific constructs**: Replace `answer(sorry)` with `True` or remove entirely. Remove any helper macros/notation defined in project-specific imports.
3. **Declare all type variables explicitly**: `variable {α : Type*}` or `(α : Type*)`. The Mathlib environment sets `autoImplicit := false` -- implicit variables like `List α` without declaring `α` will fail.
4. **Rename theorems that shadow Mathlib names**: Names like `add_zero`, `add_comm`, `mul_comm` conflict with existing Mathlib declarations. Use `rename` to give unique names, or prefix with a custom namespace.
5. **Run `normalize` first if the file uses `section`/`namespace`**: Other tools (`extract_theorems`, `theorem2sorry`, etc.) may produce non-compilable output when sections/namespaces are present because extracted names won't be fully qualified.
6. **Always use `--ignore-imports`**: Unless you're specifically testing that exact imports are correct.

## Common Pitfalls

**Custom project attributes and constructs.** Files from Lean projects often define custom attributes (e.g., `@[category research open, AMS 11]`) and helper constructs (e.g., `answer(sorry)`) via project-specific imports. When `ignore_imports: true` replaces those imports with standard Mathlib, these custom constructs become unresolvable and produce compilation errors. **Before submitting**, strip custom attributes and project-specific constructs using sed or similar. Note: `@[category ... open ...]` triggers a misleading "Candidate uses banned 'open private' command" tool error because the parser misinterprets the word `open` inside the attribute as the `open private` command -- this is a false positive that disappears once the attribute is stripped.

**`autoImplicit` is off in Mathlib environments.** Always declare type variables explicitly (e.g., `variable {α : Type*}` or `(α : Type*)`). Implicit variables like `List α` without declaring `α` will fail.

**Mathlib name shadowing.** If your theorem names match existing Mathlib declarations (e.g., `add_zero`, `add_comm`, `mul_comm`), you'll get "already declared" errors and all transformation tools will silently return unchanged content with zero stats. The error appears only in `lean_messages.errors`, not `tool_messages` -- you must inspect `lean_messages` to notice the problem. Use `rename` to give theorems unique names, or prefix with a namespace.

**Silent failures from compilation errors.** Any compilation error -- not just name shadowing -- causes transformation tools (`simplify_theorems`, `repair_proofs`, `normalize`, etc.) to silently return unchanged content with all stats at zero and no `tool_messages` errors. The only signal is non-empty `lean_messages.errors`. Always inspect `lean_messages.errors` even when `tool_messages` looks clean and stats are zero.

**`omega` cannot see through opaque definitions.** The `omega` tactic works on linear arithmetic over `Nat` and `Int`, but it treats user-defined functions as opaque. If you define `def my_double (n : Nat) := n + n` and try to prove `my_double n = 2 * n` with `omega`, it will fail because `omega` doesn't know what `my_double` computes. Use `unfold my_double` (or `simp [my_double]`) before `omega` to expose the definition.

**`simplify_theorems` vs `repair_proofs` for cleanup.** These serve different purposes:
- `simplify_theorems` with `remove_unused_tactics`: removes tactics that are no-ops (don't change the proof state at all)
- `repair_proofs` with `remove_extraneous_tactics`: removes tactics that appear **after** the proof is already complete
- For cleaning up redundant tactics, you usually want `repair_proofs` first, then `simplify_theorems`.

**Sections and namespaces.** `extract_theorems`, `theorem2sorry`, and other transformation tools may produce non-compilable output when sections/namespaces are present because extracted names won't be fully qualified. Always run `normalize` first to flatten these constructs. Note that `normalize` preserves the original indentation from inside flattened blocks -- the output may look oddly indented but still compiles correctly. **Caveat:** `normalize` may not update all references inside theorem bodies when flattening namespaces (e.g., `p k` may not become `Namespace.p k`). Always `check` the normalized output and fix any unresolved references manually.

**`rename` requires fully-qualified names.** The `declarations` parameter must use fully-qualified names including namespace prefixes. For example, if `my_thm` is inside `namespace Foo`, use `{"Foo.my_thm": "Foo.new_name"}`, not `{"my_thm": "new_name"}`. Using an unqualified name returns a `user_error` ("Source name not found").

**Non-theorem commands in `extract_theorems`.** The `extract_theorems` tool warns about any non-theorem command it encounters with `"Unsupported command kind ..."`. This includes `variable`, `open`, `notation`, `set_option`, and other non-declaration commands. These warnings are informational -- the tool still correctly extracts all theorem declarations and includes dependencies (including `variable` bindings, `open` statements, etc.) in each theorem's standalone `content` block.

**Always check both message types.** Transformation tools can "succeed" (return content with zero `tool_messages` errors) while the underlying code has compilation errors visible only in `lean_messages.errors`. Always inspect `lean_messages.errors` even when `tool_messages` is clean. This silent failure mode applies broadly: **any** compilation error (custom attributes, missing imports, syntax issues, name shadowing) causes transformation tools to return unchanged content with zero stats. The only signal is non-empty `lean_messages.errors`.

**The environments endpoint** uses `/v1/environments` (no `/api/` prefix), while all tool endpoints use `/api/v1/{tool_name}`.

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
| **CLI** (`axle`) | Local file operations, Claude Code | `pip install axiom-axle` |
| **HTTP API** (curl) | Dynamic/generated code, scripts, CI/CD | None needed |
| **Python client** | Python scripts, notebooks | `pip install axiom-axle` |

For local file operations (check, verify, normalize, repair, etc.), prefer the `axle` CLI -- it reads files directly from disk, has simpler syntax, and can write output with `-o`. Use the HTTP API when constructing Lean code dynamically or building automation scripts where content exists as strings rather than files.
