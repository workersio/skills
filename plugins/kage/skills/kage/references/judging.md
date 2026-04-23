---
name: judging
description: Finding validation and severity assessment framework. Applies 3-check false-positive gate, confidence scoring (100-point scale), severity classification, deduplication rules, and exclusion filtering. Use to validate findings before reporting.
---

# Finding Validation & Judging Framework

---

## False-Positive Gate (4-Check)

ALL findings must pass all four checks. Failure on any = DROP without scoring.

**Drop, don't downgrade.** When a finding doesn't clearly clear every gate,
*drop it.* Do NOT save weak findings by demoting them to Low. Downgrading-
to-save is the primary way a report gets polluted with noise the triager
will N/A instantly.

### Check 1: Concrete Attack Path

Trace: **attacker action -> HTTP request -> server response -> impact/loss**

Evaluate what the code/server actually permits, not what the developer intended.

**Pass examples:**
- Attacker sends modified request -> server returns other user's data
- Attacker submits crafted input -> server executes code/query
- Attacker races concurrent requests -> server processes duplicate actions

**Fail examples:**
- "Could theoretically allow..." (no actual proof)
- "An attacker with admin access, network proximity, and specific timing could..." (implausible preconditions)
- Dead code path that can't be reached
- Wrong implementation with no practical impact

### Check 2: Reachable Entry Point

The attacker can invoke the vulnerable function/endpoint considering:
- Authentication requirements (public? user? admin?)
- Network restrictions (external? internal only?)
- Rate limiting (does it block the attack?)
- Input validation (does the WAF catch it?)

**The key question**: Can a real attacker on the internet actually do this?

### Check 3: No Existing Guard

No pre-existing safeguard blocks the exploit:
- CSRF tokens validated
- Rate limiting enforced
- WAF rules catch the payload
- Input sanitization strips the attack
- Authorization properly checked

**Exception**: If the guard can be BYPASSED (WAF bypass, rate limit bypass, CSRF token leak), the finding is valid — but you must demonstrate the bypass.

### Check 4: Triager-Worthy Impact

Would a senior HackerOne / Bugcrowd triager accept this on a mature
program, or would they N/A it in under 30 seconds?

**Pass examples:**
- Data access (other users' PII, financial records, internal config).
- Code execution (RCE, SSTI, deserialization with PoC).
- Account takeover (full or partial — session theft, auth bypass, password reset).
- Financial impact (duplicate charge, free premium, coupon abuse) with proof.
- Cost amplification (unauth LLM calls, unauth compute jobs) with a cost model.
- Service disruption with concrete monetary or user-harm consequence.

**Fail examples (DROP):**
- Missing security headers without a demonstrated clickjacking / XSS chain.
- HTTP 500 on an endpoint, no onward exploitation path.
- "Unauthenticated form submit" where the only harm is DB row count.
- "Stored XSS *if* the admin UI renders unescaped" — speculation, not proof.
- Any finding whose impact statement contains "could potentially" or "if".
- Rate-limit absence with no demonstrated abuse (spam, brute-force, enumeration).
- Info disclosure (route enumeration, tech stack, stack trace) without
  demonstrating it enables further exploitation.

If Check 4 fails, drop the finding. In `greybox` mode, check `context.md`
before dropping — the source may confirm the condition that turns
speculation into demonstration.

---

## Confidence Scoring

**Starting score: 100**

### Mandatory Deductions

| Condition | Points | Rationale |
|-----------|--------|-----------|
| Privileged caller needed (owner/admin) | -25 | Reduces attacker pool significantly |
| Partial attack path (sound concept, incomplete demo) | -20 | Can't prove full exploitation |
| Self-contained impact (attacker's own data only) | -15 | No harm to other users |
| Requires victim interaction (click link, visit page) | -10 | Reduces exploitability |
| Low success rate (<20% of attempts) | -10 | Unreliable exploitation |
| Configuration-dependent (DEBUG mode, specific settings) | -10 | May not apply to production |
| Time-sensitive (must exploit within narrow window) | -5 | Reduces practical exploitability |

### Thresholds

| Score | Action |
|-------|--------|
| >= 75 | Full report with PoC and remediation |
| 60-74 | Description-only entry (no fix recommendation) |
| < 60 | Not reportable — drop |

---

## Severity Classification

### Critical (P1)
- Remote code execution
- Full database access/dump
- Mass account takeover
- Cloud infrastructure compromise (SSRF -> credentials -> access)
- Financial manipulation with monetary proof
- Complete authentication bypass

### High (P2)
- Individual account takeover
- PII access for other users (email, phone, address, SSN, payment info)
- Stored XSS in high-traffic areas with session hijack
- Privilege escalation (user -> admin)
- SSRF accessing internal services with data
- Significant business logic bypass (free premium access, payment skip)

### Medium (P3)
- Reflected XSS with cookie theft (requires click)
- CORS leaking non-critical authenticated data
- CSRF on significant state-changing actions
- Information disclosure (internal IPs, stack traces, configs)
- Rate limit bypass on security-relevant endpoints
- Subdomain takeover (without cookie theft chain)

### Low (P4)
- Open redirect (standalone, no chain)
- Clickjacking on non-sensitive pages
- Information disclosure without sensitive data
- Self-XSS
- Missing headers without demonstrated impact

---

## Deduplication Rules

### Same Root Cause = ONE Finding
- Same broken authorization check on multiple endpoints -> 1 finding, list all endpoints
- Same XSS sink on multiple pages -> 1 finding
- Same missing input validation on related params -> 1 finding

### Different Root Cause = SEPARATE Findings
- Different vuln classes (IDOR + SQLi) -> separate
- Same class but different components (auth IDOR + payments IDOR with different logic) -> separate
- Reflected vs stored XSS -> separate (different fix)

### Chain Rule
- Report chains as SINGLE findings
- Severity = final impact severity
- Include all chain links in the report
- One bug enabling another = one report, not two

---

## Exclusion List (Mandatory Drops)

A finding matching any auto-drop pattern below **MUST be dropped
entirely**. Do not demote to Low to keep it alive. This is a terminal
filter, not a severity modifier.

### Auto-Drop
- Missing security headers without impact PoC
- Version/banner disclosure without CVE
- Self-XSS
- Logout CSRF
- TRACE/TRACK method without XST
- SSL/TLS cipher configuration
- SPF/DKIM/DMARC issues
- Email enumeration via registration (unless chained)
- Default creds on non-production
- Public data "disclosed"
- Rate limiting "missing" without security impact
- Theoretical privilege escalation without PoC
- "Misconfiguration" that's actually design-intended

### Context-Dependent (Report Only If Chained)
- Open redirect -> report only with OAuth/token theft chain
- SSRF with DNS callback only -> report only if you can read responses or access internal data
- Information disclosure -> report only if it enables further exploitation

