#!/usr/bin/env python3
"""
Race Condition Detection Script
Sends N parallel requests to detect TOCTOU bugs.

Usage:
  python3 race.py --url "https://target.com/api/redeem" \
    --method POST \
    --token "Bearer eyJ..." \
    --data '{"code":"PROMO123"}' \
    --parallel 15 \
    --output results.json

Output: Structured JSON — how many succeeded vs expected.
"""
import argparse
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(__file__))
from client import make_request

results_lock = threading.Lock()
responses = []


def send_request(url, method, headers, data, idx):
    resp = make_request(url, method=method, extra_headers=headers, data=data,
                        truncate=500, timeout=15)
    with results_lock:
        responses.append({"idx": idx, "status": resp["status"],
                          "body": resp["body"], "time": time.time()})

def main():
    parser = argparse.ArgumentParser(description="Race Condition Detection")
    parser.add_argument("--url", required=True)
    parser.add_argument("--method", default="POST")
    parser.add_argument("--token", required=True)
    parser.add_argument("--data", default=None, help="Request body (JSON)")
    parser.add_argument("--parallel", type=int, default=15)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    headers = {"Authorization": args.token}
    if args.data:
        headers["Content-Type"] = "application/json"

    # Create threads
    threads = []
    barrier = threading.Barrier(args.parallel)

    def fire(idx):
        barrier.wait()  # All threads release simultaneously
        send_request(args.url, args.method, headers, args.data, idx)

    for i in range(args.parallel):
        t = threading.Thread(target=fire, args=(i,))
        threads.append(t)

    # Launch all threads
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    elapsed = time.time() - start

    # Analyze
    success = [r for r in responses if r["status"] and 200 <= r["status"] < 300]
    failed = [r for r in responses if r["status"] and r["status"] >= 400]
    errors = [r for r in responses if r["status"] is None]

    # Timing analysis
    times = [r["time"] for r in responses if r["time"]]
    time_spread = max(times) - min(times) if len(times) > 1 else 0

    result = {
        "target": args.url,
        "method": args.method,
        "parallel_requests": args.parallel,
        "elapsed_seconds": round(elapsed, 2),
        "time_spread_ms": round(time_spread * 1000, 1),
        "results": {
            "success_count": len(success),
            "fail_count": len(failed),
            "error_count": len(errors),
        },
        "responses": responses,
    }

    # Verdict
    if len(success) > 1:
        result["verdict"] = "VULNERABLE"
        result["detail"] = f"Race condition: {len(success)}/{args.parallel} requests succeeded. Expected: 1. Time spread: {time_spread*1000:.1f}ms"
        result["severity"] = "HIGH" if len(success) > 3 else "MEDIUM"
    elif len(success) == 1:
        result["verdict"] = "SAFE"
        result["detail"] = f"Only 1/{args.parallel} succeeded — proper locking in place"
    else:
        result["verdict"] = "INCONCLUSIVE"
        result["detail"] = f"No successes — endpoint may require different payload or conditions"

    output = json.dumps(result, indent=2)
    print(output)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)

if __name__ == "__main__":
    main()
