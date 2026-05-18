# AGENTS.md

This repository packages the `wio` testing workflow plugin for Codex and other coding agents.

## Canonical Paths

- Plugin: `plugins/wio`
- Skills: `plugins/wio/skills/{scan,test,doctor}/SKILL.md`
- Codex plugin manifest: `plugins/wio/.codex-plugin/plugin.json`
- Codex marketplace: `.agents/plugins/marketplace.json`
- Canonical references: `plugins/wio/references/`

## Maintenance Rules

- Do not remove existing reference context.
- Keep `SKILL.md` files concise and route detailed testing guidance through `plugins/wio/references/index.md`.
- Keep plugin files as the source of truth; avoid repo-local command or agent adapters unless a host cannot load the plugin.
- Keep test review strict: low-value tests should be marked `REDO` or `REMOVE`, not accepted for coverage.
- When adding a reference topic, add both `overview.md` and `tools.md`, then link it from the plugin reference index.
