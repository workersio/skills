<div align="center">
  <img src="header.jpg" alt="Agent workflows for high-quality software testing, test strategy, and test-suite reliability" width="100%">
</div>

# Better tests, not more tests

Most AI-written tests optimize for coverage. They assert implementation details, mock away the real risk, and pass even when the product breaks.

This repository packages testing workflows that help agents write tests worth keeping: tests with clear behavior, strong oracles, realistic setup, useful failure signals, and an explicit reason to exist.

> Quick start: install the plugin, then use `/wio:scan`, `/wio:test`, or `/wio:doctor`.

## Why this exists

Good testing is a strategy problem before it is a code generation problem. The right test depends on product risk, failure mode, test level, assertion quality, fixture design, feedback loop, and maintenance cost.

These workflows give your coding agent a shared testing vocabulary and a practical reference library for:

- finding gaps in a test strategy
- ranking high-value test candidates
- writing focused regression, unit, integration, contract, and behavior tests
- avoiding low-value coverage padding
- diagnosing flaky, slow, noisy, or low-signal test suites
- choosing when to use mocks, fixtures, property tests, fuzzing, mutation testing, security testing, or resilience testing

## What’s included

### Three workflows

All user-facing workflows are accessed through `/wio`:

| Command | What it does |
| --- | --- |
| `/wio:scan` | Maps product behavior, existing tests, CI, and risk areas to find the highest-value tests to add next. |
| `/wio:test` | Writes one focused test for a selected behavior, bug, code path, or regression risk. |
| `/wio:doctor` | Audits test-suite health: weak assertions, flakes, excessive mocks, broad snapshots, slow feedback, skipped tests, and missing critical behavior coverage. |

### Testing strategy references

The workflows use a shared reference library in `plugins/wio/references/`. Each topic has an `overview.md` for judgment and a `tools.md` for repo signals, commands, and implementation tools.

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

## Installation

Install from the workers.io skills repository:

```bash
npx skills add workersio/skills
```

Then invoke one of the WIO workflows from your agent environment:

```text
/wio:scan
/wio:test
/wio:doctor
```

## Usage examples

### Find test gaps

```text
/wio:scan Find the highest-value tests missing from this checkout flow.
/wio:scan Review the auth module and tell me what is worth testing next.
/wio:scan Look at this PR and identify the best regression tests to add.
```

Use this when you do not yet know what to test. The workflow inspects product context, code paths, current tests, fixtures, and CI before ranking candidates.

### Write a focused test

```text
/wio:test Add a regression test for this billing eligibility bug.
/wio:test Cover the tenant permission check without over-mocking it.
/wio:test Add one focused test for this parser boundary case.
```

Use this when the behavior or bug is known. The workflow chooses the narrowest useful test level, preserves the real failure mechanism, validates with the smallest relevant command, and applies a `KEEP`, `REDO`, or `REMOVE` value gate.

### Diagnose suite quality

```text
/wio:doctor Audit the current test suite.
/wio:doctor Find the biggest reasons CI test failures are hard to trust.
/wio:doctor Review test quality for the API package.
```

Use this when a suite is hard to trust. The workflow reports concrete evidence for weak assertions, flaky timing, brittle snapshots, excessive mocking, slow tests, skipped checks, CI gaps, and missing coverage of critical behavior.

## What “good” means

A generated or recommended test should answer:

- What user, operator, customer, or API consumer failure does this prevent?
- What production, release, support, debugging, or review risk does it reduce?
- Would it fail for the regression that matters?
- Is the assertion specific enough to diagnose the broken behavior?
- Does the setup preserve the important dependency, state, permission, timing, or data risk?
- Does this belong in local development, PR CI, nightly, release, or production monitoring?

If those answers are weak, the test should be redesigned or removed.

## Supported tools

WIO is packaged as a plugin for agent coding environments that support skills/plugins. The current manifests target:

- Codex
- Claude Code

The workflows are intentionally small and portable: the same three entry points, one shared reference library, no duplicate command or agent surfaces.

## Contributing

Keep the public surface area small: `scan`, `test`, and `doctor`.

Detailed testing guidance belongs in `plugins/wio/references/`, not duplicated inside workflow files. When adding a reference topic, add both `overview.md` and `tools.md`, then link it from `plugins/wio/references/index.md`.

The quality bar is simple: do not accept tests for coverage alone. A test should reduce real user risk, production risk, support load, debugging time, review time, or release risk.

## License

[MIT](LICENSE)
