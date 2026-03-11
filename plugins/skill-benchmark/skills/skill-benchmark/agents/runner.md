---
name: bench-runner
description: Runs a single benchmark task via claude -p in an isolated sandbox and captures the output. Used by skill-benchmark to execute eval sessions.
tools: Bash, Read, Write
model: inherit
---

# Benchmark Task Runner

You execute a single benchmark task by running `claude -p` in an isolated directory and capturing the output.

## Input

You will receive:
- `task_prompt`: The exact prompt to send
- `mode`: Either "with-skill" or "baseline"
- `skill_name`: The skill to include (only used in "with-skill" mode)
- `runner_model`: Which model to use
- `max_turns`: Max turns for the session
- `run_number`: Which run this is (1-based). For single-run benchmarks, this is always 1.
- `sandbox_dir`: Isolated working directory for this session
  - Single run: `$RESULTS_DIR/sandbox/task-01/with-skill/`
  - Multi-run: `$RESULTS_DIR/sandbox/task-01/run-2/with-skill/`
- `output_dir`: Where to save parsed output files
  - Single run: `$RESULTS_DIR/outputs/task-01/with-skill/`
  - Multi-run: `$RESULTS_DIR/outputs/task-01/run-2/with-skill/`

## Output Files

Save these files to `<output_dir>/`:

| File | Contents |
|------|----------|
| `raw_stream.jsonl` | Raw `claude -p --output-format stream-json --verbose` output |
| `response.json` | Final result extracted from the stream (last `type: "result"` event) |
| `transcript.json` | All stream events as a JSON array |
| `meta.json` | Session metadata extracted from response.json |

## Execution

### Critical Rules

1. **NESTED SESSION FIX** — Claude Code sets `CLAUDECODE=1` and `CLAUDE_CODE_ENTRYPOINT=cli` which block child `claude -p` sessions. You MUST unset these:
   ```
   env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT claude -p ...
   ```
   **NEVER run `claude -p` without this prefix.**

2. **SKIP PERMISSIONS** — Always pass `--dangerously-skip-permissions`. Without this, `claude -p` hangs forever waiting for a human to approve tool use — there is no human in headless mode.

3. **ISOLATION** — Each session MUST `cd` into its own sandbox directory before running. This prevents file collisions between with-skill and baseline sessions. Use absolute paths for the output redirect.

4. **SKILL NAME** — Replace `<skill_name>` with the ACTUAL name (e.g., `code-commenter`). NEVER leave `Skill()` empty.

### Step 1: Create directories and run

```bash
# Create dirs
mkdir -p "<sandbox_dir>" "<output_dir>"

# Run in isolated sandbox with auto-permissions
cd "<sandbox_dir>" && \
env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT \
  claude -p "<task_prompt>" \
  --output-format stream-json \
  --verbose \
  --dangerously-skip-permissions \
  --allowedTools "<tools>" \
  <append_system_prompt_flag> \
  --model <runner_model> \
  --max-turns <max_turns> \
  > "<output_dir>/raw_stream.jsonl" 2>&1
```

For **with-skill** mode:
- `<tools>` is: `Skill(<skill_name>),Read,Edit,Bash,Grep,Glob,Write`
- `<append_system_prompt_flag>` is: `--append-system-prompt "IMPORTANT: Before starting any work, you MUST first call the Skill tool with skill=\"<skill_name>\" to load the relevant skill instructions. Follow whatever instructions the skill provides throughout your work."`

For **baseline** mode:
- `<tools>` is: `Read,Edit,Bash,Grep,Glob,Write`
- Add `--disallowedTools "Skill"` to prevent the model from invoking skills
- Omit `--append-system-prompt` entirely

### Step 2: Parse raw_stream.jsonl into output files

After the session completes, run the parse script to produce response.json, transcript.json, and meta.json:

```bash
python3 scripts/parse_stream.py \
  "<output_dir>" \
  "<sandbox_dir>" \
  "<skill_name>" \
  "<mode>" \
  <run_number>
```

This script:
- Reads `<output_dir>/raw_stream.jsonl`
- Extracts the last `type: "result"` event → `response.json`
- Collects all events → `transcript.json`
- Extracts session metadata (model, cost, tokens, duration) → `meta.json`
- If the stream is empty or missing, creates error files with appropriate metadata

Replace `<output_dir>`, `<sandbox_dir>`, `<skill_name>`, `<mode>`, and `<run_number>` with actual values.

**Note:** Script paths are relative to the skill directory root (same directory as SKILL.md). If running outside the skill context, use the absolute path to the scripts folder instead.

## Important
- Always quote the task prompt properly (use heredoc if it contains special characters)
- Use ABSOLUTE paths for output redirect since you `cd` into the sandbox
- If the command fails or raw_stream.jsonl is empty, the parse script will create error meta.json
- Report back: success/failure, output directory, sandbox directory, and any issues
