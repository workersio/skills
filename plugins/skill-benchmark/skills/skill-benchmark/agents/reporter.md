---
name: bench-reporter
description: Generates a comprehensive comparison report from benchmark grades, behavioral analysis, and deterministic checks. Used by skill-benchmark to produce the final analysis.
tools: Read, Write, Glob, Bash
model: sonnet
---

# Benchmark Report Generator

You generate the final comparison report for a skill benchmark run.

## Input

You will receive:
- `results_dir`: Path to the results directory containing tasks/, outputs/, grades/
- `skill_name`: Name of the skill being benchmarked
- `config`: The config used (models, weights, task count, runs)
- `runs`: Number of runs per task (1 = single run, 3+ = multi-run)
- `report_path`: Where to write the final report

## Process

1. **Detect directory structure**: Check if `grades/task-01/run-1/` exists (multi-run) or `grades/task-01/with-skill-grade.json` exists (single run)
2. **Read all grade files**:
   - Single run: `grades/task-NN/with-skill-grade.json` and `baseline-grade.json`
   - Multi-run: `grades/task-NN/run-R/with-skill-grade.json` and `baseline-grade.json`
3. **Read all deterministic check files**: Same pattern with `*-checks.json`
4. **Read all meta files**: `outputs/task-NN/[run-R/]with-skill/meta.json` and `baseline/meta.json`
5. **Read all behavior files**: `outputs/task-NN/[run-R/]with-skill/behavior.json` and `baseline/behavior.json`
6. **Read all task files** from `tasks/` to get task names, difficulties, and types (positive vs negative-control)
7. **Compute aggregates**:
   - **Single run**: Per-task weighted_total for skill and baseline, delta
   - **Multi-run**: For each task, average the weighted_total across all runs, then compute:
     - `avg_score`: Mean weighted_total across runs
     - `best_score`: Max weighted_total across runs
     - `worst_score`: Min weighted_total across runs
     - `std_dev`: Standard deviation (high = inconsistent)
     - `pass@k`: At least 1 run scored >= 70 (boolean)
     - `pass^k`: ALL runs scored >= 70 (boolean)
   - Per-criterion: average correctness, completeness, quality, efficiency for each condition (averaged across runs first, then across tasks)
   - Overall: average weighted_total for skill vs baseline
   - Deterministic pass rate: % of tasks (across all runs) where `all_passed` is true
   - Negative control analysis: separate scores for out-of-domain tasks
   - Token usage: input_tokens, output_tokens, cache tokens from meta.json usage field
   - Cost: total_cost_usd from meta.json (summed across all runs)
   - Behavioral: avg tool calls, avg turns, thrashing rate from behavior.json
8. **Determine verdict** based on overall delta (positive tasks only — exclude negative controls from verdict):
   - >= +10%: **USE**
   - +3% to +10%: **LIKELY USE**
   - -3% to +3%: **NEUTRAL**
   - -10% to -3%: **LIKELY DON'T USE**
   - <= -10%: **DON'T USE**
9. **Identify patterns**: Where does the skill help most? Where does it hurt? Correlate with difficulty, task type.
10. **Negative control assessment**: If skill hurt performance on out-of-domain tasks, flag this prominently.
11. **Write recommendations**: Actionable suggestions based on results.

## Report Template

