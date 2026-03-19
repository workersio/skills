# Clean-Analyze Agent

Use the Agent tool with `subagent_type: "general-purpose"` and the following prompt to autonomously normalize, analyze, and clean a Lean 4 file.

## Agent Prompt

````
You are a Lean 4 code analysis and cleanup agent. Normalize the file, understand its structure, clean up redundant tactics, and return a structured summary.

## Input

- File path: [INSERT FILE PATH]
- Environment: [INSERT ENVIRONMENT, e.g., "lean-4.28.0"]

## Tasks

### 1. Normalize

Flatten sections and namespaces for reliable processing:

```bash
axle normalize [FILE] -o [FILE].normalized.lean -f --environment [ENV] --ignore-imports
```

Check `lean_messages.errors` in the output. If normalization fails, proceed with the original file but note the failure. If it succeeds, use the normalized file for all subsequent steps.

**Important:** `normalize` may not update all references inside theorem bodies when flattening namespaces. After normalization, always check compilation before proceeding.

### 2. Extract Theorems

Understand the file's structure:

```bash
axle extract-theorems [FILE] --environment [ENV] --ignore-imports
```

From the output, collect:
- Total number of theorems/lemmas/defs
- Names of all declarations
- Count of `sorry` occurrences (check each theorem's content for the word `sorry`)
- Any `tool_messages` warnings about unsupported commands (these are informational only -- `variable`, `open`, `notation`, etc.)
- Dependencies between theorems (from the `dependencies` field of each extracted theorem)

### 3. Repair Proofs

Remove tactics that appear after the proof is already complete:

```bash
axle repair-proofs [FILE] -o [FILE].repaired.lean -f --environment [ENV] --ignore-imports \
  --repairs remove_extraneous_tactics
```

Check `lean_messages.errors` in the output -- transformation tools can "succeed" with zero `tool_messages` errors while the code has compilation errors. Record the number of tactics removed from the output stats.

### 4. Simplify Theorems

Remove no-op tactics and unused haves:

```bash
axle simplify-theorems [FILE].repaired.lean -o [FILE].cleaned.lean -f --environment [ENV] --ignore-imports
```

Record the number of simplifications from the output stats. Again check `lean_messages.errors`.

### 5. Final Check

Verify the cleaned file still compiles:

```bash
axle check [FILE].cleaned.lean --environment [ENV] --ignore-imports
```

If check fails:
- Fall back to the repaired file (before simplification) and check that
- If that also fails, fall back to the normalized file
- Report which version is the last known-good state

## Output Format

Return exactly this structure:

```
## Analysis Result

### File Summary
- File: [path]
- Declarations: [N] total ([N] theorems, [N] lemmas, [N] defs, [N] instances)
- Sorry count: [N] (in [list of declaration names containing sorry])
- Dependencies: [summary of key dependency relationships]

### Cleanup Applied
- Extraneous tactics removed: [N] (tactics after proof was complete)
- No-op tactics simplified: [N] (tactics that didn't change proof state)
- Unused haves removed: [N]
- Total lines of proof reduced: [estimate if available]

### Compilation Status
- Original: [compiles / errors]
- Normalized: [compiles / errors / not needed]
- After repair: [compiles / errors]
- After simplify: [compiles / errors]
- Final good version: [path to the best compilable output]

### Output Files
- Normalized: [path, or "not needed"]
- Repaired: [path]
- Cleaned (final): [path]

### Observations
- [Notable patterns: heavily sorry'd proofs, complex dependency chains, potential issues]
- [Suggestions for manual improvement]
```
````

## Usage

When the user wants to analyze or clean up a Lean 4 file, call:

```
Agent(subagent_type="general-purpose", prompt="[paste the agent prompt above, filling in the file path and environment]")
```

Use the returned analysis to:
1. Give the user an overview of the file's proof structure
2. Point them to the cleaned output file
3. Highlight sorry'd proofs that need attention
4. Suggest next steps (e.g., fill in sorry'd proofs, run `verify_proof` on completed proofs)
