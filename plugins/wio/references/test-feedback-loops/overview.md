# Test Feedback Loops

## Purpose

Place each test in the feedback loop where its signal is timely, affordable, and actionable: local development, pre-commit, PR CI, merge queue, nightly, release gate, canary, or production monitoring.

## Use When / Avoid When

| Use When | Avoid When |
| --- | --- |
| A test is useful but too slow, flaky, expensive, or environment-heavy for every edit. | The test is already fast, deterministic, and correctly placed. |
| CI has retries, ignored failures, long queues, or unclear ownership. | The main problem is test design rather than execution cadence. |
| A behavior needs different controls before merge, before release, and after deploy. | Production monitoring is being used to avoid feasible pre-merge tests. |

## Core Principles

- Fast, deterministic, high-signal tests belong closest to the developer.
- Expensive or broad tests must have a reason, owner, cadence, artifacts, and failure policy.
- First-attempt pass rate matters; retries hide instability even when final CI is green.
- Local loops should help diagnose; release loops should protect high-impact risk; production loops should catch environment-only failures.
- Split suites by purpose, not by tradition: smoke, impacted, full regression, compatibility, performance, resilience, and synthetic monitoring.
- Every non-blocking or quarantined test should still be visible and owned.

## Decision Rules

| Test/Signal | Best Loop |
| --- | --- |
| New focused unit/component test for changed code. | Local and PR CI. |
| Integration/contract test for shared boundary. | PR CI or merge queue; provider verification before deploy. |
| Critical end-to-end smoke. | PR CI if stable and short; otherwise merge queue/release gate with artifacts. |
| Large matrix, browser/device compatibility, long migration, load, fuzz, mutation. | Nightly, scheduled, or release-specific loop. |
| Canary, synthetic, SLO, real traffic error-rate check. | Post-deploy production loop with rollback/escalation path. |
| Flaky diagnostic rerun. | Same commit reruns tracked separately from final pass. |

## Common Failure Modes

- Adding slow tests to PR CI without measuring runtime or flake cost.
- Moving failing tests to non-blocking jobs without owner, reason, or replacement control.
- Treating retry-passing tests as ordinary green.
- Running broad suites nightly but never triaging failures.
- No artifact trail: missing logs, screenshots, traces, seed, environment, or test report.

## Output Guidance For Agents

- State which command/loop the test should run in and why.
- Include expected runtime/fidelity tradeoff when adding broad or environment-heavy tests.
- Report commands run locally and commands left for CI/nightly/release.
- If skipping a loop, name the residual risk and the compensating control.

## Agent Checklist

- Inspect local scripts and CI jobs before adding new commands.
- Keep PR-blocking tests focused and deterministic.
- Publish machine-readable reports when supported.
- Preserve failure artifacts for broad tests.
- Track retries, skips, quarantine, and long-running tests as health signals.

## Source Anchors

- Google Testing Blog, [Just Say No to More End-to-End Tests](https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html)
- Google Research, [Taming Google-Scale Continuous Testing](https://research.google.com/pubs/archive/45861.pdf)
- GitLab, [unit test reports](https://docs.gitlab.com/ee/ci/testing/unit_test_reports.html)
- Buildkite, [flaky test management](https://buildkite.com/docs/test-engine/test-suites/flaky-test-management)
