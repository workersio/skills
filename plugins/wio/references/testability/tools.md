# Testability Tools

Use tools to find why behavior is hard to exercise: hidden dependencies, nondeterminism, shared state, side effects during construction, or missing observation points. Prefer repo-native analyzers and test runners before adding new tooling.

## Tool Categories

| Category | What It Finds | Caveat |
| --- | --- | --- |
| Static search | Globals, static calls, service locators, sleeps, random/time reads, IO in constructors. | Search hits are hypotheses; framework code may require these patterns. |
| Dependency graph/build tools | Whether dependencies are declared, layered, cyclic, or hard to replace. | Graph shape does not prove behavior is untestable. |
| Test runner diagnostics | Open handles, leaked processes, slow tests, order dependence, fixture leaks. | Diagnostics often show symptoms, not the root dependency. |
| Coverage and mutation tools | Executed but weakly asserted logic; unreachable branches. | Coverage proves execution only, not correctness. |
| Local infrastructure tools | Whether real dependencies can be made disposable and deterministic. | Containers/emulators improve fidelity but can slow feedback. |

## Repo Signals To Inspect

| Signal | Common Patterns | Evidence Provided | False Positives |
| --- | --- | --- | --- |
| Hidden time/randomness | `Date.now`, `new Date`, `time.Now`, `Instant.now`, `random`, `uuid`, fake timer setup. | Test may need injectable clock, seed, ID source, or deterministic scheduler. | Timestamping logs or metrics may not affect behavior. |
| Hard external calls | HTTP clients, SDK clients, DB connections, message producers created inside logic. | Test may need adapter injection, local emulator, contract test, or container. | Framework clients may already be mocked by test harness. |
| Global state | Singleton access, static mutable fields, process env reads, module-level caches. | Tests may leak state or require order control. | Read-only constants are usually fine. |
| Work in construction | `new` inside constructors, init blocks, import-time side effects, lifecycle hooks. | Object cannot be constructed cheaply for a focused test. | DI containers and framework boot code may be composition roots. |
| Sleep/polling | `sleep`, `setTimeout`, `Thread.sleep`, retry loops, fixed waits. | Nondeterministic synchronization or missing event boundary. | Backoff code itself may be the behavior under test. |

## Common Commands And Patterns

| Goal | Useful Starting Points |
| --- | --- |
| Find nondeterminism | `rg "Date\\.now|new Date|time\\.Now|Instant\\.now|random|uuid|sleep|setTimeout|Thread\\.sleep" src test` |
| Find hidden globals | `rg "getInstance|ServiceLocator|static .*instance|process\\.env|System\\.getenv|os\\.environ" src test` |
| Find side-effect-heavy setup | `rg "beforeAll|beforeEach|setUp|setup_method|@Before|fixture|conftest|TestMain" test tests` |
| Find import-time or constructor work | `rg "constructor|__init__|init\\(|componentDidMount|useEffect|@PostConstruct" src` |
| Inspect test runner diagnostics | Look for `--detectOpenHandles`, `--durations`, `--runInBand`, `--maxfail`, timeouts, retries, leak detection. |

## Evidence Rules

- A testability finding should cite one concrete call site or pattern and one affected test behavior.
- Prefer "this dependency is not controllable from tests" over "this code is bad."
- If proposing a seam, show how production wiring still uses the real dependency.
- Treat broad refactors as high risk unless a narrow seam cannot preserve behavior.

## Source Anchors

- Bazel, [hermetic test guidance](https://bazel.build/reference/test-encyclopedia)
- Jest, [detect open handles and configuration](https://jestjs.io/docs/configuration)
- pytest, [fixtures and safe teardowns](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- Testcontainers, [disposable real dependencies](https://docs.docker.com/testcontainers/)
