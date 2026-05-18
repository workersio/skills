# Test Level Selection

## Purpose

Choose the narrowest test level that preserves the real risk of a behavior. The goal is fast, trustworthy, diagnosable signal, not labeling tests correctly for its own sake.

## Use When / Avoid When

| Use When | Avoid When |
| --- | --- |
| A behavior could be tested as unit, component, integration, contract, end-to-end, or monitoring. | The test level is mandated by regulation or team policy and only implementation details remain. |
| Existing coverage exists at one level but does not protect the changed risk. | The behavior is undefined; clarify expected behavior before choosing a level. |
| A broad test is slow/flaky and may be replaceable by a lower-level regression. | Lower-level tests would mock away the boundary or user journey that actually failed. |

## Core Principles

- Prefer the lowest level that still includes the fault mechanism.
- Use real boundaries when the boundary is the risk: database semantics, serialization, authz policy, schema, browser behavior, provider contract, or deployment config.
- Keep end-to-end tests selective: one critical journey can protect cross-system wiring; edge-case matrices usually belong lower.
- Do not unit-test trivia, generated code, or private implementation details just to add count or coverage.
- When a high-level test catches a bug, add the narrowest durable regression test that would have caught it earlier.

## Decision Rules

| Behavior/Risk | Good First Level | Escalate When |
| --- | --- | --- |
| Pure calculation, parser, validator, permission rule, state transition. | Unit/property test. | Behavior depends on framework lifecycle, persistence, concurrency, or external contract. |
| UI component behavior, form validation, accessibility state, emitted event. | Component/DOM test. | Browser engine, routing, auth/session, or full workflow is the risk. |
| Repository, migration, query, transaction, cache, filesystem, queue adapter. | Integration test with real disposable dependency. | Production topology or cross-service timing is the risk. |
| HTTP/message schema between services. | Contract test. | Provider behavior itself must be functionally verified. |
| Critical user journey across deployed-like system. | End-to-end smoke. | The scenario is only a business-rule permutation already covered lower. |
| Production-only reliability, traffic, rollout, or SLO behavior. | Monitor, canary, synthetic, or load/resilience test. | Failure can be reproduced cheaply pre-merge. |

## Common Failure Modes

- "Ice cream cone" suites where most confidence depends on slow UI/full-stack tests.
- Mock-heavy unit tests that verify call sequences but not user, API, or domain behavior.
- Missing middle layer: no contract, schema, persistence, or adapter tests.
- Duplicating the same assertion at many levels without unique risk.
- Treating raw coverage increase as proof that the right level was chosen.

## Output Guidance For Agents

- State the behavior, risk, chosen level, and why lower levels would or would not preserve the risk.
- Mention existing tests at neighboring levels and whether the new test fills a gap or replaces duplication.
- If choosing a broad test, name the unique integration confidence it provides.
- Report residual risk if a dependency, environment, or workflow was not exercised.

## Agent Checklist

- Identify the fault mechanism the test must catch.
- Search existing tests by feature, route, API, model, and incident keyword.
- Choose the lowest level that includes that mechanism.
- Avoid mocking the subject of the claim.
- Run the selected level plus impacted neighboring tests when shared contracts changed.

## Source Anchors

- Martin Fowler, [Test Pyramid](https://martinfowler.com/bliki/TestPyramid.html)
- Martin Fowler, [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- Google Testing Blog, [Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html)
- Google Testing Blog, [Just Say No to More End-to-End Tests](https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html)
