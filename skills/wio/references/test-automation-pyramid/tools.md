# Tools

For a Test Automation Pyramid, use one fast unit-test framework per runtime, one integration-test harness for real dependencies, and one end-to-end runner for a small number of user-critical flows. Choose based on where most defects appear: unit tools for fast feedback, Testcontainers-style tools for service/data-layer confidence, and browser tools only for high-value journeys.

## pytest

- Use for: Fast Python unit and integration tests with reusable fixtures and parametrized cases.
- Languages/ecosystem: Python; commonly paired with coverage.py, tox/nox, pytest-xdist, and Testcontainers for Python.
- Why it is trusted: Official docs cover fixtures, parametrization, markers, configuration, CI practices, and plugin discovery, which makes it practical across pyramid layers.
- Official docs: https://docs.pytest.org/en/stable/
- Good usage pattern:

```
# tests/unit/test_pricing.py
import pytest
from shop.pricing import total_cents
@pytest.fixture
def cart():
    return [{"sku": "A-1", "price_cents": 1200, "qty": 2}]
@pytest.mark.parametrize(
    "coupon, expected",
    [("NONE", 2400), ("TEN_OFF", 2160)],
)
def test_total_cents_applies_coupon(cart, coupon, expected):
    assert total_cents(cart, coupon=coupon) == expected
```

## JUnit Jupiter / JUnit Platform

- Use for: JVM unit tests and service-layer tests in Java, Kotlin, Scala, and Groovy projects.
- Languages/ecosystem: JVM; integrates with Gradle, Maven, IDEs, AssertJ, Mockito, Spring Test, and Testcontainers.
- Why it is trusted: JUnit Platform has first-class support in major IDEs and build tools, and its user guide documents assertions, parameterized tests, build support, and extensions.
- Official docs: https://docs.junit.org/current/user-guide/
- Good usage pattern:

```
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import static org.junit.jupiter.api.Assertions.assertEquals;
class TaxCalculatorTest {
    private final TaxCalculator calculator = new TaxCalculator();
    @ParameterizedTest
    @CsvSource({
        "10000, CA, 10725",
        "10000, OR, 10000"
    })
    void totalsIncludeStateTax(int subtotalCents, String state, int expectedCents) {
        assertEquals(expectedCents, calculator.totalCents(subtotalCents, state));
    }
}
```

## Jest

- Use for: JavaScript/TypeScript unit tests, module tests, and UI-adjacent tests that need mocks.
- Languages/ecosystem: Node.js; common in React, React Native, Babel, and TypeScript projects.
- Why it is trusted: Official docs document configuration files, mock functions, matchers, CLI use, and coverage thresholds that fail CI when minimum coverage is not met.
- Official docs: https://jestjs.io/docs/getting-started
- Good usage pattern:

```
// invoice.test.js
const { calculateInvoice } = require('./invoice');
test('publishes invoice event with calculated total', () => {
  const publish = jest.fn();
  const invoice = calculateInvoice(
    [{ sku: 'A-1', priceCents: 1000, quantity: 2 }],
    { publish }
  );
  expect(invoice.totalCents).toBe(2000);
  expect(publish).toHaveBeenCalledWith(expect.objectContaining({
    type: 'invoice.created',
    totalCents: 2000,
  }));
});
```

## Testcontainers

- Use for: Middle-layer integration tests against real disposable dependencies such as databases, brokers, and service fakes.
- Languages/ecosystem: Java, Go, .NET, Node.js, Python, Rust, Ruby, and more; pair it with the native test framework for that runtime.
- Why it is trusted: The official site describes it as an open source library for throwaway containerized dependencies and documents broad language support plus database/message-broker modules.
- Official docs: https://testcontainers.com/
- Good usage pattern:

```
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import java.sql.DriverManager;
import static org.junit.jupiter.api.Assertions.assertEquals;
@Testcontainers
class AccountRepositoryIT {
    @Container
    static PostgreSQLContainer<?> postgres =
        new PostgreSQLContainer<>("postgres:16-alpine");
    @Test
    void storesAndReadsAccountRows() throws Exception {
        try (var connection = DriverManager.getConnection(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())) {
            connection.createStatement()
                .execute("create table accounts(id int primary key, email text)");
            connection.createStatement()
                .execute("insert into accounts values (1, 'a@example.com')");
            var rows = connection.createStatement()
                .executeQuery("select count(*) from accounts");
            rows.next();
            assertEquals(1, rows.getInt(1));
        }
    }
}
```

## Playwright

- Use for: A small top-pyramid suite of browser end-to-end tests for critical user flows.
- Languages/ecosystem: JavaScript/TypeScript primary; also supports Python, Java, and .NET.
- Why it is trusted: Official docs cover test configuration, CI-safe options such as retries and forbidOnly, web-server startup, locators, and auto-waiting web assertions.
- Official docs: https://playwright.dev/docs/intro
- Good usage pattern:

```
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './e2e',
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
// e2e/checkout.spec.ts
import { test, expect } from '@playwright/test';
test('checkout reaches payment step', async ({ page }) => {
  await page.goto('/cart');
  await page.getByRole('button', { name: 'Checkout' }).click();
  await expect(page.getByRole('heading', { name: 'Payment' })).toBeVisible();
});
```
