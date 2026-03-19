---
name: solana-audit
description: >-
  TRIGGER when: user asks to audit, review, or security-check a Solana smart contract,
  OR codebase contains solana_program, anchor_lang, pinocchio, #[program], #[derive(Accounts)].
  Also trigger for: "check for vulnerabilities", "find exploits", "security review" on Rust code
  with Solana dependencies.
allowed-tools: Read, Write, Glob, Grep, Agent, Bash(grep *), Bash(wc *)
---

# Solana Smart Contract Audit

## Trigger

Activate this skill when the user asks to:
- Audit, review, or analyze a Solana program for security vulnerabilities
- Check a Solana smart contract for bugs or exploits
- Perform security analysis on code containing `solana_program`, `anchor_lang`, `pinocchio`, `#[program]`, or `#[derive(Accounts)]`

## Workflow

### Phase 0: Setup & Configuration

Before scanning, establish the audit scope and check for prior data.

**Step 1 — Ask the user 3 configuration questions** (skip if user says "just audit it" or equivalent):

1. **Scope:** Which programs should be audited? (default: all Solana programs in the repo)
   - Example answers: "all", "just the vault program", "programs/staking and programs/rewards"
2. **Depth:** Standard or Deep? Standard runs 4 parallel scanner agents. Deep adds a 5th adversarial agent for cross-validation. (default: standard)
3. **Known constraints:** Any accepted risks or trust assumptions? (default: none)
   - Example answers: "admin is a 3/5 multisig", "we accept the upgrade authority risk", "ignore token-2022 for now"

**Step 2 — Store configuration:**

If `${CLAUDE_PLUGIN_DATA}` is available:
1. Read `${CLAUDE_SKILL_DIR}/references/templates/config-template.json` for the schema
2. Write the user's answers to `${CLAUDE_PLUGIN_DATA}/config.json`
3. Check for prior audit data:
   - `${CLAUDE_PLUGIN_DATA}/audit-log.jsonl` — if it exists and contains entries for the same program, inform the user: "Found prior audit from [date]. [N] findings were reported."
   - `${CLAUDE_PLUGIN_DATA}/accepted-risks.json` — if it exists, load accepted risks to cross-reference during Phase 3

If `${CLAUDE_PLUGIN_DATA}` is not available, proceed without persistence. Do not error or warn — just skip silently.

**Defaults** (if user skips configuration): scope=all programs, depth=standard, no known constraints.

### Phase 1: Explore

Read [references/agents/explorer.md](references/agents/explorer.md) and spawn the explorer agent using the Agent tool.

**How to construct the agent call:**

1. Read the file `${CLAUDE_SKILL_DIR}/references/agents/explorer.md`. The agent prompt is the text between the triple-backtick fences in the `## Agent Prompt` section.
2. In the prompt, replace `[Insert: repository path or "full codebase scan"]` with the actual target path (from Phase 0 scope, or the repo root).
3. Spawn the agent:
   ```
   Agent(subagent_type="Explore", prompt="<the filled-in prompt>")
   ```

It returns: program map, instruction list, account structures, PDA map, CPI graph, protocol type classification, LOC count, and threat model.

You MUST spawn this agent and wait for its output before proceeding. The explorer output is passed to every scanning agent as shared context.

### Adaptive Sizing

After the explorer agent returns, determine the program size and select the scan strategy:

| Size | Criteria | Scan Strategy |
|------|----------|---------------|
| **Small** | <500 LOC AND <5 instructions | Single combined scan agent covering all categories (A through R). Construct one prompt inline that includes all vulnerability checks from the CHEATSHEET. No separate agent files needed. |
| **Medium** | 500–2000 LOC | Standard 4-agent parallel scan (Phase 2 below) |
| **Large** | >2000 LOC | Standard 4-agent parallel scan. Inform the user: "This is a large program. Consider running with `depth: deep` for adversarial cross-validation." |

For **small programs**, construct a single agent prompt that:
- Includes the explorer output as context
- References `${CLAUDE_SKILL_DIR}/references/scoring.md` for scoring rules
- References `${CLAUDE_SKILL_DIR}/references/CHEATSHEET.md` for all 30 vulnerability types
- Instructs the agent to scan all categories (A-1 through R-3) in one pass
- Uses the same output format as the individual scanner agents
- Then skip to Phase 3 with the single agent's output

For **medium and large programs**, proceed to Phase 2.

### Phase 2: Parallel Scan

#### Pre-Scan: Syntactic Scan

Before spawning the scanner agents, run the consolidated syntactic scan:

1. Read `${CLAUDE_SKILL_DIR}/references/scripts/scan-commands.md`
2. Execute the grep commands against the target program directory
3. Collect results organized by category (A, S, C, M, L, T, R)
4. Count total hits per category

Pass the syntactic scan results to ALL scanner agents with this note prepended to their context:

> **Pass 1 (syntactic scan) has been completed by the orchestrator. Results below. Proceed directly to Pass 2 — Semantic Review.**
>
> [paste syntactic scan results here, organized by category]

This eliminates redundant grep work across 4 agents.

#### Spawning Scanner Agents

