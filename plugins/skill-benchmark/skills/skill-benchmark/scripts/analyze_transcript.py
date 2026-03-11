#!/usr/bin/env python3
"""
Analyze a transcript.json file for behavioral signals.

Usage:
    python3 analyze_transcript.py <transcript_path> <output_path>

Produces:
    <output_path> — Tool call counts, thrashing detection, error analysis (JSON)
"""

import json
import sys
import os
from collections import Counter


def analyze_transcript(transcript_path, output_path):
    if not os.path.exists(transcript_path):
        print(f"ERROR: {transcript_path} not found")
        write_empty_behavior(output_path, "transcript.json not found")
        return False

    with open(transcript_path) as f:
        events = json.load(f)

    tool_calls = Counter()
    total_tool_calls = 0
    errors_encountered = 0
    errors_recovered = 0
    thrashing_detected = False

    # Track consecutive tool calls for thrashing detection
    consecutive_tool = None
    consecutive_count = 0

    last_was_error = False

    for event in events:
        event_type = event.get("type", "")

        # Count tool usage from assistant messages
        if event_type == "assistant":
            message = event.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_name = block.get("name", "unknown")
                        tool_calls[tool_name] += 1
                        total_tool_calls += 1

                        # Thrashing detection: same tool 3+ times consecutively
                        if tool_name == consecutive_tool:
                            consecutive_count += 1
                            if consecutive_count >= 3:
                                thrashing_detected = True
                        else:
                            consecutive_tool = tool_name
                            consecutive_count = 1

        # Detect errors in tool results
        if event_type == "tool_result" or event_type == "result":
            content = event.get("content", "")
            is_error = event.get("is_error", False)

            # Check for error indicators in content
            error_indicators = ["error", "Error", "ERROR", "failed", "Failed", "FAIL", "exception", "Exception"]
            content_str = str(content) if not isinstance(content, str) else content

            if is_error or any(indicator in content_str for indicator in error_indicators):
                if last_was_error:
                    # Consecutive errors — not recovering
                    pass
                else:
                    errors_encountered += 1
                    last_was_error = True
            else:
                if last_was_error:
                    # Was in error state, now succeeded — recovered
                    errors_recovered += 1
                    last_was_error = False

    behavior = {
        "tool_calls": dict(tool_calls.most_common()),
        "total_tool_calls": total_tool_calls,
        "thrashing_detected": thrashing_detected,
        "errors_encountered": errors_encountered,
        "errors_recovered": errors_recovered,
    }

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(behavior, f, indent=2)

    print(f"Analyzed {len(events)} events. Tools: {total_tool_calls}, Errors: {errors_encountered}, Thrashing: {thrashing_detected}")
    return True


def write_empty_behavior(output_path, error_message):
    behavior = {
        "tool_calls": {},
        "total_tool_calls": 0,
        "thrashing_detected": False,
        "errors_encountered": 0,
        "errors_recovered": 0,
        "error": error_message,
    }
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(behavior, f, indent=2)


HELP_TEXT = """\
Usage: analyze_transcript.py <transcript_path> <output_path>

Analyze a transcript.json file for behavioral signals.

Arguments:
  transcript_path  Path to transcript.json (array of stream events)
  output_path      Path to write behavior.json output

Outputs:
  <output_path>  JSON with tool call counts, thrashing detection, error analysis

Behavioral signals detected:
  tool_calls          Count of each tool used (Read, Write, Bash, etc.)
  total_tool_calls    Total number of tool invocations
  thrashing_detected  True if same tool called 3+ times consecutively
  errors_encountered  Number of error events detected
  errors_recovered    Number of error-to-success transitions

Exit codes:
  0  Success — transcript analyzed
  1  Failure — transcript file not found
"""

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(HELP_TEXT)
        sys.exit(0)

    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <transcript_path> <output_path>")
        print("Run with --help for details.")
        sys.exit(1)

    transcript_path, output_path = sys.argv[1:3]
    success = analyze_transcript(transcript_path, output_path)
    sys.exit(0 if success else 1)
