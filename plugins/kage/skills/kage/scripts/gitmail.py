#!/usr/bin/env python3
"""
gitmail.py — GitHub org → public repos → trufflehog (verified secrets).

Used by kage Turn 1 recon to surface leaked credentials across an
organization's public repos. Env var GITHUB_TOKEN is strongly recommended
(5k req/hr vs 60 unauthenticated).

Usage:
    python3 gitmail.py -O <org> [--verified-only] [--timeout 300] \\
                       [--jobs 5] [-o out.json]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

GITHUB_API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "kage-gitmail"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def log(msg: str) -> None:
    print(f"[gitmail] {msg}", file=sys.stderr, flush=True)


def fetch_org_repos(org: str) -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        url = f"{GITHUB_API}/orgs/{org}/repos?per_page=100&page={page}"
        for attempt in range(3):
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 403 and "X-RateLimit-Reset" in r.headers:
                wait = max(1, int(r.headers["X-RateLimit-Reset"]) - int(time.time()) + 5)
                log(f"rate-limited; sleeping {min(wait, 120)}s")
                time.sleep(min(wait, 120))
                continue
            break
        if r.status_code == 404:
            log(f"org not found: {org}")
            return []
        if r.status_code != 200:
            log(f"error fetching org repos: {r.status_code}")
            return repos
        data = r.json()
        if not data:
            return repos
        for repo in data:
            if repo.get("fork"):
                continue
            repos.append({"name": repo["name"], "url": repo["html_url"]})
        if len(data) < 100:
            return repos
        page += 1


def scan_repo(repo: dict, verified_only: bool, timeout: int) -> dict:
    cmd = ["trufflehog", "git", repo["url"], "--json", "--no-update"]
    if verified_only:
        cmd.append("--results=verified")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except subprocess.TimeoutExpired:
        return {"repo": repo["name"], "url": repo["url"], "error": "timeout", "secrets": []}
    except FileNotFoundError:
        return {"repo": repo["name"], "url": repo["url"], "error": "trufflehog not installed", "secrets": []}

    secrets = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "DetectorName" not in obj:
            continue
        git_meta = obj.get("SourceMetadata", {}).get("Data", {}).get("Git", {})
        commit = git_meta.get("commit", "")[:8]
        path = git_meta.get("file", "Unknown")
        line_no = git_meta.get("line", "")
        file_link = repo["url"]
        if commit and path != "Unknown":
            file_link = f"{repo['url']}/blob/{commit}/{path}"
            if line_no:
                file_link += f"#L{line_no}"
        secrets.append({
            "detector": obj.get("DetectorName"),
            "verified": obj.get("Verified", False),
            "redacted": obj.get("Redacted", "")[:80],
            "file": path,
            "line": line_no,
            "commit": commit,
            "file_link": file_link,
        })

    return {"repo": repo["name"], "url": repo["url"], "secrets": secrets}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-O", "--org", required=True, help="GitHub organization")
    p.add_argument("-o", "--output", help="JSON output path (stdout if omitted)")
    p.add_argument("--verified-only", action="store_true", help="Only verified secrets (faster, fewer FPs)")
    p.add_argument("--timeout", type=int, default=300, help="Per-repo scan timeout in seconds (default 300)")
    p.add_argument("--jobs", type=int, default=5, help="Concurrent repo scans (default 5)")
    # Compat shims for the original CLI — kept so existing invocations still parse.
    p.add_argument("-r", "--repos", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("-s", "--scan", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args()

    if not TOKEN:
        log("warning: GITHUB_TOKEN not set — hitting 60 req/hr rate limit")

    log(f"fetching repos for org: {args.org}")
    repos = fetch_org_repos(args.org)
    log(f"{len(repos)} public non-fork repos")

    all_secrets, repo_results = [], []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(scan_repo, r, args.verified_only, args.timeout): r for r in repos}
        for done in as_completed(futs):
            result = done.result()
            repo_results.append(result)
            for s in result.get("secrets", []):
                entry = {"repo": result["repo"], "repo_url": result["url"], **s}
                all_secrets.append(entry)
                log(f"SECRET {result['repo']} {s['detector']} verified={s['verified']}")

    output = {
        "org": args.org,
        "scan_date": datetime.utcnow().isoformat(timespec="seconds"),
        "token_present": bool(TOKEN),
        "verified_only": args.verified_only,
        "repos_scanned": len(repo_results),
        "total_secrets": len(all_secrets),
        "secrets": all_secrets,
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        log(f"wrote {args.output}")
    else:
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
