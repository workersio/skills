# Property-Based Testing

## Strategy Map

### Purpose
Use generated inputs to test invariants, algebraic properties, round trips, metamorphic relations, and model agreement across larger input spaces than examples can cover.

### Reliability Goal
Reduce missed edge cases in deterministic logic where important correctness can be expressed independently of specific example outputs.

### When This Strategy Applies
- Input space is large and edge cases are easy to miss.
- Behavior has stable invariants: parse/serialize round trips, normalization idempotence, ordering, set laws, permission monotonicity, accounting conservation, state-machine transitions, or equivalence with a reference model.
- The code is deterministic or can be made deterministic with controlled clocks, seeds, and dependencies.
- Generated failures can be minimized and turned into regression examples.

### When This Strategy Does Not Apply
- Behavior is subjective, visual, poorly specified, or mostly copy/layout.
- Correctness cannot be expressed beyond “does not crash.”
- External side effects are expensive or hard to reset.
- Generators would produce mostly invalid or meaningless cases and no one will maintain them.
- Example tests are missing for basic intended behavior.

### Signals To Inspect First
- Public API contracts, input validation rules, parser grammars, state machines, data models, existing examples, edge-case bug reports, numeric boundaries, commutative/idempotent operations, persistence invariants, and reproducibility support.

### Test Design Principles
- Properties must be stronger than implementation restatement.
- Generators should produce valid, interesting data often enough to exercise the behavior.
- Shrinking is valuable only when failures remain reproducible.
- Combine examples with properties; examples communicate intent and cover named business cases.
- Avoid asserting the same algorithm in the oracle that production uses.

### Good Test Characteristics
- Properties describe externally visible invariants.
- Seeds and failing examples are recorded.
- Invalid and boundary inputs are generated deliberately when relevant.
- Failures shrink to understandable cases and become regression examples.
- The test isolates nondeterminism and side effects.

### Poor Test Characteristics
- Generated tests only assert no exception for business-critical logic that needs semantic properties.
- The oracle duplicates production logic.
- Generators mostly create irrelevant data.
- Random failures are not reproducible.
- Properties are so broad they hide which requirement failed.

### Execution Pattern
- Start with concrete examples and intended behavior.
- Name the invariant or metamorphic relation.
- Design generators for valid, boundary, and invalid inputs as appropriate.
- Implement the property with deterministic dependencies.
- Run with recorded seed and reasonable case count locally.
- Promote minimized failures into ordinary regression tests when useful.
- Broaden case counts or scheduled runs for higher-risk logic.

### Examples
- Parser: for every valid AST, `parse(serialize(ast))` equals the normalized AST; invalid bytes either produce a controlled error or no crash depending on the API contract.
- Permissions: adding a less privileged role never grants an action that the original role set denied unless an explicit override rule applies.

### Validation
- Run the property test and record seed/counterexample on failure.
- Mutate or manually weaken the implementation to check that the property can fail for meaningful regressions when practical.
- Inspect generator distribution for useful coverage of boundaries and invalid cases.
- Keep deterministic examples for named requirements.
- Avoid relying on a passing random run as proof of completeness.

### Failure Modes
- Weak properties pass while behavior is wrong.
- Poor generators never reach edge cases.
- Nondeterminism turns property tests flaky.
- Shrunk counterexamples are ignored instead of converted into regression tests.
- Properties encode implementation details and block refactoring.

## Overview

Property-based testing (PBT) checks general rules over generated inputs instead of checking only hand-picked examples. A team writes a property such as “decoding an encoded value returns an equivalent value,” “sorting preserves the multiset and returns ordered data,” or “a sequence of API commands matches a simple model.” The tool generates many inputs or command sequences and, on failure, shrinks the case to a smaller counterexample. This solves a specific reliability problem: example tests often under-sample edge cases and interactions in large input spaces. PBT is strongest when correctness can be stated as invariants, round trips, metamorphic relations, or agreement with a reference model.

## Best Fit

Use PBT when the input space is large, the code is deterministic enough to test repeatably, and the expected behavior can be expressed without reimplementing the system under test. It gives high ROI for pure transformations, parsers, serializers, data structures, validation logic, protocol rules, and stateful APIs that can be compared with a simple model.

It is especially useful after production bugs caused by “unusual but valid” inputs. Convert the bug into a property or generator constraint, then let the tool search nearby cases instead of adding only the one known regression example.

## Good Candidates

