# Testing Core Concepts

## Purpose

Make assertions, invariants, and tested properties the shared vocabulary for all testing decisions. A test should not start from "what tool should I use?" or "what file should I cover?" It should start from the property that must hold, the observation that can falsify it, and the assertion or invariant that turns that observation into a useful oracle.

This is a cross-cutting reference. Use [Test Oracles And Assertions](../test-oracles-and-assertions/overview.md) for detailed oracle choices, [Property-Based Testing](../property-based-testing/overview.md) for generated-input strategies, and the specialized references for security, resilience, performance, fuzzing, and suite health.

## Concept Map

| Concept | Definition | Testing Role |
| --- | --- | --- |
| Property | A rule the system should satisfy over one state, one transition, one execution trace, or multiple traces. | Defines what correctness means. |
| Assertion | An executable check of a specific observed fact at a specific point. | Turns one property obligation into a pass/fail signal. |
| Invariant | A property that must hold across a defined region of behavior, usually every reachable state or after every valid transition. | Gives the suite a reusable safety backbone. |
| Oracle | The source of truth that decides whether observed behavior is acceptable. | Connects assertions and invariants to requirements, specs, models, or human judgment. |

The practical relationship is: define the property first, express stable properties as invariants where possible, and use assertions to check those invariants or other expected facts at meaningful observation points.

## Assertions

An assertion is a precise claim about observed behavior. In tests, it should answer: "What fact, if false, proves this behavior is wrong?"

### Best Ways To Define Assertions

- Assert the public or user-visible contract: return value, persisted state, emitted event, API response, visible UI state, error type, authorization decision, or externally meaningful interaction.
- Keep the assertion narrow enough to protect the intended behavior without implicitly testing unrelated fields, formatting, timing, or implementation details.
- Use broad equality, full snapshots, and screenshot diffs only when the whole object or output is the reviewed contract. Prefer focused semantic assertions for individual behaviors.
- Use independent expected values. Do not compute the expected result by copying the production algorithm into the test.
- Prefer assertion forms that explain the failure. A domain matcher, structured diff, schema error, or custom predicate with diagnostic output is usually better than a bare truthiness check.
- Name the failure mode the assertion would catch. If no realistic bug would make the assertion fail, the assertion is low value.
- Avoid assertions that only prove execution reached a line: `not.toThrow`, `notNull`, `toBeTruthy`, mock call count, and empty snapshots are usually weak unless the test is explicitly a smoke or wiring check.
- Keep multiple assertions in one test only when they all describe the same behavior or invariant. Split unrelated properties into separate tests so failures point to one broken rule.

### How To Think About Assertions

Assertions are not decorations after setup. They are the test's core design decision. A test with expensive setup and a vague assertion is usually worse than no test because it creates confidence without a clear correctness claim.

Think of each assertion as a small contract review:

1. What property does it check?
2. What observation does it use?
3. Would it fail for the regression we care about?
4. Would it stay stable during a behavior-preserving refactor?
5. Is the failure diagnosable without reading the implementation?

Assertions can also appear outside tests as preconditions, postconditions, runtime checks, contract checks, or monitoring checks. The same discipline applies: state the obligation, keep it independent from the implementation, and decide whether failure means caller misuse, provider bug, invalid environment, or production incident.

## Invariants

An invariant is a rule that remains true across a defined behavioral scope. It is stronger than a one-off assertion because it says the system must preserve a property through construction, mutation, transitions, retries, failures, or generated command sequences.

Examples:

- Account balance never falls below the configured minimum.
- A normalized value is valid and normalizing it again changes nothing.
- Total inventory equals the sum of allocated, available, and reserved inventory.
- A user cannot gain an action by removing a more privileged role.
- A state machine never has two active leaders for the same term.

### Best Ways To Define Invariants

