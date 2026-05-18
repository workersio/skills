# Test Data And Fixtures Tools

Use fixture tooling to reduce setup noise while preserving the facts that make the test meaningful. Prefer explicit local setup for one-off cases and factories/builders for repeated valid defaults.

## Tool Categories

| Category | Examples | Evidence/Use |
| --- | --- | --- |
| Fixture systems | pytest fixtures, JUnit extensions, RSpec fixtures/hooks, Jest/Vitest setup, xUnit fixtures. | Scoped setup/teardown and dependency injection into tests. |
| Factories/builders | factory_bot, factory_boy, object mothers, test data builders. | Valid defaults with relevant overrides. |
| Fake data generators | Faker, Bogus, language-specific generators. | Synthetic names, emails, addresses, IDs, payloads. |
| Data reset/isolation | Transactions, truncation, temp dirs, containers, test schemas, rollback fixtures. | Repeatable state across runs and parallel workers. |
| Seed/migration tools | DB migrations, seed scripts, fixture loaders, schema snapshots. | Production-like schema and baseline reference data. |

## Repo Signals To Inspect

| Signal | Common Patterns | Evidence | Caveats |
| --- | --- | --- | --- |
| Fixture files | `fixtures/`, `testdata/`, `__fixtures__`, `conftest.py`, `setupTests`. | Shared setup and reusable examples. | Large fixture files often hide relevance. |
| Factories/builders | `Factory`, `Builder`, `factory_bot`, `factory_boy`, `Mother`. | Preferred valid object creation path. | Factories may create excessive associated data. |
| DB cleanup | `transaction`, `rollback`, `truncate`, `DatabaseCleaner`, `beforeEach`, `afterEach`. | Isolation strategy. | Cleanup after failure may be unreliable. |
| Random/fake data | `Faker`, `chance`, `random`, `seed`, `uuid`. | Data variation or uniqueness strategy. | Unseeded data creates nondeterministic failures. |
| Parallel workers | `xdist`, `parallel`, `shard`, `matrix`, worker IDs. | Need unique DB/schema/files/accounts per worker. | Passing serially does not prove parallel isolation. |

## Common Commands And Patterns

| Goal | Starting Commands |
| --- | --- |
| Find fixture roots | `rg --files | rg "(fixture|fixtures|testdata|__fixtures__|conftest|setupTests|TestData)"` |
| Find factories/builders | `rg "Factory|factory_bot|factory_boy|Builder|Mother|trait|sequence" test tests spec src` |
| Find cleanup/isolation | `rg "rollback|transaction|truncate|cleanup|tearDown|afterEach|afterAll|tmpdir|tmp_path|TempDir|DatabaseCleaner" test tests` |
| Find randomness | `rg "Faker|faker|random|seed|uuid|Date\\.now|time\\.Now" test tests src` |
| Find test DB/container setup | `rg "DATABASE_URL|testcontainers|docker-compose|migrate|schema|seed" .` |

## Evidence Rules

- A fixture should make the behavior easier to see; if it hides relevant facts, inline or localize it.
- Shared mutable fixtures need proof of isolation across order and parallel execution.
- Random data must be seeded or its failing example must be recorded.
- Factories should create the minimum valid graph unless the association is the behavior.

## Source Anchors

- pytest, [fixture system](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- factory_boy, [documentation](https://factoryboy.readthedocs.io/)
- factory_bot, [documentation](https://thoughtbot.github.io/factory_bot/)
- Docker, [Testcontainers](https://docs.docker.com/testcontainers/)
