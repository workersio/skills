# Tools

For Performance, Load, and Stress Testing, the useful tool types are: code-driven scenario engines for realistic user flows, protocol-oriented runners for broad backend coverage, and compact fixed-rate generators for quick capacity probes. Choose by workload model, protocol support, scripting language, CI pass/fail thresholds, and whether you need distributed load generation or only repeatable local regression checks.

## Grafana k6

- Use for: API and service load tests as code with CI-friendly thresholds.
- Languages/ecosystem: Go engine; JavaScript/TypeScript test scripts; Grafana/Prometheus-friendly.
- Why it is trusted: Official docs describe k6 as open source, Go-based, scriptable in JavaScript/TypeScript, and designed around checks plus thresholds for automation.
- Official docs: https://grafana.com/docs/k6/latest/
- Good usage pattern:

```
import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = {
  scenarios: {
    steady_api_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 20 },
        { duration: '2m', target: 20 },
        { duration: '30s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<400'],
    checks: ['rate>0.95'],
  },
};
export default function () {
  const baseUrl = __ENV.BASE_URL || 'https://staging.example.com';
  const res = http.get(`${baseUrl}/api/products?limit=20`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'returns JSON': (r) =>
      String(r.headers['Content-Type']).includes('application/json'),
  });
  sleep(1);
}
```

## Apache JMeter

- Use for: Broad protocol coverage, GUI-assisted test-plan creation, and headless load execution.
- Languages/ecosystem: Java/JVM; JMX test plans; Groovy/JSR223 scripting; Maven/Gradle/Jenkins integrations.
- Why it is trusted: Apache documents JMeter as open-source, pure Java, multi-protocol, extensible, and explicitly recommends CLI mode for load testing.
- Official docs: https://jmeter.apache.org/usermanual/
- Good usage pattern:

```
# perf/orders.jmx contains:
# Thread Group + HTTP Request Defaults + HTTP Samplers + JSON/Response Assertions.
jmeter -n \
  -t perf/orders.jmx \
  -l build/jmeter/orders.jtl \
  -j build/jmeter/jmeter.log \
  -e -o build/jmeter/html \
  -Jbase_url=https://staging.example.com \
  -Jusers=200 \
  -Jramp_seconds=120 \
  -Jduration_seconds=600
```

## Locust

- Use for: Python-coded user journeys with custom logic, fixtures, and distributed execution.
- Languages/ecosystem: Python; gevent-based concurrency; optional web UI or headless CLI.
- Why it is trusted: Locust docs cover headless execution, Python locustfiles, custom response validation, and distributed master/worker load generation.
- Official docs: https://docs.locust.io/en/stable/
- Good usage pattern:

```
# CI run:
# locust -f locustfile.py --headless --users 200 --spawn-rate 20 \
#   --run-time 10m --host https://staging.example.com
from locust import HttpUser, task, between
class ApiUser(HttpUser):
    wait_time = between(1, 3)
    @task(3)
    def browse_products(self):
        with self.client.get(
            "/api/products?limit=20",
            name="GET /api/products",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"unexpected status {resp.status_code}")
                return
            try:
                items = resp.json().get("items", [])
            except ValueError:
                resp.failure("invalid JSON")
                return
            if not items:
                resp.failure("empty product list")
    @task(1)
    def view_cart(self):
        self.client.get("/api/cart", name="GET /api/cart")
```

## Gatling

- Use for: JVM-centered, code-driven HTTP load tests with precise injection models and post-run assertions.
- Languages/ecosystem: JVM; Java, JavaScript, TypeScript, Scala, and Kotlin SDKs.
- Why it is trusted: Gatling’s main project is Apache-2.0 licensed, and its docs define code SDKs, open/closed workload injection, checks, and assertions that fail simulations when violated.
- Official docs: https://docs.gatling.io/
- Good usage pattern:

```
import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;
import java.time.Duration;
import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;
public class OrdersSimulation extends Simulation {
  HttpProtocolBuilder httpProtocol = http
      .baseUrl(System.getProperty("baseUrl", "https://staging.example.com"))
      .acceptHeader("application/json");
  ScenarioBuilder scn = scenario("orders-api")
      .exec(http("list orders")
          .get("/api/orders?limit=20")
          .check(status().is(200)));
  {
    setUp(
        scn.injectOpen(
            rampUsersPerSec(1).to(25).during(Duration.ofSeconds(60)),
            constantUsersPerSec(25).during(Duration.ofMinutes(3))
        ).protocols(httpProtocol)
    ).assertions(
        global().responseTime().percentile3().lt(500),
        forAll().failedRequests().percent().lte(1.0)
    );
  }
}
```

## Vegeta

- Use for: Constant-rate HTTP load probes, capacity checks, and small CI performance gates.
- Languages/ecosystem: Go CLI and Go library; UNIX pipeline style.
- Why it is trusted: Official docs describe Vegeta as a CLI/library with constant-rate attacks, UNIX composability, reporting, distributed use, and JSON report output.
- Official docs: https://github.com/tsenart/vegeta
- Good usage pattern:

```
mkdir -p build/vegeta
cat > targets.http <<EOF
GET https://staging.example.com/api/products?limit=20
EOF
vegeta attack \
  -rate=50/s \
  -duration=5m \
  -name=products \
  -targets=targets.http \
  | tee build/vegeta/products.bin \
  | vegeta report
vegeta report -type=json build/vegeta/products.bin > build/vegeta/products.json
jq -e \
  '.success >= 0.99 and .latencies["95th"] < 400000000' \
  build/vegeta/products.json
```