Read [references/scoring.md](references/scoring.md) for the confidence scoring rules and False Positive Gate. Then read all 4 agent prompt files and spawn them **IN PARALLEL** using 4 simultaneous Agent tool calls.

**How to construct each agent call:**

1. Read the agent prompt file (e.g., `${CLAUDE_SKILL_DIR}/references/agents/auth-state-scanner.md`). The prompt is everything between the triple-backtick fences in the `## Agent Prompt` section.
2. Replace `[INSERT EXPLORER OUTPUT HERE — the full codebase analysis from the explorer agent]` with the literal full text output from the explorer agent.
3. Replace bracketed reference paths (e.g., `[references/scoring.md]`) with absolute file paths using `${CLAUDE_SKILL_DIR}` as the base (e.g., `${CLAUDE_SKILL_DIR}/references/scoring.md`) so the agent can `Read` them directly — do NOT paste file contents inline.
4. For the logic-economic scanner, fill in the protocol type from the explorer classification so it loads the correct protocol reference.
5. Prepend the syntactic scan results (from the pre-scan step above) to each agent's context.

**Auth Scanner** ([references/agents/auth-state-scanner.md](references/agents/auth-state-scanner.md))
- Categories A-1..A-5 + S-1..S-8 — 13 vulnerability types

**CPI Scanner** ([references/agents/cpi-math-scanner.md](references/agents/cpi-math-scanner.md))
- Categories C-1..C-3 + M-1..M-4 — 7 vulnerability types

**Logic Scanner** ([references/agents/logic-economic-scanner.md](references/agents/logic-economic-scanner.md))
- Categories L-1..L-4 + T-1..T-3 — 7 vulnerability types
- Loads protocol-specific reference based on explorer's classification

**Framework Scanner** ([references/agents/framework-scanner.md](references/agents/framework-scanner.md))
- Framework-specific checks (Anchor/Native/Pinocchio) + R-1..R-3

Spawn all 4 in a single response:

```
Agent(prompt="<auth-state-scanner prompt with explorer output + syntactic scan results inserted>")
Agent(prompt="<cpi-math-scanner prompt with explorer output + syntactic scan results inserted>")
Agent(prompt="<logic-economic-scanner prompt with explorer output + syntactic scan results inserted>")
Agent(prompt="<framework-scanner prompt with explorer output + syntactic scan results inserted>")
```

Each agent returns candidates with taxonomy ID, file:line, evidence, attack path, confidence score, and FP gate result.

**DEEP mode** (when user requests thorough/deep audit or depth=deep in config): After the 4 scanners complete, also spawn a 5th adversarial agent per [references/agents/adversarial-scanner.md](references/agents/adversarial-scanner.md). Pass it the explorer output AND the merged scanner findings for cross-validation.

### Phase 3: Validate + Falsify

1. **Merge** all agent candidate lists
2. **Deduplicate** by root cause — when two agents flag the same root cause, keep the higher-confidence version. If they flag the same location with different taxonomy IDs, keep both.
3. **Sort** by confidence score, highest first. Re-number sequentially (VULN-001, VULN-002, ...).
4. **Check accepted risks** — if `accepted-risks.json` was loaded in Phase 0, cross-reference each finding by `taxonomy_id` + `file`. Mark matching findings as "Previously Accepted" with the stored reason. Still include them in the report but do not count them as new findings.
5. **Falsify** — Each agent already applied the FP Gate (concrete path, reachable entry, no mitigations). For remaining candidates, check two additional defenses:
   - Would exploitation cost more than the attacker could gain? (economic infeasibility)
   - Is there an off-chain component (keeper, multisig, timelock) that blocks the attack vector?
   If either defense holds, drop or reduce confidence accordingly.
6. **Cross-reference** with [references/exploit-case-studies.md](references/exploit-case-studies.md) — does this match a known exploit pattern?
7. **Consult individual reference files** for each confirmed finding's taxonomy ID (e.g., [references/missing-signer-check.md](references/missing-signer-check.md)) for detailed remediation guidance
8. **Assess severity** using the calibration table in [references/audit-checklist.md](references/audit-checklist.md) §Severity Calibration

For Anchor programs, also consult [references/anchor-specific.md](references/anchor-specific.md) for framework-specific gotchas.

### Phase 4: Report

Produce the final audit report. **Every finding MUST include its taxonomy ID** from [references/vulnerability-taxonomy.md](references/vulnerability-taxonomy.md) and its **confidence score**.

If there are **one or more findings**, use the standard report template:

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
- Phase 0: Scope configuration and prior audit check
- Phase 1: Codebase exploration (program map, CPI graph, threat model)
- Phase 2: Pre-scan syntactic analysis + parallel scan — 4 agents across 30 vulnerability types across 7 categories
- Phase 3: Merge, deduplicate by root cause, accepted risk check, devil's advocate falsification
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

If there are **zero findings** (clean audit), use this alternative template:

````markdown
# Security Audit Report: [Program Name]

