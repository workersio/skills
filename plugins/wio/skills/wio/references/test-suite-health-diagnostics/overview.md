# Test Suite Health Diagnostics

## Strategy Map

### Purpose
Audit an existing suite for whether it gives trustworthy, timely, diagnosable signal about meaningful software risk.

### Reliability Goal
Reduce false confidence from green but weak CI, noisy failures, flaky tests, slow feedback, unowned quarantines, and coverage metrics that do not correlate with escaped defects.

### When This Strategy Applies
- A project has tests but low trust in releases or frequent reruns.
- CI is slow, flaky, ignored, or hard to diagnose.
- Coverage exists but incidents still escape in critical behavior.
- A team needs to decide which tests to rewrite, delete, move lower, or supplement with monitoring.

### When This Strategy Does Not Apply
- The task is simply to add a focused test for a known behavior and suite health is not in question.
- There is no access to test files, CI configuration, or execution history and conclusions would be speculative.
- The diagnostic would be used as a scorecard detached from risk and ownership.

### Signals To Inspect First
- Test files, framework configuration, CI jobs, retry settings, quarantine markers, skip/xfail usage, coverage reports, mutation or flake reports, incident regressions, runtime trends, critical workflows, and ownership metadata.

### Test Design Principles
- Separate test presence, coverage, test effectiveness, and release confidence.
- Prefer signal density over test count.
- A good suite catches important regressions early with failures that identify the likely behavior and owner.
- Metrics are useful only when they change engineering action.
- Static smells are hypotheses until confirmed by execution history or targeted runs.

### Good Test Characteristics
- Critical workflows and failure modes map to explicit controls.
- Fast checks run in the right feedback loop; expensive checks run with clear purpose.
- Failures are classified, owned, and supported by useful logs/artifacts.
- Skipped, quarantined, flaky, and retried tests remain visible.
- Escaped defects lead to durable tests, monitors, canaries, or documented risk acceptance.

### Poor Test Characteristics
- Raw line coverage, test count, or final pass rate is treated as quality.
- Reruns are normal and pass-after-retry is reported as ordinary green.
- Quarantine has no owner, reason, expiry, or replacement control.
- Broad snapshots, implementation-detail assertions, and mock-only tests dominate.
- Red jobs are ignored or made non-blocking without risk review.

### Execution Pattern
- Inventory suite shape, commands, CI gates, and test artifacts.
- Classify tests by layer and protected risk.
- Inspect bad-test smells and missing critical paths.
- Review flake, runtime, retry, skip, quarantine, and failure ownership signals.
- Grade reliability, speed, signal, diagnostics, maintainability, risk coverage, and monitoring.
- Recommend concrete actions: fix, rewrite, delete, move lower, add missing test, add monitor, or accept risk.

### Examples
- Weak: “coverage is 90%, so tests are healthy.” Stronger: “changed authorization code has no denied-case tests, three quarantined API tests are unowned, and checkout E2E retries hide first-attempt failures.”
- Weak: deleting a flaky test to make CI green. Stronger: quarantine with owner and expiry, keep non-blocking execution, add artifacts, and fix the root cause or replace with a deterministic lower-level test.

### Validation
- Run cheap targeted checks where available, or state that the audit is static-only.
- Verify links between claimed risks and actual tests or monitors.
- Check that proposed deletions do not remove the only protection for a critical behavior.
- Confirm any flake claim with same-commit pass/fail evidence when possible.
- Review edited reference content for duplicated, vague, or metric-only advice.

### Failure Modes
- Audits can become subjective if findings lack evidence.
- Teams may optimize the rubric instead of reliability.
- Coverage and pass-rate dashboards hide weak assertions and retries.
- Static inspection can misclassify legitimate mocks, snapshots, or sleeps without context.
- Overly broad remediation plans fail because no owner or command is attached.

## Overview

A healthy test suite is a risk-control system, not a pile of test files. The useful question is whether CI gives timely, trustworthy, diagnosable signal when meaningful product, reliability, security, data, or release risk is introduced.

| Concept | Means | Common Failure |
| --- | --- | --- |
| Test presence | Test files, jobs, and reports exist. | Tests exist but do not protect important behavior. |
| Coverage | Production code was executed. | Covered code has weak assertions or no useful oracle. |
| Effectiveness | Tests detect real faults with low noise. | High count and coverage, weak fault detection. |
| Release confidence | CI, rollout controls, monitoring, and incidents are trusted together. | Green CI hides untested critical risk. |

## Best Fit

Use this diagnostic for suite audits, CI stabilization, release-readiness reviews, incident follow-up, platform migrations, brittle E2E reduction, or any team with tests but low trust in releases.

Do not use it as a punishment scorecard or a replacement for product-specific risk analysis. Static inspection can identify smells, but flakiness, value, and uselessness need execution history and failure context when available.

## Smell Matrix

| Smell | Why It Hurts | Better Direction |
| --- | --- | --- |
| Flaky tests | Engineers rerun instead of diagnose. | Control time, randomness, network, state, and concurrency. |
| Slow low-value tests | Feedback arrives too late and gets skipped. | Move broad checks later or replace with narrower tests. |
| Implementation-detail assertions | Safe refactors fail. | Assert observable behavior, contracts, side effects, or invariants. |
| Obscure fixtures/helpers | Failures are hard to diagnose. | Use clear names, local setup, and arrange-act-assert structure. |
| Duplicate production logic | Same bug can exist in test and code. | Use independent examples, properties, golden data, or models. |
| Excessive mocking | Tests mock interactions instead of behavior. | Use real cheap dependencies, fakes, and contract tests at boundaries. |
| Weak assertions | Coverage creates false confidence. | Strengthen behavior assertions; use mutation testing selectively. |
| Broad tests with poor localization | One failure implicates many layers. | Keep critical smoke journeys; push detail lower. |
| Timing/order/shared-state coupling | Results become nondeterministic. | Use fake clocks, explicit waits, isolated fixtures, unique data. |
| Noisy snapshots | Review becomes approval ritual. | Prefer focused semantic assertions or small reviewed snapshots. |
| Happy path only | Misses boundary, abuse, migration, recovery, and failure modes. | Add risk-based negative and failure-mode tests. |

