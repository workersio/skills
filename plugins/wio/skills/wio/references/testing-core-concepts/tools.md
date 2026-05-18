# Testing Core Concepts Tools

Use these commands to find existing assertions, invariants, and property language before deciding whether the concept is already documented or encoded in tests.

## Repo Signals To Inspect

| Signal | Common Patterns | Evidence | False Positives |
| --- | --- | --- | --- |
| Explicit assertions | `assert`, `expect`, `assertThat`, `require`, `ensure`, `check`, `verify`. | Executable checks already encode expected behavior. | Truthiness, existence, or mock-call checks may be weak. |
| Invariant language | `invariant`, `must always`, `cannot`, `never`, `preserve`, `conservation`, `monotonic`, `idempotent`. | Domain or state-machine rules may already be documented. | Marketing or comments may use "always" loosely. |
| Property tests | `@given`, `forAll`, `fc.property`, `quickcheck`, `proptest`, `invariant`. | Generated-input checks may already cover broad rule families. | Poor generators or vacuous properties can miss meaningful states. |
| Safety properties | `deny`, `isolation`, `authz`, `permission`, `bounds`, `schema`, `valid transition`, `corruption`. | Forbidden states or events are being protected. | A single example may not cover the general safety claim. |
| Liveness properties | `eventually`, `retry`, `terminal`, `drain`, `progress`, `fairness`, `timeout`, `SLO`. | Progress or recovery claims may exist. | Arbitrary sleeps are not strong evidence of liveness. |

## Common Commands

| Goal | Starting Commands |
| --- | --- |
| Find concept documentation | `rg -n "assertion|assertions|invariant|invariants|safety propert|liveness|property-based|metamorphic|oracle" docs references README* .` |
| Find weak assertions | `rg -n "toBeTruthy|toBeDefined|not\\.toThrow|assertTrue|assertNotNull|assert_called|toHaveBeenCalled\\(" test tests src` |
| Find property tests | `rg -n "@given|hypothesis|forAll|fc\\.property|quickcheck|proptest|jqwik|invariant" test tests src` |
| Find safety/security invariants | `rg -n "tenant|isolation|permission|authz|deny|cannot|never|must not|corrupt|bounds|quota|schema" .` |
| Find liveness/progress checks | `rg -n "eventually|retry|terminal|drain|progress|fairness|timeout|deadline|SLO|poll" .` |

## Evidence Rules

- Treat a documented property as useful only if it names the scope, the failure mode, and the observation that would falsify it.
- Treat an assertion as strong only if it would fail for a meaningful regression and stay stable through behavior-preserving refactors.
- Treat an invariant as useful only if initialization and every relevant transition are considered.
- Treat a liveness test as credible only when the environment assumptions and time bounds are explicit.
