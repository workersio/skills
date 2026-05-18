# CLAUDE.md

This repository packages the `wio` testing workflow skill.

## Canonical Paths

- Skill: `skills/wio/SKILL.md`
- References: `skills/wio/references/`
- Hook script: `skills/wio/scripts/test-review-reminder.py`
- Claude subagents: `.claude/agents/`
- Claude hooks: `.claude/settings.json`
- Codex subagents: `.codex/agents/`
- Codex hooks: `.codex/hooks.json`

## Maintenance Rules

- Keep detailed testing content in references, not in `SKILL.md`.
- Do not remove existing reference context.
- Keep `skills/wio` as the source of truth for WIO workflow and testing references.
- Keep the reviewer focused on user value and team time saved.
- Any test that does not materially reduce user-visible errors, production risk, support load, debugging time, review time, or release risk should be marked `REDO` or `REMOVE`.
- When adding a reference topic, add both `overview.md` and `tools.md`, then link it from the WIO reference index.
- Do not create separate `scan`, `test`, `review`, or `doctor` skills. They are command modes inside the single `wio` skill.
- Do not duplicate references under plugin, cloud, Claude, command, hook, or subagent folders.
- Subagents may inspect, challenge, and review, but the main agent writes tests and applies the final `KEEP`, `REDO`, or `REMOVE` decision.
- Claude Code discovers Markdown subagents from `.claude/agents/`; Codex discovers TOML custom agents from `.codex/agents/`. Keep those files in the official host directories.
