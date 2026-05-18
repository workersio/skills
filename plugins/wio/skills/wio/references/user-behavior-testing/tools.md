# User Behavior Testing Tools

Use tools to discover real workflows and then automate the smallest behavior that protects them. Do not let a browser runner turn every business rule into an end-to-end script.

## Tool Categories

| Category | Evidence It Provides | Caveats |
| --- | --- | --- |
| Product artifacts | User stories, acceptance criteria, docs, screenshots, API docs, design files. | Specs may be stale; compare with code and existing tests. |
| Code surface maps | Routes, controllers, commands, public APIs, event handlers, permissions. | Surface area is not usage frequency or risk. |
| Existing tests | Current scenarios, selectors, skipped paths, duplicated journeys. | Existing tests may encode poor behavior choices. |
| Browser/component tools | Playwright, Cypress, Testing Library, Selenium/Appium. | High fidelity can mean higher runtime and flake cost. |
| Production/support evidence | Incidents, tickets, analytics events, logs, SLOs. | Requires careful interpretation and may contain sensitive data. |

## Repo Signals To Inspect

| Signal | Common Patterns | Evidence | False Positives |
| --- | --- | --- | --- |
| Routes and screens | `routes`, `pages`, `screens`, `controllers`, `handlers`, `app/router`. | User entry points and workflow branches. | Internal/admin/dev routes may not be critical. |
| Accessible selectors | `getByRole`, `getByLabelText`, `aria-*`, labels, roles. | Tests may follow user-observable behavior. | `data-testid` can be valid when no user-facing selector is stable. |
| BDD/scenario files | `*.feature`, `Given/When/Then`, `Scenario Outline`. | Business examples and expected outcomes. | Step reuse can hide low-signal implementation scripts. |
| E2E configs | `playwright.config`, `cypress.config`, Selenium/Grid config. | Browser automation capacity and CI placement. | Config exists even if tests are disabled or flaky. |
| Product event names | analytics, telemetry, audit logs, domain events. | Important business state transitions. | Tracking can be stale or sampled. |

## Common Commands And Patterns

| Goal | Starting Commands |
| --- | --- |
| Find user-facing tests | `rg "getByRole|getByLabelText|getByText|cy\\.|page\\.|Scenario|Given|When|Then" test tests e2e src` |
| Find routes and workflows | `rg "router|route|Controller|Handler|screen|page|endpoint|mutation|command" src app` |
| Find permissions and roles | `rg "role|permission|authorize|policy|can\\(|forbidden|unauthorized|admin" src test tests` |
| Find incidents/regressions in repo | `rg "regression|incident|bug|support|postmortem|TODO.*test|FIXME.*test" .` |
| Check browser runner setup | `rg --files | rg "playwright|cypress|selenium|webdriver|appium"` |

## Evidence Rules

- A behavior candidate should include actor, trigger, expected outcome, and risk.
- Prefer evidence from public interfaces and existing product language over private function names.
- Use production/support signals only as prioritization evidence; do not copy sensitive data into fixtures.
- A browser test should justify why a lower level cannot protect the same user risk.

## Source Anchors

- Playwright, [locators and best practices](https://playwright.dev/docs/best-practices)
- Cypress, [test isolation and independent tests](https://docs.cypress.io/app/core-concepts/writing-and-organizing-tests)
- Testing Library, [queries](https://testing-library.com/docs/queries/about/)
- Cucumber, [Gherkin reference](https://cucumber.io/docs/gherkin/reference)
