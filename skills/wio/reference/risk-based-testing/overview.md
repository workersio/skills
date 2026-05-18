# Risk-Based Testing

## Strategy Map

### Purpose
Allocate finite test effort to the behavior, workflows, and failure modes whose failure would cause the greatest customer, business, security, operational, or compliance harm.

### Reliability Goal
Reduce escaped high-impact defects by making test depth proportional to risk instead of distributing effort evenly or chasing generic coverage.

### When This Strategy Applies
- Test capacity, CI time, device matrices, manual QA, security review, or release windows are limited.
- Failures have uneven impact across workflows, tenants, data, payments, auth, privacy, or operations.
- A change touches critical paths, high-churn modules, incident-prone areas, or risky dependencies.
- Release decisions require explicit residual-risk explanation.

### When This Strategy Does Not Apply
- All meaningful tests are cheap enough to run every time.
- Regulatory or safety constraints require a fixed verification standard regardless of perceived risk.
- Risk inputs are pure opinion with no incident, telemetry, customer, architectural, or threat-model evidence.
- Risk labels are stale and no one owns updating them.

### Signals To Inspect First
- User journeys, revenue paths, authz/authn, privacy data, SLOs, incident history, bug clusters, code churn, dependency changes, feature flags, migration plans, operational blast radius, customer tier impact, compliance requirements, and rollback difficulty.

### Test Design Principles
- Risk combines likelihood and impact, but precision is less important than making tradeoffs explicit.
- High-risk areas deserve earlier, deeper, more realistic, and more frequently run tests.
- Low-risk does not mean untested; it means proportionate validation.
- A risk model must evolve after incidents, architecture changes, and production telemetry.
- Risk-based selection needs fallback when uncertainty is high.

### Good Test Characteristics
- Critical paths have positive, negative, boundary, authorization, data-integrity, and failure-mode tests.
- Expensive suites are run where they protect identifiable risk.
- Test reports explain residual risk by feature or failure mode.
- Escaped defects update risk tags and gates.
- Release shortcuts include explicit risk acceptance.

### Poor Test Characteristics
- Testing only the easiest files while critical workflows remain uncovered.
- Using coverage percentage as the risk model.
- Skipping tests for broad shared changes because path filters look narrow.
- Treating low likelihood as low risk despite severe impact.
- Never revisiting risk after incidents.

### Execution Pattern
- Identify changed behavior and affected users/systems.
- Map likelihood and impact using evidence.
- Select test levels and depth for the highest risks first.
- Add or run focused tests for critical positive, negative, boundary, and failure paths.
- Use expensive validation only where it protects meaningful risk.
- Broaden when shared infrastructure, security, persistence, or contracts changed.
- Report residual risk and any intentional gaps.

### Examples
- Auth library change: run permission matrix, token expiry, session revocation, consumer contract, and affected downstream tests before low-risk visual snapshots.
- Password reset enumeration: prioritize abuse-case tests, rate-limit behavior, audit logging, and alerting over copy-only checks.

### Validation
- Confirm selected tests cover the highest-impact failure modes, not only the nearest files.
- Run at least one broader fallback when impact is uncertain or shared code changed.
- Check that skipped suites are low-risk for this diff with a defensible reason.
- After incidents, verify a durable regression control exists.
- Do not report “low risk” without naming evidence and remaining uncertainty.

### Failure Modes
- Risk scoring becomes performative bureaucracy.
- Teams use low-risk labels to avoid inconvenient tests.
- High-risk but hard-to-test behavior remains uncovered.
- Stale risk maps mislead selection.
- Selection ignores security, data, operational, or rollback impact.

## Overview

Risk-based testing (RBT) is a test strategy that uses product or service risk to decide what to test first, how deeply to test it, and what residual risk to accept before release. A practical risk model usually combines likelihood of failure with impact if that failure happens. High-risk areas get earlier feedback, stronger coverage, more realistic environments, and clearer release gates. RBT addresses the finite-capacity problem: exhaustive testing is infeasible except in trivial systems, so teams need an explicit way to spend test effort where failure would hurt most.

## Best Fit

