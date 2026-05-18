# Mocking And Test Doubles

## Purpose

Use test doubles to control dependencies while preserving the behavior risk under test. A double is a tool for isolation, determinism, speed, or boundary modeling, not a substitute for understanding the real dependency.

## Use When / Avoid When

| Use When | Avoid When |
| --- | --- |
| A dependency is slow, nondeterministic, costly, unavailable, destructive, or outside repo control. | The real dependency is cheap, deterministic, and central to the behavior claim. |
| The test needs to force rare errors, timeouts, retries, conflicts, or external responses. | The double would encode the same bug-prone logic as production. |
| The interaction itself is the contract: publish event, send email, call provider with specific request. | The assertion would only verify private call choreography. |

## Core Principles

- Prefer state/output assertions. Use interaction assertions when the externally visible behavior is the interaction.
- Choose the lightest double that preserves risk: dummy, stub, fake, spy, mock, emulator, container, or contract test.
- Keep doubles honest at boundaries with contract tests, schema validation, provider verification, or a smaller number of real-dependency integration tests.
- Do not mock the system under test. Mock collaborators at boundaries.
- Avoid strict call-order assertions unless order is part of the contract.
- Use fakes for meaningful behavior only when their rules are simpler and independently trustworthy.

## Decision Rules

| Need | Prefer |
| --- | --- |
| Return canned data or error. | Stub. |
| Record whether an external side effect was requested. | Spy or mock with focused verification. |
| Simulate a small in-memory domain dependency. | Fake with explicit limitations. |
| Validate API/message compatibility. | Contract test plus provider verification. |
| Exercise real DB/broker/cache semantics. | Containerized/local real dependency. |
| Prevent real network/payment/email. | Stub server, fake gateway, or mock at adapter boundary. |

## Common Failure Modes

- Over-mocking every collaborator, producing fast tests with low product fidelity.
- Verifying implementation call sequences instead of behavior or contract.
- Fakes that drift from production semantics.
- Patching the wrong namespace or leaving patches active across tests.
- Mocking framework, language, or library behavior instead of owning a testable adapter.

## Output Guidance For Agents

- Name the dependency replaced, why it is replaced, and what risk remains untested.
- State the double type and the contract it models.
- Keep assertions focused on observable behavior or the externally meaningful interaction.
- Add or point to an integration/contract test when the double stands in for a critical boundary.

## Agent Checklist

- Identify whether the dependency is part of the behavior claim.
- Use the real dependency if it is cheap and deterministic.
- Place doubles at ownership boundaries, not deep inside implementation.
- Avoid strict interaction checks unless the protocol is the behavior.
- Run at least one real/contract path for critical external boundaries.

## Source Anchors

- Martin Fowler, [Mocks Aren't Stubs](https://martinfowler.com/articles/mocksArentStubs.html)
- Martin Fowler, [TestDouble](https://martinfowler.com/bliki/TestDouble.html)
- Pact, [contract testing introduction](https://docs.pact.io/)
- Google Testing Blog, [Increase Test Fidelity By Avoiding Mocks](https://testing.googleblog.com/2024/02/increase-test-fidelity-by-avoiding-mocks.html)
