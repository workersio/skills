# Axiom API Reference

Base URL: `https://axle.axiommath.ai`

All endpoints accept POST requests with JSON bodies. Authenticate with `Authorization: Bearer $AXLE_API_KEY`. Requests without a key work but are limited to 1 concurrent request.

## Discover Available Environments

```bash
curl -s https://axle.axiommath.ai/v1/environments | jq
```

Returns a list of available Lean environments with their toolchain versions, imports, and descriptions.

## Common Response Format

Every endpoint returns these fields:

| Field | Type | Description |
|---|---|---|
| `lean_messages` | `{errors: [], warnings: [], infos: []}` | Lean compiler output |
| `tool_messages` | `{errors: [], warnings: [], infos: []}` | Axle-specific diagnostics |
| `content` | `string` | Processed Lean code (when applicable) |
| `timings` | `dict` | Execution timing in milliseconds |
| `info` | `dict` | Request metadata: `request_id`, `environment`, `total_request_time_ms`, `queue_time_ms`, `execution_time_ms`, `cached_response` |

These fields are only present on specific endpoints (not universal):

| Field | Type | Present on | Description |
|---|---|---|---|
| `okay` | `boolean` | `check`, `verify_proof` | Overall pass/fail verdict |
| `failed_declarations` | `list[string]` | `check`, `verify_proof` | Declaration names with verification-level failures |

**`failed_declarations` semantics:** This field only captures *verification-level* failures -- sorry usage, signature mismatches, disallowed axioms. It does NOT capture compilation errors (tactic failures, syntax errors, name collisions). When code fails to compile, `okay` is `false` but `failed_declarations` is empty; check `lean_messages.errors` for the actual errors.

**Import mismatch errors:** If imports don't match the environment defaults and `ignore_imports` is not set, the API returns `{"user_error": "...", "info": {...}}` instead of the standard response format. Use `ignore_imports: true` to avoid this.

## Common Parameters

These parameters appear across most endpoints:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `environment` | `string` | **required** | Lean version (e.g., `lean-4.28.0`) |
| `content` | `string` | **required** | Lean source code |
| `ignore_imports` | `bool` | `false` | Replace imports with environment defaults |
| `timeout_seconds` | `float` | `120` | Per-request timeout in seconds |

---

## 1. verify_proof

**POST** `/api/v1/verify_proof`

Validates a candidate Lean proof against a formal statement. Checks that `content` provides valid implementations for all declarations in `formal_statement`.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `formal_statement` | `string` | yes | -- | Sorried theorem statement to verify against |
| `content` | `string` | yes | -- | Candidate proof code |
| `environment` | `string` | yes | -- | Lean version |
| `permitted_sorries` | `list[string]` | no | `[]` | Declaration names allowed to use `sorry` |
| `mathlib_linter` | `bool` | no | `false` | Enable Mathlib linting |
| `use_def_eq` | `bool` | no | `true` | Use definitional equality for type comparison |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

### Response

Returns standard fields plus:
- `okay` (boolean): `true` if the proof is valid

### Verification Error Patterns

These are the specific error messages returned in `tool_messages.errors`:

- `Missing required declaration '{name}'` -- Symbol absent from content
- `Kind mismatch for '{name}'` -- Definition type mismatch (theorem vs def)
- `Theorem '{name}' does not match expected signature` -- Type changed
- `Definition '{name}' does not match expected signature` -- Value/type changed
- `Unsafe/partial function '{name}' detected` -- Disallowed function used
- `Axiom '{axiom}' is not in the allowed set` -- Non-standard axiom used
- `Declaration '{name}' uses 'sorry'` -- Unproven theorem (unless in `permitted_sorries`)
- `Candidate uses banned 'open private' command` -- Disallowed syntax

### Example

```bash
curl -s -X POST https://axle.axiommath.ai/api/v1/verify_proof \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "formal_statement": "import Mathlib\ntheorem add_comm (a b : Nat) : a + b = b + a := by sorry",
    "content": "import Mathlib\ntheorem add_comm (a b : Nat) : a + b = b + a := by omega",
    "environment": "lean-4.28.0"
  }'
```

---

## 2. check

**POST** `/api/v1/check`

Evaluates Lean code for compilation errors without formal verification. Quick syntax/type checking. Also captures `#check` and `#eval` output.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `mathlib_linter` | `bool` | no | `false` | Enable Mathlib linting |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

### Response

