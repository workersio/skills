---
name: axiom-verify
description: Verify, check, transform, and repair Lean 4 proofs using the Axiom (Axle) API. Supports proof verification, syntax checking, theorem extraction, code transformation (rename, merge, simplify), proof repair, and disproving. Use this skill whenever the user works with Lean 4 code, formal mathematics, Mathlib theorems, or mentions axiom, axle, lean verify, proof verification, formal proof, or theorem checking -- even if they don't explicitly say "axiom" but are clearly working with Lean proofs that need machine verification.
allowed-tools: Bash(curl *), Bash(axle *), Bash(echo *), Bash(cat *), Bash(jq *), Read
argument-hint: [file.lean]
---

# Axiom Lean 4 Proof Verification

Axiom provides cloud-based Lean 4 proof verification through the Axle API. It compiles and checks Lean code against a full Mathlib environment without requiring a local Lean installation -- verification results come back in seconds rather than the minutes it takes to build locally.

## Reference Files

Read these as needed based on the task:

1. [references/axiom-configuration.md](references/axiom-configuration.md) -- Setup, authentication, environment selection. Read this first if the user hasn't configured Axiom yet.
2. [references/axiom-api-reference.md](references/axiom-api-reference.md) -- All 14 API endpoints with parameters and response formats. Read when you need exact parameter names or response fields.
3. [references/axiom-cli-reference.md](references/axiom-cli-reference.md) -- CLI commands and options. Read if the user prefers the `axle` CLI over curl.
4. [references/axiom-best-practices.md](references/axiom-best-practices.md) -- Workflow guidance, scope limitations, and tips. Read when planning a multi-step workflow or hitting unexpected behavior.

## Workflow

### Step 1: Select the Right Tool

Match the user's intent to the appropriate endpoint:

| User wants to... | Endpoint | Notes |
|---|---|---|
| **Verify a proof is correct** | `verify_proof` | Checks candidate proof against a formal statement |
| **Check if code compiles** | `check` | Quick syntax and type checking |
| **Understand proof structure** | `extract_theorems` | Splits file into self-contained theorem units |
| **Rename declarations** | `rename` | Automatic reference updates throughout |
| **Convert theorem/lemma** | `theorem2lemma` | Switch between `theorem` and `lemma` keywords |
| **Stub out proofs** | `theorem2sorry` | Replace proofs with `sorry` for scaffolding |
| **Combine files** | `merge` | Intelligent deduplication across files |
| **Remove no-op tactics/haves** | `simplify_theorems` | Tactics that don't change proof state, unused haves |
| **Remove post-completion tactics** | `repair_proofs` | Tactics after proof is done, replace sorry, fix unsafe tactics |
| **Extract have statements** | `have2lemma` | Promote inline `have` to standalone lemma |
| **Stub have bodies** | `have2sorry` | Replace `have` bodies with `sorry` |
| **Extract sorry placeholders** | `sorry2lemma` | Turn `sorry` into lemma stubs |
| **Test if statement is false** | `disprove` | Attempts counterexample via Plausible |
| **Standardize formatting** | `normalize` | Clean up sections, namespaces, comments |

When unsure which tool to use:
- Start with `check` to see if the code compiles at all
- Use `extract_theorems` to understand what's in the file
- Use `normalize` first if the file uses `section`/`namespace` blocks (these can cause issues with other tools)

### Step 2: Execute

**From Claude Code**, prefer the HTTP API via curl -- it requires no installation and gives direct access to the full response JSON. All endpoints are POST requests to `https://axle.axiommath.ai/api/v1/{tool_name}`.

**For application integrations** (CI/CD, scripts, notebooks), the curl API or Python client (`pip install axiom-axle`) are the right choices. The CLI (`axle`) is a convenience wrapper around the same cloud API -- it is not local verification. All code is sent to `axle.axiommath.ai` for compilation against a full Mathlib environment.

**Verify a proof:**

```bash
curl -s -X POST https://axle.axiommath.ai/api/v1/verify_proof \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg formal "$(cat formal_statement.lean)" \
    --arg content "$(cat proof.lean)" \
    '{formal_statement: $formal, content: $content, environment: "lean-4.28.0", ignore_imports: true}')" \
  | jq '{okay, failed_declarations, lean_errors: .lean_messages.errors, tool_errors: .tool_messages.errors, tool_infos: .tool_messages.infos}'
```

**Check code compiles:**

```bash
curl -s -X POST https://axle.axiommath.ai/api/v1/check \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg content "$(cat file.lean)" \
    '{content: $content, environment: "lean-4.28.0", ignore_imports: true}')" \
  | jq '{okay, failed_declarations, lean_errors: .lean_messages.errors, tool_errors: .tool_messages.errors}'
```

**Repair broken proofs:**

