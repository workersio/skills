# Behavior To Test Map

## Purpose

Map product behavior, customer value, code surfaces, dependencies, and risk signals to concrete testing opportunities. Use this when scanning an unfamiliar repo or deciding where an agent should add the next high-value test.

## Use When / Avoid When

| Use When | Avoid When |
| --- | --- |
| The behavior is not preselected and the agent must discover good test candidates. | A single behavior is already selected; use the relevant design reference directly. |
| Existing tests are uneven, missing, or hard to relate to product risk. | There is no access to code, tests, docs, or runtime commands. |
| A change touches multiple layers and needs a compact test plan. | The goal is broad suite audit; use suite health diagnostics. |

## Core Principles

- Start with customer job, business promise, behavior, and risk; then pick files and test levels.
- Combine four maps: customer/user surface, business-critical workflows, code/dependency graph, and existing test coverage.
- Prefer candidates with clear oracle, stable setup, meaningful failure mode, and local command.
- Do not chase uncovered lines before identifying behavior worth protecting.
- Rank opportunities by customer/business impact, likelihood, confidence gap, and cost to test.
- Recommend one focused test when acting; keep larger plans as candidates.

## Decision Rules

| Code/Behavior Shape | Candidate Test |
| --- | --- |
| Product promise, sales claim, pricing page, onboarding, conversion path. | User/API workflow test for the promised outcome plus lower-level checks for rules. |
| Pure logic with branches or boundary values. | Unit examples plus property/invariant where useful. |
| Permission, tenant, role, or security-sensitive decision. | Allow/deny matrix at policy/service level plus one workflow/API check. |
| Parser, serializer, mapper, schema, migration. | Round-trip, golden, contract, or migration integration test. |
| External API/client/provider. | Adapter integration, stubbed failure-mode test, and contract verification. |
| Database query/transaction/cache behavior. | Integration test with real disposable dependency. |
| UI workflow or form. | Component/user-behavior test; one E2E smoke for critical journey. |
| Bug fix or incident. | Regression at narrowest level that would have failed before. |

## Common Failure Modes

- Mapping files to tests without naming the behavior.
- Selecting easy private helpers while ignoring public risk.
- Recommending broad E2E tests for every workflow branch.
- Counting coverage as confidence without inspecting assertions.
- Ranking candidates by developer convenience while ignoring customer, revenue, trust, data, or support impact.
- Ignoring existing commands, fixtures, and local test style.

## Output Guidance For Agents

- For each candidate, include part to test, strategy, ROI, evidence, and confidence.
- Explain ROI with customer/business impact, likelihood, confidence gap, and test cost.
- Separate "high confidence from repo evidence" from inference.
- Pick one best next test unless the user asked for a plan.
- If writing a test, cite the selected candidate and keep the implementation focused.

## Agent Checklist

- Infer customer profile and product value from README, docs, routes, UI copy, pricing, examples, sales language, support/incident notes, and domain terms.
- Inspect public surfaces: routes, commands, APIs, UI screens, jobs, events.
- Inspect changed/important code: branches, boundaries, side effects, dependencies.
- Inspect existing tests and CI commands.
- Score candidates by impact, likelihood, confidence gap, and cost.
- Choose the lowest level that preserves the risk.

## Source Anchors

- Google Testing Blog, [Code Coverage Best Practices](https://testing.googleblog.com/2020/08/code-coverage-best-practices.html)
- Inozemtseva and Holmes, [Coverage Is Not Strongly Correlated with Test Suite Effectiveness](https://www.cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf)
- Martin Fowler, [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- Google Testing Blog, [How Much Testing is Enough?](https://testing.googleblog.com/2021/06/how-much-testing-is-enough.html)
- Google Testing Blog, [Risk-Driven Testing](https://testing.googleblog.com/2014/05/testing-on-toilet-risk-driven-testing.html)
- Strategyzer, [Value Proposition Canvas](https://www.strategyzer.com/library/the-value-proposition-canvas)
