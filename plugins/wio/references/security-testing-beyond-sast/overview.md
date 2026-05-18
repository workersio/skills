# Security Testing Beyond SAST

## Strategy Map

### Purpose
Select executable security checks for behavior, configuration, dependencies, artifacts, and abuse cases that static source scanning alone cannot prove.

### Reliability Goal
Reduce security regressions in authorization, authentication, tenant isolation, input handling, supply chain, secrets, runtime configuration, and deployable artifacts.

### When This Strategy Applies
- A change touches authn/authz, object IDs, tenant boundaries, roles, sessions, secrets, parsers, uploads, webhooks, dependencies, images, IaC, or API exposure.
- Security risk depends on runtime state, user identity, persisted data, generated artifacts, or reachable routes.
- A scanner finding needs a focused regression test or triage evidence.
- A critical flow needs abuse-case tests, not just happy-path checks.

### When This Strategy Does Not Apply
- The target system is not owned or authorized for active scanning.
- The only available check is a broad scanner with no seeded auth/data and no triage plan.
- The risk is a simple code-shape issue already covered by static analysis.
- A test would encode a guessed security policy instead of a requirement.

### Signals To Inspect First
- Public API routes, user-controlled IDs, role matrices, tenant data, session lifecycle, validation rules, parsers, dependency manifests, lockfiles, containerfiles, IaC, CI secrets, logs, audit events, threat models, incidents, and security requirements.

### Test Design Principles
- Security tests need explicit properties: who can do what, with which object, under which state.
- Authorization is behavior; assert denied outcomes and absence of side effects, not only middleware calls.
- Scanner output is triage input, not proof.
- Fuzzing and property tests need a security oracle; “does not crash” is useful but incomplete.
- Active tests require scope, credentials, rate limits, and safe environments.

### Good Test Characteristics
- Object-level and property-level authorization tests cover allowed and denied users.
- Dependency, secret, container, and IaC checks run with severity policy and suppressions under review.
- DAST/API tests target owned local or staging services with seeded data and artifacts.
- Security regression tests assert fail-closed behavior, audit logs, and no unauthorized persistence where relevant.
- Findings preserve enough evidence for triage without leaking secrets.

### Poor Test Characteristics
- A scanner is added and reported as “security tested” without auth, seed data, or triage.
- Tests only assert that an auth helper was called.
- Unauthorized cases are omitted because setup is inconvenient.
- Real secrets or production targets are used in tests.
- Suppressions accumulate without expiry or justification.

### Execution Pattern
- Identify the security property affected by the change.
- Inspect routes, roles, data ownership, validation, dependencies, artifacts, and deployment config.
- Choose direct behavior tests for business-logic security and scanners for known-vulnerability or config classes.
- Implement allowed and denied cases with deterministic fixtures.
- Run targeted tests and relevant scanners.
- Triage findings, avoid leaking sensitive artifacts, and report residual risk.

### Examples
- Weak: assert `authorize()` was called. Stronger: user A receives 404/403 and no data when requesting user B’s invoice; admin access is separately allowed; audit behavior is verified if required.
- Weak: run unauthenticated DAST against an empty app. Stronger: seed test users and data, scan owned local/staging routes with safe policy, and add focused tests for object ownership.

### Validation
- Run focused security regression tests plus relevant scanners.
- Confirm denied cases fail against the vulnerable behavior when applicable.
- Check that mocks do not bypass policy, persistence, or route binding.
- Verify scanner findings have owner, severity, and suppression rationale.
- Do not treat absence of findings as proof of absence of vulnerabilities.

### Failure Modes
- Overreliance on SAST misses business-logic flaws.
- Active scans damage systems or violate authorization.
- Scanner false positives consume attention; false negatives create confidence gaps.
- Tests omit negative cases and tenant boundaries.
- Secrets appear in fixtures, logs, snapshots, or artifacts.

## Overview

Security testing beyond SAST validates behavior and operational controls that source-level rules cannot prove: authorization, tenant isolation, input handling, dependency risk, secrets, container and IaC posture, dynamic attack paths, abuse cases, and runtime configuration.

SAST is useful, but a clean SAST report does not prove security. Pair static findings with tests that exercise reachable endpoints, realistic identities, seeded data, and observable security outcomes.

## Best Fit

Use this strategy when a change touches authn/authz, roles, tenants, sessions, tokens, secrets, crypto, deserialization, file upload, redirects, SSRF-prone fetches, SQL/shell construction, dependency versions, containers, IaC, logging, audit, rate limits, or security-sensitive configuration.

It is highest value after incidents, threat-model changes, dependency advisories, public API changes, privilege changes, and releases that expose new input or trust boundaries.

## Candidate Matrix

| Risk | Test Or Check |
| --- | --- |
| Authorization | Allowed/denied matrix, horizontal and vertical privilege checks, object ownership. |
| Tenant isolation | Cross-tenant read/write attempts, scoped queries, cache/object-store partitioning. |
| Input injection | SQL/NoSQL/LDAP/shell/template/path traversal tests plus SAST/DAST where useful. |
| Session/token handling | Expiry, revocation, replay, audience, issuer, CSRF, cookie flags. |
| Secrets | Secret scanning, redaction tests, log review, config and CI variable checks. |
| Dependencies | SCA/advisory review, exploitability triage, lockfile and transitive impact. |
| Containers/IaC | Image scan, least privilege, network exposure, storage, IAM, Kubernetes policy. |
| Abuse/rate limits | Enumeration, brute force, quota bypass, alerting, audit logging. |
| Object IDs in endpoints | User A cannot read, update, delete, export, or infer User B's object via path/query/body/header IDs. |
| Mass assignment | Clients cannot set role, isAdmin, tenantId, ownerId, balance, status, or other protected fields. |
| File upload/document processing | MIME/type/size/path validation, safe storage paths, malformed input handling, metadata leakage. |
| External URLs/webhooks/callbacks | Reject private IPs, metadata endpoints, localhost, file URLs, unsafe schemes, and unapproved redirects. |
| Database/search/export filters | Tenant predicates, parameterization, pagination/sorting/export scoping, forbidden-record exclusion. |
| CI/CD workflows | Least-privilege tokens, secret exposure controls, trusted branches/environments, pinned actions where required. |
| Mobile/client storage | Sensitive values are not stored insecurely; network/session behavior fails closed. |

