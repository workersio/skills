---
name: skill-benchmark
description: >
  Benchmark any agent skill to measure whether it actually improves performance.
  Use when the user wants to evaluate, test, or compare a skill against baseline,
  or when they mention "benchmark", "eval", "skill performance", or "does this skill help".
  Runs isolated eval sessions with and without the skill, grades outputs via layered grading
  (deterministic checks + LLM-as-judge), analyzes behavioral signals, and generates a
  comparison report with a USE / DON'T USE verdict.
license: MIT
compatibility: Requires Claude Code (or similar agent with Skill tool support), python3
allowed-tools: Bash Read Write Edit Grep Glob Agent AskUserQuestion
metadata:
  author: skill-bench
  version: "1.0"
  claude-code-tools: Read, Write, Edit, Bash, Grep, Glob, Agent, AskUserQuestion
  claude-code-user-invocable: "true"
---

# Skill Benchmark

You are a skill benchmarking system. Your job is to rigorously evaluate whether a Claude Code skill improves performance compared to baseline (no skill).

**Methodology based on industry best practices (Anthropic & OpenAI eval guidance):**
- Layered grading: deterministic checks first, then LLM-as-judge
- Isolated sandbox per session — clean state, no shared artifacts
- Multiple runs to account for non-determinism
- Negative control tasks to detect false positives
- Transcript analysis for behavioral signals

## Execution Flow

Follow these steps exactly:

---

### Step 1: Gather Input

The user can run this skill in two ways:

**Option 1: Custom config** — User creates a `config.yml`:
```
cp .claude/skills/skill-benchmark/config.example.yml .claude/skills/skill-benchmark/config.yml
# edit config.yml
/skill-benchmark
```

**Option 2: Default run** — No config needed:
```
/skill-benchmark
```

#### What to do:

1. **Check for config.yml** — Look for it in order: (1) `config.yml` in the skill directory, (2) `~/.claude/skills/skill-benchmark/config.yml`, (3) path passed as argument. If found, read and use those values. If not found, use built-in defaults:
   - `runner_model: sonnet`
   - `judge_model: opus`
   - `task_count: 5`
   - `negative_controls: 1`
   - `difficulties: {easy: 2, medium: 2, hard: 1}`
   - `runs: 1`
   - `max_turns: 10`
   - `results_dir: ./skill-bench/results`

2. **Which skill to benchmark** — If `skill` is set in config.yml, use that. Otherwise ask the user via `AskUserQuestion`. Search common locations:
   - `.claude/skills/<name>/SKILL.md`
   - `~/.claude/skills/<name>/SKILL.md`
   - Direct file path

3. **Task set** — Ask if they have a custom task set directory, or if you should auto-generate tasks based on the skill's domain.

4. **Confirm settings** — Show the user the final config (loaded or default) and ask if they want to change anything before starting.

5. **Set `$RESULTS_DIR`** — Create the results directory with a skill-name and timestamp:
   ```bash
   RESULTS_DIR="<results_dir>/<skill_name>-$(date +%Y%m%d-%H%M%S)"
   mkdir -p "$RESULTS_DIR"
   ```
   All subsequent paths (`tasks/`, `sandbox/`, `outputs/`, `grades/`, `report.md`) go under `$RESULTS_DIR`. Do NOT put files directly in the base `results_dir` — always nest under the timestamped subdirectory.

---

### Step 2: Read & Analyze Target Skill

Read the target skill's `SKILL.md` file completely. Extract:
- **Domain**: What area does this skill cover? (e.g., code review, testing, deployment)
- **Capabilities**: What specific things does this skill instruct Claude to do?
- **Trigger conditions**: When should this skill be used?
- **Tools used**: What tools does the skill rely on?

Write a brief analysis summary — you'll use this to generate relevant tasks.

---

### Step 3: Generate Benchmark Tasks

If no custom task set was provided, auto-generate tasks. Design tasks following eval best practices:

#### Task Categories (all required):

1. **Positive tasks** — Tasks where the skill SHOULD help (the majority):
   - **Easy** (2 tasks): Straightforward tasks in the skill's domain
   - **Medium** (2 tasks): Tasks requiring deeper application of the skill's guidance
   - **Hard** (1 task): Complex tasks where the skill's specialized knowledge matters most

