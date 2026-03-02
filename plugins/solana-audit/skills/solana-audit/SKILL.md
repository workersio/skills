---
name: solana-audit
description: Structured Solana smart contract security audit with automated tools and parallel manual review. Use when the user asks to audit, review, or analyze a Solana program for security vulnerabilities, or when code contains solana_program, anchor_lang, #[program], or #[derive(Accounts)].
---

# Solana Smart Contract Audit

## Trigger

Activate this skill when the user asks to:
- Audit, review, or analyze a Solana program for security vulnerabilities
- Check a Solana smart contract for bugs or exploits
- Perform security analysis on code containing `solana_program`, `anchor_lang`, `#[program]`, or `#[derive(Accounts)]`

## Workflow

### Phase 1: Cheatsheet Intake + Program Understanding

1. **Read [references/CHEATSHEET.md](references/CHEATSHEET.md)** — Internalize all 25 vulnerability patterns with their grep-able keywords. This is the primary scanning reference.

2. **Clone the repository** (if URL provided): `git clone <url>`

3. **Map the program structure**:
   - Identify all program crates (look for `Cargo.toml` with `solana-program` or `anchor-lang` deps)
   - List all instructions (entry points)
   - Map account structures and their relationships
   - Identify PDAs, their seeds, and bump handling
   - Trace all CPI calls (cross-program invocations)
   - Note any external oracle or price feed dependencies

4. **Determine framework**: Native `solana_program` vs Anchor (`anchor_lang`)

5. **Establish threat model**:
   - **Assets at risk**: Token vaults, authority keys, fee pools, user deposits
   - **Trust boundaries**: Which accounts are trusted vs user-supplied?
   - **Attack surface**: Which instructions are callable by anyone? Which are admin-only?
   - **Economic incentives**: What could an attacker gain? What's the TVL?

### Phase 2: Dual-Pass Sweep

**Pass A — Syntactic Scan:** Run the grep commands from [references/audit-checklist.md](references/audit-checklist.md) §Syntactic Scan Commands. For each hit, note the file, line, and which vulnerability ID it maps to. Build candidate list.

**Pass B — Semantic Review:** Read each instruction handler for logic-level vulnerabilities that grep can't catch:
- Oracle manipulation (L-1) — Is price source manipulable?
- Economic attacks (L-2, L-3, L-4) — Flash loans, sandwich attacks, front-running
- State machine flaws — Can instructions be called in unexpected order?
- Cross-account logic — Does modifying account A affect account B incorrectly?
- Rounding direction — Does truncation consistently favor one party?

Merge Pass A and Pass B into a deduplicated candidate list.

### Phase 3: Validate + Deep Dive

For each candidate finding:

1. **Consult the individual reference file** — Read the specific vulnerability reference (e.g., [references/missing-signer-check.md](references/missing-signer-check.md)) for the candidate's taxonomy ID
2. **Walk the detection heuristics** — Follow the numbered steps in the reference file
3. **Check false positives** — Read the False Positives section. Eliminate candidates that match safe patterns (e.g., Anchor `Account<T>` auto-checks owner, PDA-derived accounts validated by seeds)
4. **Cross-reference with [references/exploit-case-studies.md](references/exploit-case-studies.md)** — Does this finding match a known exploit pattern?
5. **Assess severity** — Use the severity calibration table in [references/audit-checklist.md](references/audit-checklist.md) §Severity Calibration

For Anchor programs, also consult [references/anchor-specific.md](references/anchor-specific.md) for framework-specific gotchas.

### Phase 4: Report

Produce the final audit report. **Every finding MUST include its taxonomy ID** from [references/vulnerability-taxonomy.md](references/vulnerability-taxonomy.md) — this is what distinguishes a structured audit from an ad-hoc review.

```markdown
# Security Audit Report: [Program Name]

## Executive Summary
- Audit date, scope (files, instructions, LOC)
- Framework: Native / Anchor
- Methods: Syntactic scan, semantic review
- Finding counts by severity: X Critical, Y High, Z Medium, W Low, V Informational

## Methodology
- Phase 1: Program mapping + threat model
- Phase 2: Dual-pass sweep (syntactic grep + semantic review)
- Phase 3: Validation against vulnerability taxonomy (25 types across 7 categories)
- Reference: vulnerability taxonomy based on Wormhole, Cashio, Mango, Neodyme, Crema exploits

## Findings

### [CRITICAL] VULN-001: Title
**File:** path/to/file.rs:line
**Category:** A-1 (Missing Signer Check)
**Description:** ...
**Impact:** ...
**Recommendation:** ...

### [HIGH] VULN-002: Title
**File:** path/to/file.rs:line
**Category:** S-7 (Reinitialization)
...

## Summary Table
| ID | Title | Severity | Category | File | Status |
|---|---|---|---|---|---|
| VULN-001 | Missing Signer Check | Critical | A-1 | lib.rs:16 | Open |
| VULN-002 | Reinitialization | High | S-7 | lib.rs:11 | Open |

## Appendix
- Complete file listing reviewed
- Vulnerability taxonomy reference
```

**Report rules:**
- Every finding MUST have a `**Category:**` line with the taxonomy ID (e.g., A-1, S-7, C-1)
- Use severity from [references/audit-checklist.md](references/audit-checklist.md) §Severity Calibration
- Recommendations MUST include framework-specific fixes (e.g., `Signer<'info>`, `Account<'info, T>`, `close = destination`)
- The Summary Table MUST include the Category column with taxonomy IDs

## References

The `references/` directory contains:
- **[CHEATSHEET.md](references/CHEATSHEET.md)** — Condensed quick-lookup for all 25 vulnerability types with grep-able keywords (load this first)
- **[vulnerability-taxonomy.md](references/vulnerability-taxonomy.md)** — Full index linking to individual vulnerability reference files
- **20 individual vulnerability files** — Each with preconditions, vulnerable patterns, detection heuristics, false positives, and remediation
- **[audit-checklist.md](references/audit-checklist.md)** — Per-instruction validation checklist + syntactic grep commands
- **[anchor-specific.md](references/anchor-specific.md)** — Anchor framework-specific gotchas
- **[exploit-case-studies.md](references/exploit-case-studies.md)** — Real-world Solana exploit patterns ($500M+ in losses)
