# AGENTS.md

This repository packages the `wio` testing workflow skill for Codex and other coding agents.

## Canonical Paths

- Skill: `skills/wio/SKILL.md`
- References: `skills/wio/reference/`

## Maintenance Rules

- Do not remove existing reference context.
- Keep `skills/wio/SKILL.md` concise and route detailed testing guidance through `skills/wio/reference/index.md`.
- Keep `skills/wio` as the source of truth; avoid repo-local command, plugin, cloud, or sub-agent adapters unless a host cannot load the skill.
- Keep test review strict: low-value tests should be marked `REDO` or `REMOVE`, not accepted for coverage.
- When adding a reference topic, add both `overview.md` and `tools.md`, then link it from the WIO reference index.
- Do not create separate `scan`, `test`, or `doctor` skills. They are command modes inside the single `wio` skill.
- Do not duplicate references under plugin, cloud, Claude, command, or sub-agent folders.