2. **Negative control** (1 task): A task OUTSIDE the skill's domain where the skill should NOT activate or help. This catches false positives — if the skill hurts performance on unrelated tasks, that's a red flag.

#### Task Format

Write each task to `$RESULTS_DIR/tasks/task-NN-<difficulty>.md`:

```markdown
# Task: <descriptive-name>
difficulty: easy|medium|hard
category: <domain>
type: positive|negative-control

## Prompt
<the exact prompt that will be sent to Claude via `claude -p`>

## Expected Outcome
<clear description of what a correct response looks like>

## Verification Checks
<deterministic checks to run BEFORE LLM grading>
- file_exists: <filename that should be created>
- file_contains: <pattern> in <filename>  (or just <pattern> to search all files)
- syntax_valid: <language — run syntax checker>
- runs_without_error: <command to execute, e.g., "python3 <filename>">

## Grading Rubric
- Correctness: <specific criteria for correctness>
- Completeness: <what must be included for full marks>
- Quality: <quality expectations — best practices, clarity, etc.>

## Tags
<comma-separated tags for grouping>
```

**Task design rules:**
- Prompts must be self-contained — no prior context since they run as fresh `claude -p` sessions
- Include `Verification Checks` with concrete, deterministic things to test (file exists, code runs, output matches)
- Two domain experts should independently reach the same pass/fail verdict — if the task is ambiguous, rewrite it
- Each task must be solvable — the expected outcome must be achievable

---

### Step 4: Run Eval Sessions

For each task, run TWO sessions using `claude -p`. Each session MUST run in its own isolated sandbox directory so they cannot interfere with each other.

#### Multi-Run Support

If `runs > 1` in config, run each task N times. Each run gets its own isolated sandbox and output directory. This accounts for non-determinism in LLM outputs.

- **Directory structure for multi-run** (`runs: 3`):
  ```
  sandbox/task-01/run-1/with-skill/
  sandbox/task-01/run-1/baseline/
  sandbox/task-01/run-2/with-skill/
  sandbox/task-01/run-2/baseline/
  sandbox/task-01/run-3/with-skill/
  sandbox/task-01/run-3/baseline/
  outputs/task-01/run-1/with-skill/
  outputs/task-01/run-1/baseline/
  outputs/task-01/run-2/with-skill/
  outputs/task-01/run-2/baseline/
  ...
  grades/task-01/run-1/with-skill-grade.json
  grades/task-01/run-1/baseline-grade.json
  ...
  ```

- **Directory structure for single run** (`runs: 1`, the default):
  ```
  sandbox/task-01/with-skill/
  sandbox/task-01/baseline/
  outputs/task-01/with-skill/
  outputs/task-01/baseline/
  grades/task-01/with-skill-grade.json
  grades/task-01/baseline-grade.json
  ```

  When `runs: 1`, skip the `run-N/` subdirectory level entirely for simpler output.

- **Aggregation for multi-run**: After grading all runs, compute per-task:
  - **avg_score**: Mean of weighted_total across all runs
  - **best_score**: Max weighted_total across runs
  - **worst_score**: Min weighted_total across runs
  - **pass@k**: At least 1 run scored >= 70 (task considered "passable")
  - **pass^k**: ALL runs scored >= 70 (task consistently passes)
  - **std_dev**: Standard deviation of scores (high = inconsistent behavior)

#### Isolation Setup

Before running ANY sessions, create isolated working directories for EVERY session:

```bash
# For runs: 1 (default)
mkdir -p "$RESULTS_DIR/sandbox/task-NN/with-skill"
mkdir -p "$RESULTS_DIR/sandbox/task-NN/baseline"

# For runs: 3 (multi-run)
mkdir -p "$RESULTS_DIR/sandbox/task-NN/run-1/with-skill"
mkdir -p "$RESULTS_DIR/sandbox/task-NN/run-1/baseline"
mkdir -p "$RESULTS_DIR/sandbox/task-NN/run-2/with-skill"
# ... etc
```

Each `claude -p` call MUST `cd` into its own sandbox directory first. This prevents:
- File collisions (both sessions writing `fibonacci.py` to the same place)
- One session reading files created by the other
- Any shared state between with-skill and baseline runs
- Any shared state between different runs of the same task

#### Nested Session Fix

