# Tools

For flaky test detection and management, the practical tools are usually test runners or runner plugins that can re-run only failures, label pass-after-retry tests as flaky, emit CI-readable reports, and optionally fail the build when flakes appear. Choose the tool that matches the project’s runtime first, then prefer configurations that make flakes visible rather than silently hiding them.

## Playwright Test

- Use for: Browser/E2E suites where retries, trace capture, and flaky classification should be built into the test runner.
- Languages/ecosystem: JavaScript/TypeScript, with Playwright ecosystems for web testing.
- Why it is trusted: Playwright Test officially categorizes results as passed, flaky, or failed when retries are enabled, and supports first-retry traces for debugging.
- Official docs: https://playwright.dev/docs/test-retries
- Good usage pattern:

```
// playwright.config.ts
import { defineConfig } from '@playwright/test';
export default defineConfig({
  retries: process.env.CI ? 2 : 0,
  reporter: [['list'], ['junit', { outputFile: 'test-results/junit.xml' }]],
  use: {
    trace: 'on-first-retry',
  },
});
```

## pytest-rerunfailures

- Use for: Python test suites that need pytest-native retries, per-test flaky marks, and CI failure on detected flakes.
- Languages/ecosystem: Python / pytest.
- Why it is trusted: The pytest-rerunfailures docs cover global retries, per-test @pytest.mark.flaky, exception filtering, and --fail-on-flaky exit behavior.
- Official docs: https://pytest-rerunfailures.readthedocs.io/latest/
- Good usage pattern:

```
# pytest.ini
[pytest]
reruns = 2
reruns_delay = 1
addopts =
    --fail-on-flaky
    --only-rerun TimeoutError
    --only-rerun ConnectionError
```

## Apache Maven Surefire / Failsafe

- Use for: JVM projects using Maven that need retry-based flake detection for unit tests and integration tests.
- Languages/ecosystem: Java/JVM; JUnit 4, JUnit 5, TestNG-adjacent Maven test workflows.
- Why it is trusted: Maven Surefire/Failsafe are Apache Maven’s standard test plugins; their docs support rerunFailingTestsCount, flaky XML report elements, and failOnFlakeCount gates.
- Official docs: https://maven.apache.org/surefire/maven-surefire-plugin/examples/rerun-failing-tests.html
- Good usage pattern:

```
<!-- pom.xml: fail CI when a unit test passes only after retry -->
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-surefire-plugin</artifactId>
  <configuration>
    <rerunFailingTestsCount>2</rerunFailingTestsCount>
    <failOnFlakeCount>1</failOnFlakeCount>
  </configuration>
</plugin>

Use the Failsafe equivalent for integration tests run in verify.
```

## gotestsum

- Use for: Go projects that want go test output, JUnit reports, JSON logs, and failed-test reruns in CI.
- Languages/ecosystem: Go.
- Why it is trusted: gotestsum wraps go test, writes JUnit XML and JSON logs, re-runs failed tests, and documents guardrails such as max failure limits before reruns.
- Official docs: https://github.com/gotestyourself/gotestsum
- Good usage pattern:

```
gotestsum \
  --format=pkgname \
  --junitfile=reports/go-tests.xml \
  --jsonfile=reports/go-tests.jsonl \
  --rerun-fails=2 \
  --rerun-fails-max-failures=5 \
  --packages="./..." \
  -- -count=1 -race
```

## cargo-nextest

- Use for: Rust workspaces that need fast CI test runs with retries, flaky marking, per-profile policy, and JUnit output.
- Languages/ecosystem: Rust / Cargo.
- Why it is trusted: cargo-nextest officially marks pass-after-retry tests as flaky, supports flaky-result = "fail", per-test overrides, delay/backoff, and JUnit flaky tags.
- Official docs: https://nexte.st/docs/features/retries/
- Good usage pattern:

```
# .config/nextest.toml
# CI command: cargo nextest run --profile ci
[profile.ci]
fail-fast = false
retries = { backoff = "fixed", count = 2, delay = "1s" }
flaky-result = "fail"
[[profile.ci.overrides]]
filter = 'test(remote_api)'
retries = { backoff = "exponential", count = 2, delay = "5s", jitter = true }
```
