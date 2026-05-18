<div align="center">
  <img src="header.jpg" alt="Agent workflows for high-quality software testing, test strategy, and test-suite reliability" width="100%">
</div>

## Better tests, not more tests

Most AI-written tests optimize for coverage. They assert implementation details, mock away the real risk, and pass even when the product breaks.

WIO is one testing workflow skill with four commands: `$wio scan`, `$wio test`, `$wio review`, and `$wio doctor`.

## Structure

WIO uses one skill, command routing inside `SKILL.md`, and one shared references tree. The canonical source lives inside the plugin so plugin installs and direct skill installs do not drift:

```text
plugins/wio/
  .codex-plugin/plugin.json
  .claude-plugin/plugin.json
  skills/
    wio/
      SKILL.md
      scripts/
        test-review-reminder.py
      references/
        index.md
        <topic>/
          overview.md
          tools.md
  agents/
    wio-candidate-scout.md
    wio-strategy-critic.md
    wio-test-reviewer.md
  hooks/
    hooks.json
```

There are no separate `scan`, `test`, `review`, or `doctor` skills, no symlinked skill copies, and no copied reference trees.

## Install Surfaces

WIO supports the official install surfaces for each host:

| Host | Official shared install | Includes |
| --- | --- | --- |
| Codex | Codex plugin via `.agents/plugins/marketplace.json` and `plugins/wio/.codex-plugin/plugin.json` | Skill and plugin hook config. Codex plugin hooks require `plugin_hooks` to be enabled in the current release. |
| Claude Code | Claude plugin via `.claude-plugin/marketplace.json` and `plugins/wio/.claude-plugin/plugin.json` | Skill, Claude subagents, and Claude plugin hook config. |
| Agent skills installer | `npx skills add workersio/skills --skill wio` | Skill only: `SKILL.md`, `scripts/`, and `references/`. The installer discovers `plugins/wio/skills/wio` directly. |
| Codex project config | `.codex/agents/` and `.codex/hooks.json` | Codex custom subagents and project hooks. Codex custom agents are not installed by `skills add`. |
| Claude project config | `.claude/agents/` and `.claude/settings.json` | Project-local Claude agents and hooks for development or non-plugin use. |

The repo-level marketplaces are:

```text
.agents/plugins/marketplace.json      # Codex marketplace
.claude-plugin/marketplace.json       # Claude Code marketplace
```

## Install

Direct skill install:

```bash
npx skills add workersio/skills
```

Claude Code plugin development:

```bash
claude --plugin-dir ./plugins/wio
```

Claude Code marketplace install:

```bash
claude plugin marketplace add workersio/skills
claude plugin install wio@workersio-skills
```

Claude plugin installs include the WIO skill, plugin hooks, and Markdown
subagents from `plugins/wio/agents/`.

Codex marketplace add:

```bash
codex plugin marketplace add workersio/skills
```

For local Codex plugin testing, add this checkout as the marketplace root:

```bash
codex plugin marketplace add .
```

Codex plugin installs include the WIO skill and plugin hook config. Codex
custom agents are a separate native surface: they are loaded from
`.codex/agents/` in a project or `~/.codex/agents/` for the user.

To enable WIO Codex agents globally:

```bash
mkdir -p ~/.codex/agents
cp .codex/agents/wio-*.toml ~/.codex/agents/
```

To enable WIO Codex agents for the current project:

```bash
mkdir -p .codex/agents
cp /path/to/wio-skills/.codex/agents/wio-*.toml .codex/agents/
```

To enable the WIO Codex hook config for the current project:

```bash
cp /path/to/wio-skills/.codex/hooks.json .codex/hooks.json
```

Verify Codex agent files:

```bash
find .codex/agents ~/.codex/agents -name 'wio-*.toml' 2>/dev/null
```

## Commands

| Command | What it does |
| --- | --- |
| `$wio scan [target]` | Maps product behavior, existing tests, CI, and risk areas to find the highest-value tests to add next. |
| `$wio test [target]` | Runs the full loop: discover candidate, pick strategy, write test, validate, review, then keep only if valuable. |
| `$wio review [target]` | Reviews a test for customer value, developer-flow value, signal quality, maintainability, and false confidence. |
| `$wio doctor [target]` | Audits test-suite health: weak assertions, flakes, excessive mocks, broad snapshots, slow feedback, skipped tests, and missing critical behavior coverage. |

