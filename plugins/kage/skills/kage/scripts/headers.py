#!/usr/bin/env python3
"""
Security Header & Misconfiguration Scanner
Checks headers, CORS, CRLF, host header injection, cache poisoning indicators.

Usage:
  python3 headers.py --url "https://target.com" --output results.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from client import make_request


def fetch(url, extra_headers=None, timeout=10):
    # Headers come back already lowercased from client.make_request.
    return make_request(url, method="GET", extra_headers=extra_headers,
                        truncate=2000, timeout=timeout)

def main():
    parser = argparse.ArgumentParser(description="Header Audit")
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    findings = []

    # 1. Baseline request
    baseline = fetch(args.url)
    hdrs = baseline["headers"]

    # 2. Missing security headers
    required = {
        "strict-transport-security": "Missing HSTS — downgrade attacks possible",
        "content-security-policy": "Missing CSP — XSS risk increased",
        "x-content-type-options": "Missing X-Content-Type-Options — MIME sniffing possible",
        "x-frame-options": "Missing X-Frame-Options — clickjacking possible",
    }
    for header, desc in required.items():
        if header not in hdrs:
            findings.append({"type": "missing_header", "header": header, "detail": desc, "severity": "LOW"})

    # 3. CORS — arbitrary origin
    cors_hdrs = fetch(args.url, {"Origin": "https://evil.com"})["headers"]
    acao = cors_hdrs.get("access-control-allow-origin", "")
    acac = cors_hdrs.get("access-control-allow-credentials", "")
    if "evil.com" in acao and "true" in acac.lower():
        findings.append({"type": "cors", "detail": "Origin evil.com reflected with credentials=true", "severity": "HIGH", "evidence": f"ACAO: {acao}, ACAC: {acac}"})
    elif "evil.com" in acao:
        findings.append({"type": "cors", "detail": "Origin evil.com reflected (no credentials)", "severity": "MEDIUM", "evidence": f"ACAO: {acao}"})

    # 4. Null origin
    null_hdrs = fetch(args.url, {"Origin": "null"})["headers"]
    if null_hdrs.get("access-control-allow-origin", "") == "null" and "true" in null_hdrs.get("access-control-allow-credentials", "").lower():
        findings.append({"type": "cors_null", "detail": "Null origin accepted with credentials — exploitable via sandboxed iframe", "severity": "HIGH"})

    # 5. CRLF injection
    crlf = fetch(args.url + "/%0d%0aX-Injected:true")
    if "x-injected" in crlf["headers"]:
        findings.append({"type": "crlf", "detail": "CRLF injection — header injection possible", "severity": "HIGH"})

    # 6. Host header injection
    hhi = fetch(args.url, {"X-Forwarded-Host": "evil.com"})
    if "evil.com" in hhi.get("body", ""):
        findings.append({"type": "host_header", "detail": "X-Forwarded-Host reflected in response body", "severity": "MEDIUM"})

    # 7. Cache headers (for cache poisoning potential)
    cache_indicators = []
    for h in ["x-cache", "cf-cache-status", "age", "x-varnish", "x-served-by"]:
        if h in hdrs:
            cache_indicators.append(f"{h}: {hdrs[h]}")
    if cache_indicators:
        # Test unkeyed header
        poison = fetch(args.url + "?cb=" + str(hash(args.url))[-8:], {"X-Forwarded-Host": "evil.com"})
        if "evil.com" in poison.get("body", ""):
            findings.append({"type": "cache_poisoning", "detail": f"Cache detected ({', '.join(cache_indicators)}) and X-Forwarded-Host reflected — cache poisoning likely", "severity": "HIGH"})
        else:
            findings.append({"type": "cache_info", "detail": f"Cache detected: {', '.join(cache_indicators)}", "severity": "INFO"})

    # 8. Information disclosure
    for pattern, desc in [("x-powered-by", "Tech stack disclosed"), ("server", "Server version disclosed")]:
        if pattern in hdrs:
            findings.append({"type": "info_disclosure", "header": pattern, "value": hdrs[pattern], "detail": desc, "severity": "INFO"})

    result = {
        "target": args.url,
        "status": baseline["status"],
        "findings": findings,
        "summary": {
            "high": len([f for f in findings if f.get("severity") == "HIGH"]),
            "medium": len([f for f in findings if f.get("severity") == "MEDIUM"]),
            "low": len([f for f in findings if f.get("severity") == "LOW"]),
            "info": len([f for f in findings if f.get("severity") == "INFO"]),
        }
    }

    output = json.dumps(result, indent=2)
    print(output)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)

if __name__ == "__main__":
    main()