## Executive Summary
- **Result: No vulnerabilities identified**
- Audit date, scope (files, instructions, LOC)
- Framework: Native / Anchor / Pinocchio
- Protocol type: [from explorer classification]
- Methods: Parallel agent scan (4 agents), confidence-scored validation
- Finding counts: 0 Critical, 0 High, 0 Medium, 0 Low, 0 Informational

## Methodology
- Phase 0: Scope configuration and prior audit check
- Phase 1: Codebase exploration (program map, CPI graph, threat model)
- Phase 2: Pre-scan syntactic analysis + parallel scan — 4 agents across 30 vulnerability types across 7 categories
- Phase 3: Merge, deduplicate, devil's advocate falsification
- Phase 4: Confidence-scored report

## Categories Reviewed

All 7 categories (30 vulnerability types) were scanned:

| Category | IDs | Types Checked | Findings |
|----------|-----|---------------|----------|
| A: Authentication & Authorization | A-1..A-5 | 5 | 0 |
| S: Account & State Management | S-1..S-8 | 8 | 0 |
| C: Cross-Program Invocation | C-1..C-3 | 3 | 0 |
| M: Arithmetic & Math | M-1..M-4 | 4 | 0 |
| L: Logic & Economic | L-1..L-4 | 4 | 0 |
| T: Token-Specific | T-1..T-3 | 3 | 0 |
| R: Runtime & Deployment | R-1..R-3 | 3 | 0 |

## Scope
- Files reviewed: [list]
- Instructions analyzed: [count]
- Lines of code: [LOC]

## Disclaimer

A clean audit report does not guarantee the absence of vulnerabilities. This audit covers the 30 vulnerability types in the solana-audit taxonomy and is limited to static analysis of the on-chain program source code. It does not cover:
- Off-chain components (frontends, keepers, bots)
- Economic modeling or game-theoretic analysis beyond basic checks
- Deployment configuration (actual on-chain upgrade authority, program data account state)
- Vulnerabilities outside the taxonomy scope
- Bugs introduced after the audit date

## Appendix
- Complete file listing reviewed
- Vulnerability taxonomy reference
- Explorer output (program map, CPI graph, threat model)
````

**Report rules:**
- Every finding MUST have a `**Category:**` line with the taxonomy ID (e.g., A-1, S-7, C-1)
- Every finding MUST have a `**Confidence:**` score
- Findings >= 75 confidence MUST include framework-specific fix code
- Findings < 75 appear below the **Below Confidence Threshold** separator without fix code
- Sort by confidence descending within each severity group
- The Summary Table MUST include the Category and Confidence columns
- Recommendations MUST include framework-specific fixes (e.g., `Signer<'info>`, `Account<'info, T>`, `close = destination`)

### Audit Persistence

After generating the report, persist the results if `${CLAUDE_PLUGIN_DATA}` is available:

1. Read `${CLAUDE_SKILL_DIR}/references/templates/audit-log-schema.md` for the schema
2. Append a single JSONL line to `${CLAUDE_PLUGIN_DATA}/audit-log.jsonl` with: timestamp, program name, path, framework, protocol type, LOC, instruction count, depth, finding counts by severity, finding IDs, and taxonomy IDs
3. Inform the user: "Audit results saved. You can mark findings as accepted risks for future audits."

If `${CLAUDE_PLUGIN_DATA}` is not available, skip silently.

### Follow-Up: Formal Verification

For CRITICAL or HIGH findings involving arithmetic safety (M-1, M-2, M-3, M-4), state invariants (S-1 through S-8), or authorization logic (A-1 through A-5), suggest formal verification using `/kani-proof`:

> **Formal verification available:** Finding VULN-NNN ([taxonomy_id]: [title]) in `[function_name()]` could be formally verified using `/kani-proof` to prove the fix is correct and the vulnerability cannot recur.

Example: "Finding VULN-001 (M-1: Integer Overflow) in `calculate_reward()` could be formally verified using `/kani-proof` to prove all arithmetic operations are safe under bounded inputs."

This is a lightweight recommendation only — do not block the report on it.

## References

The `references/` directory contains:

**Core references:**
- **[CHEATSHEET.md](references/CHEATSHEET.md)** — Condensed quick-lookup for all 30 vulnerability types with grep-able keywords (load this first)
- **[scoring.md](references/scoring.md)** — False Positive Gate + confidence scoring rules (loaded by all agents)
- **[vulnerability-taxonomy.md](references/vulnerability-taxonomy.md)** — Full index linking to individual vulnerability reference files
- **[audit-checklist.md](references/audit-checklist.md)** — Per-instruction validation checklist + syntactic grep commands
- **[anchor-specific.md](references/anchor-specific.md)** — Anchor framework-specific gotchas
- **[exploit-case-studies.md](references/exploit-case-studies.md)** — Real-world Solana exploit patterns ($500M+ in losses)

**Scan automation:**
- **[scripts/scan-commands.md](references/scripts/scan-commands.md)** — Consolidated syntactic scan commands for pre-scan phase

**Persistence templates:**
- **[templates/config-template.json](references/templates/config-template.json)** — Audit configuration schema
- **[templates/audit-log-schema.md](references/templates/audit-log-schema.md)** — Audit log and accepted risks schemas

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
