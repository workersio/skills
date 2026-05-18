# Tools

Regression Test Selection / Test Impact Analysis tools usually work at one of three layers: build graph selection, test-task caching, or test-framework-level affected-test selection. Choose build-graph tools for monorepos, framework selectors for single-stack repos, and coverage/runtime selectors when static dependency graphs are too coarse. Keep a scheduled full-suite run as a backstop.

## Bazel

- Use for: Multi-language monorepos where impacted tests can be selected from reverse dependencies in the build graph.
- Languages/ecosystem: Java/JVM, C/C++, Go, Python, JavaScript, Rust, Android, iOS, and rule-based extensions.
- Why it is trusted: Bazel’s docs emphasize optimized dependency analysis, caching, multi-language support, and use in large production codebases.
- Official docs: https://bazel.build/query/language
- Good usage pattern:

```
# Run tests that reverse-depend on a changed library target.
impacted="$(bazel query 'tests(rdeps(//..., //lib/payments:payments))')"
test -z "$impacted" || bazel test $impacted
```

## Gradle

- Use for: JVM and Android projects where unchanged test tasks should be skipped or restored from cache.
- Languages/ecosystem: Java, Kotlin, Scala, Groovy, Android, and JVM plugin ecosystems.
- Why it is trusted: Gradle has built-in incremental up-to-date checks, build cache support, and a cacheable built-in Test task.
- Official docs: https://docs.gradle.org/current/userguide/build_cache.html
- Good usage pattern:

```
# Preserve Gradle User Home between CI runs so test outputs can be reused.
./gradlew test --build-cache --fail-fast
```

## Nx

- Use for: JavaScript/TypeScript monorepos where CI should run tests only for projects affected by a PR.
- Languages/ecosystem: JavaScript, TypeScript, Angular, React, Node, Vite, Jest, Vitest, Playwright, and Nx plugins.
- Why it is trusted: Nx’s affected command uses Git plus the project graph to find changed projects and their dependents before running tasks.
- Official docs: https://nx.dev/docs/features/ci-features/affected
- Good usage pattern:

```
# GitHub Actions step
- run: git fetch origin main --depth=1
- run: npx nx affected -t test --base=origin/main --head=HEAD
```

## Jest

- Use for: JavaScript/TypeScript unit tests where changed source files can be mapped to related test files.
- Languages/ecosystem: JavaScript, TypeScript, Node, React, frontend and backend unit tests.
- Why it is trusted: Jest’s official CLI supports --findRelatedTests, --changedSince, --onlyChanged, --ci, and --passWithNoTests.
- Official docs: https://jestjs.io/docs/cli
- Good usage pattern:

```
mapfile -t changed < <(
  git diff --name-only --diff-filter=ACMR origin/main...HEAD -- 'src/**/*.ts' 'src/**/*.tsx'
)
((${#changed[@]} == 0)) || npx jest --ci --findRelatedTests "${changed[@]}" --passWithNoTests
```

## pytest-testmon

- Use for: Python pytest suites that need test-level selection based on observed code dependencies.
- Languages/ecosystem: Python, pytest; internally uses Coverage.py dependency data.
- Why it is trusted: The official docs describe collecting dependencies between tests and executed code, storing .testmondata, and rerunning only affected tests after changes.
- Official docs: https://www.testmon.org/
- Good usage pattern:

```
# Cache .cache/testmon/.testmondata between CI runs.
mkdir -p .cache/testmon
TESTMON_DATAFILE=.cache/testmon/.testmondata pytest --testmon --testmon-env=ci
```
