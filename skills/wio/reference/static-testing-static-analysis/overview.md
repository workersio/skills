# Static Testing / Static Analysis

## Strategy Map

### Purpose
Use non-executing checks to catch known defect shapes in code, configuration, schemas, dependencies, and policy before runtime tests.

### Reliability Goal
Reduce preventable defects early and cheaply: type errors, nullability mistakes, unsafe APIs, taint flows, misconfiguration, dead code, policy violations, and framework misuse.

### When This Strategy Applies
- A defect class can be recognized mechanically and fixed locally.
- The repository already has type checking, linting, SAST, policy-as-code, or custom rules.
- A change modifies code or configuration where build-time checks can prevent known incidents.
- CI needs a fast gate before slower dynamic tests.

### When This Strategy Does Not Apply
- The risk depends on runtime data, user workflow intent, distributed timing, external service behavior, performance under load, or production configuration not modeled statically.
- The tool has high false-positive volume and no triage ownership.
- A rule would block urgent delivery for style-only issues without reliability value.
- Static results are being treated as proof of security or correctness.

### Signals To Inspect First
- Compiler/type-checker configuration, linter rules, SAST setup, policy checks, suppressions, baselines, generated code, build graph, dependency manifests, framework patterns, historical incidents, and CI severity policy.

### Test Design Principles
- Prefer high-confidence checks that developers can fix in the same change.
- Tune rules to local frameworks and approved patterns.
- Fail CI on new high-value findings, not every advisory warning.
- Suppressions require precise scope and reasons.
- Static analysis complements dynamic tests; it does not replace behavior verification.

### Good Test Characteristics
- Checks run locally and in CI with clear commands.
- Findings are actionable, owned, and linked to a defect class.
- Baselines shrink over time and new findings fail at appropriate severity.
- Custom rules encode repeated project-specific mistakes.
- Security findings are triaged with exploitability and context.

### Poor Test Characteristics
- Huge warning dashboards with no fix path.
- Broad ignores hide future defects.
- Style-only failures block reliability work.
- SAST pass is reported as secure application proof.
- Rules are added without checking false positives or developer workflow cost.

### Execution Pattern
- Inspect existing static tools and commands.
- Identify the defect class introduced or protected by the change.
- Run the narrowest relevant checks first, then broader checks if shared rules changed.
- Fix findings or document scoped suppressions.
- Add or tune rules only when they prevent recurring meaningful defects.
- Pair static findings with dynamic tests when behavior or exploitability matters.

### Examples
- TypeScript API change: run `tsc --noEmit` and relevant ESLint rules, then add behavior tests for runtime validation if external input is involved.
- Security sink: use CodeQL or Semgrep to flag unsafe construction, then add an authorization or injection regression test for the reachable endpoint.

### Validation
- Run the exact repository static-check command.
- Confirm new rules detect a real bad example and do not flag approved patterns excessively.
- Check suppressions are narrow and justified.
- Verify dynamic tests cover behavior static analysis cannot prove.
- Do not count number of findings as a quality metric.

### Failure Modes
- False positives cause broad disablement.
- False negatives are ignored because the dashboard is green.
- Generated or dynamic code reduces tool precision.
- Security teams own findings but product teams do not own fixes.
- Policy drift makes static gates obsolete.

## Overview

Static testing evaluates software artifacts without executing them; static analysis is the tool-supported subset applied to code, configuration, models, or generated artifacts. It catches defects that are inferable from syntax, types, API contracts, data flow, taint flow, policy rules, or coding standards before runtime tests start. ISTQB defines static analysis as analysis of artifacts such as requirements or code without executing them, usually with tool support.

For reliability work, static analysis is a fast feedback layer for “known bad shapes”: nullability/type errors, unsafe API usage, format-string mistakes, unchecked promises, injection paths, dead code, copy-pasted bugs, IaC misconfiguration, and violations of team-specific invariants. It is not a substitute for unit, integration, load, security, or exploratory testing.

## Best Fit

Use this practice where the team can encode a defect class once and prevent it repeatedly. The highest ROI usually comes from running a small, high-confidence rule set in the editor, pre-commit, pull request, and CI.

Static analysis works especially well when the finding is local, mechanical, and actionable: “this argument type is wrong,” “this sanitizer is missing,” “this banned API is used,” or “this config violates policy.” Google’s static-analysis experience emphasizes developer workflow integration and “only valuable results” because noisy tools lose adoption quickly.