## Subagents

WIO includes three focused subagents:

| Subagent | Role |
| --- | --- |
| `wio-candidate-scout` | Read-only discovery of high-value test candidates before implementation. |
| `wio-strategy-critic` | Read-only challenge of the selected strategy before editing tests. |
| `wio-test-reviewer` | Read-only post-write review that returns `KEEP`, `REDO`, or `REMOVE`. |

The main agent still writes the test. Subagents gather evidence, challenge the strategy, and review value. They do not duplicate reference content and they do not own the workflow.

Claude plugin subagents live in `plugins/wio/agents/`, which is the official Claude plugin location. Project-local Claude subagents can also be copied to `.claude/agents/` when a repo is not using the plugin.

Codex project subagents live in `.codex/agents/*.toml`, which is the official Codex custom-agent location.

## Hooks

WIO hooks only remind the active agent to validate test changes and apply the WIO value gate. The executable hook logic lives in `plugins/wio/skills/wio/scripts/test-review-reminder.py`.

Hook config exists in the official locations:

- Claude plugin hook: `plugins/wio/hooks/hooks.json`
- Claude project hook: `.claude/settings.json`
- Codex plugin hook: `plugins/wio/hooks/hooks.json`
- Codex project hook: `.codex/hooks.json`

## References

Detailed testing guidance lives only in `plugins/wio/skills/wio/references/`.

Reference topics include:

| Area | Covers |
| --- | --- |
| Behavior mapping | Turning product behavior, workflows, APIs, and incidents into test candidates. |
| Risk-based testing | Prioritizing tests by customer impact, likelihood, confidence gap, and cost. |
| Test level selection | Choosing unit, component, integration, contract, E2E, monitoring, or specialized checks. |
| Oracles and assertions | Designing assertions that fail for real regressions and explain what broke. |
| Test data and fixtures | Setup, isolation, factories, seeds, cleanup, and state management. |
| Mocking and doubles | Preserving fidelity while keeping tests deterministic and fast. |
| Suite health | Finding flakes, weak signal, slow feedback, skipped tests, and CI blind spots. |
| Advanced strategies | Static analysis, security testing, fuzzing, property-based testing, mutation testing, performance testing, resilience testing, and regression selection. |

## Usage

```text
$wio scan checkout
$wio test billing eligibility regression
$wio review tests/billing_eligibility_test.py
$wio doctor API test suite
```

Use `scan` when you do not yet know what to test. Use `test` when you want the whole candidate-strategy-write-review loop. Use `review` when a test already exists or has just been written. Use `doctor` when an existing suite is hard to trust.

## What Good Means

A generated or recommended test should answer:

- What user, operator, customer, or API consumer failure does this prevent?
- What production, release, support, debugging, or review risk does it reduce?
- Would it fail for the regression that matters?
- Is the assertion specific enough to diagnose the broken behavior?
- Does the setup preserve the important dependency, state, permission, timing, or data risk?
- Does this belong in local development, PR CI, nightly, release, or production monitoring?

If those answers are weak, the test should be redesigned or removed.

## Contributing

Keep the public surface area small: one skill, `wio`, with command modes `scan`, `test`, `review`, and `doctor`.

Detailed testing guidance belongs in `plugins/wio/skills/wio/references/`, not duplicated inside workflow files, cloud folders, subagents, hooks, or extra skill trees. When adding a reference topic, add both `overview.md` and `tools.md`, then link it from `plugins/wio/skills/wio/references/index.md`.

Host-specific files must stay minimal and point back to WIO:

- Claude Code plugins: shared install packages live in `plugins/wio/` with `.claude-plugin/plugin.json`, root-level `skills/`, `agents/`, and `hooks/`.
- Claude Code marketplace: `.claude-plugin/marketplace.json`.
- Codex plugins: shared install packages live in `plugins/wio/` with `.codex-plugin/plugin.json`, root-level `skills/`, and `hooks/`.
- Codex marketplace: `.agents/plugins/marketplace.json`.
- Codex subagents: project custom agents live in `.codex/agents/*.toml` per the official Codex subagents docs.
- Codex hooks: project hooks can live in `.codex/hooks.json` per the official Codex hooks docs.

The quality bar is simple: do not accept tests for coverage alone. A test should reduce real user risk, production risk, support load, debugging time, review time, or release risk.

## License

[MIT](LICENSE)
