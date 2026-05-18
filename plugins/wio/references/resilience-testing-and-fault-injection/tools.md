# Tools

Resilience testing tools usually cover three layers: dependency simulation, network fault injection, and platform chaos experiments. Choose the smallest blast radius that proves the behavior: use WireMock or Toxiproxy in CI, Istio for mesh-scoped service traffic faults, and Chaos Mesh or LitmusChaos for Kubernetes pod, network, node, and resource experiments. Keep experiments scoped by labels, time-boxed, and tied to assertions, probes, or SLO checks.

## Chaos Mesh

- Use for: Kubernetes-native chaos experiments against pods, networks, DNS, HTTP, JVM, stress, and cloud resources.
- Languages/ecosystem: Kubernetes CRDs; works across services written in any language.
- Why it is trusted: Its official docs define declarative CRDs such as NetworkChaos and document practical actions including delay, loss, partition, bandwidth, and netem-style faults.
- Official docs: https://chaos-mesh.org/docs/
- Good usage pattern: Scope by namespace and labels, set a short duration, and apply only from a controlled CI/staging step.

```
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: checkout-api-delay
spec:
  action: delay
  mode: one
  selector:
    namespaces:
      - checkout
    labelSelectors:
      app: checkout-api
  delay:
    latency: '250ms'
    correlation: '100'
    jitter: '50ms'
  duration: '5m'
```

## LitmusChaos

- Use for: Kubernetes chaos workflows with reusable experiments, probes, and GitOps-friendly execution.
- Languages/ecosystem: Kubernetes and cloud-native platforms; language-agnostic for application services.
- Why it is trusted: LitmusChaos is a CNCF-hosted open-source chaos engineering project, and its docs cover experiment workflows plus probes for validating steady state during chaos.
- Official docs: https://docs.litmuschaos.io/
- Good usage pattern: Use Litmus when you want repeatable chaos scenarios with explicit application selection and experiment parameters.

```
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: checkout-network-latency
  namespace: checkout
spec:
  engineState: "active"
  annotationCheck: "false"
  appinfo:
    appns: "checkout"
    applabel: "app=checkout-api"
    appkind: "deployment"
  chaosServiceAccount: pod-network-latency-sa
  experiments:
  - name: pod-network-latency
    spec:
      components:
        env:
        - name: NETWORK_LATENCY
          value: '2000'
        - name: TOTAL_CHAOS_DURATION
          value: '60'
```

## Toxiproxy

- Use for: Deterministic TCP dependency faults in integration tests, such as Redis, Postgres, Kafka, or third-party service connections.
- Languages/ecosystem: Language-agnostic TCP proxy with client libraries for Go, Python, .NET, Node.js, Java, Rust, Ruby, and others.
- Why it is trusted: Shopify’s official docs describe it as a test/CI/dev tool for simulating network conditions, with proxy APIs and broad client-library support.
- Official docs: https://github.com/Shopify/toxiproxy
- Good usage pattern: Point the application at the proxy, inject a toxic during the test, assert retry/timeout behavior, then remove the toxic in teardown. Often paired with Testcontainers.

```
toxiproxy-cli create -l localhost:26379 -u localhost:6379 checkout_test_redis
redis-cli -p 26379 SET cart:42 ready
toxiproxy-cli toxic add \
  -t latency \
  -a latency=1000 \
  -a jitter=200 \
  checkout_test_redis
redis-cli -p 26379 GET cart:42
toxiproxy-cli toxic remove \
  -n latency_downstream \
  checkout_test_redis
```

## WireMock

- Use for: HTTP dependency resilience tests, including slow responses, 5xx responses, malformed responses, and connection-level failures.
- Languages/ecosystem: Java/JVM core; also usable as a standalone server or Docker container from any language test suite.
- Why it is trusted: WireMock’s core engine is free and open source, and its official docs cover API simulation plus fault behaviors such as delays, malformed responses, and network faults.
- Official docs: https://wiremock.org/docs/simulating-faults/
- Good usage pattern: Stub the dependency behavior that should trigger client retries, circuit breaking, timeout handling, or fallback logic.

```
{
  "request": {
    "method": "POST",
    "url": "/payments/authorize"
  },
  "response": {
    "status": 503,
    "fixedDelayMilliseconds": 1500
  }
}
```

## Istio Fault Injection

- Use for: Service-mesh-level HTTP or gRPC delay and abort tests between Kubernetes services.
- Languages/ecosystem: Kubernetes with Istio service mesh; application-language agnostic.
- Why it is trusted: Istio’s official traffic-management docs include HTTPFaultInjection for injecting delays and aborts via VirtualService, including scoped examples for resilience testing.
- Official docs: https://istio.io/latest/docs/tasks/traffic-management/fault-injection/
- Good usage pattern: Gate the fault behind a test header or canary route so normal traffic keeps a default route.

```
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payments-delay
  namespace: checkout
spec:
  hosts:
  - payments.checkout.svc.cluster.local
  http:
  - match:
    - headers:
        x-resilience-test:
          exact: "true"
    fault:
      delay:
        fixedDelay: 2s
        percentage:
          value: 25
    route:
    - destination:
        host: payments.checkout.svc.cluster.local
  - route:
    - destination:
        host: payments.checkout.svc.cluster.local
```
