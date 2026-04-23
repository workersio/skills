# Tools installed in the sandbox

Inventory of what's available inside the kage container. Every tool below
runs via `$K <tool>`. HTTP to targets always goes through `scripts/tls.py`
or `scripts/browser.py` — never raw `curl`.

## Discovery & recon
- **subfinder** — passive subdomain enumeration
- **httpx** — live-host probe, tech fingerprint, status codes
- **katana** — headless crawler (JS-aware)
- **gospider** — alternate JS crawler (different SPA handling)
- **hakrawler** — fast simple crawler
- **gau**, **waybackurls** — Wayback + CommonCrawl + AlienVault URL harvest
- **dnsx** — DNS resolver / permuter
- **puredns** — high-speed bruteforce DNS resolver
- **alterx** — subdomain permutation generator
- **mapcidr** — CIDR expansion, IP-list generation
- **uncover** — Shodan / Censys / Fofa CLI query
- **amass** — deep passive + active recon (slow)

## Port scanning & service detection
- **naabu** — fast TCP port scanner
- **nmap** — service version detection, scripts
- **masscan** — internet-scale scanner

## Vuln scanning
- **nuclei** — template-based vuln scanner (dispatched via vuln-scanner sub-agent)
- **dalfox** — XSS-focused scanner
- **sqlmap** — SQL injection
- **nikto** — legacy web scanner
- **wafw00f** — WAF fingerprinting
- **schemathesis** — OpenAPI/Swagger schema-driven fuzzing

## Content & parameter discovery
- **ffuf** — fast directory / param / vhost fuzzer
- **dirsearch** — directory fuzzer (Python alternative)
- **arjun** — hidden-parameter discovery

## Secrets
- **gitleaks** — repo secret scanner
- **trufflehog** — verified-secret scanner (used by gitmail.py)
- **betterleaks** — alternative scanner; catches patterns gitleaks misses

## Client-side library CVEs
- **retire** — scans JS bundles for known-vulnerable library versions
- **js-beautify** — pretty-print minified JS for regex sweeps

## OSINT / external intel
- **`scripts/dorks.py`** — generate Google dork URLs (credentials, pii, admin, cloud, etc.)
- **`scripts/gitmail.py`** — GitHub org/user/email → repos + committer emails + TruffleHog-scanned secrets
- **interactsh-client** — OOB callback listener (blind SSRF/XSS)

## HTTP / anti-detection
- **curl_cffi** via **`scripts/tls.py`** — TLS fingerprint impersonation (chrome124/131, safari17_0, firefox133)
- **camoufox** via **`scripts/browser.py`** — undetected Firefox for Cloudflare-protected targets; drop-in shape replacement for tls.py

## URL / text processing
- **qsreplace** — replace query-string values for fuzzing
- **unfurl** — parse URLs (extract domain, path, params)
- **gf** — grep with pre-built bug-bounty patterns
- **anew** — dedup lines against a growing set
- **jq**, **ripgrep**, **parallel** — standard data wrangling + GNU parallel fan-out

## White-box / code audit
- **semgrep**, **bandit** — SAST
- **safety** — Python dependency CVE check
- **ruff** — fast Python linter

## Custom probe scripts (under `/skill/scripts/`)
- `authbypass.py`, `cors.py`, `headers.py`, `idor.py`, `race.py`, `ssrf.py`, `diff.py` — attack-class probes
- `tls.py`, `browser.py` — HTTP transports (curl_cffi and Camoufox respectively)
- `client.py` — shared `make_request()` wrapper
- `dorks.py`, `gitmail.py` — OSINT
