# Tools

Static testing tools usually fall into four buckets: lint/rule engines, type-aware analyzers, bytecode or compiler-integrated analyzers, and CI gatekeepers. Choose the native analyzer for the main language first, enable documented defaults, add stricter or security-oriented rules gradually, and make CI fail on new violations rather than relying on local editor warnings.

## ESLint

- Use for: Enforcing JavaScript code-quality rules and CI-blocking lint checks.
- Languages/ecosystem: JavaScript; TypeScript when paired with typescript-eslint.
- Why it is trusted: Its official flat config supports targeted file globs, rule configuration, and CI-friendly warning thresholds such as --max-warnings.
- Official docs: https://eslint.org/docs/latest/
- Good usage pattern:

```
// eslint.config.js
import { defineConfig } from "eslint/config";
export default defineConfig([
  {
    files: ["src/**/*.js"],
    ignores: ["dist/**"],
    rules: {
      "no-console": ["error", { allow: ["warn", "error"] }],
    },
  },
]);
// CI: npx eslint src --max-warnings 0
```

## Ruff

- Use for: Fast Python linting with Flake8-style rule families and import/code-quality checks.
- Languages/ecosystem: Python.
- Why it is trusted: Ruff has documented rule selection, stable rule status, configuration discovery, and deterministic exit codes for CI.
- Official docs: https://docs.astral.sh/ruff/
- Good usage pattern:

```
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 100
exclude = ["build", "dist", ".venv"]
[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "B"]
ignore = ["E501"]
unfixable = ["B"]
# CI: ruff check . --output-format=github
```

## SpotBugs

- Use for: Finding Java/JVM bug patterns from compiled bytecode, especially correctness and reliability defects.
- Languages/ecosystem: Java/JVM; Maven and Gradle projects.
- Why it is trusted: The Maven plugin has a documented check goal that fails builds, supports violation limits, and supports include/exclude filters for narrow suppressions.
- Official docs: https://spotbugs.readthedocs.io/en/latest/
- Good usage pattern:

```
<!-- pom.xml -->
<plugin>
  <groupId>com.github.spotbugs</groupId>
  <artifactId>spotbugs-maven-plugin</artifactId>
  <configuration>
    <failOnError>true</failOnError>
    <maxAllowedViolations>0</maxAllowedViolations>
    <excludeFilterFile>spotbugs-exclude.xml</excludeFilterFile>
  </configuration>
  <executions>
    <execution>
      <goals><goal>check</goal></goals>
    </execution>
  </executions>
</plugin>
```

## golangci-lint

- Use for: Running a curated set of Go linters consistently in local development and CI.
- Languages/ecosystem: Go.
- Why it is trusted: It documents config-file validation, v2 configuration, many built-in linters including govet, staticcheck, errcheck, and gosec, and CI-oriented flags such as --new-from-rev.
- Official docs: https://golangci-lint.run/docs/
- Good usage pattern:

```
# .golangci.yml
version: "2"
linters:
  default: none
  enable:
    - govet
    - staticcheck
    - errcheck
    - gosec
issues:
  max-issues-per-linter: 0
  max-same-issues: 0
run:
  timeout: 5m
  modules-download-mode: readonly
# CI: golangci-lint run ./... --new-from-rev=HEAD~
```

## Clippy

- Use for: Rust compiler-adjacent linting for correctness, idioms, performance, and panic-prone patterns.
- Languages/ecosystem: Rust / Cargo.
- Why it is trusted: Clippy is documented as a Cargo subcommand, ships hundreds of lint checks, supports lint levels, and can make CI fail by denying warnings.
- Official docs: https://doc.rust-lang.org/clippy/
- Good usage pattern:

```
# CI lint gate
cargo clippy --workspace --all-targets --all-features -- \
  -Dwarnings \
  -Wclippy::pedantic \
  -Dclippy::unwrap_used
```
