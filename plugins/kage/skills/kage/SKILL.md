---
name: kage
description: >
  Local pentest sandbox for a full black-box engagement. Triggers on
  "kage", "pentest", "security audit on", "audit the security of". Runs
  recon, deep testing, exploit verification, and judging inside a
  per-engagement Kali Docker container. Each host working directory gets
  its own isolated sandbox. Produces `./results/<target>/audit-report.md`.
license: MIT
compatibility: >
  Requires Docker Desktop (macOS/Windows) or Docker Engine (Linux) running,
  ~3 GB disk for the image, and network access for the first-run pull.
---

# Kage — pentest sandbox

## When to use this skill

- `kage <target>` — black-box engagement
- `pentest <target>` / `security audit on <target>` — same as above
- `kage audit <local path>` — white-box source audit only
- `kage greybox <target> <source-path>` — black-box + source context

`<target>` can be a domain, URL, wildcard (`*.example.com`), or a local
source path. In `greybox` mode, Turn 0 runs the bundled
[`audit-context-building`](references/audit-context-building/SKILL.md)
methodology on the source first, then feeds trust-boundary and auth-flow
context into Turns 2–3.

## Container model

Every tool runs inside a per-engagement Kali container via the `$K`
shim. Each working directory gets its own container (name derived from
`$PWD`), so two engagements run simultaneously without cross-contamination.

```bash
SKILL_DIR="$HOME/.claude/skills/kage"
K="$SKILL_DIR/scripts/k"
"$K" <cmd>            # runs <cmd> inside this engagement's container
"$K" ls | reset | prune | nuke   # management subcommands
```

Probes live at `/skill/scripts/*.py` inside the container (read-only
bind mount). Results go to `/workspace/results/<target>/` (bind-mounted
from your CWD).

Never run pentest tools directly on the host.

---

## Turn 0 — Setup

```bash
SKILL_DIR="$HOME/.claude/skills/kage"
K="$SKILL_DIR/scripts/k"
"$K" whoami            # warms the sandbox; surfaces docker errors

TARGET="example.com"   # derive from user prompt; slugify for paths

# Host-side mkdir so dirs are owned by your UID (host Write tool needs this).
mkdir -p "results/$TARGET"/{recon,vulns,testing,exploits,chains,verification,judging,reports}
```

Read `./creds.md` from the user's CWD if present. If absent: ask whether
to proceed black-box, or point at the template in
[`assets/creds.sample.md`](assets/creds.sample.md).

### Greybox pre-flight (only if mode is `greybox`)

Apply the
[`audit-context-building`](references/audit-context-building/SKILL.md)
methodology to `<source-path>`. For dense modules, dispatch the
[`function-analyzer`](references/audit-context-building/agents/function-analyzer.md)
sub-agent — multiple in parallel if warranted.

Output `results/$TARGET/context.md` covering: trust boundaries, auth
flow, data flow, high-value entry points, known-sensitive parameters.
All Turn-2 testers and Turn-3a exploiter read `context.md` alongside
their usual inputs.

Write `results/$TARGET/engagement.json` with `{target, scope_type,
started_at, rules_of_engagement}`.

---

## Turn 1 — Recon (two phases)

Discovery runs fast (1–3 min) as a streaming pipe. Vuln scanning is
long (5–15 min) and isolated in a sub-agent so nuclei's verbose output
doesn't pollute the main context.

### Phase 1 — Discovery

```bash
R="results/$TARGET"
"$K" bash -c '
  set -e
  cd /workspace
  R="results/'"$TARGET"'"
  (subfinder -d "'"$TARGET"'" -silent \
     | tee "$R/recon/subs.txt" \
     | httpx -silent -title -tech-detect -status-code \
     | tee "$R/recon/live.txt") &
  (gau --subs "'"$TARGET"'" > "$R/recon/wayback.txt") &
  (until [ -s "$R/recon/live.txt" ]; do sleep 1; done
   katana -u "$R/recon/live.txt" -d 3 -jc -silent -o "$R/recon/crawl.txt") &
  (python3 /skill/scripts/dorks.py -d "'"$TARGET"'" --output "$R/recon/dorks.json") &
  wait'
```

**In parallel, dispatch** [`port-scanner`](agents/port-scanner.md):
`HOSTS_FILE=$R/recon/live.txt`, `OUTDIR=$R/recon/ports/`.

**If `GITHUB_TOKEN` is set**, also run `scripts/gitmail.py`:

```bash
"$K" bash -c "GITHUB_TOKEN=\"$GH_TOKEN\" python3 /skill/scripts/gitmail.py \
   -O <guessed-org> -r -s --verified-only \
   -o /workspace/$R/recon/github.json"
```

Wait for pipe + port-scanner (+ gitmail if run) before Phase 2.

### Phase 2 — Vuln scan

Dispatch [`vuln-scanner`](agents/vuln-scanner.md) with
`LIVE_HOSTS_FILE=$R/recon/live.txt`, `OUTPUT=$R/vulns/nuclei.txt`.

Wait for vuln-scanner before Turn 2.

### Summary

Write `recon/summary.md`: subdomain count, live-host count, high-value
ports, nuclei severity counts + top hits, auth endpoints, ID-bearing
API paths, URL-accepting parameters.

Stop here if the user said `recon-only`.

---

## Turn 2 — Deep testing (parallel fan-out)

Read `recon/summary.md`. For every trigger that fires, **spawn the
matching tester sub-agents simultaneously** — emit all dispatches in
one message. Each tester issues its own `$K` calls into the shared
container (docker exec is concurrent) and writes to its own
`testing/<class>/` path.

