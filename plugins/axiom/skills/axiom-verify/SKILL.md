---
name: axiom-verify
description: Verify and transform Lean 4 proofs using the Axiom (Axle) API. Use when the user works with Lean 4 code, formal mathematics, Mathlib theorems, or mentions axiom, axle, lean verify, proof verification, formal proof, or theorem checking -- even if they don't explicitly say "axiom" but are clearly working with Lean proofs that need machine verification.
argument-hint: file.lean
---

# Axiom Lean 4 Proof Verification

Axiom provides cloud-based Lean 4 proof verification through the Axle API. It compiles and checks Lean code against a full Mathlib environment without requiring a local Lean installation -- verification results come back in seconds rather than the minutes it takes to build locally.

## Before First Use

Check these once per session before running any Axle commands:

1. **API key**: Run `echo $AXLE_API_KEY`. If empty, the user needs to get a key from `axle.axiommath.ai/app/console` and set it: `export AXLE_API_KEY=<key>`.
2. **CLI installed**: Run `axle --version`. If not found, install with `pip install axiom-axle`.
3. **Lean environment**: Check for a `lean-toolchain` file in the project root to detect the Lean version. If present, use its version (e.g., `leanprover/lean4:v4.28.0` becomes `lean-4.28.0`). If absent, default to `lean-4.28.0`.

## Reference Files

Read these as needed based on the task:

1. [references/axiom-configuration.md](references/axiom-configuration.md) -- Setup, authentication, environment selection. Read this first if the user hasn't configured Axiom yet.
2. [references/axiom-api-reference.md](references/axiom-api-reference.md) -- All 14 API endpoints with parameters and response formats. Read when you need exact parameter names or response fields.
3. [references/axiom-cli-reference.md](references/axiom-cli-reference.md) -- CLI commands and options. Read for exact flags and usage details when working with local files.
4. [references/axiom-best-practices.md](references/axiom-best-practices.md) -- Workflow guidance, result interpretation, pitfalls, and tips. Read when planning a multi-step workflow or hitting unexpected behavior.
5. [references/agents/verify-fix-agent.md](references/agents/verify-fix-agent.md) -- Agent for autonomous check → repair → verify workflow.
6. [references/agents/clean-analyze-agent.md](references/agents/clean-analyze-agent.md) -- Agent for autonomous normalize → extract → clean → check workflow.

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

**When working with local files**, prefer the `axle` CLI -- it reads files directly from disk, has simpler syntax, and can write output to files with `-o`. The CLI reads `AXLE_API_KEY` from the environment automatically. Note: CLI commands use hyphens (e.g., `verify-proof`), while the HTTP API uses underscores (`verify_proof`). All code is sent to `axle.axiommath.ai` for compilation against a full Mathlib environment -- the CLI is not local verification.

**When constructing Lean code dynamically** (generating content in scripts, CI/CD pipelines, or building code strings programmatically), use the HTTP API via curl or the Python client (`pip install axiom-axle`). The API accepts content as JSON strings, which is better suited for generated or in-memory code.

**Check code compiles:**

```bash
axle check file.lean --environment lean-4.28.0 --ignore-imports
```

**Verify a proof:**

```bash
axle verify-proof formal_statement.lean proof.lean \
  --environment lean-4.28.0 --ignore-imports
```

**Repair broken proofs:**

```bash
axle repair-proofs file.lean --environment lean-4.28.0 --ignore-imports \
  --repairs remove_extraneous_tactics,apply_terminal_tactics
```

**Disprove a conjecture:**

```bash
axle disprove file.lean --environment lean-4.28.0 --ignore-imports
```

**Normalize a file (flatten sections/namespaces):**

```bash
axle normalize file.lean -o normalized.lean --environment lean-4.28.0 --ignore-imports
```

**Extract theorems:**

```bash
axle extract-theorems file.lean --environment lean-4.28.0 --ignore-imports
```

**Simplify theorems:**

```bash
axle simplify-theorems file.lean --environment lean-4.28.0 --ignore-imports
```

**Rename declarations:**

```bash
axle rename file.lean --declarations '{"old_name": "new_name"}' \
  --environment lean-4.28.0 --ignore-imports
```

**Stub proofs with sorry:**

```bash
axle theorem2sorry file.lean --environment lean-4.28.0 --ignore-imports
```

**Write transformation output to a file** (works with normalize, repair-proofs, simplify-theorems, rename, etc.):

```bash
axle normalize file.lean -o output.lean -f --environment lean-4.28.0 --ignore-imports
```

**API example** (for dynamically constructed code):

```bash
curl -s -X POST https://axle.axiommath.ai/api/v1/check \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg content "$LEAN_CODE" \
    '{content: $content, environment: "lean-4.28.0", ignore_imports: true}')" \
  | jq '{okay, failed_declarations, lean_errors: .lean_messages.errors, tool_errors: .tool_messages.errors}'
```

For the full CLI command reference, see [references/axiom-cli-reference.md](references/axiom-cli-reference.md). For the full API parameter reference for all 14 endpoints, see [references/axiom-api-reference.md](references/axiom-api-reference.md).

### Step 3: Interpret Results

Every response includes `lean_messages` (Lean compiler output) and `tool_messages` (Axle diagnostics). Always check both -- transformation tools can "succeed" with zero `tool_messages` errors while `lean_messages.errors` reveals the code didn't compile.

Read [references/axiom-best-practices.md](references/axiom-best-practices.md) for detailed result interpretation by endpoint type (`check` vs `verify_proof` vs transformation tools vs `disprove`), the `user_error` response format, and severity levels.

**Critical:** Always use `--ignore-imports` / `"ignore_imports": true` unless testing exact imports. Without it, import mismatches return `user_error` instead of the standard response.

### Common Multi-Step Workflows

**Verify and fix a proof:** Spawn an agent following [references/agents/verify-fix-agent.md](references/agents/verify-fix-agent.md). It autonomously runs check → repair → re-check → verify and returns a structured diagnosis.

**Analyze and clean a file:** Spawn an agent following [references/agents/clean-analyze-agent.md](references/agents/clean-analyze-agent.md). It autonomously runs normalize → extract → repair → simplify → check and returns a structural summary with cleaned output.

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

Read [references/axiom-best-practices.md](references/axiom-best-practices.md) before submitting code. Key traps: custom attributes must be stripped, `autoImplicit` is off in Mathlib, name shadowing causes silent failures, sections/namespaces require `normalize` first, and transformation tools silently return unchanged content on any compilation error.
