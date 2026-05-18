# CLAUDE.md

This repository packages the `wio` Claude Code plugin for testing workflows.

## Canonical Paths

- Plugin: `plugins/wio`
- Skills: `plugins/wio/skills/{scan,test,doctor}/SKILL.md`
- Claude plugin manifest: `plugins/wio/.claude-plugin/plugin.json`
- Claude marketplace: `.claude-plugin/marketplace.json`
- Hooks: `plugins/wio/hooks/hooks.json`
- Canonical references: `plugins/wio/references/`

## Maintenance Rules

- Keep detailed testing content in references, not in `SKILL.md` files.
- Do not remove existing reference context.
- Keep plugin files as the source of truth; avoid repo-local command or agent adapters unless a host cannot load the plugin.
- Keep the reviewer focused on user value and team time saved.
- Any test that does not materially reduce user-visible errors, production risk, support load, debugging time, review time, or release risk should be marked `REDO` or `REMOVE`.
- When adding a reference topic, add both `overview.md` and `tools.md`, then link it from the plugin reference index.
