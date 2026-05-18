---
name: wio
description: Testing workflow skill for scan, test, doctor, and review commands. Use when asked to find high-value tests, pick a testing strategy, write a focused test, review test value, diagnose suite health, flaky tests, low-signal tests, or testing strategy.
argument-hint: "[scan|test|review|doctor] [target]"
user-invocable: true
metadata:
  author: workers.io
  version: "0.1.0"
---

# WIO

WIO is one testing workflow skill with four command modes:

- `scan`: find the highest-value test candidates for a codebase, change, or scope.
- `test`: write one focused high-value test for a selected behavior, code path, or regression risk.
- `review`: review a newly written or existing test for customer value, developer value, signal quality, and maintainability.
- `doctor`: diagnose test-suite health problems in a codebase or scope.

Commands are accessed through `$wio`:

| Command | What it does | Start with |
| --- | --- | --- |
| `$wio scan [target]` | Find the highest-value test candidates for a codebase, change, or scope. | [Behavior To Test Map](references/behavior-to-test-map/overview.md), [Risk-Based Testing](references/risk-based-testing/overview.md), [User Behavior Testing](references/user-behavior-testing/overview.md), [Test Level Selection](references/test-level-selection/overview.md) |
| `$wio test [target]` | Run the full test workflow: discover candidate, pick strategy, write test, validate, review, and keep only if valuable. | [Behavior To Test Map](references/behavior-to-test-map/overview.md), [Risk-Based Testing](references/risk-based-testing/overview.md), [Test Level Selection](references/test-level-selection/overview.md), [Test Oracles And Assertions](references/test-oracles-and-assertions/overview.md), [Test Data And Fixtures](references/test-data-and-fixtures/overview.md), [Mocking And Test Doubles](references/mocking-and-test-doubles/overview.md), [Test Feedback Loops](references/test-feedback-loops/overview.md) |
| `$wio review [target]` | Review a test for meaningful customer or developer value and return `KEEP`, `REDO`, or `REMOVE`. | [Test Oracles And Assertions](references/test-oracles-and-assertions/overview.md), [Test Data And Fixtures](references/test-data-and-fixtures/overview.md), [Mocking And Test Doubles](references/mocking-and-test-doubles/overview.md), [Test Feedback Loops](references/test-feedback-loops/overview.md), [Mutation Testing](references/mutation-testing/overview.md) |
| `$wio doctor [target]` | Diagnose test-suite health problems in a codebase or scope. | [Test Suite Health Diagnostics](references/test-suite-health-diagnostics/overview.md), [Flaky Test Detection and Management](references/flaky-test-detection-and-management/overview.md), [Test Feedback Loops](references/test-feedback-loops/overview.md), [Test Automation Pyramid](references/test-automation-pyramid/overview.md) |

Use [references/index.md](references/index.md) as the reference map. Load only the reference files needed for the current decision.

## Command Selection

Use `scan` when the user asks what to test next, where coverage would matter, how to prioritize testing work, or which tests would reduce user, production, support, or team risk.

Use `test` when the user asks to add a test, improve a specific test, cover a bug, or validate a change with a meaningful automated test.

Use `review` when the user asks whether a test is worth keeping, asks for test review, or after `$wio test` writes or changes a test.

Use `doctor` when the user asks to audit tests, review suite quality, find flaky or low-value tests, inspect CI test health, or explain why a test suite is slow, noisy, or low-signal.

If the user explicitly names a WIO command, follow that mode. If the command is omitted, infer the mode from the request. If no command or target is provided, show the command table and ask what they want to do. If multiple modes apply, start with `scan` before `test`, and use `doctor` only for existing suite health.

## Shared Rules

- Protect meaningful behavior, not coverage numbers.
- Establish product, user, production, support, debugging, review, or release risk before recommending or writing tests.
- A test is valuable only if it would catch a meaningful regression, save developer time, improve release confidence, or expose a real operational/customer failure mode.
- Prefer repo-native frameworks, helpers, fixtures, commands, and naming.
- Choose the narrowest test level that preserves the real failure mechanism.
- Load targeted references instead of reading the whole reference library.
- State evidence inspected, commands run, commands not run, and residual risk.
- Mark low-value tests `REDO` or `REMOVE`, not `KEEP`.

## Subagent Workflow

When the host supports subagents or parallel agents, use the WIO subagent specs in `.claude/agents/` or `.codex/agents/` to improve quality without duplicating guidance:

- `wio-candidate-scout`: read-only discovery of high-value test candidates and real risk.
- `wio-strategy-critic`: read-only challenge of the chosen test level, oracle, doubles, fixtures, and validation loop before implementation.
- `wio-test-reviewer`: post-implementation review that returns `KEEP`, `REDO`, or `REMOVE`.

