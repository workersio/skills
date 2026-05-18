# Flaky Test Detection and Management

## Strategy Map

### Purpose
Detect, classify, debug, and reduce nondeterministic test outcomes without normalizing unreliable CI.

### Reliability Goal
Protect the delivery signal by distinguishing product regressions from unreliable tests and by fixing root causes such as time, concurrency, shared state, external services, or infrastructure variance.

### When This Strategy Applies
- A test has both pass and fail outcomes on the same commit.
- Failures disappear after rerun, isolation, changed order, or changed parallelism.
- The code or tests depend on time, randomness, async work, browsers, mobile devices, threads, shared fixtures, external services, or CI resources.
- CI uses retries, quarantine, sharding, or merge gates where hidden flakiness can distort release decisions.

### When This Strategy Does Not Apply
- A failure is deterministic and explained by the diff.
- The only proposed action is increasing retries.
- A test is obsolete and should be rewritten or removed after risk review.
- The task is a small deterministic behavior change with no flake evidence.

### Signals To Inspect First
- Same-commit pass/fail history, retry metadata, seed values, test order, parallelism, logs, screenshots, traces, fixture cleanup, fixed sleeps, wall-clock reads, unseeded randomness, shared state, external network calls, CI image changes, browser/device versions, and resource limits.

### Test Design Principles
- Retries are a detection and productivity tool only when retry outcomes remain visible.
- Quarantine reduces gate damage but must keep execution, ownership, evidence, and a return path.
- Bounded condition waiting is usually better than fixed sleeps.
- Some flaky-test fixes belong in production code because nondeterministic tests can expose real races or state leaks.
- Repetition samples behavior; it cannot prove absence of low-probability flakes.

### Good Test Characteristics
- Tests wait for observable conditions, not arbitrary time.
- State is isolated with unique data, transactions, temporary resources, or clean teardown.
- Random and generated tests record seeds and shrink failures.
- Retry classifications preserve first-attempt failures.
- Failure artifacts are sufficient to reproduce or narrow the cause.

### Poor Test Characteristics
- Global retries make red CI green without recording flake status.
- Permanent skips or quarantines remove coverage silently.
- Tests assert exact timing, unordered output order, animation timing, or log wording when not required.
- Live third-party services are used in ordinary unit tests.
- Background work, ports, files, users, or databases leak across tests.

### Execution Pattern
- Confirm whether the failure is deterministic or same-commit nondeterministic.
- Collect artifacts, environment metadata, order, seed, and retry attempts.
- Reproduce with targeted repeats, isolation, order shuffling, and parallelism changes.
- Identify root cause category: test bug, production race, shared state, async wait, environment, dependency, or resource limit.
- Fix the root cause or quarantine with owner and expiry.
- Run repeated targeted validation and the smallest impacted suite.
- Report whether confidence is sampled and what flake risk remains.

### Examples
- Weak: `await sleep(5000)` after clicking submit. Stronger: wait until the order row exists or the success region is visible, with a bounded timeout and useful failure artifact.
- Weak: enabling retries on every unit test. Stronger: classify pass-after-fail in CI, record the attempt, and fix shared state or timing in the specific flaky test.

### Validation
- Run the suspected test repeatedly under the same commit.
- Run isolated and in-suite forms when order dependency is suspected.
- Vary seed, order, and parallelism only as far as the test framework supports deterministically.
- Confirm retry results remain visible in reports.
- For fixes, compare failure rate before and after using enough repetitions to be meaningful, while acknowledging sampling limits.

### Failure Modes
- Retry suppression hides real defects.
- Quarantines become permanent and reduce gate coverage.
- Reproduction loops are too broad and waste CI.
- Flake fixes weaken assertions instead of controlling nondeterminism.
- Tests pass locally but still depend on CI-only resources or timing.

## Overview

Flaky test management protects the trustworthiness of CI by identifying tests that pass and fail under the same code revision, preserving evidence, and driving root-cause fixes. It is a control layer around unit, integration, browser, mobile, and system tests; it is not a reason to normalize unreliable gates.

Retries and quarantine can reduce immediate disruption, but only if first-attempt failures, owners, artifacts, and expiry are visible. A pass-after-retry is still a flake signal.

## Best Fit

Use this strategy when CI gates merges or releases, retries are common, failures vanish after rerun, or tests depend on time, randomness, async work, concurrency, browsers, mobile devices, external services, shared fixtures, or constrained CI resources.

It is highest value in large suites, monorepos, browser/mobile automation, distributed systems, queues, scheduled jobs, event streams, caches, database-heavy tests, and teams where rerun culture is eroding trust.

## Candidate Matrix

| Candidate | What To Stabilize Or Prove |
| --- | --- |
| Known intermittent test | Same-commit pass/fail evidence, artifacts, owner, root-cause category. |
| Async/eventual behavior | Final observable state, emitted event, database row, API response, or UI condition; no fixed sleeps. |
| Browser/frontend flow | Stable locators, auto-waiting assertions, navigation/readiness conditions, screenshots/traces/videos. |
| Mobile instrumented test | Framework synchronization, device/emulator state, background work, no arbitrary sleeps. |
| Real dependency integration | Readiness checks, isolated resources, deterministic fakes where appropriate, cleanup after failure. |
| Database/migration test | Transaction/schema/data isolation, deterministic setup/teardown, unique data, order independence. |
| Concurrent code | Invariants under locks, threads, goroutines, task schedulers, pools, caches, and shared state; not exact timing. |
| Time/random/generated data | Fake clocks, seeded randomness, recorded seed, shrinkable generated cases. |
| CI/test-infra change | Retry visibility, quarantine behavior, shard/parallelism impact, report parsing, merge-gate semantics. |