| Trigger in recon | Dispatch |
|---|---|
| login / SSO / OAuth / JWT endpoints | [`auth-tester`](agents/auth-tester.md) |
| API endpoints with object IDs + 2 accounts | [`idor-tester`](agents/idor-tester.md) |
| 403s, admin panels, role-gated routes + ≥2 roles | [`access-control-tester`](agents/access-control-tester.md) |
| `url=` / `redirect=` / `proxy=` / `fetch=` / `webhook=` params | [`ssrf-tester`](agents/ssrf-tester.md) |
| parameterised URLs, search fields, forms, GraphQL vars | [`injection-tester`](agents/injection-tester.md) |
| user-facing HTML (comments, profile, search) | [`client-side-tester`](agents/client-side-tester.md) |
| OpenAPI/Swagger URL, `/graphql`, REST routes | [`api-tester`](agents/api-tester.md) |
| payment / coupon / redeem / invite / signup endpoints | [`logic-tester`](agents/logic-tester.md) |
| crawler surface thin; hidden paths likely | [`content-discovery`](agents/content-discovery.md) |
| JS bundles discovered in Turn 1 | [`js-secret-scanner`](agents/js-secret-scanner.md) |
| any live web host | [`headers-tester`](agents/headers-tester.md) |
| needs 2+ provisioned accounts (self-service signup) | use [`agentmail`](references/agentmail/SKILL.md) to spin up disposable inboxes (requires `AGENTMAIL_API_KEY`) |

In `greybox` mode, every tester also reads `results/$TARGET/context.md`
and targets source-known weak points over generic scans.

**Wait for all testers to return.** Aggregate their JSON into a
candidate-finding inventory. Every probe emits a shared
`findings[]` / `summary{}` shape; all HTTP goes through `scripts/tls.py`
(or `scripts/browser.py` for Cloudflare targets).

**5-minute rule.** If a lead doesn't prove itself within 5 minutes,
move on. No theoretical bugs.

---

## Turn 3 — Exploit, verify, chain, judge

Sequential. Each step feeds the next.

### 3a. Exploit — filter BEFORE writing a PoC

Read [`references/judging.md`](references/judging.md). For each
candidate finding:

- **Drop outright** if it matches an auto-drop pattern (missing headers
  without PoC, version banners, self-XSS, logout CSRF, TRACE/TRACK, TLS
  cipher issues, SPF/DKIM/DMARC, info-leak 500s, rate-limit absent
  without an abuse scenario). **Do NOT build a PoC for these.**
- **Drop** if the impact statement contains "could potentially" or
  requires a condition unverifiable black-box. In `greybox` mode, check
  `context.md` first — source may confirm/refute.
- **Build a PoC** only when attacker action produces an observable,
  reproducible server-side outcome with real impact (data access, code
  execution, auth bypass, cost amplification, state change, financial).

For each survivor, write a `curl_cffi` PoC at
`results/$TARGET/exploits/<slug>.py`. Drop anything that doesn't
reproduce first run.

### 3b. Verify — parallel

For each PoC, dispatch [`verifier`](agents/verifier.md) — **emit all
verifier Tasks in one message**. Each gets its own
`OUTDIR=results/$TARGET/verification/F<NNN>/`, fresh auth, clean
session, 3× reproducibility.

Aggregate into `verification/verified_findings.json`.

### 3c. Chain

Dispatch [`chain-builder`](agents/chain-builder.md) on verified
findings. It maps the 7 canonical patterns in
[`references/chains.md`](references/chains.md) and looks for creative
combinations.

### 3d. Judge

Dispatch [`judge`](agents/judge.md). It applies the 4-gate filter from
[`references/judging.md`](references/judging.md), scores confidence +
CVSS, deduplicates, enforces the exclusion list.

Outputs: `judging/approved_findings.json` (the only findings that
reach the report), `judgment.md` (audit trail), `dropped_findings.md`.

---

## Turn 4 — Audit report

Dispatch [`report-writer`](agents/report-writer.md) with:
`TARGET`, `ENGAGEMENT_JSON`, `APPROVED_FINDINGS_JSON`,
`TEMPLATE=$SKILL_DIR/references/audit-report-template.md`,
`OUTPUT=results/$TARGET/audit-report.md`.

The agent fills `{{placeholders}}` from engagement + approved findings.
It does NOT re-filter — the judge already did that. Print a summary
table to the user when done.

---

## Failure modes to surface (don't swallow)

- Docker not installed / not running → print the shim's error, stop.
- Target unreachable / DNS fails.
- Rate-limited or WAF-blocked → slow down, rotate fingerprint
  (`tls.py --impersonate <name>`), or swap to `scripts/browser.py`.
- `creds.md` missing when the user asked for authenticated testing.

## Reference docs (load on demand)

- [`references/methodology.md`](references/methodology.md) — per-attack-class triggers + invocation details
- [`references/judging.md`](references/judging.md) — 4-gate filter + severity rubric + exclusion list
- [`references/chains.md`](references/chains.md) — 7 named escalation patterns
- [`references/report-formatting.md`](references/report-formatting.md) — platform conventions (HackerOne, Bugcrowd, Intigriti)
- [`references/audit-report-template.md`](references/audit-report-template.md) — Turn 4 template
- [`references/tools.md`](references/tools.md) — full inventory of tools installed in the sandbox
- [`references/audit-context-building/SKILL.md`](references/audit-context-building/SKILL.md) — greybox methodology
- [`references/agentmail/SKILL.md`](references/agentmail/SKILL.md) — disposable-inbox provisioning
- [`assets/creds.sample.md`](assets/creds.sample.md) — scope + credentials template
- [`assets/wordlist-strategy.md`](assets/wordlist-strategy.md) — target-specific subdomain wordlists
