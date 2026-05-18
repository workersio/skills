# Tools

Mutation testing tools deliberately change production code and then rerun tests to find weak assertions. Choose by runtime, start with a narrow target package, and run it in CI or nightly jobs only after the normal test suite is stable and reasonably fast.

## PIT / PITest

- Use for: JVM mutation testing for Java and other JVM projects.
- Languages/ecosystem: Java/JVM; Maven, Gradle, JUnit, and TestNG.
- Why it is trusted: PIT is the standard JVM mutation-testing tool and documents scoped targets, reports, history, and build-failing thresholds.
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

mvn test-compile org.pitest:pitest-maven:mutationCoverage
```

## StrykerJS

- Use for: JavaScript and TypeScript mutation testing with Jest, Vitest, Mocha, Karma, and related runners.
- Languages/ecosystem: JavaScript, TypeScript, Node.js, frontend and backend test suites.
- Why it is trusted: StrykerJS documents runner integrations, mutation score thresholds, incremental mode, and HTML/CI reports.
- Official docs: https://stryker-mutator.io/docs/stryker-js/introduction/
- Good usage pattern:

```
// stryker.conf.json
{
  "$schema": "./node_modules/@stryker-mutator/core/schema/stryker-schema.json",
  "packageManager": "npm",
  "testRunner": "vitest",
  "mutate": ["src/**/*.ts", "!src/**/*.d.ts"],
  "reporters": ["html", "clear-text", "progress"],
  "thresholds": {
    "high": 80,
    "low": 70,
    "break": 70
  }
}

npx stryker run
```

## mutmut

- Use for: Python mutation testing with pytest-centered workflows.
- Languages/ecosystem: Python, pytest.
- Why it is trusted: mutmut documents incremental runs, pytest integration, configuration in `pyproject.toml`, and an interactive result browser.
- Official docs: https://mutmut.readthedocs.io/en/latest/
- Good usage pattern:

```
# pyproject.toml
[tool.mutmut]
paths_to_mutate = ["src/"]
pytest_add_cli_args_test_selection = ["tests/"]

mutmut run
mutmut browse
```

## cargo-mutants

- Use for: Rust mutation testing that works with ordinary Cargo projects.
- Languages/ecosystem: Rust / Cargo.
- Why it is trusted: cargo-mutants documents scoped mutation runs, timeouts, workspace support, and JSON/text output for automation.
- Official docs: https://mutants.rs/
- Good usage pattern:

```
cargo mutants \
  --in-place \
  --package billing-core \
  --timeout 60 \
  --output target/mutants
```

## Stryker.NET

- Use for: .NET mutation testing in C# projects.
- Languages/ecosystem: .NET, C#, test projects using common .NET test runners.
- Why it is trusted: Stryker.NET documents project selection, threshold gates, reporter options, and CI-friendly command-line usage.
- Official docs: https://stryker-mutator.io/docs/stryker-net/introduction/
- Good usage pattern:

```
dotnet stryker \
  --project src/Billing/Billing.csproj \
  --test-project tests/Billing.Tests/Billing.Tests.csproj \
  --threshold-high 80 \
  --threshold-low 70 \
  --threshold-break 70 \
  --reporter html
```