- Name the state space. Define the objects, records, queues, actors, resources, or externally observable states the invariant talks about.
- Name the valid transitions. An invariant must survive construction and every operation that can change relevant state.
- Separate always-true rules from preconditions and postconditions. Preconditions bind callers; postconditions bind the operation; invariants bind the object or system whenever it is externally observable.
- State transient exceptions explicitly. Some invariants are allowed to be temporarily broken inside a transaction, lock, batch, or internal method, but must be restored before the state is visible again.
- Prefer global domain invariants over scattered local assertions when the rule spans multiple fields, tables, services, or workflow states.
- Prove or test preservation: initialization establishes the invariant, and every transition preserves it.
- In stateful or property-based tests, check invariants after every generated action, not only at the end of a long sequence.
- Watch for vacuity. A system that never enters a critical state may satisfy a safety invariant while failing the real product goal.

### How To Think About Invariants

Invariants are the backbone of safety. They turn "this example looks right" into "this rule survives all the states we know how to explore."

A useful invariant is usually not an implementation detail. It should read like a domain, protocol, consistency, security, or resource rule. If the invariant mentions private helper calls, incidental ordering, or current storage layout, it is probably testing design choices rather than correctness.

The formal-methods view is useful even for ordinary tests:

1. `Init => Inv`: every legal initial state satisfies the invariant.
2. `Inv AND Next => Inv'`: every legal step from an invariant-satisfying state produces another invariant-satisfying state.
3. `Inv => Property`: the invariant is strong enough to imply the safety property we actually care about.

Most unit, integration, and property-based tests are not proofs, but this structure keeps test design honest. It forces the test writer to ask whether the suite checks only a final example or also the transitions that preserve correctness.

## Properties To Test

Properties describe the kind of claim the suite is making. Classifying the property helps choose the right oracle and the right test level.

### Safety Properties

Safety properties say that forbidden states or events never occur. A safety violation can be demonstrated by a finite counterexample: one bad state, one bad response, or one bad transition.

Common safety properties:

- Authorization: a user never obtains an action outside policy.
- Isolation: one tenant never reads or mutates another tenant's data.
- Integrity: accepted writes never corrupt required relationships.
- Conservation: money, inventory, credits, or quota are neither created nor lost except by named operations.
- Bounds: resource use, retries, fanout, queue length, or payload size never exceeds a defined limit.
- Type and schema validity: outputs always satisfy the public schema or protocol.
- State-machine legality: no impossible transition occurs.
- Crash and robustness safety: malformed input never causes memory corruption, process death, or uncontrolled error.

Best testing fit: focused assertions, invariants, property-based tests, fuzz harnesses with semantic invariants, static checks, model checking, mutation testing for assertion strength, and negative tests around policy boundaries.

### Liveness Properties

Liveness properties say that desired progress eventually happens. They cannot usually be falsified by a short finite prefix alone because the good event may still happen later.

Common liveness properties:

- A submitted job eventually reaches a terminal state.
- A retrying client eventually succeeds after a dependency recovers.
- A leader election eventually chooses a leader under the stated network and scheduler assumptions.
- A message that is accepted for delivery is eventually delivered or moved to a terminal failure state.
- A queue eventually drains under a defined arrival rate and worker capacity.

Best testing fit: model checking with fairness assumptions, deterministic schedulers, bounded eventual assertions tied to realistic time budgets, integration tests with controlled dependency recovery, load or soak tests, and production monitors tied to SLOs. Be explicit about assumptions; arbitrary sleeps and timeouts are weak substitutes for a progress model.

### Fairness And Environment Assumptions

Many liveness claims only make sense if the environment cooperates. A retry loop cannot guarantee progress if the dependency is down forever; a scheduler cannot guarantee starvation freedom if a runnable task is never scheduled.

Document fairness assumptions beside liveness tests:

- Which actions eventually become enabled?
- Which enabled actions are expected to run?
- Which dependencies eventually recover?
- Which time, ordering, or delivery guarantees does the system rely on?

### Functional Contract Properties

Functional contracts say an operation does what the API, UI, or domain rule promises for a known case. They are often best tested with example-based assertions because the exact expected result matters.

Examples: a price calculation, a permission matrix case, a migration rule, a validation error, an accessibility-visible state, or an API response body.

### Algebraic And Metamorphic Properties

These properties avoid hard-coding every expected output by relating multiple executions.

Examples:

- Idempotence: applying normalization twice equals applying it once.
- Round trip: parsing rendered data preserves semantic meaning.
- Commutativity: independent operations produce the same result in either order.
- Monotonicity: adding constraints cannot expand results; adding permission cannot reduce access unless a deny rule says so.
- Metamorphic relation: transforming input in a known way transforms output in a known way.

