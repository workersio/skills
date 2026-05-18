# AGENTS.md

This repository packages the `wio` testing workflow skill and plugin for Codex, Claude Code, and other coding agents.

## Canonical Paths

- Plugin: `plugins/wio`
- Skill source: `plugins/wio/skills/wio/SKILL.md`
- References: `plugins/wio/skills/wio/references/`
- Hook script: `plugins/wio/skills/wio/scripts/test-review-reminder.py`
- Claude plugin manifest: `plugins/wio/.claude-plugin/plugin.json`
- Claude marketplace: `.claude-plugin/marketplace.json`
- Claude plugin subagents: `plugins/wio/agents/`
- Claude project subagents: `.claude/agents/` when copied for project-local use
- Claude hooks: `.claude/settings.json`
- Codex plugin manifest: `plugins/wio/.codex-plugin/plugin.json`
- Codex marketplace: `.agents/plugins/marketplace.json`
- Codex subagents: `.codex/agents/`
- Codex hooks: `.codex/hooks.json`

## Maintenance Rules

- Do not remove existing reference context.
- Keep `plugins/wio/skills/wio/SKILL.md` concise and route detailed testing guidance through `plugins/wio/skills/wio/references/index.md`.
- Keep `plugins/wio/skills/wio` as the source of truth for WIO workflow and testing references.
- Keep test review strict: low-value tests should be marked `REDO` or `REMOVE`, not accepted for coverage.
- When adding a reference topic, add both `overview.md` and `tools.md`, then link it from the WIO reference index.
- Do not create separate `scan`, `test`, `review`, or `doctor` skills. They are command modes inside the single `wio` skill.
- Do not duplicate references under plugin, cloud, Claude, command, hook, or subagent folders.
- Subagents may inspect, challenge, and review, but the main agent writes tests and applies the final `KEEP`, `REDO`, or `REMOVE` decision.
- Claude Code plugins discover Markdown subagents from the plugin root `agents/` directory; project-local Claude Code discovers them from `.claude/agents/`.
- Codex discovers TOML custom agents from `.codex/agents/`. Codex plugins do not replace that project custom-agent location.
- Keep marketplace entries in the official host locations: `.agents/plugins/marketplace.json` for Codex and `.claude-plugin/marketplace.json` for Claude Code.
