# Mutation Testing

## Strategy Map

### Purpose
Audit whether existing tests fail when small artificial behavioral changes are introduced into code under test.

### Reliability Goal
Reduce false confidence from tests that execute code but do not assert behavior strongly enough to catch meaningful regressions.

### When This Strategy Applies
- Normal tests already pass and are reasonably fast/deterministic.
- The target is high-risk deterministic logic: authorization, billing, eligibility, validation, state transitions, parsers, quotas, or compliance rules.
- Coverage is high but confidence in assertions is low.
- A bug escaped because tests missed a boundary, boolean, comparison, or omitted side effect.

### When This Strategy Does Not Apply
- The baseline suite is failing, flaky, or too slow.
- The target is generated, vendored, boilerplate, UI-layout, migration, schema-only, or low-risk glue code.
- The main risk is integration compatibility, performance, accessibility, rollout, or visual behavior.
- The team would chase 100% mutation score without inspecting surviving mutants.

### Signals To Inspect First
- Mutation config, fast unit/component tests, code coverage, high-risk modules, escaped defects, weak assertions, surviving mutant reports, equivalent mutants, timeout settings, excluded generated code, and test runtime.

### Test Design Principles
- Mutation score is a proxy for test sensitivity, not correctness.
- Surviving mutants are prompts for inspection; some are equivalent, dead code, redundant logic, or unspecified behavior.
- Target small high-risk scopes before broad runs.
- A useful response is a stronger behavior test, not blindly asserting implementation details.
- Mutation amplifies flakiness and runtime cost.

### Good Test Characteristics
- Runs are scoped to changed or high-risk code.
- Surviving mutants are reviewed line by line with behavior context.
- New tests assert public behavior, boundary cases, negative cases, and side effects.
- Equivalent or irrelevant mutants are documented or excluded narrowly.
- Mutation reports are used to improve tests, not as vanity scores.

### Poor Test Characteristics
- Running mutation against slow E2E or snapshot-heavy suites.
- Adding brittle implementation-detail assertions only to kill mutants.
- Mutating generated code or migrations.
- Treating survived mutants as always real bugs.
- Reporting a score without naming the missing behavior.

### Execution Pattern
- Run baseline tests first.
- Select a focused high-risk target.
- Run the repository mutation tool with existing config or a narrow scope.
- Inspect surviving mutants and classify meaningful, equivalent, dead-code, or out-of-scope.
- Add or improve behavior tests for meaningful survivors.
- Rerun targeted tests and the mutation subset.
- Report remaining survivors and rationale.

### Examples
- Weak: tests cover withdrawal below and above balance but not exact balance. A `<=` to `<` mutant survives. Stronger: add an exact-balance boundary test asserting full withdrawal is allowed.
- Weak: kill a discount authorization mutant by asserting a private helper call. Stronger: test that an unauthorized user cannot apply the discount and persisted pricing remains unchanged.

### Validation
- Confirm baseline tests pass before mutation.
- Verify the added test fails for the meaningful mutant or original bug.
- Rerun mutation for the focused target only.
- Check for flaky tests and timeouts before trusting scores.
- Do not use coverage or mutation score alone as proof of correctness.

### Failure Modes
- Equivalent mutants waste time.
- Mutation runs become too slow for developer feedback.
- Snapshot tests kill mutants for irrelevant changes.
- High scores hide missing integration or contract tests.
- Agents overfit tests to mutants instead of user-visible behavior.

## Overview

Mutation testing checks whether existing tests fail when small, meaningful changes are injected into production code. It measures assertion strength, not coverage volume. A high line-coverage suite can still miss mutants if it executes code without verifying the behavior that matters.

Use mutation results as a diagnostic for important logic with existing tests. Do not introduce it as a broad gate before the suite is deterministic, reasonably fast, and trusted.

## Best Fit

Use mutation testing for deterministic, high-value logic where tests already run and correctness matters: calculations, permissions, validation, parsers, state machines, pricing, scheduling, retry/idempotency rules, data transformations, and security-sensitive branches.

It works best when scoped to changed files, critical modules, or post-incident areas. Whole-repo mutation runs are often too slow and noisy unless the project already has mature tooling and baselines.

## Score Interpretation

