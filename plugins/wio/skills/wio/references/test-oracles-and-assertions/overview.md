# Test Oracles And Assertions

## Purpose

Define how a test decides whether behavior is correct. A good oracle would fail for the regression that matters while avoiding brittle coupling to irrelevant implementation details. If no plausible bug would make the assertion fail, the test has weak signal.

## Use When / Avoid When

| Use When | Avoid When |
| --- | --- |
| A test exercises code but has weak, vague, or missing assertions. | The expected result is already explicit and the main problem is setup or test level. |
| Correctness can be expressed as output, state, event, invariant, schema, contract, snapshot, or comparison. | No one can state expected behavior; clarify the requirement first. |
| Snapshots/golden files are large or updated without review. | The assertion would duplicate production logic exactly. |
| A workload, generated test, or high-level flow needs invariants checked across multiple steps. | The test only needs a smoke check and no stronger product claim is available. |

## Core Principles

- Assert the observable contract: return value, state transition, persisted row, emitted event, response, visible UI, error, or invariant.
- Use independent expected values. Do not compute expected results by copying the production algorithm.
- Prefer specific semantic assertions over broad "does not throw", count-only, or giant snapshot assertions.
- Use multiple oracle styles when one is incomplete: example cases, properties, metamorphic relations, differential comparison, contracts, and golden files.
- Snapshot/golden tests protect reviewed output contracts; they are weak when updates are automatic approval rituals.
- Snapshot tests work best when the output is a readable domain representation and the snapshot is a reviewed expected result, not an unexamined dump.
- Failure messages should identify the violated behavior, not only the raw mismatch.
- Every kept test should have a falsification story: the plausible bug, the observation point, and the assertion or invariant that fails.
- Treat assertions as executable design understanding. Build the mental model first, then encode it in checks that can catch disagreement between the model and the implementation.
- Test the expected valid space, the rejected invalid space, and the boundary where valid data becomes invalid.

## Decision Rules

| Need | Better Oracle |
| --- | --- |
| Known example or regression. | Direct expected value/state/assertion with named case. |
| Large input space with stable rules. | Property-based invariant or metamorphic relation. |
| Compatibility between consumer/provider. | Contract/schema/protocol assertion. |
| Complex generated output. | Small golden/snapshot with reviewed diff and stable normalization. |
| Multiple implementations or old/new behavior. | Differential test or characterization test with explicit migration risk. |
| UI behavior. | Accessible visible state, user-facing messages, enabled/disabled state, navigation, or persisted effect. |
| Stateful workload or generated sequence. | Invariants checked after each meaningful step, plus terminal assertions and replay seed. |
| Retry, recovery, or background progress. | Bounded eventual assertion with explicit dependency/time assumptions and terminal-state checks. |
| Permission, tenant, or security behavior. | Policy invariant, deny-by-default cases, paired allowed/denied examples, and cross-tenant isolation checks. |

## Assertion Design Workflow

Use this workflow before writing or reviewing a test:

1. Name the risk: customer harm, data corruption, security failure, outage, support burden, or developer regression.
2. State the property in domain language.
3. Pick the observation point: response, UI state, persisted state, emitted event, after each transition, terminal state, metric, or trace.
4. Choose the oracle: explicit expected value, invariant, schema, contract, reference model, differential comparison, metamorphic relation, golden output, or bounded eventual check.
5. Name one plausible bug that should fail the assertion.
6. Check independence: the expected value or model must not copy the production algorithm under test.
7. Check stability: the assertion should survive behavior-preserving refactors and fail for contract changes.
8. Check the negative space: invalid input, forbidden transition, denied permission, or impossible state should be asserted explicitly when it matters.

## Invariant Guidance

- Use invariants for rules that must survive construction, mutation, retries, failures, generated command sequences, or workflow transitions.
- State the scope: object, record, account, tenant, queue, resource, operation trace, or externally visible system state.
- Separate preconditions, postconditions, and invariants. Preconditions constrain callers; postconditions constrain one operation; invariants constrain externally observable state across transitions.
- Check invariants after every meaningful step when intermediate corruption can escape through reads, events, retries, or background jobs.
- State allowed transient exceptions explicitly, such as inside a transaction, lock, migration batch, or private critical section.
- Watch for vacuity: a test that never enters the risky state can pass an invariant while missing the product failure.
- Pair important invariants across boundaries when possible: before write and after read, before send and after receive, before enqueue and after dequeue, before retry and after replay.
- Split compound assertions when the parts describe distinct facts; precise failures make invariant violations easier to diagnose.

## Falsification Gate

Return `REDO` or redesign the assertion when:

- No plausible bug, regression, or failure mode is named.
- The assertion only proves execution completed, an object exists, a value is truthy, or a mock was called.
- The test only checks status 200 or no exception for behavior with a stronger contract.
- Error-handling paths are untested even though the behavior depends on validation failure, dependency failure, retry, fallback, or cleanup.
- The expected value is computed through the same production logic under test.
- A broad snapshot hides the reviewed contract or is routinely updated without semantic review.
- Snapshot update mode can change files during normal passing test runs, or updates snapshots without first surfacing a mismatch.
- The assertion depends on private structure, incidental ordering, exact timestamps, random IDs, or current CSS/layout unless those are the contract.
- A workload checks invariants only at final completion even though intermediate corruption, duplicate effects, or leaked state would matter.
- Doubles, fixtures, or setup remove the boundary, state, permission, timing, data, or dependency behavior the test claims to protect.

## Common Failure Modes

- Tests that only assert no exception, truthiness, object existence, status 200, or mock call count.
- Expected values generated by the same code path under test.
- Snapshots so broad that reviewers cannot see the protected contract.
- Assertions on private fields, CSS classes, exact timestamps, random IDs, or incidental order.
- Too many assertions in one test, obscuring the primary behavior.

## Output Guidance For Agents

- State the oracle: what observed fact proves correctness?
- Name the regression or failure mode that would make the assertion fail.
- Name the plausible bug caught before claiming `KEEP`.
- Keep generated/random data deterministic or assert properties instead of exact incidental values.
- If using snapshot/golden output, explain the reviewed contract and normalization.
- If snapshots can auto-update, state the opt-in mechanism and ensure normal test runs only write files when the snapshot would otherwise fail.

## Agent Checklist

- Identify the expected behavior before writing code.
- Check whether the assertion would fail on the target bug.
- If no target bug exists, name a plausible regression class and verify the assertion would fail for it.
- Cover valid and invalid spaces when the bug risk lives at their boundary.
- Avoid duplicating production logic in expected values.
- Prefer semantic matchers and focused diffs.
- For workloads and stateful tests, check invariants after each meaningful transition.
- Add failure messages or case names when ambiguity would slow diagnosis.
