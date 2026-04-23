---
name: agent-constraints
description: Universal constraints that apply to every Kage sub-agent. Testing agents, the verifier, the chain-builder, the judge, and the report-writer all follow these rules. Agents link here instead of restating them.
---

# Universal sub-agent constraints

Every Kage sub-agent follows these rules. Agent files reference this doc
instead of re-stating them.

## HTTP

- **Never invoke `curl` directly.** curl has a detectable TLS fingerprint;
  WAFs block it. Route every HTTP call through `scripts/tls.py`
  (curl_cffi with rotating browser fingerprints) or the bundled probe
  scripts that already use it.
- All probe scripts emit a shared `findings[]` / `summary{}` shape.
- Truncate bodies at a reasonable limit (≤ 2 KB) in logs and findings so
  output stays parseable.

## Execution

- Every shell command runs through the Kage shim: prefix with `"$K"`.
- Never run pentest tools directly on the host.
- Non-interactive only. Never hang waiting for a TTY prompt.

## Scope discipline

- Do only the job named in your frontmatter description. Don't chase
  out-of-scope findings, don't branch into adjacent attack classes.
- If you discover something that belongs to another agent, record it in
  a note file and return — don't probe further.

## Filtering

- Testing agents report **everything they find**, including low-confidence
  signals. The `judge` sub-agent is the sole filter.
- Do not apply the exclusion list yourself. That is the judge's job.
- Mark confidence low when uncertain rather than dropping the finding.

## Output

- Write structured JSON (or JSONL) alongside any human-readable markdown.
- Send progress messages to stderr. Keep stdout clean and parseable.
- Distinct exit codes for distinct failure modes where possible.

## Time

- **5-minute rule.** If a probe doesn't yield signal within 5 minutes,
  move on and document what was tried.
- Don't retry in infinite loops. Back off and report.
