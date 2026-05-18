<div align="center">
  <img src="header.jpg" alt="Agent workflows for high-quality software testing, test strategy, and test-suite reliability" width="100%">
</div>

# Better tests, not more tests

Most AI-written tests optimize for coverage. They assert implementation details, mock away the real risk, and pass even when the product breaks.

WIO is one testing workflow skill with three commands: `$wio scan`, `$wio test`, and `$wio doctor`.

## Structure

WIO follows the same basic shape as Impeccable: one skill, command routing inside `SKILL.md`, and one shared reference tree.

```text
skills/wio/
  SKILL.md
  reference/
    index.md
    <topic>/
      overview.md
      tools.md
```

There are no separate `scan`, `test`, or `doctor` skills. There is no plugin wrapper. There are no copied reference trees.

## Commands

| Command | What it does |
| --- | --- |
| `$wio scan [target]` | Maps product behavior, existing tests, CI, and risk areas to find the highest-value tests to add next. |
| `$wio test [target]` | Writes one focused test for a selected behavior, bug, code path, or regression risk. |
| `$wio doctor [target]` | Audits test-suite health: weak assertions, flakes, excessive mocks, broad snapshots, slow feedback, skipped tests, and missing critical behavior coverage. |

## References

Detailed testing guidance lives only in `skills/wio/reference/`.

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
$wio doctor API test suite
```

Use `scan` when you do not yet know what to test. Use `test` when the behavior or bug is known. Use `doctor` when an existing suite is hard to trust.

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

Keep the public surface area small: one skill, `wio`, with command modes `scan`, `test`, and `doctor`.

Detailed testing guidance belongs in `skills/wio/reference/`, not duplicated inside workflow files, plugin files, command adapters, cloud folders, sub-agents, or extra skill trees. When adding a reference topic, add both `overview.md` and `tools.md`, then link it from `skills/wio/reference/index.md`.

The quality bar is simple: do not accept tests for coverage alone. A test should reduce real user risk, production risk, support load, debugging time, review time, or release risk.

## License

[MIT](LICENSE)
