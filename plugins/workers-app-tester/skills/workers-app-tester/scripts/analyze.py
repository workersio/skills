#!/usr/bin/env python3
"""Security-focused traffic analyzer for Android app testing.

Usage:
    python3 analyze.py --input /tmp/session/traffic.jsonl
    python3 analyze.py --input traffic.jsonl --mode idor
    python3 analyze.py --input traffic.jsonl --mode full --json
    python3 analyze.py --help

Modes: endpoints, idor, auth, exposure, headers, full (default)
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ── IDOR detection patterns ───────────────────────────────────
RE_NUMERIC_ID = re.compile(r"/(\d{1,12})(?:/|$|\?)")
RE_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
RE_HEX_ID = re.compile(r"/([0-9a-f]{16,40})(?:/|$|\?)", re.I)
RE_QUERY_ID = re.compile(
    r"[?&]((?:user|account|profile|order|item|doc|org|team|project|resource|"
    r"message|comment|invoice|payment|transaction|record|file|image|video|"
    r"id|uid|pid|oid|tid)[_-]?id)=([^&]+)", re.I
)

# ── PII / sensitive data patterns ─────────────────────────────
RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
RE_PHONE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
RE_CC = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
RE_JWT = re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}")
RE_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
RE_PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----")
RE_API_KEY_PATTERN = re.compile(
    r"(?:api[_-]?key|apikey|access[_-]?token|secret[_-]?key|"
    r"client[_-]?secret|app[_-]?secret)\s*[=:]\s*[\"']?([a-zA-Z0-9_\-]{20,})", re.I
)
RE_AWS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")
RE_FIREBASE = re.compile(r"AIza[0-9A-Za-z_-]{35}")

# ── Auth headers ──────────────────────────────────────────────
AUTH_HEADERS = {"authorization", "x-api-key", "x-auth-token", "x-csrf-token", "x-session-id"}

# ── Security response headers ─────────────────────────────────
SECURITY_HEADERS = {
    "strict-transport-security": "Missing HSTS",
    "x-content-type-options": "Missing X-Content-Type-Options",
    "x-frame-options": "Missing X-Frame-Options",
    "content-security-policy": "Missing CSP",
}
INFO_HEADERS = {"server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Security-focused analysis of captured Android app traffic.")
    p.add_argument("--input", required=True, help="Path to traffic.jsonl")
    p.add_argument("--mode", default="full",
                   choices=["endpoints", "idor", "auth", "exposure", "headers", "full"],
                   help="Analysis mode (default: full)")
    p.add_argument("--json", action="store_true", help="Output JSON instead of plain text")
    p.add_argument("--since-seconds", type=int, default=0, help="Only analyze flows from last N seconds")
    return p.parse_args()


# ── Data loading ──────────────────────────────────────────────

def load_flows(path: Path, since_seconds: int = 0) -> list[dict]:
    """Load JSONL and collapse request+response records by flow_id."""
    if not path.exists():
        return []
    flows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            fid = str(rec.get("flow_id", ""))
            if not fid:
                continue
            flow = flows.setdefault(fid, {"flow_id": fid})
            event = rec.get("event")
            flow["updated_at"] = rec.get("timestamp", 0)
            if event == "request":
                flow["request"] = rec
            elif event == "response":
                flow["response"] = rec
            elif event == "error":
                flow["error"] = rec
            if "request" not in flow:
                flow["request"] = rec

    result = list(flows.values())
    if since_seconds > 0:
        threshold = time.time() - since_seconds
        result = [f for f in result if float(f.get("updated_at", 0)) >= threshold]
    result.sort(key=lambda f: float(f.get("updated_at", 0)))
    return result


def _get(flow: dict, *keys) -> str:
    """Safely get nested values from a flow dict."""
    obj = flow
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k, "")
        else:
            return ""
    return str(obj) if obj else ""


# ── Analysis: Endpoints ───────────────────────────────────────

def analyze_endpoints(flows: list[dict]) -> dict:
    endpoint_map: dict[str, dict] = {}
    host_counts: Counter = Counter()

    for flow in flows:
        method = _get(flow, "request", "method")
        host = _get(flow, "request", "host")
        path = _get(flow, "request", "path").split("?")[0]
        status = _get(flow, "response", "status_code")
        host_counts[host] += 1
        key = f"{method} {host}{path}"
        ep = endpoint_map.setdefault(key, {"method": method, "host": host, "path": path, "hits": 0, "statuses": []})
        ep["hits"] += 1
        if status:
            ep["statuses"].append(str(status))

    return {
        "total_flows": len(flows),
        "unique_endpoints": len(endpoint_map),
        "hosts": dict(host_counts.most_common(20)),
        "endpoints": sorted(endpoint_map.values(), key=lambda e: e["hits"], reverse=True),
    }


# ── Analysis: IDOR ────────────────────────────────────────────

def _generalize_path(path: str) -> str:
    """Replace numeric IDs and UUIDs with placeholders for grouping."""
    path = RE_UUID.sub("{uuid}", path)
    path = re.sub(r"/\d{1,12}(?=/|$)", "/{id}", path)
    path = RE_HEX_ID.sub("/{hex}", path)
    return path


def analyze_idor(flows: list[dict]) -> dict:
    candidates: dict[str, dict] = {}

    for flow in flows:
        method = _get(flow, "request", "method")
        host = _get(flow, "request", "host")
        full_path = _get(flow, "request", "path")
        path = full_path.split("?")[0]
        url = f"{host}{full_path}"

        findings = []

        # Numeric IDs in path
        nums = RE_NUMERIC_ID.findall(path)
        if nums:
            findings.append(("HIGH", "Numeric ID in path", nums))

        # UUIDs in path
        uuids = RE_UUID.findall(path)
        if uuids:
            findings.append(("MEDIUM", "UUID in path", uuids))

        # Hex IDs in path
        hexids = RE_HEX_ID.findall(path)
        if hexids:
            findings.append(("MEDIUM", "Hex ID in path", hexids))

        # ID-like query params
        qids = RE_QUERY_ID.findall(full_path)
        if qids:
            findings.append(("HIGH", f"ID query params: {', '.join(p[0] for p in qids)}", [p[1] for p in qids]))

        for risk, reason, ids in findings:
            gen_path = _generalize_path(path)
            key = f"{method} {host}{gen_path}"
            cand = candidates.setdefault(key, {
                "endpoint": key, "risk": risk, "reason": reason,
                "observed_ids": [], "example_urls": [],
            })
            cand["observed_ids"].extend(ids)
            if len(cand["example_urls"]) < 3:
                cand["example_urls"].append(f"{method} {url}")
            # Upgrade risk if needed
            if risk == "HIGH" and cand["risk"] != "HIGH":
                cand["risk"] = "HIGH"

    # Deduplicate observed IDs and add test suggestions
    for cand in candidates.values():
        cand["observed_ids"] = list(dict.fromkeys(cand["observed_ids"]))[:10]
        ids = cand["observed_ids"]
        if cand["risk"] == "HIGH" and all(i.isdigit() for i in ids):
            sorted_ids = sorted(int(i) for i in ids)
            lo, hi = sorted_ids[0] - 1, sorted_ids[-1] + 1
            cand["test"] = f"Try IDs {lo}, {hi} with a different user's session to test access control"
        else:
            cand["test"] = "Substitute another user's identifier and check if their data is returned"

    sorted_cands = sorted(candidates.values(), key=lambda c: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[c["risk"]])
    return {"idor_candidates": sorted_cands}


# ── Analysis: Auth ────────────────────────────────────────────

def _decode_jwt_payload(token: str) -> dict | None:
    """Decode JWT payload (middle segment) without external deps."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload = parts[1]
        # Fix padding
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return None