```bash
curl -s -X POST https://axle.axiommath.ai/api/v1/repair_proofs \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg content "$(cat file.lean)" \
    '{content: $content, environment: "lean-4.28.0", ignore_imports: true, repairs: ["remove_extraneous_tactics", "apply_terminal_tactics"]}')" \
  | jq '{content, repair_stats, lean_errors: .lean_messages.errors, tool_errors: .tool_messages.errors}'
```

**Disprove a conjecture:**

```bash
curl -s -X POST https://axle.axiommath.ai/api/v1/disprove \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg content "$(cat conjecture.lean)" \
    '{content: $content, environment: "lean-4.28.0", ignore_imports: true}')" \
  | jq '{disproved_theorems, results, lean_errors: .lean_messages.errors, tool_errors: .tool_messages.errors}'
```

**Normalize a file (flatten sections/namespaces):**

```bash
curl -s -X POST https://axle.axiommath.ai/api/v1/normalize \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg content "$(cat file.lean)" \
    '{content: $content, environment: "lean-4.28.0", ignore_imports: true}')" \
  | jq '{content, normalize_stats, lean_errors: .lean_messages.errors, tool_errors: .tool_messages.errors}'
```

**Extract theorems:**

```bash
curl -s -X POST https://axle.axiommath.ai/api/v1/extract_theorems \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg content "$(cat file.lean)" \
    '{content: $content, environment: "lean-4.28.0", ignore_imports: true}')" \
  | jq '{theorems: (.documents | keys), lean_errors: .lean_messages.errors, tool_warnings: .tool_messages.warnings}'
```

For the full parameter reference for all 14 endpoints, see [references/axiom-api-reference.md](references/axiom-api-reference.md).

### Step 3: Interpret Results

Every response includes two types of messages -- understanding both is key to helping the user:

- **`lean_messages`**: Direct Lean compiler output. Errors here mean the Lean code itself has problems (type mismatches, tactic failures, unknown identifiers).
- **`tool_messages`**: Axle-specific diagnostics. Errors here mean the tool couldn't process the request (import mismatches, unsupported constructs, timeouts). The `tool_messages.infos` field often contains **unsolved goals** when a proof fails -- always check this for debugging context.

**Severity levels:**
- **Errors**: Result may be unusable
- **Warnings**: Suspicious but non-fatal
- **Infos**: Timing/debug output, unsolved goals

**For `check` and `verify_proof`:** These return `okay` (boolean) and `failed_declarations` (list). The `okay` flag reflects **compilation** success only -- it does not account for verification-level issues like `sorry` usage. Note the distinction:
- **Compilation errors only** (tactic failures, syntax errors, name collisions): `okay` is `false`, but `failed_declarations` is empty. The errors appear in `lean_messages.errors`.
- **Verification-level failures only** (sorry usage, signature mismatch, disallowed axioms): `okay` is `true` (code compiles), but the offending names appear in `failed_declarations` and `tool_messages.errors`. A declaration using `sorry` compiles fine, so `okay` is `true` -- you must check `failed_declarations` to detect incomplete proofs.
- **Both at once** (e.g., some theorems use sorry while other code has attribute/syntax errors): `okay` is `false` (due to compilation errors), `failed_declarations` lists the sorry/verification failures, and `lean_messages.errors` contains the compilation errors. Both must be checked.
- **Fully valid proof**: `okay` is `true` and `failed_declarations` is empty. This is the only state that means the proof is both compilable and complete.

**For transformation tools** (`repair_proofs`, `simplify_theorems`, `normalize`, etc.): These do not return `okay` or `failed_declarations`. Check that `lean_messages.errors` is empty and inspect the `content` field for the transformed result.

**For `disprove`:** Check `disproved_theorems` (list of refuted names) and `results` (dict mapping each theorem name to a human-readable outcome string). If a counterexample is found, the name appears in `disproved_theorems` and the `results` entry contains the counterexample. If disprove fails (the theorem may be true), `disproved_theorems` is empty and the `results` entry describes why the negation could not be proven.

**Import handling:** Include `"ignore_imports": true` in every request unless you have a specific reason not to (e.g., testing that exact imports are correct). Without this flag, import mismatches return a `user_error` string instead of the standard response format, which breaks JSON parsing and hides the actual verification result. Code snippets, code from different Lean/Mathlib versions, and proof-logic checks all require this flag.

**`user_error` responses:** Several error conditions return `{"user_error": "...", "info": {...}}` instead of the standard response format. This includes import mismatches (when `ignore_imports` is false), unrecognized declaration names in `rename`, and other request-level validation failures. Always check for a `user_error` field before parsing `lean_messages`/`tool_messages`.

### Common Multi-Step Workflows

**Verify and fix a proof:**
1. `check` -- see if it compiles
2. If errors: `repair_proofs` -- attempt automatic fix
3. `check` again -- verify the repair worked
4. `verify_proof` -- confirm it proves the intended statement

