---
name: solana-audit
description: Structured Solana smart contract security audit using parallel scanning agents with confidence-scored findings. Use when the user asks to audit, review, or analyze a Solana program for security vulnerabilities, or when code contains solana_program, anchor_lang, pinocchio, #[program], or #[derive(Accounts)].
---

# Solana Smart Contract Audit

## Trigger

Activate this skill when the user asks to:
- Audit, review, or analyze a Solana program for security vulnerabilities
- Check a Solana smart contract for bugs or exploits
- Perform security analysis on code containing `solana_program`, `anchor_lang`, `pinocchio`, `#[program]`, or `#[derive(Accounts)]`

## Workflow

### Phase 1: Explore

Read [references/agents/explorer.md](references/agents/explorer.md) and spawn the explorer using the Agent tool:

```
Agent(subagent_type="Explore", prompt="<paste explorer prompt from explorer.md, filling in the target path>")
```

It returns: program map, instruction list, account structures, PDA map, CPI graph, protocol type classification, and threat model.

You MUST spawn this agent and wait for its output before proceeding to Phase 2. The explorer output is passed to every scanning agent as shared context.

### Phase 2: Parallel Scan

Read [references/scoring.md](references/scoring.md) for the confidence scoring rules and False Positive Gate. Then read all 4 agent prompt files and spawn them **IN PARALLEL** using 4 simultaneous Agent tool calls, inserting the explorer output into each prompt:

**Auth Scanner** ([references/agents/auth-state-scanner.md](references/agents/auth-state-scanner.md))
- Categories A-1..A-5 + S-1..S-8 — 13 vulnerability types

**CPI Scanner** ([references/agents/cpi-math-scanner.md](references/agents/cpi-math-scanner.md))
- Categories C-1..C-3 + M-1..M-4 — 7 vulnerability types

**Logic Scanner** ([references/agents/logic-economic-scanner.md](references/agents/logic-economic-scanner.md))
- Categories L-1..L-4 + T-1..T-3 — 7 vulnerability types
- Loads protocol-specific reference based on explorer's classification

**Framework Scanner** ([references/agents/framework-scanner.md](references/agents/framework-scanner.md))
- Framework-specific checks (Anchor/Native/Pinocchio) + R-1..R-3

Spawn all 4 in a single response like this:

```
Agent(prompt="<auth-state-scanner prompt with explorer output inserted>")
Agent(prompt="<cpi-math-scanner prompt with explorer output inserted>")
Agent(prompt="<logic-economic-scanner prompt with explorer output inserted>")
Agent(prompt="<framework-scanner prompt with explorer output inserted>")
```

Each agent returns candidates with taxonomy ID, file:line, evidence, attack path, confidence score, and FP gate result.

**DEEP mode** (when user requests thorough/deep audit): After the 4 scanners complete, also spawn a 5th adversarial agent per [references/agents/adversarial-scanner.md](references/agents/adversarial-scanner.md). Pass it the explorer output AND the merged scanner findings for cross-validation.

### Phase 3: Validate + Falsify

1. **Merge** all agent candidate lists
2. **Deduplicate** by root cause — when two agents flag the same root cause, keep the higher-confidence version. If they flag the same location with different taxonomy IDs, keep both.
3. **Sort** by confidence score, highest first. Re-number sequentially (VULN-001, VULN-002, ...).
4. **Falsify** — Each agent already applied the FP Gate (concrete path, reachable entry, no mitigations). For remaining candidates, check two additional defenses:
   - Would exploitation cost more than the attacker could gain? (economic infeasibility)
   - Is there an off-chain component (keeper, multisig, timelock) that blocks the attack vector?
   If either defense holds, drop or reduce confidence accordingly.
5. **Cross-reference** with [references/exploit-case-studies.md](references/exploit-case-studies.md) — does this match a known exploit pattern?
6. **Consult individual reference files** for each confirmed finding's taxonomy ID (e.g., [references/missing-signer-check.md](references/missing-signer-check.md)) for detailed remediation guidance
7. **Assess severity** using the calibration table in [references/audit-checklist.md](references/audit-checklist.md) §Severity Calibration

For Anchor programs, also consult [references/anchor-specific.md](references/anchor-specific.md) for framework-specific gotchas.

### Phase 4: Report

Produce the final audit report. **Every finding MUST include its taxonomy ID** from [references/vulnerability-taxonomy.md](references/vulnerability-taxonomy.md) and its **confidence score**.

```markdown
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
```

**Report rules:**
- Every finding MUST have a `**Category:**` line with the taxonomy ID (e.g., A-1, S-7, C-1)
- Every finding MUST have a `**Confidence:**` score
- Findings >= 75 confidence MUST include framework-specific fix code
- Findings < 75 appear below the **Below Confidence Threshold** separator without fix code
- Sort by confidence descending within each severity group
- The Summary Table MUST include the Category and Confidence columns
- Recommendations MUST include framework-specific fixes (e.g., `Signer<'info>`, `Account<'info, T>`, `close = destination`)

## References

The `references/` directory contains:

**Core references:**
- **[CHEATSHEET.md](references/CHEATSHEET.md)** — Condensed quick-lookup for all 30 vulnerability types with grep-able keywords (load this first)
- **[scoring.md](references/scoring.md)** — False Positive Gate + confidence scoring rules (loaded by all agents)
- **[vulnerability-taxonomy.md](references/vulnerability-taxonomy.md)** — Full index linking to individual vulnerability reference files
- **[audit-checklist.md](references/audit-checklist.md)** — Per-instruction validation checklist + syntactic grep commands
- **[anchor-specific.md](references/anchor-specific.md)** — Anchor framework-specific gotchas
- **[exploit-case-studies.md](references/exploit-case-studies.md)** — Real-world Solana exploit patterns ($500M+ in losses)

**20 individual vulnerability files** — Each with preconditions, vulnerable patterns, detection heuristics, false positives, and remediation

**Agent prompts** (`references/agents/`):
- **[explorer.md](references/agents/explorer.md)** — Phase 1 exploration
- **[auth-state-scanner.md](references/agents/auth-state-scanner.md)** — Auth Scanner (Categories A + S)
- **[cpi-math-scanner.md](references/agents/cpi-math-scanner.md)** — CPI Scanner (Categories C + M)
- **[logic-economic-scanner.md](references/agents/logic-economic-scanner.md)** — Logic Scanner (Categories L + T)
- **[framework-scanner.md](references/agents/framework-scanner.md)** — Framework Scanner (Framework + R)
- **[adversarial-scanner.md](references/agents/adversarial-scanner.md)** — DEEP mode threat modeling

**Protocol-specific references** (`references/protocols/`) — loaded on-demand based on explorer classification:
- **[lending-protocol.md](references/protocols/lending-protocol.md)** — Collateral, liquidation, interest rate patterns
- **[dex-amm-protocol.md](references/protocols/dex-amm-protocol.md)** — Swap, LP token, AMM curve patterns
- **[staking-protocol.md](references/protocols/staking-protocol.md)** — Reward distribution, epoch, delegation patterns
- **[bridge-protocol.md](references/protocols/bridge-protocol.md)** — Message verification, replay, guardian patterns
