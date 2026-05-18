# User Behavior Testing

## Purpose

Turn real user goals, workflows, roles, accessibility affordances, and failure modes into tests that assert observable outcomes. This reference is for selecting behavior worth protecting, not for automating every screen path.

## Use When / Avoid When

| Use When | Avoid When |
| --- | --- |
| A feature affects user-visible flows, roles, permissions, navigation, forms, notifications, or recovery. | The target is internal deterministic logic with no meaningful user or external-client behavior. |
| Product risk comes from how steps combine, not from one isolated function. | The only available information is implementation shape; inspect product/API behavior first. |
| Existing tests assert implementation details but miss what users observe. | The behavior is too volatile or unspecified to encode without product clarification. |

## Core Principles

- Start from a user goal and expected outcome: what changed for the user, account, API client, or operator?
- Prefer user-observable interactions and assertions: roles, labels, accessible names, visible state, emitted events, persisted records, or API responses.
- Keep journeys short. Use setup APIs/fixtures for preconditions unless the setup path is the behavior under test.
- Include meaningful negative paths: denied access, invalid input, retry/recovery, duplicate submission, empty state, and partial failure.
- Use broad UI/end-to-end tests sparingly for critical journeys; push rule permutations and boundary cases lower.
- A behavior test should fail when the user experience or contract breaks, not when private structure changes.

## Decision Rules

| Behavior Source | Test Direction |
| --- | --- |
| Critical user journey, checkout/signup/recovery/admin action. | One end-to-end or workflow smoke plus focused lower-level cases for branches. |
| Form, component, page, or screen behavior. | Component/browser test using accessible locators and visible assertions. |
| Role or permission behavior. | Direct policy/service tests for matrix coverage plus one workflow denial/allowance check. |
| Public API behavior. | Request/response tests, contract/schema checks, and negative/error cases. |
| Incident, support ticket, analytics drop, or customer complaint. | Regression test at the narrowest level that reproduces the failed behavior; add monitor if pre-prod cannot see it. |

## Common Failure Modes

- Testing CSS classes, component names, private hooks, or mock calls instead of behavior.
- Long scripts that combine setup, many assertions, and unrelated user goals.
- Happy-path-only journeys that miss denied, invalid, empty, duplicate, and recovery states.
- Fragile selectors that break on harmless markup changes.
- BDD/Gherkin text that restates implementation steps without business examples.

## Output Guidance For Agents

- Name the actor, precondition, action, and user-observable outcome.
- Explain why the selected behavior is worth testing: critical path, regression, permission risk, data loss, revenue, support, or API contract.
- Keep setup separate from the behavior under test.
- Report what is covered lower vs what the user-level test uniquely covers.

## Agent Checklist

- Inspect routes, screens, controllers, docs, stories, incidents, and existing E2E tests.
- Identify the user goal before choosing selectors or mocks.
- Use accessible/user-facing locators when available.
- Assert one main outcome and only supporting state needed to diagnose failure.
- Avoid broad journeys for branch matrices.

## Source Anchors

- Testing Library, [queries and guiding principles](https://testing-library.com/docs/queries/about/)
- Playwright, [test user-visible behavior](https://playwright.dev/docs/best-practices)
- Google Testing Blog, [What Makes a Good End-to-End Test?](https://testing.googleblog.com/2016/09/testing-on-toilet-what-makes-good-end.html)
- Cucumber, [BDD and Gherkin reference](https://cucumber.io/docs)
