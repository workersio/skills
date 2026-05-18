# Resilience Testing and Fault Injection

## Strategy Map

### Purpose
Validate behavior when dependencies, infrastructure, time, resources, or concurrency fail in controlled ways.

### Reliability Goal
Reduce production risk from timeouts, retries, cascading failures, data corruption, duplicate side effects, missing fallbacks, poor recovery, and absent observability.

### When This Strategy Applies
- The code uses external APIs, databases, queues, caches, schedulers, background workers, cloud infrastructure, retry policies, circuit breakers, or health checks.
- A failure mode has defined expected behavior: fail closed, degrade, queue, retry, compensate, alert, or reject.
- The test can inject a scoped, repeatable fault and observe user-visible behavior or durable state.
- Payments, auth, checkout, healthcare, logistics, control planes, or multi-tenant systems depend on safe failure behavior.

### When This Strategy Does Not Apply
- The code is pure deterministic logic with no runtime dependency failure mode.
- Expected behavior under fault is undefined.
- The only assertion is an internal retry-library call.
- Faults would affect unrelated users or systems.
- A simpler unit, contract, migration, or performance test covers the actual risk.

### Signals To Inspect First
- Dependency clients, timeout/retry settings, circuit breakers, idempotency keys, queues, transactions, compensation logic, health/readiness probes, fallback UI, error budgets, incidents, runbooks, logs, metrics, traces, and blast-radius controls.

### Test Design Principles
- Inject faults at the boundary where behavior matters, not randomly for spectacle.
- Assert user-facing outcome, durable state, side-effect safety, and observability.
- Prefer deterministic fakes, proxies, containers, or scoped platform faults over real outages.
- Fault tests cannot prove reliability; they demonstrate behavior for selected conditions.
- Blast radius and cleanup are part of the test design.

### Good Test Characteristics
- A payment timeout leaves the order pending, records retry state, avoids duplicate charge, and emits actionable telemetry.
- A recommendation-service failure still renders the product page with an explicit degraded state.
- Tests use fake clocks, bounded polling, isolated tenants, and deterministic dependency failures.
- Cluster-level experiments have stop conditions and health hypotheses.

### Poor Test Characteristics
- Randomly killing pods with no expected outcome.
- Asserting only that retry was called.
- Using real third-party outages or sleeps.
- Fault injection without cleanup or isolation.
- Broad chaos tests with failures that cannot identify owner or cause.

### Execution Pattern
- Identify the dependency or infrastructure failure risk.
- Define expected degraded, recovery, and data-safety behavior.
- Choose the narrowest layer that preserves the fault semantics.
- Inject a deterministic fault with scoped blast radius.
- Assert response, state, side effects, retries, and telemetry.
- Run targeted validation and broaden only for operational risks.
- Report untested fault modes and environment limits.

### Examples
- Weak: “service survives chaos” after random pod deletion. Stronger: for test tenant only, add latency to payment route, assert checkout response, order state, idempotency, retry record, and alert metric.
- Weak: mock a database client private method. Stronger: use a fake or container/proxy to simulate timeout at the persistence boundary and assert transaction rollback.

### Validation
- Run the fault test and verify the fault was actually injected.
- Confirm assertions would fail without timeout, idempotency, fallback, or recovery behavior.
- Check cleanup restores dependency state.
- Inspect logs/metrics/traces when observability is part of the requirement.
- Avoid claiming resilience beyond the tested fault, load, and environment.

### Failure Modes
- Faults are unrealistic or too broad.
- Tests are flaky because timing and cleanup are uncontrolled.
- Mocks hide transport, serialization, or concurrency failures.
- Fault tests pass while telemetry is absent.
- Recovery behavior duplicates side effects or corrupts state.

## Overview

Resilience testing verifies how a system behaves when dependencies, infrastructure, time, capacity, or network conditions fail. Fault injection deliberately creates failures such as timeouts, 500s, latency, connection resets, queue saturation, clock skew, partial outages, or failover events.

The goal is not to break production theatrically. The goal is to prove timeout, retry, fallback, backpressure, idempotency, recovery, alerting, and blast-radius behavior under controlled conditions.

## Best Fit

Use this strategy for distributed services, dependency-heavy workflows, queues, caches, payment/auth/email providers, storage, region failover, circuit breakers, autoscaling, background workers, migrations, and SLO-critical paths.

It is highest value when expected behavior under fault is explicit and observable: what should fail fast, retry, degrade, queue, compensate, roll back, alert, or stay unavailable.

## Scope Ladder

| Level | Use When | Example |
| --- | --- | --- |
| Unit | Timeout, retry, backoff, or circuit-breaker logic is local. | Fake clock and fake dependency return timeout/5xx. |
| Integration | Transport, serialization, persistence, or idempotency matters. | App talks to fake payment server through real HTTP client. |
| Proxy/network fault | Latency, reset, partition, or packet behavior matters. | Toxiproxy between service and dependency. |
| Staging/system | Recovery, autoscaling, queues, or failover spans components. | Kill worker, saturate queue, verify drain and alerts. |
| Controlled production | Only production topology exposes the risk and blast radius is bounded. | Region failover exercise with stop conditions and rollback. |

