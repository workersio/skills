# Workload Modeling

## Purpose

Design workloads that exercise important user sessions, API/client behavior, operator tasks, or background flows with enough realism, adversarial pressure, and controlled variance to expose bugs that simple example tests miss.

## Use When / Avoid When

| Use When | Avoid When |
| --- | --- |
| A user session combines multiple interactions, states, roles, data shapes, or dependencies. | One deterministic rule has a clear narrow unit or integration test. |
| Bugs are likely to appear from sequence, timing, data mix, cache state, retries, permissions, or cross-feature interaction. | No safe environment, oracle, or cleanup strategy exists. |
| Performance, E2E, synthetic monitoring, or stateful/property testing needs a representative scenario. | Variance would make failures unreproducible or mask correctness. |
| Realistic misuse, duplicate actions, stale state, partial failure, or boundary data could break the workflow. | No one can name the invariant or assertion that should fail when the workload exposes a bug. |

## Core Principles

- Start with a real task: what the user, API client, operator, or job is trying to accomplish during a session.
- Target bug-prone joins: auth, validation, persistence, cache, queues, external providers, concurrency/time, retries/idempotency, migrations, and UI/API boundaries.
- Add adversarial but plausible behavior deliberately. Do not rely on random variance to discover obvious edge classes.
- Preserve replayability. Every variable run needs a seed, generated inputs, branch choices, and enough artifacts to reproduce failure.
- Assert invariants and user-visible outcomes throughout the workload, not only final completion.
- Vary meaningful dimensions: roles, account age, data volume, payload shape, locale/time, optional steps, ordering, dependency responses, and think time.
- Name the plausible bug the workload should catch and the assertion or invariant that would fail.
- Put limits on workload dimensions. Every loop, queue, retry, generated case count, payload size, timeout, and concurrent actor count should be bounded or intentionally unbounded with an explicit assertion/stop condition.
- Keep destructive or expensive workloads in safe environments with cleanup, rate limits, and explicit blast-radius controls.

## Workload Shapes

| Shape | Best Fit |
| --- | --- |
| Browser journey | Critical UI workflows where routing, auth, accessibility, rendering, and backend wiring combine. |
| API scenario | Client sessions that create, update, query, retry, and verify persisted or emitted state. |
| CLI/session script | Developer or operator tasks with filesystem, config, credentials, or process boundaries. |
| Background-job flow | Queues, schedules, retries, idempotency, fanout, and eventual terminal states. |
| Load profile | Realistic traffic mix, payloads, think time, concurrency, and pass/fail thresholds. |
| Stateful/property sequence | Many valid operation sequences with invariants checked after each step. |
| Synthetic monitor | Production-like smoke path that verifies critical availability and contract outcomes. |

## Variance Rules

- Use bounded ranges and weighted choices, not arbitrary randomness.
- Record seed and generated scenario summary on every run.
- Keep the task goal stable even when inputs and branch choices vary.
- Include known edge classes deliberately; do not rely on randomness to discover obvious boundaries.
- Shrink or capture failing cases into deterministic regression tests when possible.

## Adversarial Workload Classes

Use these classes to turn a realistic session into a bug-finding workload. Pick only the classes that match the product risk.

| Class | Examples | Useful Assertions Or Invariants |
| --- | --- | --- |
| Boundary data | Empty, max length, high cardinality, unicode, old version, timezone/locale, exact limits. | Schema validity, normalized output, bounds, no truncation, stable persisted state. |
| Invalid or surprising input | Missing fields, unknown enum, malformed-but-parseable payload, unsupported file, bad config. | Controlled rejection, no partial writes, specific error semantics, audit/log signal. |
| Invalid transitions | Update after delete, cancel after complete, retry after terminal failure, resume stale draft. | State machine legality, terminal state stability, no duplicate side effects. |
| Duplicate and replayed actions | Double submit, webhook replay, idempotency key reuse, retry after timeout. | Idempotency, one persisted effect, one emitted event, safe response on replay. |
| Permission and tenant edges | Lower role, removed role, expired session, cross-tenant id, feature flag mismatch. | Deny by default, tenant isolation, monotonic permission behavior, no leaked state. |
| Ordering and concurrency | Out-of-order events, parallel mutations, stale read then write, delayed queue. | Conservation, version checks, eventual terminal state, no lost updates. |
| Dependency faults | Timeout, 429/500, partial response, stale cache, duplicate delivery, slow provider. | Fallback/retry limits, no corruption, recovery outcome, diagnosable failure artifact. |
| Recovery and cleanup | Crash/resume, rollback, abandoned session, cleanup job, interrupted upload. | Resources released, invariant restored, user-visible recovery path, no orphaned state. |
| Error handling | Validation failure, non-fatal provider error, rejected event, failed cleanup, partial commit. | Specific error semantics, no swallowed failure, no corrupt state, cleanup/audit signal. |

## Assertion And Invariant Design

- Define the correctness checks before adding variance.
- Check invariants after every meaningful step when intermediate corruption matters.
- Use terminal assertions for final user-visible outcomes, persisted state, emitted events, or API contracts.
- Use bounded eventual assertions only when the product property is progress, such as a job reaching a terminal state.
- Avoid workloads that only assert completion, status 200, object existence, or absence of thrown errors unless the workload is explicitly a smoke check.
- For stateful workloads, prefer a simple model, ledger, or state machine that is independent from the implementation under test.
- Record enough failure artifacts to diagnose which step, seed, branch, input, or invariant failed.
- Check both sides of important boundaries: accepted/rejected input, allowed/denied action, before/after persistence, enqueue/dequeue, retry/replay, and dependency failure/recovery.

## Falsification Gate

Before proposing or keeping a workload, answer all of these:

1. What plausible production bug, incident class, or escaped regression could this workload catch?
2. Which assertion or invariant fails for that bug?
3. Does the workload preserve the real failure mechanism, or did mocks/setup remove it?
4. Can the failure be replayed from a seed, generated input summary, artifact, or deterministic command?
5. If the workload is high-level, what narrower regression test should capture a minimized failing case?

If the answers are vague, redesign the workload before implementation.

## Output Guidance For Agents

- Name the actor, session goal, interactions, adversarial classes, invariants, variance model, replay mechanism, and safe execution command.
- Explain which bug-prone areas the workload is meant to surface.
- State the plausible bug it would catch and the assertion or invariant that would fail.
- State what belongs in this workload versus lower-level focused tests.
- Report limitations: environment realism, data realism, dependency fidelity, runtime cost, flake risk, and cleanup risk.

## Agent Checklist

- Inspect docs, routes, commands, APIs, existing E2E/performance tests, fixtures, and CI jobs.
- Map the session to important product or operational tasks.
- Choose the smallest workload level that preserves the interaction risk.
- Define assertions and invariants before adding variance.
- Add adversarial classes deliberately and tie each one to a risk.
- Bound generated work, retries, queues, payload sizes, and concurrency so failures are diagnosable rather than runaway.
- Make failure replay deterministic.
- Check that at least one plausible bug would fail a named assertion or invariant.
- Validate in a safe environment and record residual risk.

## Source Anchors

- Playwright, [best practices](https://playwright.dev/docs/best-practices)
- Grafana k6, [scenarios](https://grafana.com/docs/k6/latest/using-k6/scenarios/)
- Locust, [writing a locustfile](https://docs.locust.io/en/stable/writing-a-locustfile.html)
- Hypothesis, [stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html)
- TigerBeetle, [TigerStyle](https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md)
- Google SRE, [Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)
