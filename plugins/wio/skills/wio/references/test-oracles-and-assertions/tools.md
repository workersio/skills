# Test Oracles And Assertions Tools

Assertion tools should make correctness precise and failure diagnosis cheap. Prefer native assertion libraries and matchers already used in the repo.

## Tool Categories

| Category | Examples | Evidence/Use |
| --- | --- | --- |
| Assertion libraries | JUnit/AssertJ/Hamcrest, pytest assertions, Jest/Vitest expect, Chai, xUnit/NUnit. | Direct expected behavior with useful diffs. |
| Snapshot/golden tools | Jest snapshots, approval tests, golden files, image/text diff tools. | Reviewed complex output contracts. |
| Property/metamorphic tools | Hypothesis, QuickCheck-style libraries, fast-check, jqwik. | Invariants across large input spaces. |
| Contract/schema validators | Pact, JSON Schema, OpenAPI, protobuf/buf, XML schema. | Boundary compatibility or payload shape. |
| Mutation testing | PIT, Stryker, mutmut, cargo-mutants. | Whether assertions fail when behavior changes. |

## Repo Signals To Inspect

| Signal | Common Patterns | Evidence | False Positives |
| --- | --- | --- | --- |
| Weak assertions | `not.toThrow`, `assertTrue`, `toBeTruthy`, `notNull`, `called`, empty snapshots. | Low oracle strength. | Smoke tests may intentionally assert only availability. |
| Snapshot/golden files | `__snapshots__`, `.snap`, `golden`, `approved`, `received`. | Output contracts exist. | Large unreviewed snapshots are low signal. |
| Property tests | `@given`, `forAll`, `fc.property`, `quickcheck`, `proptest`. | Invariant-based oracle capability. | Poor generators can miss important classes. |
| Schema/contract files | `openapi`, `schema`, `proto`, `pact`, `graphql`. | Formal boundary oracle. | Schema presence does not prove behavior. |
| Mutation config | `pitest`, `stryker`, `mutmut`, `cargo mutants`. | Assertion effectiveness evidence. | Mutation is expensive and noisy on generated/glue code. |

## Common Commands And Patterns

| Goal | Starting Commands |
| --- | --- |
| Find weak assertions | `rg "toBeTruthy|toBeDefined|not\\.toThrow|assertTrue|assertNotNull|assert_called|toHaveBeenCalled\\(" test tests src` |
| Find snapshots/goldens | `rg --files | rg "(__snapshots__|\\.snap$|golden|approved|received|fixtures/.*expected)"` |
| Find property tests | `rg "@given|hypothesis|forAll|fc\\.property|quickcheck|proptest|jqwik" test tests src` |
| Find schema/contract oracles | `rg "jsonschema|openapi|swagger|pact|protobuf|buf|graphql|schema" .` |
| Find mutation tooling | `rg "pitest|stryker|mutmut|cargo-mutants|mutation" .` |

## Evidence Rules

- A strong assertion must identify the externally meaningful behavior it protects.
- A snapshot/golden assertion needs stable normalization and a reviewed diff.
- A property assertion needs a valid input generator and a clear invariant.
- Mutation survivors are evidence of weak tests only after filtering equivalent or irrelevant mutations.

## Source Anchors

- Jest, [snapshot testing](https://jestjs.io/docs/snapshot-testing)
- Hypothesis, [strategies](https://hypothesis.readthedocs.io/en/latest/reference/strategies.html)
- Pact, [contract tests](https://docs.pact.io/)
- PIT, [mutation testing quickstart](https://pitest.org/quickstart/maven/)
