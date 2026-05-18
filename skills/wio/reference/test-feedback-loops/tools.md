# Test Feedback Loops Tools

Use loop tooling to make test signal fast, visible, and attributable. The tool should answer: what ran, why it ran, how long it took, what failed, whether it retried, and who owns the failure.

## Tool Categories

| Category | Evidence It Provides | Caveats |
| --- | --- | --- |
| Local scripts | Developer-facing commands and focused suite selection. | Scripts may drift from CI. |
| CI workflow config | Blocking gates, matrix, cache, artifacts, retries, schedules. | Green status may hide non-blocking or retried failures. |
| Test reports | JUnit XML, coverage XML/LCOV, HTML reports, traces, screenshots. | Reports must be uploaded even on failure to be useful. |
| Flake/runtime analytics | Same-commit pass/fail, retry rate, slowest tests, ownership. | Vendor dashboards need correct test identity and metadata. |
| Production checks | Synthetic monitors, canaries, SLO dashboards, alerting. | Production signal is late; use only for risks pre-prod cannot cheaply observe. |

## Repo Signals To Inspect

| Signal | Common Patterns | Evidence | False Positives |
| --- | --- | --- | --- |
| Package scripts | `test`, `test:unit`, `test:integration`, `test:e2e`, `ci`, `coverage`. | Supported local loops. | Scripts may be unused or broken. |
| CI jobs | `.github/workflows`, `.gitlab-ci.yml`, `buildkite`, `circleci`, `azure-pipelines`. | Blocking vs scheduled loops and artifact policy. | Job names may not match actual test scope. |
| Retry config | `retries`, `flaky`, `rerun`, `--reruns`, `continue-on-error`, `allow_failure`. | Hidden instability or accepted risk. | Retries can be legitimate for known external instability if tracked. |
| Report output | `junit.xml`, `coverage.xml`, `lcov.info`, Playwright/Cypress traces. | Machine-readable diagnostics. | Generated reports may not be uploaded. |
| Time split/sharding | `matrix`, `shard`, `parallel`, `xdist`, Bazel targets. | Suite runtime management. | Parallelism can hide shared-state leaks. |

## Common Commands And Patterns

| Goal | Starting Commands |
| --- | --- |
| Find local test commands | `rg "\"test|test:|ci|coverage|e2e|integration\"" package.json pyproject.toml tox.ini noxfile.py Makefile justfile Taskfile.yml pom.xml build.gradle Cargo.toml` |
| Inspect CI loops | `rg "test|coverage|junit|artifact|matrix|schedule|retry|allow_failure|continue-on-error|shard|parallel" .github .gitlab-ci.yml buildkite* .circleci azure-pipelines.yml` |
| Find report config | `rg "junit|lcov|coverage.xml|html-report|trace|screenshot|artifact|upload-artifact|reports:junit" .` |
| Find quarantine/skips | `rg "skip|xfail|todo|quarantine|flaky|only\\(" test tests e2e src` |
| Find long tests | Use runner support: `pytest --durations=20`, Jest `slowTestThreshold`, Playwright HTML report, Gradle/Maven test reports, Bazel timing logs. |

## Evidence Rules

- Always separate first-attempt failures from retry-passing results when data exists.
- A proposed PR gate should include expected scope and why it is stable enough to block.
- A proposed scheduled job should include owner, cadence, and action on failure.
- Report whether artifacts are available for diagnosing high-level failures.

## Source Anchors

- GitHub Actions, [matrix jobs](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs)
- GitLab, [JUnit test reports](https://docs.gitlab.com/ee/ci/testing/unit_test_reports.html)
- Bazel, [test encyclopedia](https://bazel.build/reference/test-encyclopedia)
- Playwright, [CI and traces in best practices](https://playwright.dev/docs/best-practices)
