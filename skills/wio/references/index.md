# Testing Practice References

Reference selection starts with the reliability risk, not with the easiest test to write. These practices are complementary: a high-quality testing plan often combines a focused behavior test, a boundary or integration check, and an honest statement of residual risk.

## WIO Entry Points

WIO exposes one skill with four command modes:

| Command | Primary References |
| --- | --- |
| scan | Behavior To Test Map, Risk-Based Testing, User Behavior Testing, Test Level Selection, and the relevant topic reference for the chosen strategy. |
| test | Full loop: candidate discovery, strategy selection, test implementation, validation, and review. Use behavior mapping, risk, level selection, oracles, data, doubles, and feedback loops. |
| review | Test value gate: customer/developer value, oracle strength, realistic setup, feedback-loop fit, and `KEEP`, `REDO`, or `REMOVE`. |
| doctor | Test Suite Health Diagnostics, then targeted references for level, oracle, doubles, data, flake, and feedback-loop findings. |

Load only the reference files needed for the current decision.

## Exploration Order

1. Infer product/customer context from README, docs, examples, UI copy, routes, API docs, pricing/plans, support/incident notes, and domain terms.
2. Inventory test files, commands, framework config, CI jobs, fixtures, skips, retries, reports, and existing naming/style.
3. Inspect the production code behind the reviewed or candidate test: public behavior, dependencies, state, side effects, data, and boundaries.
4. Decide the customer/business risk and fault mechanism before choosing unit, component, integration, contract, E2E, monitoring, or specialized testing.
5. Load only the specific reference files needed for that decision; use each `tools.md` sibling for repo signals and commands.
6. Report concise evidence, not internal exploration notes.

## WIO Test Pipeline

`$wio test` should not jump straight to writing code. The expected pipeline is:

1. Discover a candidate with real user, production, support, release, review, or developer-flow value.
2. Pick the strategy: test level, oracle, data/fixture setup, doubles, and feedback loop.
3. Write one focused repo-native test.
4. Validate with the smallest relevant command.
5. Review the written test for value and signal.
6. Return `KEEP`, `REDO`, or `REMOVE`.

When subagents are available, use:

- `wio-candidate-scout` for discovery.
- `wio-strategy-critic` before editing.
- `wio-test-reviewer` after validation.

These subagents are process accelerators, not separate doctrine.

## Quick Selection

| Reference | Use When | Look Elsewhere When |
| --- | --- | --- |
| [Testing Core Concepts](./testing-core-concepts/overview.md) | You need the high-level vocabulary for assertions, invariants, safety properties, liveness properties, and other property types before choosing a test strategy. | A concrete test strategy is already selected and you only need implementation details. |
| [Test Automation Pyramid](./test-automation-pyramid/overview.md) | A change needs the right balance of unit, component, integration, contract, and end-to-end tests. | The suite shape is already healthy and the primary risk is security, load, rollout, or production monitoring. |
| [Testability](./testability/overview.md) | Code is hard to exercise because dependencies, state, time, IO, or control flow are tangled. | The behavior is already easy to isolate and the question is which test layer should cover it. |
| [Test Level Selection](./test-level-selection/overview.md) | A behavior needs a unit, component, integration, contract, E2E, or CI-only decision. | The test layer is already known and the question is how to implement the test cleanly. |
| [User Behavior Testing](./user-behavior-testing/overview.md) | Tests should be derived from real user workflows, product risks, and failure modes. | The target is internal deterministic logic with no meaningful user-facing behavior. |
| [Mocking And Test Doubles](./mocking-and-test-doubles/overview.md) | A test needs practical dependency substitution without losing the real risk. | Real dependencies are cheap, deterministic, and necessary to preserve the behavior under test. |
| [Test Feedback Loops](./test-feedback-loops/overview.md) | A test needs to be placed in local development, PR CI, nightly, release, or production monitoring loops. | Runtime placement is obvious and the main problem is test design. |
| [Test Oracles And Assertions](./test-oracles-and-assertions/overview.md) | A test needs a clear correctness oracle, assertion strategy, invariant, snapshot, or golden file. | The assertion is obvious and the main risk is environment or dependency setup. |
| [Test Data And Fixtures](./test-data-and-fixtures/overview.md) | Tests need reliable data setup, isolation, factories, seeds, or cleanup. | The test has no stateful data or fixture needs. |
| [Behavior To Test Map](./behavior-to-test-map/overview.md) | A codebase scan needs to map product behavior and code shape to testing opportunities. | A single behavior is already selected. |
| [Test Suite Health Diagnostics](./test-suite-health-diagnostics/overview.md) | An existing suite needs auditing for weak signal, noisy CI, flaky failures, shallow assertions, or misleading coverage. | A known behavior needs one focused test and suite health is not in question. |
| [Flaky Test Detection and Management](./flaky-test-detection-and-management/overview.md) | Test outcomes vary under the same code revision, retries are common, or nondeterminism is likely. | Failures are deterministic product regressions. |
| [Static Testing / Static Analysis](./static-testing-static-analysis/overview.md) | Defects can be caught from code, type, config, policy, or dependency shape before runtime. | The risk depends on runtime behavior, user intent, distributed timing, UX, or performance under load. |
| [Security Testing Beyond SAST](./security-testing-beyond-sast/overview.md) | Security confidence depends on behavior, authz, tenant boundaries, dependencies, secrets, IaC, containers, dynamic checks, or abuse cases. | A source-level rule already fully covers the defect class. |
| [Risk-Based Testing](./risk-based-testing/overview.md) | Test effort must be prioritized by customer, business, security, operational, or compliance impact. | All meaningful validation is cheap enough to run every time, or mandatory standards dictate the scope. |
| [Property-Based Testing](./property-based-testing/overview.md) | Deterministic logic has large input spaces and correctness can be expressed as invariants, round trips, metamorphic relations, or model agreement. | Behavior is subjective, visual, poorly specified, or dominated by expensive side effects. |
| [Fuzz Testing / Continuous Fuzzing](./fuzz-testing-continuous-fuzzing/overview.md) | Parsers, decoders, protocols, file formats, URL/path handling, or untrusted inputs need robustness testing. | There is no deterministic harness, input boundary, or oracle. |
| [Mutation Testing](./mutation-testing/overview.md) | Existing tests execute important code but may not fail for meaningful behavioral changes. | The baseline suite is flaky, slow, failing, or the target is generated/low-risk glue. |
| [Regression Test Selection / Test Impact Analysis](./regression-test/overview.md) | Full regression is too slow and affected-test selection can safely accelerate feedback. | Dependency metadata is unreliable and no full-suite fallback exists. |
| [Performance, Load, and Stress Testing](./performance-load-and-stress-testing/overview.md) | Latency, throughput, saturation, overload, scaling, or launch readiness is the main risk. | There are no SLOs, baselines, realistic workloads, or useful observability. |
| [Resilience Testing and Fault Injection](./resilience-testing-and-fault-injection/overview.md) | Dependency failure, timeout, retry, failover, backpressure, recovery, or cascading-failure behavior matters. | Expected behavior under fault is undefined or blast-radius controls are missing. |