**CRITICAL:** Claude Code blocks `claude -p` inside an existing session via `CLAUDECODE` and `CLAUDE_CODE_ENTRYPOINT` env vars. You MUST unset these.

#### Session Commands

Every `claude -p` call MUST include `--dangerously-skip-permissions` — without it, headless sessions hang forever waiting for a human to approve tool use.

**Session A — With Skill:**
```bash
# For runs: 1 → sandbox/task-NN/with-skill, outputs/task-NN/with-skill
# For runs: 3 → sandbox/task-NN/run-R/with-skill, outputs/task-NN/run-R/with-skill
cd "$SANDBOX_DIR" && \
env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT \
  claude -p "<task_prompt>" \
  --output-format stream-json \
  --verbose \
  --dangerously-skip-permissions \
  --allowedTools "Skill(<skill_name>),Read,Edit,Bash,Grep,Glob,Write" \
  --append-system-prompt "IMPORTANT: Before starting any work, you MUST first call the Skill tool with skill=\"<skill_name>\" to load the relevant skill instructions. Follow whatever instructions the skill provides throughout your work." \
  --model <runner_model> \
  --max-turns <max_turns> \
  > "$OUTPUT_DIR/raw_stream.jsonl" 2>&1
```

**Why `--append-system-prompt`?** Without it, the skill is merely *available* as a tool — the model must choose to call it. For straightforward tasks, the model often skips the skill entirely and writes code directly. The appended system prompt ensures the skill is always invoked, making the benchmark a fair comparison of "with skill instructions" vs "without".

**Session B — Baseline (no skill):**
```bash
cd "$SANDBOX_DIR" && \
env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT \
  claude -p "<task_prompt>" \
  --output-format stream-json \
  --verbose \
  --dangerously-skip-permissions \
  --allowedTools "Read,Edit,Bash,Grep,Glob,Write" \
  --disallowedTools "Skill" \
  --model <runner_model> \
  --max-turns <max_turns> \
  > "$OUTPUT_DIR/raw_stream.jsonl" 2>&1
```

**Why `--disallowedTools "Skill"`?** The `Skill` tool is a built-in that `--allowedTools` alone does not restrict. Without explicitly disallowing it, the baseline model may still invoke the skill, contaminating the comparison.

Where `$SANDBOX_DIR` and `$OUTPUT_DIR` depend on run count:
- `runs: 1` → `$RESULTS_DIR/sandbox/task-NN/<mode>` and `$RESULTS_DIR/outputs/task-NN/<mode>`
- `runs: N` → `$RESULTS_DIR/sandbox/task-NN/run-R/<mode>` and `$RESULTS_DIR/outputs/task-NN/run-R/<mode>`

**IMPORTANT:**
- `--dangerously-skip-permissions` is REQUIRED — without it, `claude -p` hangs waiting for permission approval with no human to click "Allow".
- Replace `<skill_name>` with the ACTUAL skill name from Step 1 (e.g., `code-commenter`). Do NOT leave `Skill()` empty — that means no skill is loaded and both sessions become identical.
- Always `cd` into the sandbox BEFORE running `claude -p`. This is the isolation mechanism.
- Use absolute paths for the output redirect (`> .../raw_stream.jsonl`) since you're cd'ing.

#### Execution Strategy

- Run Session A and Session B for the SAME task+run in parallel (use background Bash commands)
- Process tasks sequentially to avoid overwhelming the system
- For multi-run: complete all runs of task-01 before starting task-02
- Within a task, you MAY run multiple runs in parallel if system resources allow
- After each session completes, parse `raw_stream.jsonl` to produce THREE files in the output directory:

**response.json** — Extract the last `type: "result"` event from the JSONL stream.

**transcript.json** — All stream events collected into a JSON array.

**meta.json** — Session metadata extracted from response.json. Contains: `session_id`, `model` (from `modelUsage` keys), `skill_name`, `mode`, `stop_reason`, `duration_ms`, `duration_api_ms`, `num_turns`, `total_cost_usd`, and `usage` (input/output/cache tokens). The `scripts/parse_stream.py` script handles this extraction — run it with `--help` for the full field list.

If a session fails or times out, log the error in meta.json and mark it as a failed run (score: 0).

---

### Step 5: Grade Outputs (Layered Grading)

