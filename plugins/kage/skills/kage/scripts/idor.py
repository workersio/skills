#!/usr/bin/env python3
"""
IDOR Detection Script
Tests if attacker can access victim's resources.

Usage:
  python3 idor.py --url "https://target.com/api/users/{id}" \
    --attacker-token "Bearer eyJ..." \
    --victim-token "Bearer eyJ..." \
    --victim-id "456" \
    --attacker-id "123" \
    --methods GET,PUT,DELETE

Output: Structured JSON with pass/fail per method.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from client import make_request


def request(url, method="GET", token=None, data=None, timeout=10):
    return make_request(url, method=method, token=token, data=data,
                        truncate=2000, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description="IDOR Detection")
    parser.add_argument("--url", required=True, help="URL with {id} placeholder")
    parser.add_argument("--attacker-token", required=True)
    parser.add_argument("--victim-token", required=True)
    parser.add_argument("--victim-id", required=True)
    parser.add_argument("--attacker-id", required=True)
    parser.add_argument("--methods", default="GET", help="Comma-separated: GET,PUT,PATCH,DELETE")
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args()

    results = {"target": args.url, "findings": [], "summary": {"vulnerable": 0, "safe": 0, "error": 0}}

    for method in args.methods.split(","):
        method = method.strip().upper()

        # Baseline and own-access stay GET to compare response shape regardless
        # of whether the attack method is mutating.
        victim_url = args.url.replace("{id}", args.victim_id)
        baseline = request(victim_url, method="GET", token=args.victim_token)

        attacker_url = args.url.replace("{id}", args.victim_id)
        attack = request(attacker_url, method=method, token=args.attacker_token)

        own_url = args.url.replace("{id}", args.attacker_id)
        own = request(own_url, method="GET", token=args.attacker_token)

        finding = {
            "method": method,
            "url": attacker_url,
            "baseline_status": baseline["status"],
            "attack_status": attack["status"],
            "own_status": own["status"],
        }

        if attack["error"]:
            finding["result"] = "ERROR"
            finding["detail"] = attack["error"]
            results["summary"]["error"] += 1
        elif attack["status"] and attack["status"] < 400:
            # Attacker got 2xx/3xx on victim's resource — check if it's victim's data
            if baseline["body"] and attack["body"]:
                # Compare: does the attack response look like the victim's data?
                body_similarity = len(set(attack["body"].split()) & set(baseline["body"].split())) / max(len(set(baseline["body"].split())), 1)
                finding["body_similarity"] = round(body_similarity, 2)

                if body_similarity > 0.5 and attack["body"] != own["body"]:
                    finding["result"] = "VULNERABLE"
                    finding["detail"] = f"Attacker ({method}) got victim's data. Status: {attack['status']}. Body similarity: {body_similarity:.0%}"
                    finding["evidence"] = attack["body"][:500]
                    results["summary"]["vulnerable"] += 1
                else:
                    finding["result"] = "LIKELY_SAFE"
                    finding["detail"] = f"Got {attack['status']} but response differs from victim's data"
                    results["summary"]["safe"] += 1
            else:
                finding["result"] = "NEEDS_REVIEW"
                finding["detail"] = f"Got {attack['status']} — manual review needed"
                finding["evidence"] = attack["body"][:500]
                results["summary"]["vulnerable"] += 1
        else:
            finding["result"] = "SAFE"
            finding["detail"] = f"Access denied: {attack['status']}"
            results["summary"]["safe"] += 1

        results["findings"].append(finding)

    # Output
    output = json.dumps(results, indent=2)
    print(output)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)

if __name__ == "__main__":
    main()
