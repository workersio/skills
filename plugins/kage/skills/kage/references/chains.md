---
name: chains
description: Vulnerability chain analysis and escalation. Maps 7 proven chain patterns (Open Redirect→OAuth ATO, SSRF→RCE, XSS→Privesc, IDOR→ATO, Subdomain Takeover→Cookie Theft, Race→Financial, Info Disclosure→Exploitation). Use after testing phase to identify chain opportunities that escalate individual findings into critical impact.
---

# Vulnerability Chain Patterns and Methodology

Chaining findings turns individual low/medium issues into critical
outcomes (account takeover, RCE, data breach). Score chains by final
impact, not by the sum of their links.

## The 7 Documented Chain Patterns

### 1. Open Redirect to OAuth ATO

Bypass `redirect_uri` validation using an open redirect on the target domain. The OAuth authorization code is sent to the redirect, which forwards it to an attacker-controlled server.

Flow: Find open redirect on target --> Use as redirect_uri in OAuth flow --> Steal authorization code --> Exchange for access token --> Account takeover

### 2. SSRF to Cloud Metadata to RCE

SSRF on a cloud-hosted application provides access to the instance metadata endpoint. Extract IAM credentials, enumerate permissions, and escalate.

Flow: SSRF vulnerability --> Access 169.254.169.254 --> Extract IAM credentials --> Enumerate permissions (enumerate-iam) --> Privilege escalation --> RCE or data access

### 3. XSS to Admin Action to Privilege Escalation

Stored XSS that executes in an admin's browser context. The XSS payload programmatically performs admin actions (create admin account, change permissions, extract data).

Flow: Stored XSS in user-generated content --> Admin views content --> XSS executes admin API calls --> Privilege escalation or data exfiltration

### 4. IDOR to PII Leak to Account Takeover

IDOR exposes user data (email, phone, security questions). Use the leaked information to complete password reset flows, answer security questions, or steal API keys.

Flow: IDOR leaks user PII --> Use PII for password reset bypass --> Or answer security questions --> Or steal API keys --> Account takeover

### 5. Subdomain Takeover to Cookie Theft

Register an abandoned subdomain (dangling CNAME/A record). If the parent domain sets cookies with `Domain=.target.com`, the taken-over subdomain can read those cookies.

Flow: Identify dangling DNS record --> Register/claim the subdomain --> Set up cookie-stealing page --> Read parent-domain scoped cookies --> Session hijack

### 6. Race Condition to Financial Impact

Race conditions in payment, transfer, or redemption endpoints allow duplicate operations. Demonstrate actual monetary loss.

Flow: Identify financial transaction endpoint --> Send concurrent requests --> Demonstrate duplicate transaction --> Calculate monetary impact

### 7. Info Disclosure to Full Exploitation

Transform informational findings (version numbers, internal paths, debug output) into critical vulnerabilities by demonstrating exploitation.

Flow: Information leak (debug endpoint, stack trace, config file) --> Extract actionable data (credentials, internal URLs, architecture info) --> Use data to exploit deeper vulnerability

## Building Custom Chains

Every time you find something, stop and map what new position it gives you. Look at what is accessible from that position. If you cannot escalate right now, note it and come back when you find the missing link.

### Three Layers

1. **Initial Finding**: The entry point vulnerability (XSS, SSRF, IDOR, open redirect, info disclosure)
2. **Bridge/Enabler**: The connection that amplifies the initial finding (leaked credentials, OAuth flow, admin context)
3. **Final Impact**: The business-critical outcome (ATO, RCE, data breach, financial loss)

## Presentation

Present chains as single reports. Walk the triager through the complete
attack scenario step by step. Each step should be reproducible, and the
final impact should be stated in business terms.

Don't submit individual links as separate reports — the chain as a whole
carries materially higher impact than its parts.
