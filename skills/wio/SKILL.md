---
name: wio
description: Testing workflow skill for scan, test, and doctor commands. Use when asked to find high-value tests, write a focused test, review test value, diagnose suite health, flaky tests, low-signal tests, or testing strategy.
argument-hint: "[scan|test|doctor] [target]"
user-invocable: true
metadata:
  author: workers.io
  version: "0.1.0"
---

# WIO

WIO is one testing workflow skill with three command modes:

- `scan`: find the highest-value test candidates for a codebase, change, or scope.
- `test`: write one focused high-value test for a selected behavior, code path, or regression risk.
- `doctor`: diagnose test-suite health problems in a codebase or scope.

Commands are accessed through `$wio`:

| Command | What it does | Start with |
| --- | --- | --- |
| `$wio scan [target]` | Find the highest-value test candidates for a codebase, change, or scope. | [Behavior To Test Map](reference/behavior-to-test-map/overview.md), [Risk-Based Testing](reference/risk-based-testing/overview.md), [User Behavior Testing](reference/user-behavior-testing/overview.md), [Test Level Selection](reference/test-level-selection/overview.md) |
| `$wio test [target]` | Write one focused high-value test for a selected behavior, code path, or regression risk. | [Test Level Selection](reference/test-level-selection/overview.md), [Test Oracles And Assertions](reference/test-oracles-and-assertions/overview.md), [Test Data And Fixtures](reference/test-data-and-fixtures/overview.md), [Mocking And Test Doubles](reference/mocking-and-test-doubles/overview.md), [Test Feedback Loops](reference/test-feedback-loops/overview.md) |
| `$wio doctor [target]` | Diagnose test-suite health problems in a codebase or scope. | [Test Suite Health Diagnostics](reference/test-suite-health-diagnostics/overview.md), [Flaky Test Detection and Management](reference/flaky-test-detection-and-management/overview.md), [Test Feedback Loops](reference/test-feedback-loops/overview.md), [Test Automation Pyramid](reference/test-automation-pyramid/overview.md) |

Use [reference/index.md](reference/index.md) as the reference map. Load only the reference files needed for the current decision.

## Command Selection

Use `scan` when the user asks what to test next, where coverage would matter, how to prioritize testing work, or which tests would reduce user, production, support, or team risk.

Use `test` when the user asks to add a test, improve a specific test, cover a bug, or validate a change with a meaningful automated test.

Use `doctor` when the user asks to audit tests, review suite quality, find flaky or low-value tests, inspect CI test health, or explain why a test suite is slow, noisy, or low-signal.

If the user explicitly names a WIO command, follow that mode. If the command is omitted, infer the mode from the request. If no command or target is provided, show the command table and ask what they want to do. If multiple modes apply, start with `scan` before `test`, and use `doctor` only for existing suite health.

## Shared Rules

- Protect meaningful behavior, not coverage numbers.
- Establish product, user, production, support, debugging, review, or release risk before recommending or writing tests.
- Prefer repo-native frameworks, helpers, fixtures, commands, and naming.
- Choose the narrowest test level that preserves the real failure mechanism.
- Load targeted references instead of reading the whole reference library.
- State evidence inspected, commands run, commands not run, and residual risk.
- Mark low-value tests `REDO` or `REMOVE`, not `KEEP`.

## scan

Find the best parts to test next, the right strategy for each, and the ROI of testing them. This mode is read-only: inspect the repo, existing tests, and references; do not edit files.

Start with:

- [Behavior To Test Map](reference/behavior-to-test-map/overview.md)
- [Risk-Based Testing](reference/risk-based-testing/overview.md)
- [User Behavior Testing](reference/user-behavior-testing/overview.md)
- [Test Level Selection](reference/test-level-selection/overview.md)

Workflow:

1. Establish product/customer context from repo evidence.
2. Inventory existing test frameworks, commands, fixtures, CI, and test layers.
3. Map high-value behavior before low-level helpers.
4. Choose the narrowest test strategy that preserves the real user or production risk.
5. Rank candidates by impact, likelihood, confidence gap, and cost.

Output:

- Scope and evidence inspected.
- Ranked candidates, ideally 3-5.
- Best next test and why it is the first investment.
- Tempting low-value tests to avoid, if any.
- Questions that would materially change the ranking.

## test

Write tests only when they protect meaningful behavior. A useful test reduces future user errors, production incidents, support work, debugging time, review time, or release risk.

Start with:

- [Test Level Selection](reference/test-level-selection/overview.md)
- [Test Oracles And Assertions](reference/test-oracles-and-assertions/overview.md)
- [Test Data And Fixtures](reference/test-data-and-fixtures/overview.md)
- [Mocking And Test Doubles](reference/mocking-and-test-doubles/overview.md)
- [Test Feedback Loops](reference/test-feedback-loops/overview.md)

Workflow:

1. Establish the product/user risk from repo evidence before writing a test.
2. Inspect existing tests, framework conventions, fixtures, commands, and CI shape.
3. Select the narrowest test level that preserves the real failure mechanism.
4. Define the protected behavior, regression it catches, oracle, setup, and validation command before editing.
5. Write one focused test using repo-native style and existing helpers.
6. Validate with the smallest relevant command. If it is unsafe or unclear, state that instead of guessing.
7. Apply the value gate before finalizing: `KEEP`, `REDO`, or `REMOVE`.

Output:

- Behavior protected.
- Why this test is worth keeping.
- Files changed.
- Validation command and result, or why it was not run.
- Verdict: `KEEP`, `REDO`, or `REMOVE`.
- Remaining risk.

## doctor

Run a read-only test-suite health scan and report likely concerns with evidence. Do not edit, delete, rewrite, quarantine, or disable tests.

Start with:

- [Test Suite Health Diagnostics](reference/test-suite-health-diagnostics/overview.md)
- [Flaky Test Detection and Management](reference/flaky-test-detection-and-management/overview.md)
- [Test Feedback Loops](reference/test-feedback-loops/overview.md)
- [Test Automation Pyramid](reference/test-automation-pyramid/overview.md)

Workflow:

1. Identify repository root, language/framework stack, test runners, CI systems, naming conventions, and test layers.
2. Inventory suite shape and test commands.
3. Scan for weak assertions, excessive mocking, flaky timing, shared state, broad snapshots, slow tests, skipped/quarantined tests, and missing critical-risk coverage.
4. Inspect CI and monitoring signals when available.
5. Grade reliability, speed, signal, diagnostic value, maintainability, risk coverage, and monitoring.

Output:

- Scope, stack, frameworks, CI, evidence inspected, and whether tests were run.
- Overall grade and confidence.
- Top concerns with severity, confidence, evidence, why it matters, and suggested action.
- Rubric scores.
- Suite-shape gaps, bad test smells, monitoring gaps, quick wins, and material follow-up questions.
