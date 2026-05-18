# Regression Test Selection / Test Impact Analysis

## Strategy Map

### Purpose
Select and validate the existing tests most likely to be affected by a diff while preserving safe fallback to broader regression coverage.

### Reliability Goal
Reduce slow feedback without silently missing regressions caused by dependency, configuration, shared-code, or behavioral impact outside the changed files.

### When This Strategy Applies
- Full suites are too slow for every local or PR run.
- The repository has reliable dependency graphs, package boundaries, coverage maps, ownership tags, or affected-test tooling.
- A change is localized enough to select focused tests but still needs regression confidence.
- CI has periodic full-suite fallback.

### When This Strategy Does Not Apply
- There are few tests and full validation is cheap.
- Dependency metadata is missing or unreliable and no fallback exists.
- The change touches broad shared infrastructure, build config, test framework, auth, serialization, or global behavior without wider validation.
- New features lack test history and need new focused tests first.

### Signals To Inspect First
- Changed files, public APIs, import/dependency graph, generated clients, build scripts, package manifests, test ownership tags, coverage maps, affected-project scripts, previous failures, CI path filters, and broad-impact files.

### Test Design Principles
- RTS/TIA accelerates feedback; it does not design good tests by itself.
- Selection must be conservative when impact is uncertain.
- New, changed, previously failing, and flaky tests often deserve inclusion even if dependency mapping is narrow.
- Path filters are coarse and can miss semantic dependencies.
- Periodic full runs are part of safe selection.

### Good Test Characteristics
- Selected tests map clearly to changed behavior, dependents, contracts, and critical workflows.
- Broad-impact files trigger fallback suites.
- Tool output is inspectable and explainable.
- Full-suite or larger validation runs periodically or before release.
- Agents add missing focused tests instead of only selecting existing ones.

### Poor Test Characteristics
- Running only tests in the same directory as changed files for shared-library changes.
- Skipping auth, serialization, or persistence tests because path filters do not include them.
- Treating impacted-test tooling as infallible.
- No fallback for unsupported language, dynamic imports, generated code, or config changes.
- Reporting success after running only a new test when wider impact is obvious.

### Execution Pattern
- Understand the diff and intended behavior.
- Inspect dependency and test-selection conventions.
- Run focused tests for directly changed behavior.
- Include dependent packages, contracts, and critical workflows affected by public API changes.
- Apply broad fallback for shared infrastructure, config, or uncertain impact.
- Add or update regression tests for new behavior.
- Report selected commands and residual risk.

### Examples
- Weak: changed shared billing library, run only `billing.test.ts`. Stronger: run billing unit tests, dependent package tests, checkout pricing integration tests, and contract tests for exposed pricing API.
- Weak: path filter skips tests after schema change. Stronger: include migration, serialization, API, and consumer tests that depend on the schema.

### Validation
- Run selected commands and verify they exercise the changed behavior.
- For selection tooling, inspect or log why tests were selected.
- Run fallback suites when broad files, unsupported changes, or dependency uncertainty appear.
- Periodically compare selected runs against full-suite results.
- Do not claim full regression confidence from narrow selection.

### Failure Modes
- Dependency graphs omit dynamic or generated edges.
- Path filters create false confidence.
- Flaky tests distort historical selection.
- Selectors skip newly added tests or previously failing tests.
- Full-suite fallback disappears because selected runs are faster.

## Overview

Regression Test Selection, also called Test Impact Analysis, runs the tests most likely to be affected by a diff instead of always running the full regression suite. Selection can come from dependency graphs, build targets, import graphs, coverage maps, history, changed-package analysis, ownership metadata, or CI path filters.

Use it as a feedback accelerator, not as proof that the whole product works. Good RTS/TIA still needs focused regression tests, contract/integration checks for public boundaries, smoke or release validation, and periodic full-suite fallback.

## Best Fit

Use RTS/TIA when three conditions are true:

| Condition | What To Look For |
| --- | --- |
| Full validation is expensive | Full suites take long enough that selected feedback materially helps. |
| Impact is explainable | Build files, imports, package manifests, coverage maps, or target graphs are current. |
| Fallback exists | CI still runs broader suites on merge, nightly, release, or force-full triggers. |