## Candidate Matrix

| Fault | Validate |
| --- | --- |
| Dependency timeout/5xx | Bounded timeout, retry budget, fallback, user-visible error, no thread/connection exhaustion. |
| Slow dependency | Backpressure, queue depth, latency budget, cancellation, circuit breaker behavior. |
| Connection reset/network partition | Safe retry, idempotency, duplicate prevention, recovery after dependency returns. |
| Database/cache unavailable | Correct degradation, data consistency, no silent corruption. |
| Queue saturation | Rate limiting, dead-letter behavior, worker recovery, alerting. |
| Region/node/process failure | Failover, leader election, health checks, rollback, state reconciliation. |
| Clock skew/time jump | Token/session/scheduling behavior remains bounded and auditable. |

## When Not To Use

Do not inject faults when expected behavior is undefined, observability is missing, rollback is unclear, or blast radius is uncontrolled. Start with unit/integration tests around timeout and retry logic before broad chaos experiments.

Avoid fault injection against shared or production systems without explicit authorization, rate limits, abort controls, stakeholder awareness, and monitoring.

## Safety And Observability

| Need | Minimum Bar |
| --- | --- |
| Hypothesis | Name the fault, expected user-visible behavior, and system invariant before injecting. |
| Blast radius | Limit tenant, environment, traffic, duration, concurrency, and dependency scope. |
| Abort path | Define stop conditions, rollback, and owner watching the run. |
| Telemetry | Capture logs, metrics, traces, retry counts, queue depth, saturation, alerts, and recovery time. |
| Data integrity | Check idempotency, duplicate prevention, compensation, reconciliation, and partial-write behavior. |
| After-action | Record what failed, what recovered, what did not run, and what remains accepted risk. |

## Signals

| Strong Signal | Use With Judgment | Avoid |
| --- | --- | --- |
| Diff touches retries, timeouts, circuit breakers, queues, pools, failover, or dependency clients. | Non-critical dependency with simple fallback. | No defined success criteria under fault. |
| Past incidents involved cascading failure, saturation, duplicate work, or slow recovery. | Manual operational runbooks exist but are untested. | Faults injected where telemetry cannot prove outcome. |
| SLO-critical path depends on external services. | Local fakes can simulate only part of the fault. | Random chaos without scoped hypothesis. |
| Code changes connection pools, worker pools, rate limits, idempotency, or recovery jobs. | Fault path is rare but high impact. | Fault test with mocks that bypass transport or persistence behavior. |

## Workflow

1. Name the fault hypothesis and expected behavior.
2. Choose the smallest safe level: unit, integration with fake server, proxy fault, staging exercise, or controlled production experiment.
3. Add observability: logs, metrics, traces, alerts, queue depth, retry counts, saturation, and recovery time.
4. Inject one fault at a time with stop conditions.
5. Verify user-visible behavior, data integrity, resource limits, and recovery.
6. Record residual risk and any behavior that remains intentionally untested.

## Examples

| Weak | Stronger |
| --- | --- |
| “Chaos test payment provider.” | Fake payment server returns timeouts; assert bounded retry, idempotency key reuse, no duplicate capture, user receives retryable failure. |
| Retry forever on dependency 500. | Retry with budget, circuit breaker, metric, alert, and clear failure response. |
| Kill a pod and call it resilient. | Verify readiness, in-flight request handling, queue recovery, and SLO impact. |
| Simulate dependency failure but inspect no telemetry. | Assert logs/metrics/alerts, retry counts, saturation, and recovery time. |
| Inject broad random faults in staging. | Inject one named fault with stop conditions and a falsifiable expected outcome. |

## Packages And Libraries

| Area | Tools |
| --- | --- |
| Network/service faults | Toxiproxy, WireMock, Hoverfly, Mountebank, Envoy/Linkerd/Istio fault injection. |
| Kubernetes/infra | LitmusChaos, Chaos Mesh, Gremlin, PowerfulSeal, kube-monkey-style tools. |
| Cloud/provider | AWS Fault Injection Simulator, Azure Chaos Studio, Google Cloud fault/testing patterns. |
| Load plus fault | k6, Gatling, Locust, JMeter paired with dependency fault controls. |
| App patterns | Circuit breakers, retry libraries, fake clocks, local test servers, idempotency test fixtures. |

## Source Anchors

- SRE and chaos-engineering practice frame fault injection as hypothesis-driven reliability work with blast-radius controls, not random breakage.
- Service-mesh and proxy tools are useful when transport behavior matters; fake servers are better when application response semantics are the target.
- Load tools plus fault injection are useful when degradation, saturation, queue buildup, and recovery are part of the expected behavior.

## Quality Bar

- Every fault has a hypothesis, expected behavior, blast-radius control, and stop condition.
- Tests assert recovery and resource bounds, not just that an error occurred.
- Retry behavior has budgets and does not amplify outages.
- Data integrity and idempotency are verified for partially completed work.
- Findings include commands, environment, telemetry reviewed, and untested fault modes.
