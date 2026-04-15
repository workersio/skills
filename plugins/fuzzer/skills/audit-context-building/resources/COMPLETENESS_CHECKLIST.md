# Completeness Checklist

Analysis is NOT complete until every item is checked.

## Structural Completeness (Per-Function)
- [ ] Purpose section: 2+ sentences
- [ ] Inputs & Assumptions: All parameters + implicit inputs
- [ ] Outputs & Effects: All returns, state writes, external calls, events
- [ ] Block-by-Block Analysis: Every logical block (no gaps)
- [ ] Cross-Function Dependencies: All calls and shared state

## Content Depth (Per-Function)
- [ ] 3+ invariants identified
- [ ] 5+ assumptions documented
- [ ] First Principles applied at least once
- [ ] 5 Whys or 5 Hows applied 3+ times total
- [ ] Risk analysis for all external interactions

## Anti-Hallucination
- [ ] All claims cite file paths and line numbers
- [ ] No vague statements -- replaced with "unclear; need to check X"
- [ ] Contradictions resolved explicitly
- [ ] Every invariant/assumption tied to actual code

## System-Level Security Mapping (MANDATORY)

### Authentication coverage
- [ ] Listed EVERY route/endpoint with file:line
- [ ] Documented auth status (yes/no/how) for each
- [ ] Flagged unauth routes accepting user input

### Tenant isolation / Ownership
- [ ] Found EVERY database query (SELECT, UPDATE, DELETE, INSERT)
- [ ] Checked tenant/ownership filtering for each query taking request IDs
- [ ] Traced shared helpers that may enforce ownership

### Data flow tracing
- [ ] Traced sensitive data paths: input -> processing -> storage -> output
- [ ] Identified trust boundary crossings
- [ ] Checked for sensitive data in logs, errors, analytics

### External boundaries
- [ ] Listed EVERY webhook endpoint + signature verification status
- [ ] Listed EVERY OAuth integration + token storage
- [ ] Listed EVERY external API call + error handling

## Written Artifacts (MANDATORY)

1. **Route map** -- every endpoint: path, method, file:line, auth status
2. **Query map** -- every DB query: file:line, ID used, tenant ownership check
3. **Trust boundary diagram** -- public / authenticated / service / internal surfaces
4. **Sensitive data inventory** -- what, where stored, how protected
5. **Integration inventory** -- every external service, connection method, credentials