def analyze_auth(flows: list[dict]) -> dict:
    auth_seen: dict[str, dict] = {}
    endpoints_with_auth: set[str] = set()
    endpoints_without_auth: set[str] = set()
    all_endpoints: set[str] = set()
    jwt_claims: list[dict] = []
    token_values: list[str] = []

    for flow in flows:
        method = _get(flow, "request", "method")
        host = _get(flow, "request", "host")
        path = _get(flow, "request", "path").split("?")[0]
        ep = f"{method} {host}{path}"
        all_endpoints.add(ep)

        req_headers = flow.get("request", {}).get("request_headers", {})
        found_auth = False

        for hname, hval in req_headers.items():
            if hname.lower() in AUTH_HEADERS or hname.lower() == "cookie":
                found_auth = True
                key = hname.lower()
                entry = auth_seen.setdefault(key, {"header": hname, "count": 0, "type": "unknown"})
                entry["count"] += 1

                val = str(hval)
                if val != "<redacted>":
                    token_values.append(val)
                    if val.startswith("Bearer "):
                        entry["type"] = "Bearer"
                        jwt_payload = _decode_jwt_payload(val[7:])
                        if jwt_payload:
                            entry["type"] = "Bearer JWT"
                            jwt_claims.append(jwt_payload)
                    elif val.startswith("Basic "):
                        entry["type"] = "Basic"
                    elif RE_JWT.search(val):
                        entry["type"] = "JWT (raw)"
                        jwt_payload = _decode_jwt_payload(RE_JWT.search(val).group())
                        if jwt_payload:
                            jwt_claims.append(jwt_payload)
                elif "redacted" in val:
                    entry["type"] = "present (redacted in logs)"

        if found_auth:
            endpoints_with_auth.add(ep)
        else:
            endpoints_without_auth.add(ep)

    # Endpoints that are sometimes authed, sometimes not
    inconsistent = endpoints_with_auth & endpoints_without_auth

    # Build test suggestions
    suggestions = []
    if endpoints_with_auth:
        sample = list(endpoints_with_auth)[:3]
        suggestions.append(f"Strip auth header from: {', '.join(sample)} — check for 401")
    if jwt_claims:
        for claim in jwt_claims[:1]:
            if "exp" in claim:
                suggestions.append(f"Replay token after expiry (exp={claim['exp']})")
            if "sub" in claim or "user_id" in claim:
                uid = claim.get("sub") or claim.get("user_id")
                suggestions.append(f"Change user ID in JWT from {uid} to another user's ID")
            if "role" in claim:
                suggestions.append(f"Modify JWT role from '{claim['role']}' to 'admin'")

    # Deduplicate JWT claims for display
    unique_claims = {}
    for c in jwt_claims:
        key = json.dumps(c, sort_keys=True)
        unique_claims[key] = c

    return {
        "auth_mechanisms": list(auth_seen.values()),
        "endpoints_with_auth": len(endpoints_with_auth),
        "endpoints_without_auth": sorted(endpoints_without_auth - endpoints_with_auth)[:20],
        "inconsistent_auth": sorted(inconsistent)[:10],
        "jwt_claims": list(unique_claims.values())[:5],
        "test_suggestions": suggestions,
    }


