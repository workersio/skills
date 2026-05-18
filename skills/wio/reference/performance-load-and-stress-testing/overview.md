# Performance, Load, and Stress Testing

## Strategy Map

### Purpose
Validate latency, throughput, saturation, scalability, and overload behavior under realistic workloads and environments.

### Reliability Goal
Reduce production risk from performance regressions, capacity limits, queue buildup, resource exhaustion, and degraded user experience that functional tests cannot expose.

### When This Strategy Applies
- A change affects request paths, database queries, caching, concurrency, background jobs, payload size, algorithms, infrastructure, or release capacity.
- SLOs, latency budgets, throughput targets, or launch-readiness thresholds exist.
- The workload can be modeled with representative users, data, traffic mix, and dependency behavior.
- Overload or graceful degradation behavior matters.

### When This Strategy Does Not Apply
- No baseline, workload model, or success criteria exists.
- The environment is so unrealistic that results would mislead.
- The risk is functional correctness better covered by unit/integration tests.
- Load would hit systems without authorization or safe isolation.
- The test cannot observe bottlenecks or user-visible outcomes.

### Signals To Inspect First
- SLOs, p95/p99 latency, throughput, error budgets, concurrency, traffic mix, payload sizes, cache hit rates, data volume, DB indexes, queue depth, CPU/memory/IO, autoscaling, dependency limits, and production telemetry.

### Test Design Principles
- Performance tests are models; realism and baselines determine value.
- Measure user-visible outcomes and saturation signals, not only average latency.
- Small focused benchmarks catch algorithmic regressions; load tests catch system capacity and interactions.
- Stress tests should define acceptable degradation and recovery.
- Do not hide correctness errors inside performance runs.

### Good Test Characteristics
- Workloads reflect real request mixes, think times, data sizes, auth paths, cache states, and dependency behavior.
- Assertions include latency percentiles, error rates, resource saturation, queue depth, and recovery.
- Baselines compare before/after under similar conditions.
- Results include enough telemetry to locate bottlenecks.
- Tests are scoped to safe environments with cleanup.

### Poor Test Characteristics
- A synthetic benchmark with unrealistic data is used as launch proof.
- Only average latency is reported.
- Load generation overwhelms dependencies unrelated to the change.
- No correctness assertions run during load.
- Performance claims lack environment, version, workload, or baseline details.

### Execution Pattern
- Define the performance risk and success criteria.
- Choose benchmark, load, stress, soak, or capacity test level.
- Build representative data and workload.
- Run a baseline if possible.
- Execute with observability enabled.
- Analyze percentiles, errors, resource saturation, and correctness.
- Rerun after fixes and report environment and residual risk.

### Examples
- Weak: call one endpoint in a tight loop with one user and average latency. Stronger: replay representative authenticated traffic mix with realistic payloads, assert p95/p99 and error budget, and inspect DB/cache/queue metrics.
- Weak: microbenchmark a cache change only. Stronger: pair a focused benchmark with an integration load test that verifies cache hit behavior and backend saturation.

### Validation
- Run the configured performance command or benchmark with documented environment.
- Compare against baseline and thresholds.
- Verify functional correctness during the run.
- Inspect telemetry for saturation and bottlenecks.
- Repeat suspicious results to rule out environmental noise.
- State limits of the workload model.

### Failure Modes
- Unrepresentative workloads create false confidence.
- Shared environments add noise or harm other users.
- Averages hide tail latency.
- Missing telemetry prevents diagnosis.
- Optimizations change behavior or weaken tests.

## Overview

Performance, load, and stress testing exercise a system under controlled traffic to learn whether it meets latency, throughput, error-rate, and saturation expectations. In practice: performance testing measures behavior against performance goals, load testing validates expected or increasing production-like demand, and stress testing pushes beyond expected demand or with constrained resources to expose breaking points and recovery behavior. These definitions align with ISTQB terminology.

The reliability problem this solves is not “is the code functionally correct?” but “does the whole service remain useful when queues, caches, databases, networks, autoscalers, and dependencies interact under pressure?” Google SRE frames stress testing as a way to quantify confidence in systems at scale, not just individual components.

## Best Fit

Highest ROI comes when the system has user-visible latency or availability SLOs, real traffic growth, costly outages, expensive infrastructure, autoscaling behavior, shared downstream dependencies, or business-critical launch events.

Use it before major releases, migrations, pricing or traffic-model changes, infrastructure resizing, large customer onboarding, regional failover work, cache strategy changes, or changes to concurrency limits, queueing, retries, batching, rate limiting, or database indexes.

It is especially useful when paired with production observability, because load-test results without server-side metrics mostly say “it got slower,” not “why.”

## Good Candidates

