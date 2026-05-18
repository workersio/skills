# Behavior To Test Map Tools

Use these signals to discover test candidates in an unfamiliar repo. The output should be a ranked map, not a dump of every uncovered file.

## Tool Categories

| Category | Evidence It Provides | Caveats |
| --- | --- | --- |
| Customer/business discovery | README, docs, UI copy, pricing, examples, onboarding, support/incident notes, analytics names. | Repo evidence may reveal product intent but not actual market priority. |
| Surface discovery | Routes, public APIs, CLI commands, jobs, events, UI screens. | Public surface does not equal high risk. |
| Change and ownership history | Git diff, recent commits, issue links, TODOs, incidents. | Recent churn can be noisy without behavior context. |
| Existing test inventory | Test files, names, markers, snapshots, skipped/quarantined tests. | Presence of tests does not prove useful assertions. |
| Runtime/coverage reports | Touched code, slow tests, missing branches, mutation survivors. | Metrics are prompts, not proof of value. |
| Dependency/boundary inspection | DB, queue, network, auth, filesystem, schema, external provider usage. | Boundary names can be misleading. |

## Repo Signals To Inspect

| Signal | Common Patterns | Evidence | False Positives |
| --- | --- | --- | --- |
| Customer profile/value | `README`, `docs`, `examples`, `pricing`, `plans`, `checkout`, `onboarding`, UI copy. | What the product sells, who uses it, and which outcomes matter. | Marketing/demo copy can be stale. |
| Jobs/pains/gains | `problem`, `workflow`, `benefit`, `pain`, `goal`, `use case`, `customer`, `user`. | Customer job-to-be-done and promised value. | Generic docs language may not reflect real usage. |
| Entry points | `routes`, `controllers`, `handlers`, `commands`, `jobs`, `pages`, `screens`. | User/API behaviors worth mapping. | Generated or internal-only entry points. |
| Domain rules | `policy`, `permission`, `validator`, `calculator`, `state`, `workflow`. | Logic with clear oracles. | Names can be generic or unused. |
| Boundaries | `Client`, `Gateway`, `Repository`, `Adapter`, `Producer`, `Consumer`. | Integration, contract, or double decisions. | Thin wrappers may not warrant direct tests. |
| Existing tests | Similar filenames, describe names, regression labels, snapshots. | Coverage gaps and local style. | Tests may be weak or stale. |
| Risk traces | `bug`, `regression`, `incident`, `security`, `tenant`, `payment`, `auth`. | High-impact candidate hints. | Comments may be historical. |

## Common Commands And Patterns

| Goal | Starting Commands |
| --- | --- |
| Infer product/customer context | `rg "customer|user|pricing|plan|checkout|onboard|benefit|workflow|use case|problem|goal|pain|trust|secure|reliable" README* docs src app` |
| List tests | `rg --files | rg "(test|spec|__tests__|e2e|integration|contract)"` |
| Find public surfaces | `rg "route|router|Controller|Handler|Command|Job|Event|Mutation|Query|screen|page" src app` |
| Find risky behavior | `rg "auth|permission|policy|tenant|payment|invoice|delete|refund|migration|retry|timeout|idempot" src test tests` |
| Compare tests to source | `rg --files src app lib | sed 's#\\.[^.]*$##'` then search matching test names with `rg`. |
| Inspect current change | `git diff --stat && git diff --name-only` |
| Find weak or missing assertions | `rg "TODO.*test|FIXME.*test|not\\.toThrow|toBeTruthy|assertTrue|snapshot" test tests src` |

## Candidate Evidence Template

| Field | Required Evidence |
| --- | --- |
| Part to test | Public user/API/domain behavior, not private method name. |
| Customer/business value | Customer job, pain, gain, product promise, revenue path, trust path, support cost, compliance, or reliability outcome. |
| ROI | Impact, likelihood, confidence gap, and implementation cost. |
| Gap | Missing test, weak assertion, wrong level, flaky/disabled coverage, or untested boundary. |
| Strategy | Lowest level that preserves the fault mechanism; oracle; data/fixture; double or real dependency; feedback loop. |
| Command | Existing local or CI command to run it. |

## Evidence Rules

- Rank candidates with explicit confidence: confirmed by tests/code/docs/product evidence, inferred from code shape, or speculative.
- If business context is inferred, say so; do not overstate ROI as fact.
- Do not recommend a test whose expected behavior cannot be stated.
- Prefer candidates that can be implemented with existing test patterns and commands.
- Flag missing tooling as a separate prerequisite, not as the test candidate itself.

## Source Anchors

- Google Testing Blog, [Code Coverage Best Practices](https://testing.googleblog.com/2020/08/code-coverage-best-practices.html)
- Google Testing Blog, [Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html)
- GitLab, [JUnit report examples by tool](https://docs.gitlab.com/ci/testing/unit_test_report_examples/)
- Playwright, [best practices](https://playwright.dev/docs/best-practices)
- Harvard Business School Working Knowledge, [What Customers Want from Your Products](https://www.library.hbs.edu/working-knowledge/what-customers-want-from-your-products)