Good repository shapes include Bazel, Pants, Nx, Gradle, Maven, Cargo workspaces, Go modules, pnpm/yarn/npm workspaces, and other systems with explicit package or target boundaries.

## Inspection Order

1. Find the build system and test runner: package/workspace manifests, Bazel/Pants/Nx/Gradle/Maven/Cargo/Go configs, pytest/tox configs, and CI workflows.
2. Search existing scripts for `affected`, `changed`, `related`, `impact`, `testmon`, `predictive`, `selected`, `rdeps`, `onlyChanged`, or `findRelatedTests`.
3. Read CI conventions before adding new commands: PR selected tests, merge full tests, nightly/release suites, smoke jobs, and tags/markers.
4. Classify the diff before selecting tests: local source, shared library, public API/schema, config/build, new behavior, flaky/concurrency/global-state.
5. Treat “no tests selected” for production code as a finding: add a focused test, fix metadata, or run a broader suite.

## Candidate Matrix

| Change Area | Select These Tests | Add Or Check |
| --- | --- | --- |
| Pure functions/domain utilities | Direct importers and dependent modules. | Boundary, invariant, and changed business-rule cases. |
| Packages/modules | Changed package plus reverse dependents. | Public API, serialization, validation, compatibility. |
| Services/API endpoints | Route/service tests, consumer contracts, request-path integration tests. | Status, schema, authz, idempotency, persistence effects. |
| UI components/screens | Component tests and importing page tests. | Visible behavior, accessibility state, user interaction, emitted events. |
| Permissions/validation | Rule-matrix tests. | Allowed, denied, boundary, role, feature-flag cases. |
| State machines/workflows | Transition and guard tests. | Valid/rejected transitions, cancellation, retries, terminal states. |
| Database/migrations | Repository, query, model, migration, integration tests. | Constraints, defaults, rollback when supported, existing-data compatibility. |
| Adapters/integrations | Adapter and contract tests with fakes or recorded fixtures. | Payload mapping, auth, retry, timeout, error translation. |
| Concurrency/async | Focused tests plus race/stress checks when available. | Ordering guarantees, idempotency, cancellation, backpressure. |

## Force Broader Validation

Do not rely on narrow selection when the diff touches:

- Root build/test config, lockfiles, dependency versions, compilers, CI, generated-code configuration, or test framework setup.
- Global state, bootstrapping, environment loading, routing, auth middleware, feature flags, shared fixtures, schemas, migrations, or global assets.
- Dynamic loading, reflection, plugin registries, runtime imports, filesystem globbing, or service locators.
- Safety-critical, security-critical, payment, privacy, data-destructive, compliance, migration, or release-critical behavior.
- Production code where the selector returns zero tests.

## Test Placement Rules

| Situation | Better Placement |
| --- | --- |
| One clear bug in pure logic | Add one focused regression near the domain module and run related tests. |
| Behavior is a matrix | Add multiple cases for roles, states, locales, currencies, feature flags, or input classes. |
| Public API/schema changes | Add or update contract and integration tests, then run selected dependents. |
| UI interaction changes | Prefer component/page tests; keep E2E for critical journey smoke only. |
| External integration mapping changes | Use adapter tests, fake servers, recorded fixtures, and contract checks. |
| Shared module refactor | Run selected tests plus reverse dependents; broaden when public APIs moved. |

## Limitations And Mitigations

| Risk | Mitigation |
| --- | --- |
| Dependency graph misses dynamic/config/generated edges. | Define force-full patterns and keep dependency metadata current. |
| Coverage/history data is stale or biased. | Run periodic full suites and compare selected runs against full runs. |
| False negatives skip a relevant test. | Prefer conservative over-selection when impact is uncertain. |
| Flaky tests corrupt confidence. | Quarantine or label flakes; preserve first-attempt/retry signal. |
| Selector is opaque. | Record changed files, selected tests, skipped tests, selector version, and fallback reason. |
| Selection costs too much. | Use coarser package/project selection when precise test-level analysis is slower than useful. |

