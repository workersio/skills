#!/usr/bin/env python3
"""
Response Comparison Tool
Sends two requests and compares responses to detect access control issues.

Usage:
  python3 diff.py \
    --url-a "https://target.com/api/users/123" --headers-a "Authorization: Bearer ATTACKER_TOKEN" \
    --url-b "https://target.com/api/users/123" --headers-b "Authorization: Bearer VICTIM_TOKEN" \
    --output diff.json

  # Or compare with/without auth:
  python3 diff.py \
    --url-a "https://target.com/api/admin" --headers-a "" \
    --url-b "https://target.com/api/admin" --headers-b "Authorization: Bearer ADMIN_TOKEN"
"""
import argparse
import difflib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from client import make_request


def _parse_headers(headers_str):
    headers = {}
    if not headers_str:
        return headers
    # Header pairs are separated by ";;" and key:value by ":"; this lets
    # callers pass multiple headers on a single CLI flag.
    for h in headers_str.split(";;"):
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()
    return headers


def send(url, headers_str="", timeout=10):
    return make_request(url, method="GET",
                        extra_headers=_parse_headers(headers_str),
                        truncate=0, timeout=timeout)

def main():
    parser = argparse.ArgumentParser(description="Response Diff")
    parser.add_argument("--url-a", required=True, help="First request URL")
    parser.add_argument("--headers-a", default="", help="Headers for request A (Key: Value;; Key2: Value2)")
    parser.add_argument("--url-b", required=True, help="Second request URL")
    parser.add_argument("--headers-b", default="", help="Headers for request B")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    resp_a = send(args.url_a, args.headers_a)
    resp_b = send(args.url_b, args.headers_b)

    # Calculate similarity
    if resp_a["body"] and resp_b["body"]:
        ratio = difflib.SequenceMatcher(None, resp_a["body"], resp_b["body"]).ratio()
        words_a = set(resp_a["body"].split())
        words_b = set(resp_b["body"].split())
        word_overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
    else:
        ratio = 0.0
        word_overlap = 0.0

    # Generate diff (first 50 lines)
    diff_lines = list(difflib.unified_diff(
        resp_a["body"].splitlines()[:50],
        resp_b["body"].splitlines()[:50],
        lineterm="", fromfile="Request A", tofile="Request B"
    ))

    result = {
        "request_a": {"url": args.url_a, "status": resp_a["status"], "length": resp_a["length"]},
        "request_b": {"url": args.url_b, "status": resp_b["status"], "length": resp_b["length"]},
        "comparison": {
            "status_match": resp_a["status"] == resp_b["status"],
            "body_similarity": round(ratio, 3),
            "word_overlap": round(word_overlap, 3),
            "length_diff": abs(resp_a["length"] - resp_b["length"]),
        },
        "diff_preview": "\n".join(diff_lines[:30]),
    }

    # Verdict
    if resp_a["status"] == resp_b["status"] and ratio > 0.8:
        result["verdict"] = "SAME_RESPONSE"
        result["detail"] = f"Both return {resp_a['status']} with {ratio:.0%} similarity — possible access control issue if requests have different auth levels"
    elif resp_a["status"] != resp_b["status"]:
        result["verdict"] = "DIFFERENT_STATUS"
        result["detail"] = f"A={resp_a['status']}, B={resp_b['status']} — access control is enforced"
    elif ratio < 0.3:
        result["verdict"] = "DIFFERENT_CONTENT"
        result["detail"] = f"Same status but very different content ({ratio:.0%} similar)"
    else:
        result["verdict"] = "PARTIAL_MATCH"
        result["detail"] = f"{ratio:.0%} similar — needs manual review"

    output = json.dumps(result, indent=2)
    print(output)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)

if __name__ == "__main__":
    main()