# ── Analysis: Exposure ────────────────────────────────────────

def _redact_sample(value: str) -> str:
    """Show first 3 and last 3 chars with *** in middle."""
    if len(value) <= 8:
        return value[:2] + "***"
    return value[:3] + "***" + value[-3:]


def _scan_text(text: str) -> list[dict]:
    """Scan text for PII patterns. Return findings."""
    findings = []
    checks = [
        (RE_EMAIL, "email", "MEDIUM"),
        (RE_PHONE, "phone", "MEDIUM"),
        (RE_CC, "cc-like", "HIGH"),
        (RE_SSN, "ssn-like", "HIGH"),
        (RE_JWT, "jwt-token", "LOW"),
        (RE_PRIVATE_KEY, "private-key", "CRITICAL"),
        (RE_API_KEY_PATTERN, "api-key", "HIGH"),
        (RE_AWS_KEY, "aws-key", "CRITICAL"),
        (RE_FIREBASE, "firebase-key", "HIGH"),
    ]
    for pattern, ptype, risk in checks:
        matches = pattern.findall(text)
        if matches:
            sample = matches[0] if isinstance(matches[0], str) else str(matches[0])
            findings.append({"type": ptype, "risk": risk, "sample": _redact_sample(sample)})
    return findings


def analyze_exposure(flows: list[dict]) -> dict:
    findings = []
    large_responses = []

    for flow in flows:
        method = _get(flow, "request", "method")
        host = _get(flow, "request", "host")
        path = _get(flow, "request", "path").split("?")[0]
        status = _get(flow, "response", "status_code")
        ep = f"{method} {host}{path} -> {status}"

        # Scan response body
        resp_body = _get(flow, "response", "response_body_preview")
        if resp_body:
            for f_ in _scan_text(resp_body):
                findings.append({**f_, "flow": ep, "location": "response_body"})
            if len(resp_body) > 2000:
                large_responses.append({"endpoint": ep, "preview_size": len(resp_body)})

        # Scan request body
        req_body = _get(flow, "request", "request_body_preview")
        if req_body:
            for f_ in _scan_text(req_body):
                findings.append({**f_, "flow": ep, "location": "request_body"})

    # Deduplicate by (flow, type, location)
    seen = set()
    unique = []
    for f_ in findings:
        key = (f_["flow"], f_["type"], f_["location"])
        if key not in seen:
            seen.add(key)
            unique.append(f_)

    # Sort by risk
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    unique.sort(key=lambda x: risk_order.get(x["risk"], 4))

    return {"findings": unique, "large_responses": large_responses[:20]}


