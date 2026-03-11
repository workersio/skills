# Configuration Reference

## Variables

- `$RESULTS_DIR`: `<results_dir>/<skill-name>-<timestamp>/` (created in Step 1)
- Default runner model: `sonnet`
- Default judge model: `opus`
- Default task count: `5` (+ 1 negative control)
- Default runs: `1`
- Default max turns: `10`

## Config File Support

Users can create a `config.yml` to customize the benchmark. The file is auto-detected at:
1. `.claude/skills/skill-benchmark/config.yml` (project-level — checked first)
2. `~/.claude/skills/skill-benchmark/config.yml` (user-level — fallback)
3. Passed as argument: `/skill-benchmark path/to/config.yml`

To set up: copy `config.example.yml` to `config.yml` and edit:
```bash
cp .claude/skills/skill-benchmark/config.example.yml .claude/skills/skill-benchmark/config.yml
```

## Expected format

All fields are optional — missing fields use defaults:

```yaml
# Models — use aliases (sonnet, opus, haiku) or full model IDs
runner_model: sonnet        # Model that executes tasks (default: sonnet)
judge_model: opus           # Model that grades outputs (default: opus)

# Skill to benchmark (optional — overrides interactive prompt)
skill: code-commenter       # Skill name or path to SKILL.md

# Task generation
task_count: 5               # Positive tasks to generate (default: 5)
negative_controls: 1        # Negative control tasks (default: 1)
difficulties:               # Distribution across levels
  easy: 2
  medium: 2
  hard: 1

# Runs — run each task multiple times to account for non-determinism
runs: 1                     # Number of runs per task (default: 1, set 3+ for rigor)

# Grading weights (must sum to 100)
weights:
  correctness: 40
  completeness: 25
  quality: 20
  efficiency: 15

# Execution
max_turns: 10               # Max turns per session (default: 10)

# Output
results_dir: ./skill-bench/results   # Where to save results
```

## Parsing config

When reading config, parse it as YAML using python3:
```bash
python3 -c "
import yaml, json
with open('config.yml') as f:
    config = yaml.safe_load(f)
print(json.dumps(config))
"
```
If `yaml` module is not available, the config file also supports simple `key: value` parsing line by line.