## Root-Cause Map

| Symptom | Likely Cause | Better Fix |
| --- | --- | --- |
| Passes alone, fails in suite | Shared state, order dependency, leaked fixture. | Isolate data, clean teardown, shuffle/order tests to reproduce. |
| Fails only under parallelism | Races, fixed ports, shared temp paths, unsafe globals. | Unique resources, locking, per-worker fixtures, race/stress checks. |
| UI element missing intermittently | Async rendering, unstable selector, animation, network timing. | Auto-waiting assertions, stable locators, readiness conditions, traces. |
| Same seed fails, another passes | Randomness or generated data bug. | Record seed, shrink case, add deterministic regression. |
| CI-only failures | Resource pressure, image/version drift, dependency readiness. | Capture environment metadata, limits, versions, and dependency health. |
| Pass-after-retry hidden as green | Retry suppression. | Report first attempt, classify flaky, keep owner and artifact links. |

## Signals

| Strong Signal | Weak Signal | Avoid Treating As Proof |
| --- | --- | --- |
| Same test has pass and fail outcomes on the same commit. | A single suspicious failure with no history. | “It passed after rerun.” |
| Test passes alone but fails in suite or under parallelism. | Fixed sleeps, wall-clock reads, or shared fixtures in nearby tests. | Local-only success for CI-only flake. |
| Retry metadata, seed, order, screenshot, trace, or logs identify nondeterminism. | Recent CI image/browser/device change. | Global retry success rate without per-test first-attempt data. |
| Browser/mobile tests fail on readiness, navigation, or device state. | External service call in ordinary tests. | Permanent skip or quarantine with no owner. |

## Management Rules

- Prefer root-cause fixes over weaker assertions.
- Use quarantine only with owner, reason, evidence, expiry, and continued non-blocking execution.
- Keep retries visible; never collapse pass-after-fail into ordinary green.
- Reproduce with targeted repeats, isolation, order shuffle, parallelism changes, and seed replay.
- Validate fixes with repeated targeted runs plus the smallest impacted suite.
- State that repeated passes are sampled confidence, not proof of stability.

## Limits And Tradeoffs

| Constraint | Practical Response |
| --- | --- |
| Repetition cannot prove absence of flakes. | Report sample size, environment, order, seed, timing, and remaining risk. |
| Broad rerun loops waste CI. | Repeat failed or suspected tests first; broaden only for shared state or release risk. |
| Quarantine reduces gate coverage. | Keep non-blocking execution and define a return path before quarantine is accepted. |
| Root cause is ambiguous. | Add observability before speculative fixes: attempt number, seed, order, worker, environment, dependency versions. |
| Some flakes expose production races. | Investigate whether the fix belongs in product code, not only the test. |

## Examples

| Weak | Stronger |
| --- | --- |
| Sleep for five seconds after submit. | Wait for an observable order row or success region with bounded timeout and artifact. |
| Retry every unit test globally. | Classify pass-after-fail, preserve retry attempts, and fix the specific shared-state or timing cause. |
| Skip a flaky checkout E2E forever. | Quarantine with owner/expiry, keep it running non-blocking, add traces, and replace brittle checks lower when possible. |
| Assert exact timestamp, animation timing, or unordered output order. | Use controlled clocks, tolerances, stable ordering, or user-visible outcomes. |
| Use a real mailbox/payment sandbox in ordinary tests. | Use a fake boundary or contract test; reserve live checks for scoped integration jobs. |

## Packages And Libraries

| Area | Useful Tools |
| --- | --- |
| Python | pytest reruns, pytest-randomly, pytest-xdist, Hypothesis seed replay, flaky/flakefinder-style plugins. |
| JavaScript/TypeScript | Playwright retries/traces, Cypress retries/artifacts, Jest retry helpers, Vitest repeat/sequence controls. |
| JVM | JUnit retry extensions, Gradle test retry plugin, Maven Surefire reruns, stress/repeat rules. |
| Go/Rust | Go race detector and repeated test runs; cargo-nextest retries and reporting. |
| CI Analytics | Datadog CI Visibility, Develocity test analytics, Buildkite/GitHub/GitLab artifacts, custom JUnit XML analysis. |

## Source Anchors

- Google and Microsoft engineering material both treat same-code inconsistent outcomes as a CI trust problem, not a normal test result.
- Playwright, Bazel, Develocity, Datadog, and Microsoft-style systems preserve retry/flaky status as distinct signal.
- pytest and framework docs repeatedly call out overly strict timing, floating-point, ordering, and external dependency assertions as flake sources.
- Flaky-test research identifies async waits, concurrency, order dependency, isolation problems, remote services, and resource leaks as common causes.

## Quality Bar

- Flake claims cite same-commit pass/fail evidence when possible.
- First-attempt and retry outcomes remain visible.
- Fixes control nondeterminism rather than deleting meaningful assertions.
- Quarantined tests keep ownership, execution, artifacts, and a return path.
- Residual risk names sample size, commands run, and commands not run.