Subagents must read only targeted files and targeted WIO references. They return findings to the main agent; they do not write reports or copy reference content. Project subagent definitions, when present, live in official host directories: `.claude/agents/` and `.codex/agents/`.

For `$wio test`, use this sequence:

1. Discover a valuable candidate. Use `wio-candidate-scout` if available.
2. Pick the strategy. Use `wio-strategy-critic` to challenge the proposed level, oracle, fixture/data setup, mocks, and validation command before editing.
3. Write one focused test in the main agent, using repo-native patterns.
4. Validate with the smallest relevant command.
5. Review the written test. Use `wio-test-reviewer` if available.
6. Keep the test only if review returns `KEEP`; otherwise revise (`REDO`) or remove (`REMOVE`).

If subagents are unavailable, perform the same stages in the main agent and explicitly label the review stage.

## scan

Find the best parts to test next, the right strategy for each, and the ROI of testing them. This mode is read-only: inspect the repo, existing tests, and references; do not edit files.

Start with:

- [Behavior To Test Map](references/behavior-to-test-map/overview.md)
- [Risk-Based Testing](references/risk-based-testing/overview.md)
- [User Behavior Testing](references/user-behavior-testing/overview.md)
- [Test Level Selection](references/test-level-selection/overview.md)
- [Testing References Index](references/index.md)

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

Write tests only when they protect meaningful behavior. A useful test reduces future user errors, production incidents, support work, debugging time, review time, or release risk. Do not jump straight to implementation.

Start with:

- [Test Level Selection](references/test-level-selection/overview.md)
- [Test Oracles And Assertions](references/test-oracles-and-assertions/overview.md)
- [Test Data And Fixtures](references/test-data-and-fixtures/overview.md)
- [Mocking And Test Doubles](references/mocking-and-test-doubles/overview.md)
- [Test Feedback Loops](references/test-feedback-loops/overview.md)
- [Testing References Index](references/index.md)

Workflow:

1. Discover the highest-value candidate in scope from product risk, code shape, existing tests, CI, and user/developer impact.
2. Pick the right strategy: test level, oracle, data/fixture setup, doubles, and feedback loop.
3. State the protected behavior, regression it catches, why it matters, and validation command before editing.
4. Write one focused test using repo-native style and existing helpers.
5. Validate with the smallest relevant command. If it is unsafe or unclear, state that instead of guessing.
6. Review the test for value, signal, maintainability, and developer flow impact.
7. Apply the value gate before finalizing: `KEEP`, `REDO`, or `REMOVE`.

Output:

- Candidate chosen and why it beat alternatives.
- Strategy chosen and why it preserves the real risk.
- Behavior protected.
- Why this test is worth keeping.
- Files changed.
- Validation command and result, or why it was not run.
- Verdict: `KEEP`, `REDO`, or `REMOVE`.
- Remaining risk.

## review

Review a test as a quality gate, not as a rubber stamp. The test must justify its existence through customer value, production value, support/debugging value, review value, or release confidence.

Start with:

- [Test Oracles And Assertions](references/test-oracles-and-assertions/overview.md)
- [Test Data And Fixtures](references/test-data-and-fixtures/overview.md)
- [Mocking And Test Doubles](references/mocking-and-test-doubles/overview.md)
- [Test Feedback Loops](references/test-feedback-loops/overview.md)
- [Mutation Testing](references/mutation-testing/overview.md)
- [Testing References Index](references/index.md)

Workflow:

1. Identify the behavior or failure mode the test claims to protect.
2. Check whether that behavior matters to a user, operator, customer, API consumer, release, support/debugging loop, or developer workflow.
3. Check whether the assertion would fail for the meaningful regression.
4. Check whether setup, fixtures, mocks, and data preserve the real failure mechanism.
5. Check whether the validation command is the smallest useful loop and whether CI placement is appropriate.
6. Return `KEEP`, `REDO`, or `REMOVE` with evidence.

Output:

- Verdict: `KEEP`, `REDO`, or `REMOVE`.
- Protected behavior and value.
- Signal strengths.
- Weaknesses or false-confidence risks.
- Required changes if `REDO`, or removal reason if `REMOVE`.

## doctor

Run a read-only test-suite health scan and report likely concerns with evidence. Do not edit, delete, rewrite, quarantine, or disable tests.

Start with:

- [Test Suite Health Diagnostics](references/test-suite-health-diagnostics/overview.md)
- [Flaky Test Detection and Management](references/flaky-test-detection-and-management/overview.md)
- [Test Feedback Loops](references/test-feedback-loops/overview.md)
- [Test Automation Pyramid](references/test-automation-pyramid/overview.md)

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