* Round-trip behavior: parse(render(x)) == normalize(x), decode(encode(x)) == x.
* Canonicalization and normalization: output is valid, idempotent, and preserves required meaning.
* Collections and algorithms: sorted output is ordered, preserves elements, and is idempotent.
* Financial, scheduling, and date/time logic: invariants around bounds, monotonicity, conservation, and reversibility.
* Compilers, query planners, and interpreters: generated programs or expressions compare against a simpler interpreter, old implementation, or semantic model.
* Stateful APIs: generated command sequences compare a real implementation against an in-memory model.
* Migrations and rewrites: old and new implementations agree across generated valid inputs, with explicit handling for intentional behavior changes.

## When Not To Use

Do not start with PBT when behavior is poorly specified, subjective, or mostly visual. It will create noise if the team cannot state a meaningful property beyond “does not crash.” Avoid it for flows dominated by expensive external side effects unless you can isolate dependencies, reset state cheaply, and make runs reproducible.

PBT is not a replacement for example tests. Keep examples for documented business cases, fixed regressions, and cases where exact expected output matters. For binary memory-safety discovery or coverage-guided exploration, use fuzzing tools; PBT can complement them by supplying semantic assertions.

## Limitations

The hard part is the oracle: deciding what must always be true. Weak properties pass buggy code; properties that duplicate implementation logic give false confidence. Hughes explicitly warns against replicating production code in tests and recommends property styles such as invariants, postconditions, metamorphic properties, inductive properties, and model-based properties.

Generator quality controls test value. Biased generators may never reach the risky part of the domain, while over-filtering invalid inputs can waste runs or make tests pass vacuously. FsCheck’s documentation calls out the need to observe input distribution because filtered test data can invalidate conclusions.

Shrinking is powerful but not free. Complex generators can make shrinking slow or produce counterexamples that are still hard to interpret. Stateful PBT has higher setup cost: teams must define commands, preconditions, postconditions, cleanup, and a model. Random testing is also not exhaustive; passing a property means no counterexample was found under the configured search, not that the property is proven.

## Signals

### Good Signs

* Failures shrink to small, understandable counterexamples.
* Properties find edge cases that example tests missed.
* Generated inputs cover meaningful domain classes, not just trivial values.
* Properties read like domain rules or API contracts.
* Counterexamples become regression tests or seeded replay cases.

### Misuse Signs

* Most generated cases are discarded by assumptions or filters.
* Properties restate the implementation instead of the specification.
* Tests are flaky because time, concurrency, I/O, or shared state is uncontrolled.
* The main response to failures is “increase the run count” rather than improve the property or generator.
* CI time grows while failures are rare, vague, or not actionable.

## Examples

Sorting: Generate lists. Assert the result is ordered, has the same element counts as the input, and sorting it again does not change it. Do not rely only on idempotence; a function that always returns [] may pass some weak properties.

JSON or protocol round trip: Generate valid domain objects, serialize them, parse them, and compare semantic equivalence. Use normalize(x) when serialization is canonicalized or loses insignificant formatting.

Key-value store state machine: Model expected state as an in-memory map. Generate sequences of put, delete, and get. After each operation, compare the real store result with the model. Reset the store per test run.

Migration differential test: Generate inputs accepted by both old and new code. Assert equivalent outputs. For intentional changes, encode the compatibility boundary explicitly instead of weakening the assertion globally.

## Packages And Libraries

* Python: Hypothesis. Mature, widely used, strong shrinking and replay support; official docs describe generated inputs, edge cases, and stateful testing.
* Java / JVM: jqwik for JUnit-style Java/Kotlin properties; ScalaCheck for Scala and Java, with integrations in Scala testing ecosystems.
* Kotlin: Kotest property testing module, integrated with the Kotest framework and Kotlin multiplatform support.
* JavaScript / TypeScript: fast-check. Official docs emphasize generation, multiple runs, seeded repeatability, and counterexample shrinking.
* .NET: FsCheck. Mature QuickCheck-inspired library for F#, C#, and VB; note that its site says some docs are outdated for the currently maintained v3 line.
* Rust: proptest. Hypothesis-inspired Rust PBT library; official docs describe minimal failing-case discovery and note passive maintenance status.
* Clojure: test.check. Official Clojure guide presents generators, properties, seeds, and tradeoffs in generator completeness.
* Erlang / BEAM: PropEr and Quviq QuickCheck are established options; Erlang Common Test includes support for running property-based tools in test suites.
* Haskell: QuickCheck remains the foundational library; Hedgehog is also common for integrated shrinking, but QuickCheck is the authoritative baseline for the practice.
