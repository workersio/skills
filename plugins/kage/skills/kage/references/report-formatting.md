---
name: reporting
description: Bug bounty report writing for HackerOne, Bugcrowd, Intigriti, and direct VDPs. Generates copy-paste ready reports with reproduction steps, raw HTTP evidence, business-language impact, and CVSS scoring. Use after findings are validated by the judge.
---

# Report Writing and Validation Techniques

The report is the product. Not the bug. The report.

## Audience

Write for triagers: competent developers, NOT security specialists. They work through large queues and make quick decisions. Clarity and reproducibility determine whether your report gets accepted or bounced.

## Report Components

### Title
Format: `[Vuln Class] in [endpoint/feature] leads to [Impact]`

Examples:
- "IDOR in /api/v1/invoices/{id} leads to access to all customer invoices"
- "Stored XSS in comment field leads to admin session hijacking"

### Summary
2-3 sentences covering what the vulnerability is, where it exists, and what the impact is.

### Reproduction Steps
Exact, copy-paste ready steps. Number each step. Include:
- Full URLs
- HTTP method and headers
- Request bodies (with example values)
- Expected vs actual responses
- Screenshots at each step

### Impact Statement
Write in business language, not security jargon:
- "Any authenticated user can download any other user's invoices, including PII and financial data"
- NOT "BOLA vulnerability allows horizontal privilege escalation"

### Evidence
- Screenshots of each step
- Raw HTTP requests and responses as TEXT (not just screenshots -- triagers need to copy-paste)
- Video walkthrough for complex chains

### Suggested Fix (Optional)
Appreciated by triagers. Brief and actionable.

## Critical Mistakes

- Writing for hackers, not triagers
- Omitting reproduction steps (immediate N/A)
- Submitting too early before confirming the full chain
- Submitting too late -- don't chase indefinitely, submit within approximately 24 hours
- Missing raw HTTP requests (screenshots alone are insufficient)
- Overstating impact without demonstrating it

## 4-Gate Validation

Before submitting, pass every gate:

### G0: Is this actually exploitable RIGHT NOW?
Real proof of concept, not theoretical. Can you demonstrate it working against the live target?

### G1: Is the endpoint in scope?
Confirmed on the program's scope page. Check for excluded domains, endpoints, and vulnerability types.

### G2: Is this a known/duplicate?
Search Hacktivity (HackerOne), public disclosures, changelogs, and recent patches. Check if the vulnerability was recently fixed.

### G3: Does it cause real harm?
Fund theft, PII leak, account takeover, remote code execution. If you cannot articulate concrete harm, reconsider submitting.

## CVSS 3.1 Scoring Guide

### Attack Vector
Network > Adjacent > Local > Physical

### Privileges Required
None > Low > High

### User Interaction
None > Required

### Impact (Confidentiality / Integrity / Availability)
High = Critical data exposure, arbitrary writes, or complete service disruption

A Network/None/None attack with High C/I/A impact = Critical (9.0+)

## Platform-Specific Formats

### HackerOne
- Markdown formatting
- Attach PoC files
- Select weakness type from taxonomy
- Search Hacktivity for duplicate check
- Use structured vulnerability information fields

### Bugcrowd
- P1-P4 severity rating
- VRT (Vulnerability Rating Taxonomy) category selection
- Priority queues based on severity
- Researcher-facing submission form

### Intigriti
- Built-in CVSS calculator
- PoC video encouraged
- EU-focused programs
- Structured submission flow

### Direct VDP (Vulnerability Disclosure Program)
- Email format to security@target.com
- Include remediation suggestions
- Professional tone
- Allow reasonable response time (90 days standard)

## Human Tone Rules

- Start with impact, not vulnerability name
- Write like you are explaining to a smart developer
- Use "I" and active voice ("I found" not "It was discovered")
- One concrete example beats three abstract sentences
- Be direct and factual, not dramatic
