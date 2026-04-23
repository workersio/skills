# Audit report template

Rendered by Kage Turn 4. `{{...}}` placeholders are filled from
`engagement.json` + `approved_findings.json`. Delete this heading block
before shipping the final `audit-report.md`.

---

# Security Audit Report — {{target}}

**Engagement dates:** {{started_at}} → {{finished_at}}
**Operator:** {{operator}}
**Scope type:** {{scope_type}}
**Tool:** Kage v{{skill_version}}

---

## 1. Executive Summary

{{exec_summary}}

The audit identified **{{total_findings}} finding(s)**:

| Severity | Count |
|---|---|
| Critical | {{critical_count}} |
| High | {{high_count}} |
| Medium | {{medium_count}} |
| Low | {{low_count}} |
| Informational | {{info_count}} |

**Top risks:**

{{top_risks_bullets}}

**Recommended immediate actions:**

{{immediate_actions_bullets}}

---

## 2. Scope & Methodology

### 2.1 In scope
{{in_scope}}

### 2.2 Out of scope
{{out_of_scope}}

### 2.3 Rules of engagement
{{rules_of_engagement}}

### 2.4 Methodology

Testing followed a 5-phase model:

1. **Reconnaissance** — subdomain enumeration, port scanning, content
   discovery, technology fingerprinting, JS secret analysis.
2. **Vulnerability analysis** — targeted testing across authentication,
   authorization, injection, SSRF, client-side, cache, cloud, and logic
   attack surfaces.
3. **Exploitation** — working proofs-of-concept for every suspected issue.
4. **Verification** — each PoC re-run from a clean session at least 3× to
   confirm reproducibility.
5. **Judging** — 3-gate validation (exploitable now? in scope? real harm?)
   before inclusion in this report.

---

## 3. Findings

Findings are numbered `KAGE-NNN`, ordered by severity then CVSS score. Each is
self-contained: a developer can reproduce and remediate without reading the
rest of the report.

{{#each findings}}

### {{id}} — {{title}}

| | |
|---|---|
| **Severity** | {{severity}} |
| **CVSS 3.1 score** | {{cvss_score}} |
| **CVSS 3.1 vector** | `{{cvss_vector}}` |
| **Affected asset** | {{affected_asset}} |
| **Category** | {{category}} |
| **OWASP Top 10** | {{owasp_ref}} |

#### Description
{{description}}

#### Impact
{{impact}}

#### Reproduction steps
{{#each reproduction}}
{{@index}}. {{this}}
{{/each}}

#### Evidence

**Request:**
```http
{{evidence.request}}
```

**Response:**
```http
{{evidence.response}}
```

{{#if evidence.screenshot}}
![Evidence screenshot]({{evidence.screenshot}})
{{/if}}

#### Remediation
{{remediation}}

#### References
{{#each references}}
- {{this}}
{{/each}}

---
{{/each}}

## 4. Remediation Roadmap

| Priority | Finding | Fix summary | Effort |
|---|---|---|---|
{{#each findings}}
| {{priority}} | {{id}} | {{remediation_summary}} | {{effort}} |
{{/each}}

### 4.1 Immediate (ship within 7 days)
{{immediate_remediation_list}}

### 4.2 Short term (ship within 30 days)
{{short_term_remediation_list}}

### 4.3 Long term (architectural)
{{long_term_remediation_list}}

---

## Appendix A — Raw artifacts

Raw outputs from every phase are retained under `results/{{target}}/`:

| File | Contents |
|---|---|
| `recon/subs.txt` | Enumerated subdomains |
| `recon/live.txt` | HTTP-reachable hosts + tech fingerprints |
| `recon/ports.txt` | Open TCP ports per host |
| `recon/crawl.txt` | Discovered URLs (katana + gau + waybackurls) |
| `vulns/nuclei.txt` | Nuclei template scan results |
| `vulns/secrets.txt` | Secrets found in JS bundles / source |
| `testing/*/` | Per-pass deep-testing output |
| `exploits/*.py` | Working PoCs |
| `judging/approved_findings.json` | Findings accepted for this report |
