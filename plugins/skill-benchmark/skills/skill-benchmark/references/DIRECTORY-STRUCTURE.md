# Output Directory Structure

## Single run (`runs: 1`, default)

```
$RESULTS_DIR/
├── tasks/
│   ├── task-01-easy.md
│   ├── task-02-medium.md
│   └── task-NN-negative.md
├── sandbox/
│   ├── task-01/
│   │   ├── with-skill/
│   │   └── baseline/
│   └── ...
├── outputs/
│   ├── task-01/
│   │   ├── with-skill/
│   │   │   ├── raw_stream.jsonl
│   │   │   ├── response.json
│   │   │   ├── transcript.json
│   │   │   ├── meta.json
│   │   │   └── behavior.json
│   │   └── baseline/
│   │       └── (same files)
│   └── ...
├── grades/
│   ├── task-01/
│   │   ├── with-skill-checks.json
│   │   ├── with-skill-grade.json
│   │   ├── baseline-checks.json
│   │   └── baseline-grade.json
│   └── ...
└── report.md
```

## Multi-run (`runs: 3`)

```
$RESULTS_DIR/
├── tasks/                              # Same — tasks don't change per run
│   └── task-01-easy.md
├── sandbox/
│   ├── task-01/
│   │   ├── run-1/
│   │   │   ├── with-skill/
│   │   │   └── baseline/
│   │   ├── run-2/
│   │   │   ├── with-skill/
│   │   │   └── baseline/
│   │   └── run-3/
│   │       ├── with-skill/
│   │       └── baseline/
│   └── ...
├── outputs/
│   ├── task-01/
│   │   ├── run-1/
│   │   │   ├── with-skill/
│   │   │   │   ├── raw_stream.jsonl
│   │   │   │   ├── response.json
│   │   │   │   ├── transcript.json
│   │   │   │   ├── meta.json
│   │   │   │   └── behavior.json
│   │   │   └── baseline/
│   │   │       └── (same files)
│   │   ├── run-2/
│   │   │   └── ...
│   │   └── run-3/
│   │       └── ...
│   └── ...
├── grades/
│   ├── task-01/
│   │   ├── run-1/
│   │   │   ├── with-skill-checks.json
│   │   │   ├── with-skill-grade.json
│   │   │   ├── baseline-checks.json
│   │   │   └── baseline-grade.json
│   │   ├── run-2/
│   │   │   └── ...
│   │   └── run-3/
│   │       └── ...
│   └── ...
└── report.md
```