* Public APIs, internal platform APIs, service meshes, gateways, and edge services.
* Search, checkout, payments, authentication, file upload, streaming, messaging, and notification flows.
* Batch pipelines where throughput, queue depth, backlog drain time, or memory growth matters.
* Systems using autoscaling, connection pools, worker pools, queues, caches, or rate limits.
* Multi-tenant systems where noisy-neighbor effects or shared limits can degrade other customers.
* Launch readiness: “Can we handle 3x expected peak for 30 minutes and recover without manual intervention?”
* Regression gates for mature services: “p95 latency under 300 ms and error rate under 1% at 1,000 RPS.”

## When Not To Use

Do not start with load testing when the team lacks basic production metrics, clear SLOs, representative traffic shape, or a realistic test environment. The result will usually be misleading.

Avoid expensive full-system tests for small, CPU-bound functions where microbenchmarks or profiling give a faster answer.

Do not use synthetic load as proof that production will be safe if real users have different think times, request mixes, payload sizes, auth paths, cache hit rates, regions, or dependency behavior.

Do not run uncontrolled stress tests against shared production dependencies unless blast radius, rate limits, rollback, and stakeholder communication are explicit.

## Limitations

Load tests are models, not reality. The hardest parts are workload realism, dependency realism, data realism, and interpreting bottlenecks. AWS recommends production-like environments and synthetic or sanitized production data for cloud workload load testing; this is often the difference between useful signal and false confidence.

A test can overload the load generator before the service. Always monitor generator CPU, network, open files, connection reuse, DNS behavior, and outbound bandwidth.

Average latency is usually the wrong decision metric. Tail latency matters because distributed services often amplify rare slow events across many subrequests; Google’s “The Tail at Scale” remains authoritative because it describes this behavior from large production systems and is still cited in latency engineering.

Beware coordinated omission: a load generator that waits for slow responses before sending more traffic can under-report user-experienced latency during stalls. wrk2 was created specifically to address this by measuring against intended request timing.

Stress tests can cause cascading failures if retries, queues, autoscaling, or partial dependency failures create positive feedback loops; Google SRE documents overload-driven cascades as a common distributed-systems failure mode.

## Signals

### Helpful Signals

* Test scenarios map to named SLOs, user journeys, and expected peak/soak/spike profiles.
* Results include p50/p90/p95/p99 latency, throughput, error rate, saturation, queue depth, retry rate, GC pauses, connection-pool use, cache hit rate, database metrics, and dependency latency.
* The team can identify the bottleneck and the next scaling constraint.
* Repeated runs are comparable, versioned, and tied to changes in code, config, infrastructure, or data.
* The system degrades predictably: rate limits, backpressure, shedding, and alerts fire before total failure.

### Misuse Signals

* Success is reported as “handled N users” without request rate, request mix, payloads, duration, or error budget.
* Only client-side averages are reviewed.
* The test passes only because caches are warm, auth is bypassed, data is tiny, or dependencies are mocked unrealistically.
* Load tests run rarely, require heroic setup, or are ignored unless a launch fails.
* Stress tests find breaking points but no one changes capacity plans, limits, dashboards, or runbooks.

## Examples

A checkout team defines a pre-holiday test: 2x normal peak for 20 minutes, then a 5x spike for 3 minutes. Pass criteria: p95 checkout API latency under 500 ms, payment authorization errors under 0.5%, no queue backlog older than 2 minutes, and no database CPU above 80% for more than 5 minutes.

A platform API team adds a CI performance gate for one critical endpoint: run 10 minutes at the previous release’s p95 traffic, fail if p99 latency regresses by more than 20% or error rate exceeds 1%. k6 thresholds are a common way to express pass/fail criteria on metrics such as request failure rate and percentile latency.

An SRE team runs a controlled stress test in staging with one dependency rate-limited to production quota. The goal is not maximum RPS; it is verifying backpressure, retry budgets, autoscaling behavior, alert timing, and recovery after load returns to normal.

## Packages And Libraries

General HTTP/API: Apache JMeter, Grafana k6, Gatling, Locust. JMeter is mature and broad; k6 is code-oriented and strong for threshold-based automation; Gatling is strong for code-defined simulations and workload modeling; Locust is Python-native and supports distributed load generation.

High-throughput benchmarking: wrk2 for constant-throughput HTTP benchmarking and coordinated-omission-aware latency measurement. Use carefully; it is better for focused endpoint benchmarking than complex user journeys.

Cloud/provider services: Azure Load Testing when the team wants managed load generation, JMeter compatibility, and Azure resource-metric integration. AWS Well-Architected guidance is useful even when using open-source tools: run sustained tests, discover breaking points, and model production scale.

Tool choice is ecosystem-specific; the durable practice is representative workload modeling, clear pass/fail thresholds, server-side observability, and repeatable comparison.
