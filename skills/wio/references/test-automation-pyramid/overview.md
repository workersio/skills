# Test Automation Pyramid

## Strategy Map

### Purpose
Select a balanced automated-test portfolio for a change or codebase without treating any layer as inherently superior.

### Reliability Goal
Reduce release risk from suites that are too slow, too brittle, too narrow, or too dominated by broad end-to-end tests to give fast diagnostic feedback.

### When This Strategy Applies
- CI feedback is too slow or noisy for frequent shipping.
- A change has behavior that can be asserted at multiple levels and needs the lowest level that still gives real confidence.
- A team is deciding which checks belong in unit, component, integration, contract, browser, or end-to-end suites.
- A bug found at a high level should be converted into a narrower durable regression test.

### When This Strategy Does Not Apply
- The goal is to satisfy a fixed percentage split rather than protect risk.
- The behavior only becomes meaningful in a real deployed workflow and lower-level tests would mock away the actual risk.
- The proposed unit tests target trivial getters, private helpers, generated code, or framework wiring without observable behavior.
- The suite already has fast focused coverage and the main risk is performance, security, rollout, or production monitoring.

### Signals To Inspect First
- Public APIs, user workflows, critical business paths, service contracts, existing test layers, CI duration, flake history, bug reports, dependency boundaries, data stores, authentication/authorization rules, and deployment topology.

### Test Design Principles
- Use the pyramid as a feedback and risk heuristic, not a quota.
- Prefer the lowest level that exercises the behavior at risk without replacing the risk with mocks.
- Keep broad tests for unique cross-system confidence; move duplicated edge-case matrices lower.
- When an end-to-end test catches a bug, add the narrowest meaningful regression test that would have caught it earlier.
- Mocks are useful for expensive or nondeterministic boundaries, but tests that mock every meaningful collaborator often verify wiring fantasies rather than product behavior.

### Good Test Characteristics
- Fast deterministic tests cover domain rules, validation, boundaries, permissions, and state transitions.
- Integration and contract tests cover real boundaries: database semantics, serialization, schemas, message formats, API expectations, and adapter behavior.
- End-to-end tests cover a small set of critical journeys with stable data, useful artifacts, and assertions users or external clients would care about.
- Failures identify a likely layer, owner, and behavior.

### Poor Test Characteristics
- An ice-cream-cone suite where most signal comes from slow UI or full-stack tests.
- Unit tests that only assert private call sequences or mock interactions.
- Snapshots used as broad approval tests with no explanation of what must not change.
- Coverage-padding tests that execute code without meaningful assertions.
- Broad tests that duplicate every lower-level case and become slow flaky bottlenecks.

### Execution Pattern
- Understand the changed behavior and customer or integration risk.
- Inventory existing tests by layer and identify the missing confidence.
- Choose the lowest layer that preserves the real risk.
- Add focused cases for meaningful happy, boundary, negative, and failure paths.
- Keep only broad workflow checks that add unique integration confidence.
- Run targeted tests first, then broaden to impacted suites when shared behavior or contracts changed.
- Report what risk remains outside the selected layers.

### Examples
- Weak: a browser checkout test asserts every fee-calculation permutation. Stronger: unit tests cover fee boundaries; integration tests cover persistence and payment-adapter behavior; one browser test covers the critical successful checkout journey.
- Weak: a component test asserts internal hook calls. Stronger: it renders the public component, performs user actions, and asserts accessible output or emitted events.

### Validation
- Run the relevant unit/component/integration/E2E commands, not only the new file if shared behavior changed.
- For regression work, confirm the test fails on the broken behavior or would fail for the intended regression.
- Check that mocks do not replace the behavior being claimed as covered.
- Inspect runtime and flake risk for any added high-level tests.
- Do not cite coverage increase as proof of suite quality.

### Failure Modes
- Rigid percentage targets drive bad test placement.
- Over-mocking makes the base fast but low-confidence.
- Too many E2E tests slow shipping and obscure failures.
- Missing middle-layer tests let API, schema, persistence, and adapter regressions escape.
- High-level snapshots become expensive approval rituals.

## Overview

The Test Automation Pyramid is a portfolio model for automated tests: many small, fast, deterministic tests at the bottom; fewer integration, contract, or component tests in the middle; and a small number of broad end-to-end tests at the top. Its reliability value comes from localizing failures quickly and avoiding a suite dominated by slow, flaky, hard-to-debug UI or full-stack tests. Martin Fowler describes the core idea as having many more low-level unit tests than high-level broad-stack GUI tests, while Google’s guidance uses the pyramid to avoid “ice cream cone” and “hourglass” test suites.

## Best Fit

Highest ROI appears in teams that ship frequently, run CI on every change, and need fast feedback before merge or deploy. The pyramid is especially useful when a product has enough logic, integration points, and user workflows that relying only on manual QA or end-to-end automation would make releases slow and failures ambiguous.

