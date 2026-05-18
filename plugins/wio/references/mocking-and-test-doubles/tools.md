# Mocking And Test Doubles Tools

Prefer the repo's existing double framework. Add a new tool only when the current stack cannot model the boundary cleanly.

## Tool Categories

| Category | Examples | Evidence/Use |
| --- | --- | --- |
| Mock/spy libraries | unittest.mock, Mockito, Jest mocks, Sinon, Moq, NSubstitute, GoogleMock. | Replace collaborators and verify externally meaningful calls. |
| Stub servers/service virtualization | WireMock, MockServer, MSW, local HTTP handlers. | Control HTTP/API responses and failure modes. |
| Contract testing | Pact, OpenAPI/AsyncAPI validators, schema compatibility tools. | Check consumer/provider agreement without full environment. |
| Disposable real dependencies | Testcontainers, docker compose, local emulators. | Use real DB/broker/cache/provider-like behavior in integration tests. |
| In-memory fakes | Repository fakes, fake clocks, fake queues, fake email/payment gateways. | Fast deterministic behavior when semantics are simple and owned. |

## Repo Signals To Inspect

| Signal | Common Patterns | Evidence | Caveats |
| --- | --- | --- | --- |
| Mock framework imports | `mock`, `patch`, `Mockito`, `jest.fn`, `vi.fn`, `sinon`, `Moq`, `NSubstitute`. | Established double style and patching capabilities. | Imports do not prove the double is appropriate. |
| Adapter boundaries | `Gateway`, `Client`, `Repository`, `Port`, `Adapter`, `Provider`. | Natural place to substitute dependencies. | Naming may be inconsistent. |
| Contract artifacts | `pacts/`, OpenAPI specs, protobuf schemas, schema snapshots. | Doubles may be kept honest by contracts. | Contract files need provider verification to matter. |
| Fake infrastructure | `FakeClock`, `InMemory`, `StubServer`, `MockServer`, `LocalStack`. | Repo already has deterministic substitutes. | Fakes can drift or hide production behavior. |
| Strict verification | `verifyNoMoreInteractions`, exact call order, broad snapshots of calls. | Brittle interaction testing risk. | Some protocols require exact sequencing. |

## Common Commands And Patterns

| Goal | Starting Commands |
| --- | --- |
| Find double usage | `rg "jest\\.fn|vi\\.fn|sinon|Mockito|mock\\(|patch\\(|MagicMock|Moq|NSubstitute|GoogleMock|EXPECT_CALL" test tests src` |
| Find strict interaction checks | `rg "verifyNoMoreInteractions|InOrder|toHaveBeenCalledTimes|calledOnce|EXPECT_CALL|assert_called_once" test tests` |
| Find boundary adapters | `rg "Client|Gateway|Adapter|Repository|Provider|Port|Service" src` |
| Find contract tooling | `rg "pact|openapi|swagger|asyncapi|protobuf|buf|schema" .` |
| Find real dependency harnesses | `rg "testcontainers|docker-compose|wiremock|mockserver|localstack|msw|nock" .` |

## Evidence Rules

- A mock is justified when it removes irrelevant cost/nondeterminism or verifies a meaningful outbound protocol.
- A fake is justified when its semantics are smaller than production and still representative for the behavior.
- A container/emulator is justified when real dependency semantics are the risk.
- Flag tests that would pass if production never integrated with the real provider.

## Source Anchors

- Python, [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- Mockito, [documentation](https://site.mockito.org/)
- Pact, [consumer tests](https://docs.pact.io/implementation_guides/javascript/docs/consumer)
- Docker, [Testcontainers](https://docs.docker.com/testcontainers/)
