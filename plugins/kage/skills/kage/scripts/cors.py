#!/usr/bin/env python3
"""
CORS Misconfiguration Detection Script.

Usage:
  python3 cors.py --url "https://target.com/api/me" \
    --token "Bearer eyJ..." \
    --output results.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from client import make_request


def check_cors(url, origin, token=None, timeout=10):
    resp = make_request(url, method="GET", token=token,
                        extra_headers={"Origin": origin},
                        truncate=0, timeout=timeout)
    headers = resp["headers"]
    acao = headers.get("access-control-allow-origin", "")
    acac = headers.get("access-control-allow-credentials", "")
    return {"origin": origin, "acao": acao,
            "credentials": str(acac).lower() == "true",
            "status": resp["status"]}

def main():
    parser = argparse.ArgumentParser(description="CORS Detection")
    parser.add_argument("--url", required=True)
    parser.add_argument("--token", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    # Extract domain from URL
    from urllib.parse import urlparse
    parsed = urlparse(args.url)
    domain = parsed.hostname

    test_origins = [
        f"https://evil.com",
        f"https://attacker-{domain}",
        f"https://{domain}.evil.com",
        f"https://evil.{domain}",
        "null",
        f"https://sub.{domain}",
    ]

    results = {"target": args.url, "findings": [], "summary": {"vulnerable": 0, "safe": 0}}

    for origin in test_origins:
        r = check_cors(args.url, origin, args.token)
        finding = {"origin_tested": origin, "acao_returned": r["acao"], "credentials": r["credentials"]}

        if r["acao"] == origin and r["credentials"]:
            finding["result"] = "VULNERABLE"
            finding["detail"] = f"Origin {origin} reflected with credentials=true. Full cross-origin data theft possible."
            finding["severity"] = "HIGH"
            results["summary"]["vulnerable"] += 1
        elif r["acao"] == origin:
            finding["result"] = "REFLECTED_NO_CREDS"
            finding["detail"] = f"Origin reflected but no credentials. Limited impact unless chained."
            results["summary"]["safe"] += 1
        elif r["acao"] == "*" and r["credentials"]:
            finding["result"] = "WILDCARD_WITH_CREDS"
            finding["detail"] = "Wildcard with credentials — browser won't send cookies but misconfigured."
            results["summary"]["vulnerable"] += 1
        elif r["acao"] == "null" and origin == "null" and r["credentials"]:
            finding["result"] = "VULNERABLE"
            finding["detail"] = "Null origin accepted with credentials. Exploitable via sandboxed iframe."
            finding["severity"] = "HIGH"
            results["summary"]["vulnerable"] += 1
        else:
            finding["result"] = "SAFE"
            finding["detail"] = f"Origin not reflected or no credentials"
            results["summary"]["safe"] += 1

        results["findings"].append(finding)

    output = json.dumps(results, indent=2)
    print(output)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)

if __name__ == "__main__":
    main()