Best testing fit: property-based testing, differential tests, and generated examples with shrinking.

### Model And Differential Properties

A model property compares the implementation against a simpler reference model. A differential property compares two implementations, versions, providers, or execution modes.

Use this when exact expected results are tedious but a simpler oracle exists. Keep the model simpler than production; if it repeats the production algorithm, it becomes a dependent oracle and loses value.

### Non-Functional Properties

Some correctness properties are not pure functional output:

- Performance: latency, throughput, saturation, and resource use stay within bounds for a workload.
- Resilience: the system degrades, retries, falls back, or recovers under named faults.
- Security: confidentiality, integrity, availability, authorization, auditability, and abuse resistance hold under adversarial behavior.
- Operability: failures produce diagnosable logs, metrics, traces, or audit events.
- Compatibility: clients and providers preserve schema, protocol, and migration guarantees.

These still need assertions and invariants. A load test without correctness assertions, a chaos test without recovery assertions, or a security test without policy invariants is mostly traffic generation.

### Hyperproperties

Some properties compare multiple executions, not one trace in isolation. Examples include determinism, noninterference, confidentiality, and "same input under equivalent permissions gives equivalent output." These are often missed by ordinary tests because no single run looks wrong.

Test them with paired executions, differential checks, metamorphic tests, information-flow analysis, or formal methods when the risk justifies it.

## Property Definition Workflow

Use this workflow before adding or reviewing tests:

1. Name the risk: customer harm, security failure, data corruption, outage, compliance issue, or maintenance risk.
2. State the property in domain language.
3. Classify it: safety, liveness, fairness assumption, functional contract, algebraic/metamorphic, model/differential, non-functional, or hyperproperty.
4. Choose the observation point: before call, after call, after every transition, over a trace, across two traces, or in production telemetry.
5. Choose the oracle: explicit expected value, invariant, schema, contract, reference model, differential comparison, metamorphic relation, golden output, or human-reviewed artifact.
6. Define the assertion shape: narrow semantic assertion, state invariant check, eventual assertion, structured matcher, snapshot/golden diff, metric threshold, or monitor.
7. Check falsifiability: identify at least one plausible bug that would fail the assertion.
8. Check stability: the test should survive behavior-preserving refactors and fail when the protected contract changes.
9. Check scope: use the lowest test level that preserves the real risk, then add broader tests only for integration, workflow, or operational confidence that lower levels cannot provide.

## Source Anchors

- Google Testing Blog, [Prefer Narrow Assertions in Unit Tests](https://testing.googleblog.com/2024/04/prefer-narrow-assertions-in-unit-tests.html)
- Google, [Software Engineering at Google: Unit Testing](https://abseil.io/resources/swe-book/html/ch12.html)
- GoogleTest, [Assertions Reference](https://google.github.io/googletest/reference/assertions.html)
- Eiffel, [Design by Contract and Assertions](https://www.eiffel.org/doc/eiffel/I2E-_Design_by_Contract_and_Assertions)
- Leslie Lamport, [PlusCal Tutorial Session 9: Liveness](https://lamport.org/tla/tutorial/session9.html)
- Microsoft Research, Leslie Lamport, [Proving the Correctness of Multiprocess Programs](https://www.microsoft.com/en-us/research/publication/proving-correctness-multiprocess-programs/)
- Lamport, Matthews, Tuttle, and Yu, [Specifying and Verifying Systems With TLA+](https://lamport.org/pubs/spec-and-verifying.pdf)
- Cornell University, Alpern and Schneider, [Defining Liveness](https://ecommons.cornell.edu/entities/publication/2ed32f4f-cc5c-413b-ba16-5498641f1939)
- Amazon Science, [How Amazon Web Services uses formal methods](https://www.amazon.science/publications/how-amazon-web-services-uses-formal-methods)
- UCL Discovery, Barr et al., [The Oracle Problem in Software Testing: A Survey](https://discovery.ucl.ac.uk/id/eprint/1471263/)
- Hypothesis, [Stateful tests and invariants](https://hypothesis.readthedocs.io/en/latest/stateful.html)
