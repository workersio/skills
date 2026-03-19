# Verify-Fix Agent

Use the Agent tool with `subagent_type: "general-purpose"` and the following prompt to autonomously check, repair, and verify a Lean 4 proof file.

## Agent Prompt

````
You are a Lean 4 proof verification and repair agent. Check the file, attempt repairs if needed, and return a structured diagnosis.

## Input

- File path: [INSERT FILE PATH]
- Formal statement path: [INSERT PATH, or "none" if just checking compilation]
- Environment: [INSERT ENVIRONMENT, e.g., "lean-4.28.0"]

## Tasks

### 1. Pre-process

Read the file. If it contains `section` or `namespace` blocks, normalize first:

```bash
axle normalize [FILE] -o [FILE].normalized.lean -f --environment [ENV] --ignore-imports
```

If normalize succeeds (check `lean_messages.errors` is empty in output), use the normalized file for all subsequent steps. Otherwise, proceed with the original file.

### 2. Check Compilation

```bash
axle check [FILE] --environment [ENV] --ignore-imports
```

Parse the JSON output:
- If `okay: true`: skip to Step 5 (verify) if a formal statement was provided, otherwise report success
- If `okay: false`: proceed to Step 3 (repair)

Note any `lean_messages.errors` -- these guide repair strategy selection.

### 3. Repair

Run repair with all available strategies:

```bash
axle repair-proofs [FILE] -o [FILE].repaired.lean -f --environment [ENV] --ignore-imports \
  --repairs remove_extraneous_tactics,apply_terminal_tactics,replace_sorry
```

Check the output:
- Inspect `lean_messages.errors` in the repair output (transformation tools can "succeed" with zero `tool_messages` errors while `lean_messages.errors` reveals compilation failures)
- If the repaired file exists, use it for subsequent steps

### 4. Re-check Compilation

```bash
axle check [FILE].repaired.lean --environment [ENV] --ignore-imports
```

If still failing:
- Try `axle simplify-theorems` to remove no-op tactics that may be interfering
- Report remaining errors in the diagnosis

### 5. Verify Proof (if formal statement provided)

Only run this if a formal statement path was provided:

```bash
axle verify-proof [FORMAL_STATEMENT_PATH] [FILE] --environment [ENV] --ignore-imports
```

Parse the result:
- `okay: true` + empty `failed_declarations`: proof is valid
- `okay: false` + empty `failed_declarations`: compilation error (check `lean_messages.errors`)
- `okay: false` + non-empty `failed_declarations`: verification failure (sorry usage, signature mismatch, disallowed axioms -- details in `tool_messages.errors`)

### 6. Optional Cleanup

If compilation succeeded, optionally run:

```bash
axle simplify-theorems [FILE] -o [FILE].simplified.lean -f --environment [ENV] --ignore-imports
```

This removes no-op tactics and unused haves for cleaner output.

## Output Format

Return exactly this structure:

```
## Verification Result

### Status: [PASS / COMPILE_FAIL / REPAIRED / VERIFY_FAIL]

- PASS: Code compiles and (if formal statement provided) proof is verified
- COMPILE_FAIL: Code does not compile, repair did not fully fix it
- REPAIRED: Code had errors, repair fixed them (re-check passed)
- VERIFY_FAIL: Code compiles but proof verification failed

### Compilation
- Original: [okay / failed]
- After repair: [okay / failed / not attempted]
- Errors: [list of lean_messages.errors, or "none"]

### Repairs Applied
- Strategies used: [remove_extraneous_tactics, apply_terminal_tactics, replace_sorry]
- Tactics removed: [count, or "N/A"]
- Sorry replaced: [count, or "N/A"]
- Terminal tactics applied: [count, or "N/A"]

### Verification (if applicable)
- Result: [valid / failed / not attempted]
- Failed declarations: [list, or "none"]
- Details: [tool_messages.errors summary, or "N/A"]

### Output Files
- Normalized: [path, or "not needed"]
- Repaired: [path, or "not needed"]
- Simplified: [path, or "not attempted"]

### Remaining Issues
- [List any unresolved errors or warnings]
- [Suggestions for manual fixes if automated repair was insufficient]
```
````

## Usage

When the user wants to verify and fix a Lean 4 file, call:

```
Agent(subagent_type="general-purpose", prompt="[paste the agent prompt above, filling in the file path, formal statement path, and environment]")
```

Use the returned diagnosis to:
1. Report the verification status to the user
2. Point them to repaired/simplified output files
3. Guide manual fixes for any remaining issues
4. Re-run with the formal statement if initial check was compilation-only
