# Testability

## Purpose

Testability is the ability to exercise important behavior with controlled inputs, observable outputs, and deterministic dependencies without changing product behavior. Use it when the blocker is not "what should be tested?" but "this code shape makes a useful test slow, brittle, or impossible."

## Use When / Avoid When

| Use When | Avoid When |
| --- | --- |
| Dependencies, time, randomness, global state, network, storage, or framework wiring hide the behavior. | The behavior is already easy to exercise and the only decision is test level or assertion style. |
| The only available test would require private-method access, monkeypatching internals, or a broad end-to-end flow. | A refactor would change public behavior, persistence format, security posture, or API contracts without a separate migration plan. |
| A small seam would let the test control one hard dependency while preserving production wiring. | The proposed seam exists only for tests and makes production code less coherent. |

## Core Principles

- Test through public behavior; introduce seams so setup is controllable, not so assertions can inspect internals.
- Separate object graph construction from work. Constructors and module initializers should not perform hidden IO, network calls, clock reads, or background work.
- Make dependencies explicit at the boundary that owns them: constructor, function parameter, interface, port, fixture, or composition root.
- Control nondeterminism: clocks, randomness, generated IDs, concurrency, filesystem paths, locale, timezone, and external services.
- Prefer narrower changes: pure extraction, adapter interface, injectable clock/random/source, or explicit configuration beats a large architecture rewrite.
- Keep production wiring real. Tests may use doubles, but the application path should still compose real collaborators in one place.

## Decision Rules

| Situation | Better Move |
| --- | --- |
| Code calls a singleton, service locator, static global, or environment read deep inside logic. | Pass the dependency or resolved value at the module boundary; keep lookup in the composition layer. |
| Constructor starts work or reads external state. | Move work to an explicit method or factory; keep construction cheap and side-effect-light. |
| Test needs sleeps or wall-clock waits. | Inject a clock, scheduler, event, fake timer, or explicit synchronization point. |
| Test requires private method access. | Test the observable behavior, or extract a named collaborator only if the behavior has independent value. |
| Real dependency is cheap and deterministic. | Use it; mocking it may reduce fidelity without improving feedback. |
| Real dependency is expensive, nondeterministic, or outside repo control. | Use a fake/stub/mock, local emulator, contract test, or containerized dependency depending on the risk. |

## Common Failure Modes

- Adding `if test` branches or exported internals that production code should not rely on.
- Replacing all collaborators with mocks and claiming product behavior is covered.
- Injecting a huge context object that preserves hidden coupling under a different name.
- Refactoring many modules to "improve testability" before identifying the behavior and the smallest useful seam.
- Making test setup pass by weakening validation, authz, transactions, or production invariants.

## Output Guidance For Agents

- Name the testability blocker as evidence: hidden dependency, uncontrollable state, nondeterminism, or missing observation point.
- Describe the minimal seam and why it preserves product behavior.
- Keep production wiring visible and add or update tests against behavior, not the seam itself.
- State what was not changed: public API, data format, runtime behavior, external contract, or deployment config.

## Agent Checklist

- Identify the behavior and the dependency that prevents a focused test.
- Search for existing seam patterns before inventing one.
- Prefer parameterizing time, randomness, IDs, and external clients over patching globals.
- Keep construction separate from work.
- Run the narrow test and one broader impacted suite when wiring changed.

## Source Anchors

- Google Testing Blog, [Writing Testable Code](https://testing.googleblog.com/2008/08/by-miko-hevery-so-you-decided-to.html)
- Google Testing Blog, [Guide to Writing Testable Code](https://testing.googleblog.com/2008/11/guide-to-writing-testable-code.html)
- Bazel, [Test Encyclopedia](https://bazel.build/reference/test-encyclopedia)
- Google Testing Blog, [Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html)