# ── Analysis: Headers ─────────────────────────────────────────

def analyze_headers(flows: list[dict]) -> dict:
    hosts: dict[str, dict] = {}

    for flow in flows:
        host = _get(flow, "request", "host")
        if not host:
            continue
        entry = hosts.setdefault(host, {"missing": set(), "cors": [], "info": set()})

        resp_headers = flow.get("response", {}).get("response_headers", {})
        resp_lower = {k.lower(): v for k, v in resp_headers.items()} if resp_headers else {}

        # Check missing security headers
        for hdr, msg in SECURITY_HEADERS.items():
            if hdr not in resp_lower:
                entry["missing"].add(msg)

        # CORS check
        acao = resp_lower.get("access-control-allow-origin", "")
        acac = resp_lower.get("access-control-allow-credentials", "")
        if acao == "*" and acac.lower() == "true":
            entry["cors"].append("Allow-Origin: * with credentials (dangerous)")
        elif acao == "*":
            entry["cors"].append("Allow-Origin: * (overly permissive)")

        # Info disclosure
        for hdr in INFO_HEADERS:
            val = resp_lower.get(hdr, "")
            if val:
                entry["info"].add(f"{hdr}: {val}")

    # Convert sets to lists for JSON serialization
    result = {}
    for host, data in hosts.items():
        result[host] = {
            "missing": sorted(data["missing"]),
            "cors": list(set(data["cors"]))[:5],
            "info": sorted(data["info"]),
        }

    return {"hosts": result}


# ── Full analysis ─────────────────────────────────────────────

def run_full(flows: list[dict]) -> dict:
    return {
        "endpoints": analyze_endpoints(flows),
        "idor": analyze_idor(flows),
        "auth": analyze_auth(flows),
        "exposure": analyze_exposure(flows),
        "headers": analyze_headers(flows),
    }


# ── Plain text formatting ─────────────────────────────────────