Use it as a risk and feedback-speed heuristic, not a quota. Google has suggested 70% unit, 20% integration, and 10% end-to-end as a first guess, but explicitly notes that the exact mix depends on the team.

## Good Candidates

* Domain logic with many edge cases: pricing, authorization rules, validation, state transitions, parsers, schedulers.
* Components with stable public interfaces where behavior can be asserted without booting the whole system.
* Service boundaries: HTTP APIs, message contracts, database access, external dependency adapters.
* CI/CD pipelines where test runtime and flakiness directly affect developer throughput.
* Microservice systems where contract tests can catch provider-consumer incompatibilities earlier than full environment tests. Pact’s documentation frames contract testing as a way to verify inter-application messages without relying only on expensive, brittle integration tests.

## When Not To Use

Do not use the pyramid as a rigid reporting target detached from risk. A UI-heavy application may need many component-level UI tests. A data pipeline may need more integration tests around schemas, storage, and external systems than classic web-app diagrams imply.

Avoid forcing unit tests around trivial getters, generated code, framework wiring, or private implementation details. Fowler’s “Practical Test Pyramid” stresses behavior-focused tests and warns that tests too tightly coupled to implementation become refactoring friction rather than a safety net.

Do not use the pyramid to eliminate end-to-end tests entirely. Some risks only show up when the deployed system runs as a whole: authentication flows, resource allocation, concurrency, browser behavior, cross-service compatibility, and production-like configuration.

## Limitations

The pyramid does not define universal test-level names. “Unit,” “integration,” “component,” “service,” and “end-to-end” vary across teams. Agree on scope, dependencies allowed, runtime expectations, and ownership instead of arguing over labels.

It can create false confidence when the base is full of isolated tests that mock every meaningful collaborator. It can also create waste when broad tests duplicate lower-level assertions. A practical rule: when a high-level test catches a bug, add or fix the lowest-level test that could have caught it, then keep only the broad assertion that still adds unique confidence.

Flakiness is an operational cost, not a cosmetic issue. Google defines a flaky test as one that can both pass and fail against the same code, and reported that such failures can consume investigation effort and erode trust in CI.

End-to-end tests are expensive assets. Google’s end-to-end testing guidance recommends keeping the count low, focusing them on important use cases, and designing them for debuggability with logs, screenshots, and preserved state.

## Signals

### Working Signals

* Most PR feedback comes from fast tests before developers switch context.
* Failed tests usually identify a narrow cause: function, module, adapter, contract, or workflow.
* E2E tests cover critical journeys, not every business rule permutation.
* CI has low flaky-failure rate, stable runtime, and clear ownership for failures.
* New bugs found at high levels result in lower-level regression tests.

### Misuse Signals

* “Ice cream cone”: most automation is UI or full-stack E2E.
* “Hourglass”: many unit and E2E tests but missing integration/contract coverage.
* Frequent reruns are normal behavior.
* Teams quarantine failures indefinitely.
* Coverage targets drive low-value tests.
* Broad tests assert UI text, layout, or implementation details unrelated to the risk being tested.

## Examples

A payments team tests fee calculation with unit tests for boundary cases and currencies. It adds integration tests for database persistence and payment-provider adapter behavior using controlled test doubles. It keeps one E2E checkout test for the critical “authorized card creates paid order and receipt” journey.

A microservice team uses consumer-driven contract tests for API expectations between services. Provider CI runs those contracts before deployment. One nightly E2E test verifies that the deployed services can complete the most important customer workflow.

A frontend team unit-tests pure formatting and state reducers, component-tests forms through accessible DOM queries, and keeps a few browser E2E tests for login, checkout, and account recovery.

## Packages And Libraries

### JVM:

* JUnit — unit and component tests.
* Mockito — test doubles.
* Testcontainers — integration tests with disposable real dependencies.
* Pact JVM — consumer-driven contract tests.

### JavaScript / TypeScript:

* Jest or Vitest — unit and component tests.
* Testing Library — DOM/component tests focused on user-observable behavior.
* Playwright or Cypress — browser end-to-end and critical workflow tests.

### Python:

* pytest — unit, component, and integration tests.
* unittest.mock — test doubles.
* Testcontainers for Python — integration tests with real services.
* Pact Python — contract tests.

### .NET:

* xUnit.net or NUnit — unit and component tests.
* Moq / NSubstitute — test doubles.
* Testcontainers for .NET — disposable infrastructure integration tests.
* Playwright for .NET — browser E2E tests.

### C++:

* GoogleTest / GoogleMock — unit, component, and mock-based tests.

### Cross-ecosystem:

* Selenium WebDriver — browser automation where cross-browser compatibility or legacy support matters.
* Pact — contract testing for HTTP and message-based integrations.
* Testcontainers — database, broker, and dependency-backed integration tests without shared mutable test environments.