| Result | Meaning | Action |
| --- | --- | --- |
| Survived mutant changes observable behavior | Test oracle is weak or missing. | Add or strengthen behavior-focused tests. |
| Survived mutant is equivalent | Mutated code is behaviorally indistinguishable in this context. | Mark/ignore with reason if tooling supports it. |
| Survived mutant is in low-risk glue/generated code | Score is noisy for this scope. | Exclude, lower priority, or accept explicitly. |
| Killed mutant comes from brittle snapshot or implementation assertion | Test may be high-churn but low-value. | Prefer semantic assertions. |
| High score but integration failures still escape | Unit-level oracles are strong but boundary coverage is missing. | Add contract/integration tests, not more mutation tuning. |

## Candidate Matrix

| Target | Mutants Should Reveal |
| --- | --- |
| Boundary checks | Missing off-by-one, inclusive/exclusive, null/empty, limit tests. |
| Boolean and permission logic | Missing denied cases, role combinations, feature-flag paths. |
| Arithmetic and money | Weak rounding, sign, currency, tax, discount, conservation checks. |
| Error handling | Tests that ignore failure semantics or exception translation. |
| State machines | Missing transition, guard, cancellation, or terminal-state assertions. |
| Parsers/serializers | Weak validation, normalization, round-trip, and malformed-input checks. |

## When Not To Use

Avoid mutation testing when the baseline suite is failing, flaky, extremely slow, mostly snapshot-based, or dominated by generated code and low-risk glue. Do not chase 100 percent mutation score; equivalent mutants and low-value code make that target wasteful.

Do not use mutation score as a team ranking metric. Use it to decide which tests to improve, which code needs clearer seams, and where risk is acceptable.

## Signals

| Strong Signal | Use With Judgment | Avoid |
| --- | --- | --- |
| High-risk logic has coverage but past bugs escaped. | Newly changed files with focused tests but uncertain assertion strength. | Generated code, getters/setters, framework wiring. |
| Mutants survive in conditions, comparisons, arithmetic, or error paths. | Partial runs on a noisy suite. | Treating equivalent mutants as mandatory failures. |
| A survived mutant maps to a named requirement or incident. | Low score in low-risk glue. | Optimizing score without improving behavior tests. |

## Workflow

1. Run mutation testing on the smallest meaningful target.
2. Review surviving mutants and discard equivalent or low-risk cases explicitly.
3. Add or strengthen behavior tests for meaningful survivors.
4. Re-run the target and report score only with scope and caveats.
5. Expand to adjacent modules only when the risk justifies the cost.

## Test Improvement Rules

- Add tests that express the requirement the mutant violated, not tests that merely kill the mutant.
- Prefer boundary, negative, error-path, and invariant tests over implementation-call assertions.
- Promote incident-related survived mutants into durable regression tests.
- Keep mutation runs deterministic; do not draw conclusions from flaky or failing baseline tests.
- Report excluded files and equivalent mutants so the score remains interpretable.

## Examples

| Survived Mutant | Better Test |
| --- | --- |
| greater-than changed to greater-than-or-equal in an age/limit check. | Boundary cases at limit - 1, limit, and limit + 1. |
| denied permission changed to allowed. | Explicit allowed and denied role matrix. |
| exception removed from invalid input path. | Assert specific error semantics, not just no crash. |
| rounding mode changed in invoice total. | Currency examples plus conservation/property tests. |

## Packages And Libraries

| Ecosystem | Tools |
| --- | --- |
| JavaScript/TypeScript | StrykerJS. |
| JVM | PIT/Pitest, Major for research or specialized use. |
| .NET | Stryker.NET. |
| Python | mutmut, cosmic-ray, mutatest. |
| Ruby | mutant. |
| PHP | Infection. |
| Scala | Stryker4s. |
| C/C++ | Mull, specialized compiler-based mutation tooling. |

## Source Anchors

- Mutation-testing research at large scale treats mutation score as a test-effectiveness signal, not a direct quality score.
- Equivalent mutants, generated code, snapshots, and low-risk glue are known sources of noisy mutation results.
- Mutation testing is most useful when paired with a deterministic baseline suite and risk-scoped targets.

## Quality Bar

- Mutation scope is tied to risk or changed behavior.
- Surviving mutants are triaged as meaningful, equivalent, or accepted risk.
- New tests would fail for the survived mutant before the fix.
- Reports include scope, command, baseline status, and runtime cost.
