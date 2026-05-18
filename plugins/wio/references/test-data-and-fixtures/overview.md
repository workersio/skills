# Test Data And Fixtures

## Purpose

Create test data that is minimal, isolated, deterministic, readable, and representative of the behavior under test. Good fixture design makes failures diagnose behavior instead of setup noise.

## Use When / Avoid When

| Use When | Avoid When |
| --- | --- |
| Tests need database rows, files, users, accounts, messages, API responses, clocks, or generated values. | The test has no stateful setup and inline literals are clearer. |
| Existing fixtures are shared, huge, order-dependent, or hard to understand. | Reusing a production dump would expose sensitive data or unstable assumptions. |
| A failure may come from setup leakage, uniqueness collisions, time, locale, or teardown. | The main risk is not data setup but incorrect oracle or test level. |

## Core Principles

- Use the smallest data that expresses the behavior. Every field should either matter or be a clear valid default.
- Isolate tests: unique identities, independent accounts/tenants, temporary paths, transaction rollback, or cleanup.
- Prefer builders/factories for valid defaults; override only fields relevant to the case.
- Make randomness reproducible: fixed seed, recorded seed, or deterministic examples.
- Keep fixture scope narrow. Shared global fixtures should be stable, read-only, and cheap.
- Never copy production PII/secrets into tests; anonymize or synthesize representative data.

## Decision Rules

| Data Need | Better Pattern |
| --- | --- |
| One simple value or object. | Inline literal or local helper. |
| Many valid domain objects with small variations. | Factory/builder with traits and explicit overrides. |
| Persistence semantics matter. | Real test database/container with migrations and cleanup. |
| External API payloads matter. | Contract fixture, schema-valid example, or stub response near the test. |
| Large generated input space. | Property-based generators with constraints and seeds. |
| Regression from real data shape. | Minimal anonymized reproducer, not a broad production dump. |

## Common Failure Modes

- Mystery fixtures: large shared setup where the relevant fields are invisible.
- Order dependence from shared mutable accounts, static caches, or non-unique names.
- Factories that silently create many unrelated records and slow the suite.
- Random fake data that changes failures or hides edge cases.
- Cleanup in `after` hooks that does not run after setup failure; prefer rollback or safe teardown patterns.

## Output Guidance For Agents

- Show the data fields that matter to the behavior and hide irrelevant defaults behind local builders.
- State isolation mechanism: transaction, temp directory, unique ID, cleanup, container, or fake clock.
- Record seeds or generated examples for randomized/property failures.
- Avoid adding broad global fixtures unless multiple tests genuinely share stable setup.

## Agent Checklist

- Identify the minimum valid data for the behavior.
- Keep setup local unless reuse is clearly valuable.
- Use unique identities for persisted or external resources.
- Control time, randomness, locale, and timezone.
- Verify cleanup/rollback happens even on failure.

## Source Anchors

- pytest, [fixtures and safe teardowns](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- Cypress, [test isolation](https://docs.cypress.io/app/core-concepts/writing-and-organizing-tests)
- factory_bot, [factory definitions and sequences](https://thoughtbot.github.io/factory_bot/)
- Faker, [repeatable fake data guidance](https://faker.readthedocs.io/)
