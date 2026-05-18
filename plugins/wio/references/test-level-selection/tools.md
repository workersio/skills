# Test Level Selection Tools

Use repo signals to classify how tests are already layered, then choose the missing level by risk. Directory names are useful clues, but dependency scope and runtime behavior matter more than names.

## Tool Categories

| Category | Examples | Evidence |
| --- | --- | --- |
| Native test runners | pytest, JUnit, Jest/Vitest, Go test, cargo test, xUnit/NUnit. | Unit/component commands, markers, runtime, coverage scope. |
| Integration harnesses | Testcontainers, docker compose, local emulators, in-memory servers. | Real dependency coverage without shared mutable environments. |
| Contract tools | Pact, schema validators, OpenAPI/AsyncAPI checks, protobuf compatibility checks. | Consumer/provider compatibility evidence. |
| Browser/mobile runners | Playwright, Cypress, Selenium, Appium. | User journey and browser/device behavior evidence. |
| CI orchestration | GitHub Actions, GitLab CI, Buildkite, Bazel, Gradle/Maven profiles. | Which layers block PRs, run nightly, retry, or publish artifacts. |

## Repo Signals To Inspect

| Signal | File/Command Patterns | Evidence | Caveats |
| --- | --- | --- | --- |
| Test directory names | `unit`, `component`, `integration`, `contract`, `e2e`, `system`, `acceptance`. | Intended layer taxonomy. | Names often drift; inspect dependencies and setup. |
| Markers/tags | `@Tag`, `@Category`, `pytest.mark`, `describe`, `test.describe`, `slow`, `integration`. | Selectable suites and CI grouping. | Tags can be stale or underused. |
| Dependency setup | `docker-compose.yml`, `testcontainers`, emulator config, test DB URLs. | Middle-layer tests may be available. | Shared DBs and long-lived envs reduce isolation. |
| Contract artifacts | `pacts/`, `openapi.yaml`, `*.proto`, schema fixtures, broker config. | Boundary expectations exist. | Schemas without provider verification are weak evidence. |
| Browser config | `playwright.config.*`, `cypress.config.*`, Selenium/Grid config. | End-to-end or component browser capacity. | UI tests may be broad, flaky, or not user-observable. |

## Common Commands And Patterns

| Goal | Starting Commands |
| --- | --- |
| Inventory test files | `rg --files | rg "(test|spec|__tests__|e2e|integration|contract)"` |
| Find layer tags | `rg "@(Tag|Category)|pytest\\.mark|describe\\(|test\\.describe|slow|integration|e2e|contract" test tests src` |
| Find integration dependencies | `rg "testcontainers|docker compose|docker-compose|postgres|mysql|redis|kafka|localstack|wiremock|mockserver" .` |
| Find contract checks | `rg "pact|openapi|swagger|asyncapi|protobuf|buf|schema" .` |
| Find browser tests | `rg "playwright|cypress|selenium|webdriver|appium|getByRole|cy\\.|page\\." .` |

## Evidence Rules

- Classify a test by what it boots and what it can fail on, not by filename alone.
- A lower-level test is enough only if it preserves the dependency or behavior that could regress.
- A higher-level test is justified when it protects unique wiring, browser, auth, deployment, or journey risk.
- Report if the repo lacks commands to run the chosen level locally.

## Source Anchors

- Google Testing Blog, [Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html)
- Pact, [contract testing introduction](https://docs.pact.io/)
- Testcontainers, [Docker docs](https://docs.docker.com/testcontainers/)
- Playwright, [best practices](https://playwright.dev/docs/best-practices)