Use a two-layer grading approach: deterministic checks first, then LLM-as-judge. This catches clear failures fast and uses the model for nuanced assessment.

#### Layer 1: Deterministic Checks

For each session output, run the deterministic checks script:

```bash
# For runs: 1 → sandbox/task-NN/<mode>, grades/task-NN/<mode>-checks.json
# For runs: N → sandbox/task-NN/run-R/<mode>, grades/task-NN/run-R/<mode>-checks.json
python3 "scripts/run_checks.py" \
  "$RESULTS_DIR/tasks/task-NN-<difficulty>.md" \
  "$SANDBOX_DIR" \
  "$GRADES_DIR/<mode>-checks.json"
```

This script reads the `## Verification Checks` section from the task file and runs each check (file_exists, syntax_valid, runs_without_error, file_contains) in the sandbox directory.

Save results to `$RESULTS_DIR/grades/task-NN/<mode>-checks.json`:
```json
{
  "file_exists": true,
  "syntax_valid": true,
  "runs_without_error": true,
  "file_contains": {"def add": true, "def subtract": true},
  "all_passed": true
}
```

If deterministic checks fail (file missing, syntax error, runtime crash), the task gets a correctness ceiling of 50 regardless of LLM grading — the code doesn't work.

#### Layer 2: LLM-as-Judge

For each task, launch a **grader subagent** (use the Agent tool with `subagent_type: "general-purpose"` and `model` set to the judge model).

The grader prompt MUST include:
1. The original task prompt
2. The expected outcome from the task file
3. The grading rubric from the task file
4. The actual output to grade (the `result` field from response.json)
5. The deterministic check results from Layer 1
6. Instructions to score each criterion on a 0-100 scale with justification

Also tell the grader to READ the actual files the session created in the sandbox directory (`$RESULTS_DIR/sandbox/task-NN/<mode>/`) to verify correctness — don't just grade the text output, verify the code actually exists and is correct.

Grade EACH output independently (do not show the grader both outputs — this prevents comparison bias).

**Grading criteria and default weights:**
- **Correctness (40%)**: Does the output solve the task correctly? Cap at 50 if deterministic checks failed.
- **Completeness (25%)**: Are all requirements addressed?
- **Quality (20%)**: Code quality, best practices, clarity of explanation
- **Efficiency (15%)**: Was the solution direct and efficient? (Also factor in token usage)

The grader MUST return a structured response. Instruct it to output JSON:
```json
{
  "deterministic_checks_passed": true|false,
  "correctness": { "score": 0-100, "justification": "..." },
  "completeness": { "score": 0-100, "justification": "..." },
  "quality": { "score": 0-100, "justification": "..." },
  "efficiency": { "score": 0-100, "justification": "..." },
  "weighted_total": 0-100,
  "summary": "..."
}
```

Save grades to the corresponding grades directory:
- `runs: 1` → `$RESULTS_DIR/grades/task-NN/with-skill-grade.json` and `baseline-grade.json`
- `runs: N` → `$RESULTS_DIR/grades/task-NN/run-R/with-skill-grade.json` and `baseline-grade.json`

You can run graders for different tasks/runs in parallel using background agents.

---

### Step 6: Analyze Transcripts

Before generating the report, analyze the transcript.json files for behavioral signals. This is critical — scores alone don't tell the full story.

For each session, run the analyze script:

```bash
# For runs: 1 → outputs/task-NN/<mode>/
# For runs: N → outputs/task-NN/run-R/<mode>/
python3 "scripts/analyze_transcript.py" \
  "$OUTPUT_DIR/transcript.json" \
  "$OUTPUT_DIR/behavior.json"
```

This extracts from transcript.json:
- **Tool call counts**: How many times each tool was used (Read, Write, Edit, Bash, etc.)
- **Thrashing detection**: Did the session loop or retry the same action? (same tool called 3+ times consecutively)
- **Error recovery**: Did the session hit errors and recover, or fail silently?

Output (`behavior.json`):
```json
{
  "tool_calls": {"Read": 2, "Write": 1, "Bash": 3, "Edit": 0},
  "total_tool_calls": 6,
  "thrashing_detected": false,
  "errors_encountered": 0,
  "errors_recovered": 0
}
```

---

### Step 7: Generate Comparison Report

After all grading and analysis is complete, generate the final report.