Use RBT when failures have uneven impact and the team cannot run every meaningful test on every change. It gives high ROI for large regression suites, manual or exploratory testing, release readiness, security testing, migration cutovers, performance and resilience validation, and systems with clear critical journeys or SLO/error-budget exposure. It works best when risk inputs are evidence-based: incidents, defect clusters, production telemetry, code churn, dependency changes, customer impact, revenue exposure, privacy/security impact, and operational blast radius. Google’s SRE guidance is useful here because it treats reliability as an explicit risk/cost tradeoff rather than a vague goal of “maximum quality.”

## Good Candidates

Good candidates include authentication, authorization, payments, refunds, entitlement checks, data durability, privacy boundaries, audit logging, rollback paths, schema migrations, feature-flagged releases, dependency upgrades, concurrency-sensitive code, backfills, failover, retry/idempotency logic, and recently fragile components.

RBT is also useful for expensive suites: slow end-to-end tests, cross-browser/device matrices, performance tests, chaos/resilience tests, penetration-testing follow-up, and manual UAT. For security work, OWASP-style likelihood and impact factors help distinguish “easy to exploit with severe business impact” from “theoretical but low-impact” issues.

## When Not To Use

Do not use RBT as a substitute for cheap, deterministic baseline checks. Fast unit tests, contract tests, linting, type checks, and smoke tests should usually run by default.

Avoid RBT when all relevant tests are cheap enough to run every time, when regulatory or safety obligations require fixed coverage, or when the team lacks traceability from tests to features, risks, or failure modes. It is also a poor fit when risk scores are political, frozen, or based only on seniority-driven gut feel.

Never use “low risk” as a permanent skip label. Low-risk tests still need sampling, rotation, or scheduled full-suite execution.

## Limitations

Risk scoring is a decision aid, not truth. It can overfit to known incidents, miss rare coupled failures, and under-test boring paths that later become critical. A coarse “high/medium/low” matrix without named failure modes usually becomes ceremony.

Automated test selection can reduce cost, but it needs safe fallbacks, dependency awareness, and flake handling. Google research on regression test selection found that the problem remains largely open at scale, and Microsoft’s Azure Test Impact Analysis documentation explicitly describes fallback-to-full-run behavior when unsupported changes or scenarios are detected.

RBT also creates maintenance work: risk tags must change after incidents, architecture changes, new threat models, and customer-impact data. If the risk model is not updated, it becomes stale faster than the test suite.

## Signals

Signs RBT is helping: high-severity defects are found earlier; test reports explain residual risk by feature or failure mode; incidents and escaped defects update risk tags and release gates; CI or manual-test effort drops for low-risk changes without increasing rollback, incident, or customer-impact rates; risk discussions are short, evidence-based, and include engineering plus product, security, or operations when relevant.

Signs RBT is being misused: every test is labeled critical; the same “high-risk” suite runs forever unchanged; risk labels become a way to skip disliked tests; low-risk areas are never sampled; scoring meetings take longer than writing or running tests; release decisions cite a green risk-based suite while ignoring untested dependencies, flakiness, or environment gaps.

## Examples

Checkout release: mark card authorization, capture, refund, tax calculation, idempotency, fraud-rule interaction, and rollback as high risk. Run API contract tests, reconciliation checks, production-like smoke tests, and targeted exploratory charters on every checkout PR. Run the full cross-browser cart matrix nightly unless UI changes or telemetry raise risk.

Shared auth-library change: force all permission, token-expiry, session-revocation, and consumer contract tests, even if impacted-test tooling selects a smaller set. Run affected downstream projects for breadth. Defer low-risk UI snapshot tests to nightly.

Password-reset enumeration risk: score likelihood and impact using a security model. If discoverability is high and impact is account compromise, prioritize abuse-case tests, rate-limit validation, audit logging, alerting, and monitoring checks before lower-impact UI polish tests.

## Packages And Libraries

RBT is mostly a planning and prioritization practice. Mature tooling helps encode risk metadata and run selected suites; it does not decide risk for the team.

Python: use pytest custom markers and selection expressions for tags such as risk_high, security, payments, or migration.

Java/JVM: use JUnit @Tag and platform filtering for risk- or workflow-based suite selection.

Build, monorepo, and CI: use Bazel test tags for release/check-in policy, Nx affected for changed-project task selection, and Azure Pipelines Test Impact Analysis where its supported scenarios match the stack. Keep a full-run fallback for unsupported changes and periodic validation.
