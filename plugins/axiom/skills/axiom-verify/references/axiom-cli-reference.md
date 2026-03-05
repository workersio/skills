# Axiom CLI Reference

The `axle` CLI provides command-line access to all Axiom tools. Each CLI command mirrors an API endpoint.

## Installation

```bash
pip install axiom-axle
```

Requires Python 3.11 or higher.

### Verify Installation

```bash
axle --version
python -c "from axle import AxleClient; print('OK')"
```

## Global Options

Global options must appear **before** the subcommand name:

| Option | Description |
|---|---|
| `--version` | Display version information |
| `--url URL` | Custom API server (default: `https://axle.axiommath.ai`) |
| `--json` | Force JSON output format (JSON is already the default) |

**Note:** `--environment` is a per-command option, not a global option. Use shell redirection (`> output.json`) to write results to a file.

## Input Methods

All commands accept input as a file path or from stdin via `-`:

```bash
# From file
axle check file.lean --environment lean-4.28.0

# From stdin
cat file.lean | axle check - --environment lean-4.28.0
```

## Parameter Formats

- **Lists** use comma-separated syntax: `--names foo,bar,baz`
- **Dicts** accept key=value pairs or JSON: `--declarations '{"old": "new"}'` or `--declarations old=new`
- **Boolean flags** that default to true use `--no-` prefix to disable: `--no-use-def-eq`, `--no-failsafe`

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Failure (general error) |
| `2` | Invalid arguments (unrecognized flags, missing required args) |
| `3` | Validation failed (with `--strict` flag) |
| `130` | User interrupt (Ctrl+C) |

## Commands

**Note:** CLI commands use hyphens (e.g., `verify-proof`), while the HTTP API uses underscores (`verify_proof`).

### environments

```bash
axle environments
```

Lists all available Lean environments with their toolchain versions and descriptions.

### verify-proof

```bash
axle verify-proof formal.lean proof.lean \
  --environment lean-4.28.0
```

The two positional arguments are the formal statement file and the candidate proof file, in that order.

Optional flags: `--permitted-sorries NAME`, `--mathlib-linter`, `--no-use-def-eq`, `--ignore-imports`, `--timeout-seconds N`, `--strict`

### check

```bash
axle check file.lean --environment lean-4.28.0
```

Optional flags: `--mathlib-linter`, `--ignore-imports`, `--timeout-seconds N`, `--strict`

### extract-theorems

```bash
axle extract-theorems file.lean --environment lean-4.28.0
```

Writes extracted theorems to an `extract_theorems/` directory by default.

Optional flags: `--ignore-imports`, `--timeout-seconds N`

### rename

```bash
axle rename file.lean \
  --declarations '{"old_name": "new_name"}' \
  --environment lean-4.28.0
```

Optional flags: `--ignore-imports`, `--timeout-seconds N`

### theorem2lemma

```bash
axle theorem2lemma file.lean --environment lean-4.28.0
```

Optional flags: `--names NAME`, `--indices N`, `--target lemma|theorem`, `--ignore-imports`

### theorem2sorry

```bash
axle theorem2sorry file.lean --environment lean-4.28.0
```

Optional flags: `--names NAME`, `--indices N`, `--ignore-imports`, `--timeout-seconds N`

### merge

```bash
axle merge file1.lean file2.lean --environment lean-4.28.0
```

Optional flags: `--no-use-def-eq`, `--include-alts-as-comments`, `--ignore-imports`

### simplify-theorems

```bash
axle simplify-theorems file.lean --environment lean-4.28.0
```

Optional flags: `--names NAME`, `--indices N`, `--simplifications remove_unused_tactics,remove_unused_haves,rename_unused_vars`, `--ignore-imports`

### repair-proofs

```bash
axle repair-proofs file.lean --environment lean-4.28.0
```

Optional flags: `--names NAME`, `--indices N`, `--repairs remove_extraneous_tactics,apply_terminal_tactics,replace_unsafe_tactics`, `--terminal-tactics TACTIC`, `--ignore-imports`

### have2lemma

```bash
axle have2lemma file.lean --environment lean-4.28.0
```

Optional flags: `--names NAME`, `--indices N`, `--include-have-body`, `--no-include-whole-context`, `--reconstruct-callsite`, `--verbosity LEVEL`, `--ignore-imports`

### have2sorry

```bash
axle have2sorry file.lean --environment lean-4.28.0
```

Optional flags: `--names NAME`, `--indices N`, `--ignore-imports`

### sorry2lemma

```bash
axle sorry2lemma file.lean --environment lean-4.28.0
```

Optional flags: `--names NAME`, `--indices N`, `--no-extract-sorries`, `--no-extract-errors`, `--no-include-whole-context`, `--reconstruct-callsite`, `--verbosity LEVEL`, `--ignore-imports`

### disprove

```bash
axle disprove file.lean --environment lean-4.28.0
```

Optional flags: `--names NAME`, `--indices N`, `--terminal-tactics TACTIC`, `--ignore-imports`

### normalize

```bash
axle normalize file.lean --environment lean-4.28.0
```

Optional flags: `--normalizations remove_sections,expand_decl_names,remove_duplicates,split_open_in_commands,normalize_module_comments,normalize_doc_comments`, `--no-failsafe`, `--ignore-imports`