Read all grade files, meta files, and behavior files, then compute:
1. **Per-task scores**: Weighted total for skill vs baseline
2. **Per-task deltas**: skill_score - baseline_score
3. **Aggregate scores**: Average across all tasks
4. **Per-criterion aggregates**: Average correctness, completeness, quality, efficiency for each condition
5. **Deterministic pass rate**: % of tasks where all deterministic checks passed (skill vs baseline)
6. **Negative control results**: How did the skill perform on out-of-domain tasks?
7. **Token usage & cost comparison**: From meta.json `total_cost_usd` and `usage` fields
8. **Behavioral comparison**: Tool usage patterns, thrashing, turn efficiency from behavior.json
9. **Verdict logic**:
   - Delta >= +10%: **USE** — skill significantly helps
   - Delta between +3% and +10%: **LIKELY USE** — skill provides moderate benefit
   - Delta between -3% and +3%: **NEUTRAL** — skill has negligible effect
   - Delta between -10% and -3%: **LIKELY DON'T USE** — skill may hurt
   - Delta <= -10%: **DON'T USE** — skill significantly hurts

Write the report to `$RESULTS_DIR/report.md` using this format:

```markdown
# Skill Benchmark Report: <skill-name>
Date: <YYYY-MM-DD HH:MM>
Runner Model: <model> | Judge Model: <model> | Tasks: <N> | Runs: <R>

## Verdict: <emoji> <VERDICT>
**Skill scores <X>% <higher/lower> than baseline on average.**

## Summary
| Metric | With Skill | Baseline | Delta |
|--------|-----------|----------|-------|
| Avg Score | X% | Y% | +/-Z% |
| Correctness | X% | Y% | +/-Z% |
| Completeness | X% | Y% | +/-Z% |
| Quality | X% | Y% | +/-Z% |
| Efficiency | X% | Y% | +/-Z% |

## Deterministic Check Pass Rate
| Condition | Pass Rate |
|-----------|-----------|
| With Skill | X/N tasks (Y%) |
| Baseline | X/N tasks (Y%) |

## Per-Task Breakdown
| # | Task | Type | Difficulty | Skill | Baseline | Delta | Winner |
|---|------|------|-----------|-------|----------|-------|--------|
| 1 | ... | positive | easy | X% | Y% | +/-Z% | Skill/Baseline |
| N | ... | negative | - | X% | Y% | +/-Z% | ... |

## Negative Control Results
<How did the skill perform on out-of-domain tasks? If it hurt performance, flag this.>

## Where Skill Helps
- <identified patterns where skill outperformed baseline>

## Where Skill Hurts
- <identified patterns where baseline outperformed skill>

## Behavioral Analysis
| Metric | With Skill | Baseline | Delta |
|--------|-----------|----------|-------|
| Avg Tool Calls | X | Y | +/-Z |
| Avg Turns | X | Y | +/-Z |
| Thrashing Detected | X/N | Y/N | |
| Avg Duration (s) | X | Y | +/-Z |
| Avg Cost | $X | $Y | +/-$Z |
| Total Cost | $X | $Y | +/-$Z |

## Recommendations
- <actionable suggestions based on the results>
- <suggestions for improving the skill if it underperformed>
- <flag if skill hurts negative control tasks>
```

Present the report to the user and tell them where the full results are saved.

---

## References

- [Output directory structure](references/DIRECTORY-STRUCTURE.md) — full tree for single-run and multi-run modes
- [Configuration](references/CONFIG.md) — config format, variables, and parsing

## Available scripts

- **`scripts/parse_stream.py`** — Parse `raw_stream.jsonl` → `response.json`, `transcript.json`, `meta.json`
- **`scripts/analyze_transcript.py`** — Analyze `transcript.json` → `behavior.json` (tool counts, thrashing, errors)
- **`scripts/run_checks.py`** — Run deterministic verification checks from task file against sandbox

Run any script with `--help` for full usage details.

## Error Handling

- If a `claude -p` session fails: log the error, score as 0, continue with remaining tasks
- If a grader agent fails: retry once, then score as "UNGRADED" and exclude from averages
- If the target skill file cannot be found: list available skills and ask user to choose
- If fewer than 2 tasks complete successfully: abort and report insufficient data
- If deterministic checks crash (e.g., python3 not available): log warning, skip to LLM grading