**Analyze and clean a file:**
1. `normalize` -- standardize formatting first (flatten sections/namespaces)
2. `extract_theorems` -- understand the structure
3. `repair_proofs` with `remove_extraneous_tactics` -- remove tactics after proof is already complete
4. `simplify_theorems` -- remove unused haves and no-op tactics
5. `check` -- verify nothing broke

**Scaffold a proof development:**
1. Write formal statements
2. `theorem2sorry` -- stub out proofs with `sorry` (use `names` parameter to target specific theorems)
3. Fill in proofs incrementally
4. `check` after each proof to verify progress
5. `sorry2lemma` -- track remaining obligations (generates `{name}.sorried` lemma stubs inserted before each sorry'd theorem)
6. `verify_proof` for final verification

**Test a conjecture:**
1. `disprove` -- look for counterexamples first
2. If no counterexample found, attempt the proof
3. `check` incrementally as you build the proof
4. `verify_proof` when complete

### Common Pitfalls

- **Custom project attributes and constructs.** Files from Lean projects often define custom attributes (e.g., `@[category research open, AMS 11]`) and helper constructs (e.g., `answer(sorry)`) via project-specific imports. When `ignore_imports: true` replaces those imports with standard Mathlib, these custom constructs become unresolvable and produce compilation errors. **Before submitting**, strip custom attributes and project-specific constructs using sed or similar: `sed 's/@\[category [^]]*\]//' file.lean` removes `@[category ...]` blocks; replace `answer(sorry)` with `True` or remove it entirely. Note: `@[category ... open ...]` triggers a misleading "Candidate uses banned 'open private' command" tool error because the parser misinterprets the word `open` inside the attribute as the `open private` command -- this is a false positive that disappears once the attribute is stripped.
- **`autoImplicit` is off in Mathlib environments.** Always declare type variables explicitly (e.g., `variable {α : Type*}` or `(α : Type*)`). Implicit variables like `List α` without declaring `α` will fail.
- **Mathlib name shadowing.** If your theorem names match existing Mathlib declarations (e.g., `add_zero`, `add_comm`, `mul_comm`), you'll get "already declared" errors and all transformation tools will silently return unchanged content with zero stats. The error appears only in `lean_messages.errors`, not `tool_messages` -- you must inspect `lean_messages` to notice the problem. Use `rename` to give theorems unique names, or prefix with a namespace.
- **`omega` cannot see through opaque definitions.** The `omega` tactic works on linear arithmetic over `Nat` and `Int`, but it treats user-defined functions as opaque. If you define `def my_double (n : Nat) := n + n` and try to prove `my_double n = 2 * n` with `omega`, it will fail because `omega` doesn't know what `my_double` computes. Use `unfold my_double` (or `simp [my_double]`) before `omega` to expose the definition.
- **`simplify_theorems` vs `repair_proofs` for cleanup.** These serve different purposes:
  - `simplify_theorems` with `remove_unused_tactics`: removes tactics that are no-ops (don't change the proof state at all)
  - `repair_proofs` with `remove_extraneous_tactics`: removes tactics that appear **after** the proof is already complete
  - For cleaning up redundant tactics, you usually want `repair_proofs` first, then `simplify_theorems`.
- **Sections and namespaces.** `extract_theorems`, `theorem2sorry`, and other transformation tools may produce non-compilable output when sections/namespaces are present because extracted names won't be fully qualified. Always run `normalize` first to flatten these constructs. Note that `normalize` preserves the original indentation from inside flattened blocks -- the output may look oddly indented but still compiles correctly. **Caveat:** `normalize` may not update all references inside theorem bodies when flattening namespaces (e.g., `p k` may not become `Namespace.p k`). Always `check` the normalized output and fix any unresolved references manually.
- **`rename` requires fully-qualified names.** The `declarations` parameter must use fully-qualified names including namespace prefixes. For example, if `my_thm` is inside `namespace Foo`, use `{"Foo.my_thm": "Foo.new_name"}`, not `{"my_thm": "new_name"}`. Using an unqualified name returns a `user_error` ("Source name not found").
- **Non-theorem commands in `extract_theorems`.** The `extract_theorems` tool warns about any non-theorem command it encounters with `"Unsupported command kind ..."`. This includes `variable`, `open`, `notation`, `set_option`, and other non-declaration commands. These warnings are informational -- the tool still correctly extracts all theorem declarations and includes dependencies (including `variable` bindings, `open` statements, etc.) in each theorem's standalone `content` block.
- **Always check both message types.** Transformation tools can "succeed" (return content with zero `tool_messages` errors) while the underlying code has compilation errors visible only in `lean_messages.errors`. Always inspect `lean_messages.errors` even when `tool_messages` is clean. This silent failure mode applies broadly: **any** compilation error (custom attributes, missing imports, syntax issues, name shadowing) causes transformation tools to return unchanged content with zero stats. The only signal is non-empty `lean_messages.errors`.
- **The environments endpoint** uses `/v1/environments` (no `/api/` prefix), while all tool endpoints use `/api/v1/{tool_name}`.