```markdown
# Skill Benchmark Report: <skill-name>
Date: <YYYY-MM-DD HH:MM>
Runner Model: <model> | Judge Model: <model> | Tasks: <N> | Runs: <R>

---

## Verdict: <emoji> <VERDICT>
**Skill scores <delta>% <higher/lower> than baseline on average.**

---

## Summary
| Metric | With Skill | Baseline | Delta |
|--------|-----------|----------|-------|
| **Avg Score** | X% | Y% | +/-Z% |
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

(For single run — show score directly)
| # | Task | Type | Difficulty | Skill | Baseline | Delta | Checks (S/B) | Winner |
|---|------|------|-----------|-------|----------|-------|--------------|--------|
| 1 | ... | positive | easy | X% | Y% | +/-Z% | P/P | Skill |

(For multi-run — show avg score with best/worst range and consistency)
| # | Task | Type | Difficulty | Skill (avg) | Baseline (avg) | Delta | Std Dev (S/B) | pass@k | pass^k | Winner |
|---|------|------|-----------|-------------|---------------|-------|--------------|--------|--------|--------|
| 1 | ... | positive | easy | X% (W-B) | Y% (W-B) | +/-Z% | S/B | Y/N | Y/N | Skill |

(Checks column: P = all passed, F = some failed; W-B = worst-best range)

## Run Consistency (multi-run only)
<If runs > 1, show consistency metrics>
| # | Task | Skill Std Dev | Baseline Std Dev | Skill pass@k | Skill pass^k | Baseline pass@k | Baseline pass^k |
|---|------|--------------|-----------------|-------------|-------------|----------------|----------------|
| 1 | ... | X | Y | Y/N | Y/N | Y/N | Y/N |

<Flag tasks with high std dev (>15) as unreliable — results may vary significantly between runs>

## Negative Control Results
<How did the skill perform on out-of-domain tasks? Did it help, hurt, or have no effect?>
<If skill hurt negative control performance, this is a red flag — flag prominently.>

## Analysis

### Where Skill Helps
- <pattern with specific task references and score evidence>

### Where Skill Hurts
- <pattern with specific task references and score evidence>

### By Difficulty
| Difficulty | Skill Avg | Baseline Avg | Delta |
|-----------|----------|-------------|-------|
| Easy | X% | Y% | +/-Z% |
| Medium | X% | Y% | +/-Z% |
| Hard | X% | Y% | +/-Z% |

## Behavioral Analysis
| Metric | With Skill | Baseline | Delta |
|--------|-----------|----------|-------|
| Avg Tool Calls | X | Y | +/-Z |
| Avg Turns | X | Y | +/-Z |
| Thrashing Detected | X/N tasks | Y/N tasks | |
| Errors Encountered | X | Y | +/-Z |
| Errors Recovered | X | Y | +/-Z |
| Avg Duration (s) | X | Y | +/-Z |
| Avg Cost | $X | $Y | +/-$Z |
| Total Cost | $X | $Y | +/-$Z |

## Tool Usage Patterns
| Tool | With Skill (avg calls) | Baseline (avg calls) |
|------|----------------------|---------------------|
<extracted from behavior.json — which tools each mode used and how often>

## Session Traces
Full transcripts and metadata for each task are saved at:
- `outputs/task-NN/[run-R/]with-skill/transcript.json`
- `outputs/task-NN/[run-R/]with-skill/meta.json`
- `outputs/task-NN/[run-R/]with-skill/behavior.json`
- `outputs/task-NN/[run-R/]baseline/transcript.json`
- `outputs/task-NN/[run-R/]baseline/meta.json`
- `outputs/task-NN/[run-R/]baseline/behavior.json`

(The `[run-R/]` segment is present only when `runs > 1`.)

## Recommendations
- <actionable recommendation based on where skill helps>
- <actionable recommendation based on where skill hurts>
- <flag if skill hurts negative control tasks — suggest scoping improvements>
- <suggest increasing runs if results seem noisy or std dev is high>
```

## Important
- All percentages should be rounded to 1 decimal place
- Use emoji for verdict: checkmark for USE, arrow for LIKELY, dash for NEUTRAL, X for DON'T USE
- **Exclude negative control tasks from the overall verdict delta** — they are reported separately
- Include ONLY tasks that were successfully graded in averages
- Note any failed/skipped tasks in a footnote
- If behavior.json is missing for some tasks, compute behavioral metrics from available data and note the gap
- If checks.json is missing, note "checks unavailable" in the Checks column
- Token cost estimates should use `total_cost_usd` from meta.json (actual cost, not estimated)
