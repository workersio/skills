# Audit Report Template

````markdown
# Security Audit Report: [Program Name]

## Executive Summary
- Audit date, scope (files, instructions, LOC)
- Framework: Native / Anchor / Pinocchio
- Protocol type: [from explorer classification]
- Methods: Parallel agent scan (4 agents + adversarial), confidence-scored validation
- Finding counts by severity: X Critical, Y High, Z Medium, W Low, V Informational
- Confidence threshold: 75/100

## Methodology
- Phase 1: Codebase exploration (program map, CPI graph, threat model)
- Phase 2: Parallel scan — 4 agents across 30 vulnerability types across 7 categories
- Phase 3: Merge, deduplicate by root cause, devil's advocate falsification
- Phase 4: Confidence-scored report
- Reference: vulnerability taxonomy based on Wormhole, Cashio, Mango, Neodyme, Crema exploits

## Findings

### [CRITICAL] VULN-001: Title (Confidence: 95/100)
**File:** path/to/file.rs:line
**Category:** A-1 (Missing Signer Check)
**Description:** ...
**Attack Path:** caller → instruction → state change → impact
**Impact:** ...
**Recommendation:** ...
**Fix:**
```rust
// Remediation code (framework-specific)
```

### [HIGH] VULN-002: Title (Confidence: 80/100)
**File:** path/to/file.rs:line
**Category:** S-7 (Reinitialization)
...

---
### Below Confidence Threshold
---

### [MEDIUM] VULN-003: Title (Confidence: 60/100)
**File:** path/to/file.rs:line
**Category:** M-2 (Division Precision Loss)
**Description:** ...
**Impact:** ...
*(No fix recommendation — below confidence threshold)*

## Summary Table
| ID | Title | Severity | Category | Confidence | File | Status |
|---|---|---|---|---|---|---|
| VULN-001 | Missing Signer Check | Critical | A-1 | 95 | lib.rs:16 | Open |
| VULN-002 | Reinitialization | High | S-7 | 80 | lib.rs:11 | Open |
| --- | Below Confidence Threshold | --- | --- | <75 | --- | --- |
| VULN-003 | Division Precision Loss | Medium | M-2 | 60 | math.rs:45 | Open |

## Appendix
- Complete file listing reviewed
- Vulnerability taxonomy reference
- Explorer output (program map, CPI graph, threat model)
````
