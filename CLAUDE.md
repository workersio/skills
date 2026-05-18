# CLAUDE.md

This repository packages the `wio` testing workflow skill.

## Canonical Paths

- Skill: `skills/wio/SKILL.md`
- References: `skills/wio/reference/`

## Maintenance Rules

- Keep detailed testing content in references, not in `SKILL.md`.
- Do not remove existing reference context.
- Keep `skills/wio` as the source of truth; avoid repo-local command, plugin, cloud, or sub-agent adapters unless a host cannot load the skill.
- Keep the reviewer focused on user value and team time saved.
- Any test that does not materially reduce user-visible errors, production risk, support load, debugging time, review time, or release risk should be marked `REDO` or `REMOVE`.
- When adding a reference topic, add both `overview.md` and `tools.md`, then link it from the WIO reference index.
- Do not create separate `scan`, `test`, or `doctor` skills. They are command modes inside the single `wio` skill.
- Do not duplicate references under plugin, cloud, Claude, command, or sub-agent folders.
