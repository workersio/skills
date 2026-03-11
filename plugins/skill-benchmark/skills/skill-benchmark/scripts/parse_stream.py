#!/usr/bin/env python3
"""
Parse raw_stream.jsonl from a claude -p session into structured output files.

Usage:
    python3 parse_stream.py <output_dir> <sandbox_dir> <skill_name> <mode> <run_number>

Produces:
    <output_dir>/response.json   — Last "type": "result" event from the stream
    <output_dir>/transcript.json — All stream events as a JSON array
    <output_dir>/meta.json       — Session metadata extracted from response.json
"""

import json
import sys
import os


def parse_stream(output_dir, sandbox_dir, skill_name, mode, run_number):
    raw_path = os.path.join(output_dir, "raw_stream.jsonl")
    events = []
    result_event = None

    if not os.path.exists(raw_path):
        print(f"ERROR: {raw_path} not found")
        write_error_files(output_dir, sandbox_dir, skill_name, mode, run_number, "raw_stream.jsonl not found")
        return False

    with open(raw_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                events.append(event)
                if event.get("type") == "result":
                    result_event = event
            except json.JSONDecodeError:
                pass

    # response.json
    with open(os.path.join(output_dir, "response.json"), "w") as f:
        if result_event:
            json.dump(result_event, f, indent=2)
        else:
            json.dump({"error": True, "message": "No result event found in stream"}, f, indent=2)

    # transcript.json
    with open(os.path.join(output_dir, "transcript.json"), "w") as f:
        json.dump(events, f, indent=2)

    # meta.json
    if result_event:
        model_usage = result_event.get("modelUsage", {})
        model_name = list(model_usage.keys())[0] if model_usage else "unknown"
        usage = result_event.get("usage", {})

        meta = {
            "session_id": result_event.get("session_id"),
            "model": model_name,
            "skill_name": skill_name if mode == "with-skill" else None,
            "mode": mode,
            "run_number": int(run_number),
            "stop_reason": result_event.get("stop_reason"),
            "is_error": result_event.get("is_error", False),
            "duration_ms": result_event.get("duration_ms"),
            "duration_api_ms": result_event.get("duration_api_ms"),
            "num_turns": result_event.get("num_turns"),
            "total_cost_usd": result_event.get("total_cost_usd", 0),
            "usage": {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                "total_tokens": (
                    usage.get("input_tokens", 0)
                    + usage.get("output_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                ),
            },
            "sandbox_dir": sandbox_dir,
        }
    else:
        meta = write_error_meta(sandbox_dir, skill_name, mode, run_number, "No result event found in stream")

    with open(os.path.join(output_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Parsed {len(events)} events. Result: {'OK' if result_event else 'MISSING'}")
    return result_event is not None


def write_error_meta(sandbox_dir, skill_name, mode, run_number, error_message):
    return {
        "session_id": None,
        "model": "unknown",
        "skill_name": skill_name if mode == "with-skill" else None,
        "mode": mode,
        "run_number": int(run_number),
        "stop_reason": "error",
        "is_error": True,
        "duration_ms": 0,
        "duration_api_ms": 0,
        "num_turns": 0,
        "total_cost_usd": 0,
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "total_tokens": 0,
        },
        "sandbox_dir": sandbox_dir,
        "error_message": error_message,
    }


def write_error_files(output_dir, sandbox_dir, skill_name, mode, run_number, error_message):
    with open(os.path.join(output_dir, "response.json"), "w") as f:
        json.dump({"error": True, "message": error_message}, f, indent=2)
    with open(os.path.join(output_dir, "transcript.json"), "w") as f:
        json.dump([], f, indent=2)
    meta = write_error_meta(sandbox_dir, skill_name, mode, run_number, error_message)
    with open(os.path.join(output_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


HELP_TEXT = """\
Usage: parse_stream.py <output_dir> <sandbox_dir> <skill_name> <mode> <run_number>

Parse raw_stream.jsonl from a claude -p session into structured output files.

Arguments:
  output_dir    Directory containing raw_stream.jsonl (output files written here)
  sandbox_dir   Sandbox directory where the session ran
  skill_name    Name of the skill being benchmarked
  mode          "with-skill" or "baseline"
  run_number    Run number (1-based integer)

Outputs:
  <output_dir>/response.json    Last "type": "result" event from the stream
  <output_dir>/transcript.json  All stream events as a JSON array
  <output_dir>/meta.json        Session metadata (model, cost, tokens, duration)

Exit codes:
  0  Success — result event found and parsed
  1  Failure — missing file or no result event in stream
"""

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(HELP_TEXT)
        sys.exit(0)

    if len(sys.argv) != 6:
        print(f"Usage: {sys.argv[0]} <output_dir> <sandbox_dir> <skill_name> <mode> <run_number>")
        print("Run with --help for details.")
        sys.exit(1)

    output_dir, sandbox_dir, skill_name, mode, run_number = sys.argv[1:6]
    success = parse_stream(output_dir, sandbox_dir, skill_name, mode, run_number)
    sys.exit(0 if success else 1)