## When Not To Use

Do not add broad scanners as blocking gates without triage policy, owners, baselines, and severity rules. Avoid noisy DAST against unstable or unseeded environments; it creates alerts without confidence.

Do not use this strategy as a substitute for secure design review or threat modeling when the issue is architectural: trust boundaries, data flow, key management, tenancy, or operational access.

## Scanner And Test Limits

| Limit | Practical Response |
| --- | --- |
| SAST cannot prove runtime authorization or business logic. | Add executable denied-case tests around real policy and data boundaries. |
| DAST sees only reachable/crawlable surfaces. | Use authenticated, seeded, scoped targets and preserve artifacts. |
| SCA/container scans find known vulnerabilities, not exploitability by themselves. | Triage by reachability, severity, exposure, and compensating controls. |
| Secret scanners can miss novel formats or flag fake values. | Use redaction, verified-secret workflows where available, and rotation policy for real findings. |
| IaC scanners may not know organization-specific topology. | Pair static policy with deployment review and runtime controls where needed. |
| Fuzz/property tests know generated inputs, not business authorization intent. | Encode security invariants explicitly: tenant isolation, deny-by-default, bounded resources. |

## Signals

| Strong Signal | Use With Judgment | Avoid |
| --- | --- | --- |
| Diff changes identity, permissions, data scoping, or exposed endpoints. | Framework upgrade with unclear reachable impact. | “SAST passed” as sole security evidence. |
| User-controlled input reaches filesystem, network, SQL, shell, templates, or deserialization. | Dependency advisory with disputed exploitability. | Untriaged scanner output as quality metric. |
| Secrets, logs, audit, alerts, or runtime config changed. | Low-risk internal tool with limited access. | Tests that assert only happy-path admin behavior. |
| Lockfiles, Dockerfiles, Kubernetes, Terraform, Helm, or CI workflows changed. | Existing scanner has unrelated baseline findings. | Broad new blocking gate with no owner or threshold. |
| OpenAPI, GraphQL schema, or route map can seed API checks. | Spec may not cover auth or stateful flows. | Unauthenticated crawl used as complete assurance. |

## Workflow

1. Identify the trust boundary, actor, asset, and failure impact.
2. Run existing static, dependency, secret, container, or IaC checks relevant to the change.
3. Add behavior tests for authorization, tenant isolation, input handling, or abuse cases.
4. Use dynamic scans only against safe, seeded, non-production targets with scoped credentials.
5. Triage findings by reachability, exploitability, impact, and compensating controls.
6. Report residual risk, suppressions, and checks not run.

## Examples

| Weak | Stronger |
| --- | --- |
| Only test that admin can update a user. | Also test non-admin, wrong tenant, disabled account, and audit log behavior. |
| Run a dependency scanner and fail on every advisory. | Triage reachable vulnerable paths, patch or suppress with reason and expiry. |
| Secret scan finds token and logs it in CI output. | Redact evidence, rotate if real, and add scanner/reporting controls. |
| DAST a random staging environment. | Scan a seeded local/staging target with known credentials, scope, and cleanup. |
| Test an invoice endpoint only with the owner's token. | Also request another user's invoice and assert 403/404 without leaking object details. |
| Mock the authorization layer in a security regression. | Exercise the real policy path with seeded identities and data. |

## Packages And Libraries

| Area | Tools |
| --- | --- |
| SAST/query | CodeQL, Semgrep, language analyzers. |
| Dependency/SCA | Dependabot, npm/yarn/pnpm audit, pip-audit, Safety, OSV-Scanner, Snyk, OWASP Dependency-Check. |
| Secrets | gitleaks, trufflehog, detect-secrets, GitHub secret scanning. |
| DAST/API | OWASP ZAP, Burp Suite, Schemathesis, RESTler, StackHawk. |
| Containers/IaC | Trivy, Grype, Syft, Checkov, tfsec, Terrascan, kube-score, kube-linter, OPA/Conftest. |
| Authz/API tests | Framework test clients, contract tests, seeded identities, policy-unit tests. |

## Source Anchors

- OWASP ASVS is useful for testable application security requirements; OWASP WSTG is useful for running web application testing.
- OWASP API guidance highlights object-level and property-level authorization as runtime risks that need application-context tests.
- NIST SSDF treats black-box tests, fuzzing, web app scanners, dependency checks, and other verification methods as complements to static analysis.
- OWASP SAMM emphasizes automated testing at scale while reserving deeper business-logic security testing for requirements-driven review.
- ZAP baseline/passive scanning and active scanning have different risk profiles; active scanning needs explicit authorization and safe targets.

## Quality Bar

- Tests include denied and cross-boundary cases, not only allowed happy paths.
- Scanner findings are triaged by reachable risk and documented suppressions.
- Secrets and security logs are redacted in artifacts.
- Dynamic tests run only against authorized, isolated targets.
- Residual risk names the actor, asset, missing check, and reason.