## Determinism Rules

- Freeze time, seed randomness, isolate temp directories, reset databases/global state, and avoid order dependence.
- Mock external services, time, randomness, email/SMS/payment providers, and slow infrastructure at meaningful boundaries.
- Do not mock the function under test or every internal collaborator; selected tests must still exercise real behavior.
- Name tests by behavior and regression risk, not by implementation unit alone.

## Signals

| Strong Signal | Use With Judgment | Avoid As Sole Signal |
| --- | --- | --- |
| Existing affected/changed/related/testmon/predictive/impact tooling. | Mirrored source/test paths without dependency awareness. | Filename guessing only. |
| Localized diff in package, module, endpoint, component, or domain service. | Shared package with finite, discoverable reverse dependents. | Broad config, schema, lockfile, or bootstrap changes. |
| Accurate build graph or package metadata. | Partial coverage data that may be stale. | Dynamic dependencies the selector cannot model. |
| Selector can list selected tests before running them. | Tags such as unit, integration, smoke, or contract without direct impact mapping. | Silent zero-test outcomes for production code. |

## Examples

```sh
npx jest --findRelatedTests src/pricing/discount.ts --coverage
```

Good for a localized TypeScript utility when imports are mostly static. Add a focused regression test such as "does not stack loyalty discount on sale items." This does not replace checkout UI, tax, payment, or full order validation.

```sh
nx affected -t test --base="$BASE_SHA" --head="$HEAD_SHA"
nx affected -t build --base="$BASE_SHA" --head="$HEAD_SHA"
```

Good for monorepos where project boundaries and reverse dependencies are maintained. Shared libraries can fan out broadly; that is a feature of conservative selection.

Avoid brittle filename mapping:

```sh
git diff --name-only origin/main...HEAD |
  sed 's#^src/#tests/#' |
  sed 's#\.ts$#.test.ts#'
```

This misses importers, reverse dependents, shared modules, config, generated files, and tests with different names.

## Packages And Libraries

| Ecosystem | Useful Tools |
| --- | --- |
| JavaScript/TypeScript | Jest, Vitest, Nx affected, Turborepo task skipping, Playwright filters for tagged E2E subsets. |
| Python | pytest node IDs/-k/-m, pytest-testmon, Pants changed/dependent analysis. |
| JVM | Gradle --tests, Maven/Gradle filters, Bazel/Pants targets, Develocity PTS, Ekstazi, Infinitest. |
| Go | Package-level go test, changed-package scripts, Bazel/Pants in monorepos. |
| Rust | Cargo package/test filters, cargo-nextest, changed-crate tools after maintenance review. |
| Ruby | RSpec path/line/tag filters, --only-failures, --bisect, Knapsack Pro for splitting. |
| .NET | Azure DevOps TIA/VSTest where supported, dotnet test --filter, NCrunch. |
| Mobile | Android Gradle plus Develocity PTS for supported unit tests, Xcode -only-testing/-skip-testing, maintained affected-module Gradle plugins. |
| Backend/API | Bazel, Pants, Pact or other contract-test frameworks for selected boundary checks. |
| CI/Infra | GitHub/GitLab/Azure/Buildkite path filters, build caches, remote execution, Launchable, Datadog TIA. |

## Source Anchors

- Fowler-style TIA frames the problem as mapping changed code to tests that exercise or depend on it.
- Azure DevOps TIA and similar systems include fallback behavior because impact maps are incomplete.
- Bazel/Pants/Nx-style graph selection is strongest when dependencies are declared and test targets are explicit.
- Historical and predictive selection must account for flakiness, newly added tests, and unsupported change types.

## Quality Bar

- Selection is based on dependency, coverage, target, package, or history signals, not only filename guesses.
- Each selected layer has an explainable relationship to the diff.
- New behavior or bug fixes get a focused test that would fail before the fix.
- Broad-impact files trigger fallback behavior.
- Production-code changes do not silently pass with zero selected tests.
- Selected runs are backed by periodic or risk-based full runs.
- Tests assert user-visible or contract-relevant behavior, not implementation trivia.