def format_report(results: dict) -> str:
    lines = []

    if "endpoints" in results:
        ep = results["endpoints"]
        lines.append(f"=== ENDPOINT MAP ===")
        lines.append(f"total_flows={ep['total_flows']} unique_endpoints={ep['unique_endpoints']}")
        hosts_str = ", ".join(f"{h}({c})" for h, c in list(ep["hosts"].items())[:10])
        if hosts_str:
            lines.append(f"hosts: {hosts_str}")
        for e in ep["endpoints"][:30]:
            statuses = ",".join(sorted(set(e["statuses"])))
            lines.append(f"  {e['method']:6s} {e['host']}{e['path']}  x{e['hits']}  [{statuses}]")
        lines.append("")

    if "idor" in results:
        idor = results["idor"]
        lines.append("=== IDOR CANDIDATES ===")
        if not idor["idor_candidates"]:
            lines.append("  No IDOR candidates detected.")
        for c in idor["idor_candidates"]:
            lines.append(f"[{c['risk']}] {c['endpoint']}")
            lines.append(f"  Reason: {c['reason']}")
            lines.append(f"  IDs seen: {', '.join(c['observed_ids'][:5])}")
            lines.append(f"  Test: {c['test']}")
            for ex in c.get("example_urls", [])[:2]:
                lines.append(f"  Example: {ex}")
        lines.append("")

    if "auth" in results:
        auth = results["auth"]
        lines.append("=== AUTH ANALYSIS ===")
        for mech in auth["auth_mechanisms"]:
            lines.append(f"  {mech['header']}: type={mech['type']} seen={mech['count']}x")
        if auth["jwt_claims"]:
            for claim in auth["jwt_claims"][:2]:
                safe = {k: v for k, v in claim.items() if k in ("sub", "role", "exp", "iss", "aud", "user_id", "email")}
                lines.append(f"  JWT claims: {json.dumps(safe)}")
        if auth["endpoints_without_auth"]:
            lines.append(f"  Unauthenticated endpoints ({len(auth['endpoints_without_auth'])}):")
            for ep in auth["endpoints_without_auth"][:10]:
                lines.append(f"    {ep}")
        if auth["inconsistent_auth"]:
            lines.append(f"  Inconsistent auth ({len(auth['inconsistent_auth'])}):")
            for ep in auth["inconsistent_auth"][:5]:
                lines.append(f"    {ep}")
        if auth["test_suggestions"]:
            lines.append("  Test suggestions:")
            for s in auth["test_suggestions"]:
                lines.append(f"    - {s}")
        lines.append("")

    if "exposure" in results:
        exp = results["exposure"]
        lines.append("=== DATA EXPOSURE ===")
        if not exp["findings"]:
            lines.append("  No sensitive data patterns detected.")
        for f_ in exp["findings"][:20]:
            lines.append(f"[{f_['risk']}] {f_['type']} in {f_['location']}")
            lines.append(f"  Flow: {f_['flow']}")
            lines.append(f"  Sample: {f_['sample']}")
        if exp["large_responses"]:
            lines.append(f"  Large responses (potential over-fetching):")
            for lr in exp["large_responses"][:5]:
                lines.append(f"    {lr['endpoint']} ({lr['preview_size']} chars in preview)")
        lines.append("")

    if "headers" in results:
        hdrs = results["headers"]
        lines.append("=== SECURITY HEADERS ===")
        for host, data in list(hdrs["hosts"].items())[:10]:
            lines.append(f"  {host}:")
            if data["missing"]:
                lines.append(f"    Missing: {'; '.join(data['missing'])}")
            if data["cors"]:
                lines.append(f"    CORS: {'; '.join(data['cors'])}")
            if data["info"]:
                lines.append(f"    Info disclosure: {'; '.join(data['info'])}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    flows = load_flows(Path(args.input), args.since_seconds)

    if not flows:
        print("No flows found in traffic log.")
        return 1

    mode_map = {
        "endpoints": lambda f: {"endpoints": analyze_endpoints(f)},
        "idor": lambda f: {"idor": analyze_idor(f)},
        "auth": lambda f: {"auth": analyze_auth(f)},
        "exposure": lambda f: {"exposure": analyze_exposure(f)},
        "headers": lambda f: {"headers": analyze_headers(f)},
        "full": run_full,
    }

    results = mode_map[args.mode](flows)

    if args.json:
        # Convert sets to lists for JSON
        print(json.dumps(results, indent=2, default=lambda x: sorted(x) if isinstance(x, set) else str(x)))
    else:
        print(format_report(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
