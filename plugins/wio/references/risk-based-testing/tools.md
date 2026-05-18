# Tools

Risk-Based Testing is mostly implemented with tools that support risk tagging and selection, plus targeted gates for high-impact risks such as critical user journeys, performance/SLO failure, and security exposure. Choose test frameworks for the code/runtime where most defects are introduced, then add specialized tools only for risk classes that need separate evidence, such as browser flows, load thresholds, or web security scans.

## pytest

- Use for: Risk-tiered Python unit, integration, API, and service tests using markers.
- Languages/ecosystem: Python.
- Why it is trusted: pytest has first-party support for custom markers, CLI selection with -m, and strict marker validation to catch mistyped risk labels in CI.
- Official docs: https://docs.pytest.org/en/stable/how-to/mark.html
- Good usage pattern: Register risk markers, run high-risk tests first, and fail fast before broader regression.

```
# tests/test_transfer_limits.py
import pytest
@pytest.mark.risk_high
@pytest.mark.parametrize("amount, expected_status", [(100, "approved"), (10_001, "review")])
def test_transfer_limit_policy(api_client, amount, expected_status):
    response = api_client.post("/transfers", json={"amount": amount, "currency": "USD"})
    assert response.status_code == 200
    assert response.json()["status"] == expected_status
# CI example:
# pytest --strict-markers -m risk_high --maxfail=1
```

## JUnit Platform / JUnit Jupiter

- Use for: Risk-tagged JVM tests where Java/Kotlin services need selective execution by business-critical areas.
- Languages/ecosystem: Java, Kotlin, JVM; works with Gradle, Maven, IDEs, and other JUnit Platform engines.
- Why it is trusted: JUnit’s official docs define @Tag for tagging and filtering tests, and document native build-tool filtering through Gradle’s includeTags.
- Official docs: https://docs.junit.org/current/user-guide/
- Good usage pattern: Put risk tags close to the test, then let the build select only high-risk tags for a fast pre-merge lane.

```
import static org.junit.jupiter.api.Assertions.assertThrows;
import java.math.BigDecimal;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
@Tag("risk-high")
class TransferPolicyTest {
    private final TransferService service = new TransferService();
    @Test
    void requiresReviewForLargeTransfer() {
        assertThrows(ReviewRequiredException.class,
            () -> service.authorizeTransfer("acct-1", "acct-2", BigDecimal.valueOf(10_001)));
    }
}
// Gradle selection:
// test { useJUnitPlatform { includeTags("risk-high") } }
```

## Playwright Test

- Use for: High-risk browser journeys such as checkout, login, onboarding, entitlement, and payment flows.
- Languages/ecosystem: TypeScript/JavaScript first; Playwright also documents Python, Java, and .NET entry points.
- Why it is trusted: Playwright Test has built-in tags, annotations, and --grep/--grep-invert filtering for running only selected risk classes.
- Official docs: https://playwright.dev/docs/test-annotations
- Good usage pattern: Tag business-critical journey tests and run them before full UI regression; pair with API tests for setup data.

```
import { test, expect } from '@playwright/test';
test.describe('checkout', { tag: '@risk-high' }, () => {
  test('large card payment is sent to manual review', async ({ page }) => {
    await page.goto('/checkout');
    await page.getByLabel('Amount').fill('10001');
    await page.getByRole('button', { name: 'Pay' }).click();
    await expect(page.getByText('Manual review required')).toBeVisible();
  });
});
// CI example:
// npx playwright test --grep @risk-high
```

## k6

- Use for: Performance-risk testing with SLO-style thresholds that fail CI when latency or error budgets are exceeded.
- Languages/ecosystem: JavaScript test scripts; Go-based runtime.
- Why it is trusted: k6 thresholds are documented as pass/fail criteria, and failed thresholds produce a non-zero exit code; scenarios model separate traffic patterns.
- Official docs: https://grafana.com/docs/k6/latest/using-k6/thresholds/
- Good usage pattern: Encode the risk as a threshold, not just a report; use scenario-specific checks for critical endpoints.

```
import http from 'k6/http';
import { check } from 'k6';
export const options = {
  scenarios: {
    checkout: { executor: 'constant-vus', vus: 20, duration: '3m' },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    'http_req_duration{scenario:checkout}': ['p(95)<500'],
    checks: ['rate>0.99'],
  },
};
export default function () {
  const res = http.post(`${__ENV.BASE_URL}/checkout`, JSON.stringify({ sku: 'plan-pro' }), {
    headers: { 'Content-Type': 'application/json' },
  });
  check(res, {
    'checkout accepted': (r) => r.status === 201,
  });
}
```

## OWASP ZAP

- Use for: Security-risk regression on deployed web apps and APIs, especially passive baseline scans in CI/CD.
- Languages/ecosystem: Platform/tooling; typically run via Docker in CI.
- Why it is trusted: The official ZAP baseline scan is documented for CI/CD use, supports rule configs that change alerts to FAIL or IGNORE, and returns exit codes for build gating.
- Official docs: https://www.zaproxy.org/docs/docker/baseline-scan/
- Good usage pattern: Generate a baseline rule file once, promote security-relevant rules to FAIL, and keep accepted false positives explicit.

```
# Generate once, then edit selected rules from WARN to FAIL or IGNORE:
docker run --rm -v "$(pwd):/zap/wrk/:rw" ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t "$APP_URL" -g zap-rules.conf
# CI gate:
docker run --rm -v "$(pwd):/zap/wrk/:rw" ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t "$APP_URL" -c zap-rules.conf -r zap-report.html
```