## Suite Problems

| Problem | Diagnostic Signal | Action |
| --- | --- | --- |
| Ice-cream-cone distribution | Many UI/E2E tests, few lower-level checks. | Rebalance toward unit, component, integration, and contract tests. |
| Missing boundary tests | Unit tests pass but APIs/events/schemas break late. | Add contract and targeted integration tests. |
| High runtime | Developers avoid full suites or lose context. | Split local, PR, post-merge, nightly, release, and canary loops. |
| High flake or retry rate | Reruns are normal. | Track flake by test, owner, job, environment, and signature. |
| Ignored failures | Red or non-blocking jobs persist. | Treat persistent red as production-risk signal. |
| Quarantine without return | Quarantine count and age grow. | Require owner, ticket, protected risk, reason, expiry, and escalation. |
| Duplicated coverage | Same behavior tested at many layers. | Keep narrowest reliable test unless broader one protects unique integration risk. |
| Poor incident regression | Escaped defects do not create durable controls. | Add regression test, monitor, canary, or explicit risk acceptance. |

## Metrics

| Useful Metric | Reveals | Should Trigger |
| --- | --- | --- |
| First-attempt pass vs final pass | Hidden retries and instability. | Separate flake signal from green status. |
| Flake/retry rate | Same-code inconsistency and wasted CI. | Fix, rewrite, or quarantine with owner and expiry. |
| Runtime trend and p95/p99 slow tests | Feedback-loop decay. | Split stages, parallelize, remove duplication, or move tests lower. |
| Quarantine/skipped/disabled age | Silent loss of protection. | Review by owner, protected risk, and expiry. |
| Escaped defects by missed control | Missing or weak defenses. | Add targeted tests, monitors, canaries, or rollout gates. |
| Mutation score, selectively | Weak assertions in important logic. | Improve tests around meaningful survivors. |
| Critical workflow/control map | Whether important risks have protection. | Add or document missing controls. |

Misleading alone: raw line coverage, test count, final pass rate, number of E2E tests, assertion count, and dashboard count. Use them only as prompts for investigation.

## Grading Rubric

Score each dimension from 0 to 4:

| Dimension | Strong Signal |
| --- | --- |
| Reliability | Deterministic, isolated tests with rare retries. |
| Speed | Feedback arrives in the loop it serves. |
| Signal | Failures usually indicate real product, contract, security, data, or reliability risk. |
| Diagnostics | Failures identify likely cause, owner, logs, and reproduction path. |
| Maintainability | Tests are readable, owned, reviewed, and pruned. |
| Risk coverage | Critical workflows and failure modes map to tests, monitors, canaries, or manual controls. |
| Monitoring | Flake, retry, runtime, quarantine, skipped tests, ownership, and escaped defects are measured and acted on. |

| Grade | What The Team Observes |
| --- | --- |
| A | CI is trusted; red builds are rare and meaningful; critical risks have explicit controls. |
| B | CI is generally reliable; known weak areas have owners and budgets. |
| C | CI is useful but noisy; reruns, weak ownership, or incomplete monitoring remain. |
| D | CI is distrusted; slow, flaky, or quarantined tests linger. |
| F | Tests are ceremonial; red builds are ignored or disabled; production is the main detector. |

Hard caps: common merge-gate reruns or unowned quarantines cap at C; ignored red builds, no CI history, no ownership, or repeated missed critical risks cap at D; disabling tests to ship without risk acceptance is F.

## Inspection Checklist

- Classify tests by layer, dependency scope, owner, and protected risk.
- Search for sleeps, wall-clock time, randomness, shared accounts, live services, global fixtures, and order dependence.
- Review assertions, snapshots, mocks, names, fixtures, and failure messages.
- Review 30-90 days of CI history if available; separate first-attempt failure from final pass.
- Identify top failure signatures, rising runtime, retry rate, flake rate, non-blocking failures, and quarantine age.
- For escaped defects, ask whether a test or monitor existed, ran, passed incorrectly, or was ignored.
- Verify dashboards have owners, thresholds, review cadence, and escalation.

## Examples

| Finding | Action |
| --- | --- |
| Checkout has coverage but no duplicate-capture, rollback, or provider-idempotency tests. | Add idempotency unit tests, adapter integration tests, provider contracts, and one checkout smoke. |
| Frontend has hundreds of broad snapshots and frequent auto-updates. | Replace with focused assertions for accessible behavior, permissions, critical text, and state transitions. |
| CI passes after retries while first-attempt failures rise. | Track retry rate, identify top flaky tests, quarantine only with owner/expiry, and fix timing/shared-state causes. |

## Packages And Libraries

Supporting evidence can come from CI test analytics, flaky-test dashboards, coverage reports, mutation testing, test runtime reports, incident trackers, and postmortems. The diagnostic itself is a review framework: tools provide evidence, but the output must be concrete actions.

## References

Useful source traditions include Google Testing Blog material on flaky tests, coverage, test sizes, and CI; Microsoft flaky-test management work; Martin Fowler and Thoughtworks on the test pyramid; Gerard Meszaros on xUnit test smells; empirical research on coverage versus effectiveness; Google-scale mutation-testing research; NIST SSDF; and incident reports from Cloudflare, GitLab, and CrowdStrike.