## Decision Path

1. If the intended property is unclear, start with [Testing Core Concepts](./testing-core-concepts/overview.md), then inspect requirements, public APIs, existing tests, incidents, and user workflows before writing tests.
2. If code is hard to exercise, use [Testability](./testability/overview.md).
3. If the question is where a test belongs, use [Test Level Selection](./test-level-selection/overview.md) and [Test Automation Pyramid](./test-automation-pyramid/overview.md).
4. If behavior should come from user workflows, use [User Behavior Testing](./user-behavior-testing/overview.md).
5. If dependency substitution is the decision, use [Mocking And Test Doubles](./mocking-and-test-doubles/overview.md).
6. If the suite exists but trust is low, use [Test Suite Health Diagnostics](./test-suite-health-diagnostics/overview.md).
7. If red CI often turns green after reruns, use [Flaky Test Detection and Management](./flaky-test-detection-and-management/overview.md).
8. If defects are recognizable from code or config shape, use [Static Testing / Static Analysis](./static-testing-static-analysis/overview.md).
9. If security risk extends beyond code shape, use [Security Testing Beyond SAST](./security-testing-beyond-sast/overview.md).
10. If test capacity is constrained, use [Risk-Based Testing](./risk-based-testing/overview.md).
11. If examples keep missing deterministic edge cases, use [Property-Based Testing](./property-based-testing/overview.md).
12. If untrusted or structured inputs can crash, hang, corrupt, or violate invariants, use [Fuzz Testing / Continuous Fuzzing](./fuzz-testing-continuous-fuzzing/overview.md).
13. If coverage is high but assertions feel weak, use [Mutation Testing](./mutation-testing/overview.md).
14. If full regression is too slow, use [Regression Test Selection / Test Impact Analysis](./regression-test/overview.md).
15. If user-visible reliability depends on traffic, latency, or saturation, use [Performance, Load, and Stress Testing](./performance-load-and-stress-testing/overview.md).
16. If dependency or infrastructure failure is the risk, use [Resilience Testing and Fault Injection](./resilience-testing-and-fault-injection/overview.md).

## Cross-Cutting Testing Judgment

- Coverage is not confidence; covered code can still have weak assertions or no useful oracle.
- Passing tests are not proof of reliable software; they are evidence about selected behaviors under selected conditions.
- The best test level is the lowest level that preserves the real risk.
- The best assertion is one that would fail for the regression or failure mode that matters.
- Mocks are useful for boundaries, speed, and determinism, but excessive mocking can test the mock instead of the system.
- Fast tests are valuable when they still exercise the behavior at risk.
- End-to-end tests are valuable for critical workflows but should remain selective, observable, and debuggable.
- Snapshot tests need a clear protected contract; unreviewed snapshot updates create low-signal approval tests.
- Regression tests should prove that a specific failure cannot silently return.
- Candidate selection should maximize test ROI: customer/business impact, likelihood, confidence gap, and cost to test.
- Validation reports should name commands run, commands not run, and residual risk.
