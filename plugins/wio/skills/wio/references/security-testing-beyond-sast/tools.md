# Tools

Security testing beyond SAST usually needs a mix of dynamic web/API testing, dependency and SBOM checks, container/IaC scanning, secret leakage detection, and fuzzing. Choose tools by where they give a CI-friendly signal: block high-confidence regressions, produce reviewable reports, and keep noisy or unauthenticated checks out of merge-blocking paths.

## OWASP ZAP

- Use for: Dynamic application security testing of running web apps and APIs.
- Languages/ecosystem: Language-agnostic; best for HTTP services, browser apps, and API backends.
- Why it is trusted: ZAP has official Docker automation, CI-oriented baseline scans, rule configuration, and documented exit codes.
- Official docs: https://www.zaproxy.org/docs/
- Good usage pattern: Run a passive baseline against a deployed test environment; make only selected findings merge-blocking.

```
cat > zap-rules.conf <<'EOF'
10020	FAIL	(X-Frame-Options Header Scanner)
10021	FAIL	(X-Content-Type-Options Header Missing)
10015	WARN	(Cache-control headers)
*	OUTOFSCOPE	.*\.(png|jpg|css|js)$
EOF
docker run --rm -v "$PWD:/zap/wrk:rw" ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t "$APP_URL" -c zap-rules.conf -I -J zap-report.json -m 3 -s
```

## Trivy

- Use for: Vulnerability, secret, misconfiguration, and license scanning across repos, images, IaC, and Kubernetes artifacts.
- Languages/ecosystem: Containers, Linux OS packages, Kubernetes, Terraform/Kubernetes YAML, and lockfiles for JavaScript, Python, Java, Go, Rust, .NET, and others.
- Why it is trusted: Official docs cover multiple scanners, broad language coverage, and CI-friendly severity/exit-code gating.
- Official docs: https://trivy.dev/docs/
- Good usage pattern: Gate high/critical findings before deploy; separate repo scans from final image scans.

```
set -euo pipefail
trivy fs \
  --scanners vuln,misconfig,secret \
  --severity HIGH,CRITICAL \
  --exit-code 1 .
trivy image \
  --scanners vuln,secret \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  --exit-code 1 "$IMAGE"
```

## OWASP Dependency-Check

- Use for: Software composition analysis focused on known vulnerabilities in third-party dependencies.
- Languages/ecosystem: Strongest fit for Java/JVM builds; also useful in polyglot repos through CLI analyzers and build plugins.
- Why it is trusted: It is an OWASP SCA project with CLI/build-tool integration, multiple report formats, suppression support, and CVSS-based build failure thresholds.
- Official docs: https://dependency-check.github.io/DependencyCheck/
- Good usage pattern: Use HTML for human review and JUnit/SARIF-style output for CI; pair with dependency update automation.

```
dependency-check.sh \
  --project "payments-api" \
  --scan . \
  --format HTML \
  --format JUNIT \
  --out build/dependency-check \
  --nvdApiKey "$NVD_API_KEY" \
  --junitFailOnCVSS 7 \
  --failOnCVSS 7
```

## Gitleaks

- Use for: Detecting committed secrets in Git history, pull requests, directories, and stdin.
- Languages/ecosystem: Language-agnostic; works well in Git repos, pre-commit hooks, and CI pipelines.
- Why it is trusted: The official CLI documents Git, directory, and stdin scan modes, config precedence, SARIF/JUnit reports, redaction, baselines, and exit-code behavior.
- Official docs: https://github.com/gitleaks/gitleaks
- Good usage pattern: Scan only the pushed commit range in PRs, redact output, and allowlist test fixtures deliberately.

```
cat > .gitleaks.toml <<'EOF'
[extend]
useDefault = true
[[allowlists]]
description = "checked-in test fixtures"
paths = ['''(^|/)testdata/fixtures/''']
EOF
git fetch --depth=50 origin main:refs/remotes/origin/main
gitleaks git --log-opts="origin/main..HEAD" \
  --config .gitleaks.toml --redact \
  --report-format sarif --report-path gitleaks.sarif \
  --exit-code 1 .
```

## Jazzer

- Use for: Coverage-guided fuzz testing of JVM code paths such as parsers, deserializers, validators, and security-sensitive normalization logic.
- Languages/ecosystem: Java/JVM; integrates with JUnit 5, Maven, Gradle, and Bazel.
- Why it is trusted: Jazzer is a libFuzzer-based JVM fuzzer with official JUnit integration and documented fuzz-test annotations, duration controls, and build-tool setup.
- Official docs: https://github.com/CodeIntelligenceTesting/jazzer
- Good usage pattern: Encode security invariants as fuzz tests; run short fuzzing in CI and longer campaigns nightly.

```
import static org.junit.jupiter.api.Assertions.assertTrue;
import com.code_intelligence.jazzer.junit.FuzzTest;
import com.code_intelligence.jazzer.mutation.annotation.NotNull;
import com.code_intelligence.jazzer.mutation.annotation.WithUtf8Length;
import java.nio.file.Path;
class UploadPathFuzzTest {
  private static final Path UPLOAD_ROOT = Path.of("/srv/app/uploads").normalize();
  @FuzzTest(maxDuration = "30s")
  void normalizedUploadPathStaysUnderRoot(
      @NotNull @WithUtf8Length(max = 256) String name) {
    Path candidate = UPLOAD_ROOT.resolve(name).normalize();
    assertTrue(candidate.startsWith(UPLOAD_ROOT), "path traversal: " + name);
  }
}
```
