# Contributing

`@workersio/skills` is intentionally one skill with five command modes: `scan`,
`test`, `workload`, `review`, and `doctor`. Please keep contributions aligned
with that shape.

## What Belongs Here

- Improvements to the testing workflow.
- Better examples, command wording, and agent instructions.
- New testing reference topics under `plugins/wio/skills/wio/references/`.
- Fixes to Codex or Claude Code plugin packaging.
- Hook or subagent changes that reinforce the existing workflow.

## What Does Not Belong Here

- Separate `scan`, `test`, `workload`, `review`, or `doctor` skills.
- Duplicated reference material under plugin, cloud, hook, or subagent folders.
- Tests accepted only because they increase coverage.
- Broad rewrites that make host-specific files the source of truth.

## Reference Topics

When adding a reference topic:

1. Add `overview.md`.
2. Add `tools.md`.
3. Link the topic from `plugins/wio/skills/wio/references/index.md`.
4. Keep `plugins/wio/skills/wio/SKILL.md` concise and route details through the reference index.

## Review Standard

Every generated or recommended test should reduce real risk: user impact,
production risk, release risk, support load, debugging time, review time, or
suite maintenance cost. Low-value tests should be marked `REDO` or `REMOVE`.

## Release Checklist

Before tagging a release:

1. Verify `plugins/wio/.codex-plugin/plugin.json`.
2. Verify `plugins/wio/.claude-plugin/plugin.json`.
3. Verify `.agents/plugins/marketplace.json`.
4. Verify `.claude-plugin/marketplace.json`.
5. Check that README install commands still match the package layout.
6. Update `CHANGELOG.md`.