Returns standard fields plus:
- `okay` (boolean): `true` if code compiles without errors (warnings don't affect this)

---

## 3. extract_theorems

**POST** `/api/v1/extract_theorems`

Splits a Lean file into self-contained theorem units, each with its dependencies resolved.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

### Response

Returns standard fields plus:
- `documents` (dict): Maps theorem names to objects containing:
  - `declaration`: Raw theorem source code
  - `content`: Standalone compilable code block with all dependencies
  - `signature`: The theorem declaration (excluding proof)
  - `type`: Pretty-printed theorem type
  - `type_hash`: Hash for deduplication
  - `is_sorry`: Boolean indicating incomplete proof
  - `index`: Declaration index in the file
  - `line_pos` / `end_line_pos`: Position information
  - `proof_length`: Tactic count estimate
  - `tactic_counts`: Frequency of each tactic used
  - `local_type_dependencies` / `local_value_dependencies`: Dependencies within the file
  - `external_type_dependencies` / `external_value_dependencies`: Dependencies from imports
  - `document_messages` / `theorem_messages`: Per-theorem compilation messages

---

## 4. rename

**POST** `/api/v1/rename`

Renames declarations with automatic reference updates throughout the file.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `declarations` | `dict` | yes | -- | Mapping of old names to new names. **Must use fully-qualified names** including namespace prefixes (e.g., `{"Ns.old": "Ns.new"}`). Returns `user_error` if a name is not found. |
| `environment` | `string` | yes | -- | Lean version |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

### Example

```bash
curl -s -X POST https://axle.axiommath.ai/api/v1/rename \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "theorem my_thm : 1 + 1 = 2 := by norm_num\n#check my_thm",
    "declarations": {"my_thm": "addition_identity"},
    "environment": "lean-4.28.0"
  }'
```

With namespaces, use fully-qualified names:

```bash
curl -s -X POST https://axle.axiommath.ai/api/v1/rename \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "namespace Foo\ntheorem bar : 1 + 1 = 2 := by norm_num\nend Foo",
    "declarations": {"Foo.bar": "Foo.baz"},
    "environment": "lean-4.28.0"
  }'
```

---

## 5. theorem2lemma

**POST** `/api/v1/theorem2lemma`

Converts between `theorem` and `lemma` keywords. By default converts to `lemma`.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `names` | `list[string]` | no | all | Specific declarations to convert |
| `indices` | `list[int]` | no | all | Declarations by index (0-based, supports negative) |
| `target` | `string` | no | `"lemma"` | Target keyword |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

---

## 6. theorem2sorry

**POST** `/api/v1/theorem2sorry`

Replaces theorem proofs with `sorry`. Useful for creating proof scaffolds or isolating specific theorems during development.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `names` | `list[string]` | no | all | Specific declarations to stub |
| `indices` | `list[int]` | no | all | Declarations by index (0-based, supports negative) |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

---

## 7. merge

**POST** `/api/v1/merge`

Consolidates multiple Lean files into one with intelligent deduplication. Orders declarations topologically, resolves conflicts, and prefers error-free/sorry-free proofs.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `documents` | `list[string]` | yes | -- | List of Lean source code strings |
| `environment` | `string` | yes | -- | Lean version |
| `use_def_eq` | `bool` | no | `true` | Use definitional equality for dedup |
| `include_alts_as_comments` | `bool` | no | `false` | Keep alternative defs as comments |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

---

## 8. simplify_theorems

**POST** `/api/v1/simplify_theorems`

Removes unnecessary tactics and cleans up proofs. Makes proofs more readable without changing their validity.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `names` | `list[string]` | no | all | Specific declarations to simplify |
| `indices` | `list[int]` | no | all | Declarations by index (0-based, supports negative) |
| `simplifications` | `list[string]` | no | all | Which simplifications to apply |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

### Available Simplifications

- `remove_unused_tactics` -- Remove tactics that don't affect the proof state
- `remove_unused_haves` -- Remove `have` bindings that are never referenced
- `rename_unused_vars` -- Rename unused variables to `_`

### Response

Returns standard fields plus:
- `simplification_stats` (dict): Count of each simplification type applied

---

## 9. repair_proofs

**POST** `/api/v1/repair_proofs`

Attempts to automatically repair broken proofs. Particularly useful after Lean or Mathlib version upgrades.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `names` | `list[string]` | no | all | Specific declarations to repair |
| `indices` | `list[int]` | no | all | Declarations by index (0-based, supports negative) |
| `repairs` | `list[string]` | no | all | Which repair strategies to apply |
| `terminal_tactics` | `list[string]` | no | `["grind"]` | Tactics to try for closing goals (tried in order) |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

### Available Repairs

- `remove_extraneous_tactics` -- Remove tactics after a proof is already complete
- `apply_terminal_tactics` -- Replace `sorry` by applying terminal tactics to close goals
- `replace_unsafe_tactics` -- Swap deprecated/unsafe tactics for safe alternatives (e.g., `native_decide` to `decide +kernel`)

### Response

Returns standard fields plus:
- `repair_stats` (dict): Count of each repair type applied

### Limitations

- Does not guarantee repaired proofs are semantically correct
- May introduce new errors in complex multi-goal proofs
- Works best on simple, localized issues

---

## 10. have2lemma

**POST** `/api/v1/have2lemma`

Extracts inline `have` statements into standalone top-level lemmas.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `names` | `list[string]` | no | all | Specific declarations to process |
| `indices` | `list[int]` | no | all | Declarations by index (0-based, supports negative) |
| `include_have_body` | `bool` | no | `false` | Include the `have` proof body in the lemma (not always robust) |
| `include_whole_context` | `bool` | no | `true` | Include full proof context as parameters |
| `reconstruct_callsite` | `bool` | no | `false` | Rewrite the original proof to call the new lemma |
| `verbosity` | `float` | no | `0` | Pretty-printer verbosity (0-2; increase for coercions/polymorphic functions) |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

### Response

Returns standard fields plus:
- `lemma_names` (list): Auto-generated lemma names

---

## 11. have2sorry

**POST** `/api/v1/have2sorry`

Replaces `have` statement bodies with `sorry`. Creates proof stubs from inline `have` steps.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `names` | `list[string]` | no | all | Specific declarations to process |
| `indices` | `list[int]` | no | all | Declarations by index (0-based, supports negative) |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

---

## 12. sorry2lemma

**POST** `/api/v1/sorry2lemma`

Extracts `sorry` placeholders and error locations into top-level lemma stubs. Built on Mathlib's `extract_goal` tactic.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `names` | `list[string]` | no | all | Specific declarations to process |
| `indices` | `list[int]` | no | all | Declarations by index (0-based, supports negative) |
| `extract_sorries` | `bool` | no | `true` | Lift sorries into standalone lemmas |
| `extract_errors` | `bool` | no | `true` | Also lift error locations into lemmas |
| `include_whole_context` | `bool` | no | `true` | Include full proof context |
| `reconstruct_callsite` | `bool` | no | `false` | Rewrite original to call the new lemma |
| `verbosity` | `float` | no | `0` | Pretty-printer verbosity (0-2) |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

### Response

Returns standard fields plus:
- `lemma_names` (list): Auto-generated lemma names

---

## 13. disprove

**POST** `/api/v1/disprove`

Attempts to disprove theorems by proving their negation. Uses the Plausible library for counterexample generation.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `names` | `list[string]` | no | all | Specific declarations to disprove |
| `indices` | `list[int]` | no | all | Declarations by index (0-based, supports negative) |
| `terminal_tactics` | `list[string]` | no | `["grind"]` | Tactics to try for proving negation |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

### Response

Returns standard fields plus:
- `results` (dict): Maps each theorem name to a human-readable outcome string
  - **Disproved**: `"Disprove: goal is false! Proof of negation by plausible.\n\nFound a counter-example!\nn := 1\n..."` -- the counterexample details are included in the string
  - **Not disproved**: `"Disprove: failed to prove negation. Remaining goal: ..."` -- the unprovable goal is shown
- `disproved_theorems` (list): Names of successfully refuted theorems. Empty if no counterexample was found.

The `disprove` endpoint first tries Plausible (random testing for counterexamples), then applies `terminal_tactics` (default: `["grind"]`) to try to prove the negation.

---

## 14. normalize

**POST** `/api/v1/normalize`

Standardizes Lean file formatting. Run this before other tools if the file uses `section`/`namespace` blocks or `open ... in` commands.

### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `string` | yes | -- | Lean source code |
| `environment` | `string` | yes | -- | Lean version |
| `normalizations` | `list[string]` | no | `["remove_sections", "remove_duplicates", "split_open_in_commands"]` | Which normalizations to apply |
| `failsafe` | `bool` | no | `true` | Return original content if normalization introduces errors |
| `ignore_imports` | `bool` | no | `false` | Auto-replace imports |
| `timeout_seconds` | `float` | no | `120` | Timeout in seconds |

### Available Normalizations

- `remove_sections` -- Flatten `section`/`namespace` blocks, fully qualify declaration names
- `expand_decl_names` -- Prepend enclosing namespaces to make names unambiguous
- `remove_duplicates` -- Remove duplicate declarations and commands
- `split_open_in_commands` -- Split combined `open ... in` commands into separate statements
- `normalize_module_comments` -- Convert module docs (`/-! -/`) to regular comments
- `normalize_doc_comments` -- Convert doc comments (`/-- -/`) to regular comments

### Response

Returns standard fields plus:
- `normalize_stats` (dict): Count of each normalization type applied
