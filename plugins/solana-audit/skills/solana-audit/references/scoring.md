# Confidence Scoring

Consistent scoring rules for all scanning agents. Load this before evaluating any candidate finding.

---

## False Positive Gate

Every candidate MUST pass all 3 checks before receiving a confidence score. If any check fails, DROP the candidate.

1. **Concrete attack path** — You can specify: Caller → instruction call → state change → loss/impact. If you cannot trace a specific sequence of operations leading to harm, the finding fails this check.
2. **Reachable entry point** — The attack entry point is callable by the attacker. It bypasses all access controls (signer checks, authority validation, PDA constraints). If the instruction is admin-only and the admin is a multisig/governance, note this but do not drop — apply the privileged-caller deduction instead.
3. **No existing mitigations** — No preventive guards already handle this: Anchor constraints (`Account<T>`, `Signer<T>`, `has_one`, `seeds`), `require!()` checks, PDA derivation validation, or runtime enforcement. If a mitigation exists, the finding fails this check.

## Confidence Score

Start at **100**. Apply all applicable deductions:

| Deduction | Points | Condition |
|-----------|--------|-----------|
| Privileged caller | -25 | Attack requires admin, multisig, governance, or other privileged role |
| Incomplete path | -20 | Concept is sound but cannot specify exact execution sequence end-to-end |
| Self-contained impact | -15 | Loss is limited to the attacker's own funds or a single user who opts in |

Deductions stack. A finding requiring a privileged caller with incomplete path scores 100 - 25 - 20 = 55.

## Threshold

- **Score >= 75**: Include detailed remediation with fix code blocks (Native + Anchor/Pinocchio as applicable)
- **Score < 75**: Include in report with description and impact, but WITHOUT fix recommendations
- **Score < 50**: Consider dropping entirely — explain why it was retained if kept

## Do Not Report

- **Linter/compiler issues**: Clippy warnings, formatting, naming, redundant comments
- **By-design privileges**: Admin fee-setting, parameter changes, pausing — these are features, not vulnerabilities, unless a concrete exploit path exists
- **Insufficient logging**: Missing event emissions or logging
- **Vague centralization**: "admin could rug" without a specific mechanism and attack path
- **Implausible preconditions**: Compromised validator, >50% token supply by attacker. *Note*: Common SPL token behaviors (Token-2022 transfer fees, permanent delegates, freeze authority) are NOT implausible if the program accepts arbitrary mints
- **Gas/compute optimizations**: CU savings, unnecessary account reallocations

## Output Per Finding

```
- Confidence: [score]/100 (deductions: [list or "none"])
- FP Gate: [PASS/FAIL — concrete path: yes/no, reachable: yes/no, no mitigations: yes/no]
```
