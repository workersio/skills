# Tools

Test Suite Health Diagnostics usually needs three kinds of tools: coverage gates, mutation testing, and runner diagnostics for slow, flaky, leaky, or CI-unfriendly tests. Choose the tool native to the project runtime first; add mutation testing when coverage looks healthy but assertions may be weak; emit JUnit/XML or coverage reports so CI can trend failures over time.

## Jest

- Use for: JS/TS projects that need coverage thresholds plus diagnostics for slow tests and hanging async resources.
- Languages/ecosystem: JavaScript, TypeScript, Node.js, React and frontend test suites.
- Why it is trusted: Jest has first-class config files, build-failing coverageThreshold, slow-test reporting, and --detectOpenHandles for diagnosing tests that keep the process alive.
- Official docs: https://jestjs.io/docs/configuration
- Good usage pattern:

```
// jest.config.cjs
const { defineConfig } = require('jest');
module.exports = defineConfig({
  collectCoverage: true,
  collectCoverageFrom: ['src/**/*.{js,ts}', '!src/**/*.d.ts'],
  coverageProvider: 'v8',
  slowTestThreshold: 3,
  openHandlesTimeout: 1000,
  coverageThreshold: {
    global: { branches: 75, functions: 80, lines: 85, statements: 85 },
    './src/security/': { branches: 90, lines: 90 },
  },
});

Run leak diagnostics only when needed:

npx jest --coverage --detectOpenHandles
```

## pytest + pytest-cov

- Use for: Python projects that need coverage gates, slow-test visibility, and CI-friendly reports.
- Languages/ecosystem: Python, pytest-based unit/integration test suites.
- Why it is trusted: pytest documents built-in duration profiling, and pytest-cov provides pytest-native coverage, branch coverage, XML reports, and --cov-fail-under gates.
- Official docs: https://docs.pytest.org/en/stable/ and https://pytest-cov.readthedocs.io/en/latest/
- Good usage pattern:

```
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
  "-ra",
  "--durations=10",
  "--durations-min=0.5",
  "--cov=src/payments",
  "--cov-branch",
  "--cov-report=term-missing:skip-covered",
  "--cov-report=xml:reports/coverage.xml",
  "--cov-fail-under=85",
  "--junitxml=reports/pytest.xml"
]
```

## JaCoCo

- Use for: JVM projects that need enforceable line/branch coverage in Maven or Gradle CI.
- Languages/ecosystem: Java, Kotlin, Scala, JVM test suites.
- Why it is trusted: The JaCoCo Maven plugin supplies the runtime agent, report generation, and a check goal that fails the build when configured coverage rules are not met.
- Official docs: https://www.jacoco.org/jacoco/trunk/doc/maven.html
- Good usage pattern:

```
<!-- pom.xml -->
<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
  <executions>
    <execution>
      <goals><goal>prepare-agent</goal></goals>
    </execution>
    <execution>
      <id>coverage-check</id>
      <phase>verify</phase>
      <goals><goal>report</goal><goal>check</goal></goals>
      <configuration>
        <rules>
          <rule>
            <element>BUNDLE</element>
            <limits>
              <limit>
                <counter>BRANCH</counter>
                <value>COVEREDRATIO</value>
                <minimum>0.70</minimum>
              </limit>
              <limit>
                <counter>CLASS</counter>
                <value>MISSEDCOUNT</value>
                <maximum>0</maximum>
              </limit>
            </limits>
          </rule>
        </rules>
      </configuration>
    </execution>
  </executions>
</plugin>
```

## PIT / PITest

- Use for: JVM projects where high coverage is not enough and you need to find weak or missing assertions.
- Languages/ecosystem: Java and JVM test suites, commonly paired with JUnit and JaCoCo.
- Why it is trusted: PIT’s Maven plugin runs mutation analysis with mutationCoverage, scopes mutation via targetClasses/targetTests, and supports mutation and coverage thresholds that fail the build.
- Official docs: https://pitest.org/quickstart/maven/
- Good usage pattern:

```
<!-- pom.xml -->
<plugin>
  <groupId>org.pitest</groupId>
  <artifactId>pitest-maven</artifactId>
  <configuration>
    <targetClasses>
      <param>com.acme.billing.service*</param>
    </targetClasses>
    <targetTests>
      <param>com.acme.billing*</param>
    </targetTests>
    <mutationThreshold>75</mutationThreshold>
    <coverageThreshold>80</coverageThreshold>
    <outputFormats>
      <param>HTML</param>
      <param>XML</param>
    </outputFormats>
    <withHistory>true</withHistory>
  </configuration>
</plugin>

Run in CI or a nightly quality job:

mvn test-compile org.pitest:pitest-maven:mutationCoverage
```

## cargo-nextest

- Use for: Rust projects that need faster CI runs plus explicit diagnostics for flaky, slow, timed-out, or leaky tests.
- Languages/ecosystem: Rust, Cargo workspaces.
- Why it is trusted: nextest repository config controls profiles, retries, timeouts, and reports; it marks retry-passing tests as flaky, supports slow/timeout policies, detects some subprocess leaks, and emits JUnit XML.
- Official docs: https://nexte.st/docs/configuring-nextest/
- Good usage pattern:

```
# .config/nextest.toml
[profile.ci]
retries = 2
slow-timeout = { period = "30s", terminate-after = 4, grace-period = "10s" }
leak-timeout = { period = "500ms", result = "fail" }
status-level = "slow"
final-status-level = "flaky"
[profile.ci.junit]
path = "junit.xml"
store-failure-output = true
cargo nextest run --profile ci
```