It is also a strong fit for secure development programs. OWASP SAMM recommends automated static and dynamic security testing, then tuning tools to reduce false positives and false negatives for the organization’s stack.

## Good Candidates

Good candidates include security-sensitive paths such as authentication, authorization, request parsing, deserialization, SQL or shell construction, cryptography usage, and secret handling.

They also include public APIs, SDKs, shared libraries, typed service boundaries, concurrency primitives, framework lifecycle hooks, infrastructure-as-code, Dockerfiles, Kubernetes manifests, and generated code that humans rarely inspect carefully.

A repeated production issue is a strong signal for a custom rule. After an outage caused by missing idempotency checks before payment capture, for example, a team can add a Semgrep, CodeQL, Error Prone, or Roslyn analyzer rule that flags the risky call pattern in future pull requests.

## When Not To Use

Do not start with a broad default rule set and make every warning a merge blocker. This usually creates alert fatigue, mass suppressions, and distrust.

Avoid heavy static-analysis rollout for throwaway prototypes, exploratory spikes, or legacy systems where no one has time to triage the backlog. Start with a baseline and block only new high-confidence findings.

Do not rely on static analysis for behavior that depends on runtime data, distributed timing, production configuration, external services, performance under load, business intent, or UX correctness. Use dynamic tests, contract tests, fuzzing, model checking, review, observability, and incident analysis for those risks.

## Limitations

Static analysis can produce false positives and false negatives. OWASP notes that tools may report non-vulnerabilities as vulnerabilities and may miss issues when they lack runtime, framework, dependency, or external-system context.

Some tools need a successful build, compile database, dependency graph, or framework model. Generated code, reflection, dynamic dispatch, macros, monkey-patching, and metaprogramming can reduce precision.

Security SAST is best treated as a triage source, not proof of safety. It detects recognizable patterns; it does not prove the absence of authorization flaws, design flaws, unsafe operational configuration, or exploitable chains.

Operational cost is real: rule ownership, version upgrades, CI time, suppressions, baselines, custom framework models, and developer education. The team needs clear severity policy: which rules are advisory, which fail CI, and who owns exceptions.

## Signals

| Healthy Signal | Misuse Signal |
| --- | --- |
| Findings are fixed in the same pull request. | Dashboards grow but fixes do not. |
| CI blocks only new high-confidence issues. | Every warning is treated equally. |
| Suppressions require narrow reasons. | Broad ignores hide future defects. |
| Alert volume and false-positive rate trend down. | Style warnings block reliability work. |
| Old baseline shrinks over time. | Security owns triage but product teams own no remediation. |
| Known incident classes stop recurring. | Success is measured by finding count instead of prevented regressions. |
| Developers run tools locally without being forced. | Tools are treated as proof that runtime behavior is safe. |

## Examples

A Python service runs ruff check . for lint and formatter-adjacent defects, plus mypy or pyright for typed modules. Untyped legacy packages are excluded initially; new packages must pass stricter checks.

A TypeScript frontend runs tsc --noEmit in CI and eslint with typescript-eslint rules for unsafe promises, unused variables, and framework-specific mistakes.

A C++ platform team generates compile_commands.json, runs clang-tidy on changed files, and enables bugprone-*, performance-*, selected cert-*, and clang-analyzer-* checks. Existing findings are baselined; new critical findings fail CI.

An application-security team uses CodeQL or Semgrep to flag SQL construction from request-controlled values. Findings are reviewed by engineers; the rule is tuned to recognize the team’s approved query builder and sanitizer.

## Packages And Libraries

| Ecosystem | Tools |
| --- | --- |
| Cross-language security | GitHub CodeQL, Semgrep. |
| JavaScript/TypeScript | TypeScript compiler with --noEmit, ESLint, typescript-eslint. |
| Python | Ruff, mypy, Pyright. |
| Java/JVM | Error Prone, SpotBugs, PMD, Checkstyle. |
| C/C++ | clang-tidy, Clang Static Analyzer with a compile command database. |
| Go | go vet, Staticcheck; treat heuristics as guidance, not proof. |
| Rust | Clippy. |
| .NET | Roslyn/.NET analyzers with configurable severities and optional fixes. |
