#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize android-app-tester mitmproxy capture logs.")
    parser.add_argument("--input", required=True, help="Path to traffic.jsonl")
    parser.add_argument("--since-seconds", type=int, default=0, help="Only include flows updated in the last N seconds")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of flows to print")
    parser.add_argument("--show-headers", action="store_true", help="Include request and response headers")
    parser.add_argument("--show-body", action="store_true", help="Include request and response body previews")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of plain text")
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def collapse_flows(records: list[dict[str, object]]) -> list[dict[str, object]]:
    flows: dict[str, dict[str, object]] = {}
    for record in records:
        flow_id = str(record.get("flow_id", ""))
        if not flow_id:
            continue
        flow = flows.setdefault(flow_id, {"flow_id": flow_id})
        event = record.get("event")
        flow["updated_at"] = record.get("timestamp", 0)
        if event == "request":
            flow["request"] = record
        elif event == "response":
            flow["response"] = record
        elif event == "error":
            flow["error"] = record

        if "request" not in flow:
            flow["request"] = record

    collapsed = list(flows.values())
    collapsed.sort(key=lambda item: float(item.get("updated_at", 0)))
    return collapsed


def filter_recent(flows: list[dict[str, object]], since_seconds: int) -> list[dict[str, object]]:
    if since_seconds <= 0:
        return flows
    threshold = time.time() - since_seconds
    return [flow for flow in flows if float(flow.get("updated_at", 0)) >= threshold]


def preview(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\n", "\\n")
    return value if len(value) <= 200 else value[:197] + "..."


def plain_text(flows: list[dict[str, object]], show_headers: bool, show_body: bool) -> None:
    if not flows:
      print("No captured flows matched the requested window.")
      return

    host_counts = Counter()
    for flow in flows:
        request = flow.get("request", {})
        if isinstance(request, dict):
            host = request.get("host")
            if host:
                host_counts[str(host)] += 1

    print(f"flows={len(flows)}")
    if host_counts:
        host_summary = ", ".join(f"{host} ({count})" for host, count in host_counts.most_common(5))
        print(f"hosts={host_summary}")

    print("recent_flows:")
    for flow in flows:
        request = flow.get("request", {})
        response = flow.get("response", {})
        error = flow.get("error", {})

        method = request.get("method", "?") if isinstance(request, dict) else "?"
        host = request.get("host", "?") if isinstance(request, dict) else "?"
        path = request.get("path", "?") if isinstance(request, dict) else "?"
        status = response.get("status_code") if isinstance(response, dict) else None
        timestamp = float(flow.get("updated_at", 0))
        clock = time.strftime("%H:%M:%S", time.localtime(timestamp)) if timestamp else "?"
        outcome = f"-> {status}" if status is not None else "-> pending"
        if isinstance(error, dict) and error.get("error"):
            outcome = f"-> error: {error['error']}"

        print(f"- [{clock}] {method} {host}{path} {outcome}")

        if show_headers and isinstance(request, dict):
            req_headers = request.get("request_headers", {})
            if req_headers:
                print(f"  request_headers={json.dumps(req_headers, ensure_ascii=False)}")
        if show_body and isinstance(request, dict):
            req_body = preview(request.get("request_body_preview"))
            if req_body:
                print(f"  request_body={req_body}")

        if show_headers and isinstance(response, dict):
            resp_headers = response.get("response_headers", {})
            if resp_headers:
                print(f"  response_headers={json.dumps(resp_headers, ensure_ascii=False)}")
        if show_body and isinstance(response, dict):
            resp_body = preview(response.get("response_body_preview"))
            if resp_body:
                print(f"  response_body={resp_body}")


def main() -> int:
    args = parse_args()
    records = load_records(Path(args.input))
    flows = collapse_flows(records)
    flows = filter_recent(flows, args.since_seconds)
    if args.limit > 0:
        flows = flows[-args.limit:]

    if args.json:
        print(json.dumps(flows, ensure_ascii=False, indent=2))
        return 0

    plain_text(flows, args.show_headers, args.show_body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
