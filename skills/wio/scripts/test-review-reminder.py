#!/usr/bin/env python3
import json
import re
import sys


TEST_PATH_RE = re.compile(r"(__tests__|tests?|specs?)/|[._-](test|spec)", re.IGNORECASE)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_input = json.dumps(payload.get("tool_input", {}), sort_keys=True)
    if not TEST_PATH_RE.search(tool_input):
        return 0

    print(
        json.dumps(
            {
                "systemMessage": (
                    "WIO: test file changed. Before finalizing, run the smallest "
                    "relevant validation and apply `$wio review`: KEEP, REDO, or REMOVE."
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

