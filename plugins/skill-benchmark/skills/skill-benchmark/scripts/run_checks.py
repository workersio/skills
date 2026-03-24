#!/usr/bin/env python3
"""
Run deterministic verification checks for a single session's sandbox output.

Usage:
    python3 run_checks.py <task_file> <sandbox_dir> <output_path>

Reads the task file's Verification Checks section, runs each check in the
sandbox directory, and writes results to output_path as JSON.

Produces:
    <output_path> — JSON with file_exists, syntax_valid, runs_without_error,
                     file_contains, all_passed, details
"""

import json
import os
import re
import shlex
import subprocess
import sys


def parse_verification_checks(task_content):
    """Extract verification checks from task markdown."""
    checks = {
        "file_exists": [],
        "file_contains": [],
        "syntax_valid": [],
        "runs_without_error": [],
    }

    in_checks = False
    for line in task_content.splitlines():
        stripped = line.strip()

        if stripped.startswith("## Verification Checks"):
            in_checks = True
            continue
        if in_checks and stripped.startswith("## "):
            break
        if not in_checks:
            continue

        # Parse check lines: "- check_type: value"
        match = re.match(r"^-\s*(file_exists|file_contains|syntax_valid|runs_without_error):\s*(.+)$", stripped)
        if match:
            check_type = match.group(1)
            value = match.group(2).strip()
            checks[check_type].append(value)

    return checks


# Allowed executables for runs_without_error commands
ALLOWED_EXECUTABLES = {
    "python3", "python", "node", "npx", "ruby", "cargo", "go", "java", "javac",
    "rustc", "gcc", "g++", "make", "bash", "sh",
}

# Shell metacharacters that indicate injection risk
SHELL_METACHARACTERS = set(";|&$`><(){}[]!#~")


def validate_and_split_command(cmd):
    """Validate a command against the allowlist and return split args.

    Returns (args_list, error_string). If error_string is not None, the command
    is rejected.
    """
    if any(c in cmd for c in SHELL_METACHARACTERS):
        return None, f"rejected (shell metacharacters): {cmd}"

    try:
        parts = shlex.split(cmd)
    except ValueError as e:
        return None, f"rejected (parse error): {cmd} — {e}"

    if not parts:
        return None, f"rejected (empty command): {cmd}"

    if parts[0] not in ALLOWED_EXECUTABLES:
        return None, f"rejected (not in allowlist): {parts[0]}"

    return parts, None


def run_checks(task_file, sandbox_dir, output_path):
    # Read and parse task file
    with open(task_file) as f:
        task_content = f.read()

    check_defs = parse_verification_checks(task_content)
    results = {}
    details = []

    # file_exists
    file_exists_results = {}
    for filename in check_defs["file_exists"]:
        filepath = os.path.join(sandbox_dir, filename)
        exists = os.path.isfile(filepath)
        file_exists_results[filename] = exists
        if not exists:
            details.append(f"file missing: {filename}")
    results["file_exists"] = file_exists_results if file_exists_results else True

    # syntax_valid
    syntax_results = {}
    for lang in check_defs["syntax_valid"]:
        lang_lower = lang.lower().strip()
        # Find relevant files to check
        for filename in check_defs["file_exists"]:
            filepath = os.path.join(sandbox_dir, filename)
            if not os.path.isfile(filepath):
                syntax_results[filename] = False
                details.append(f"syntax check skipped (file missing): {filename}")
                continue

            if lang_lower == "python" and filename.endswith(".py"):
                r = subprocess.run(
                    ["python3", "-m", "py_compile", filepath],
                    capture_output=True, timeout=30
                )
                syntax_results[filename] = r.returncode == 0
                if r.returncode != 0:
                    details.append(f"syntax error in {filename}: {r.stderr.decode()[:200]}")
            elif lang_lower == "javascript" and filename.endswith(".js"):
                r = subprocess.run(
                    ["node", "--check", filepath],
                    capture_output=True, timeout=30
                )
                syntax_results[filename] = r.returncode == 0
                if r.returncode != 0:
                    details.append(f"syntax error in {filename}: {r.stderr.decode()[:200]}")
            elif lang_lower == "typescript" and filename.endswith(".ts"):
                r = subprocess.run(
                    ["npx", "tsc", "--noEmit", filepath],
                    capture_output=True, timeout=60
                )
                syntax_results[filename] = r.returncode == 0
                if r.returncode != 0:
                    details.append(f"syntax error in {filename}: {r.stderr.decode()[:200]}")
    results["syntax_valid"] = syntax_results if syntax_results else True

    # runs_without_error
    run_results = {}
    for cmd in check_defs["runs_without_error"]:
        args, rejection_reason = validate_and_split_command(cmd)
        if rejection_reason:
            run_results[cmd] = False
            details.append(rejection_reason)
            continue
        try:
            r = subprocess.run(
                args, shell=False, capture_output=True, cwd=sandbox_dir, timeout=30
            )
            run_results[cmd] = r.returncode == 0
            if r.returncode != 0:
                stderr = r.stderr.decode()[:200]
                details.append(f"runtime error for '{cmd}': {stderr}")
        except subprocess.TimeoutExpired:
            run_results[cmd] = False
            details.append(f"timeout for '{cmd}'")
        except Exception as e:
            run_results[cmd] = False
            details.append(f"exception for '{cmd}': {str(e)[:200]}")
    results["runs_without_error"] = run_results if run_results else True

    # file_contains
    contains_results = {}
    for pattern in check_defs["file_contains"]:
        # Pattern can be "pattern in filename" or just "pattern" (search all files)
        match = re.match(r"^(.+?)\s+in\s+(\S+)$", pattern)
        if match:
            search_pattern = match.group(1).strip()
            filename = match.group(2).strip()
            filepath = os.path.join(sandbox_dir, filename)
            if os.path.isfile(filepath):
                content = open(filepath).read()
                found = search_pattern in content
                contains_results[pattern] = found
                if not found:
                    details.append(f"pattern not found: '{search_pattern}' in {filename}")
            else:
                contains_results[pattern] = False
                details.append(f"file missing for contains check: {filename}")
        else:
            # Search pattern in all known files
            found = False
            for filename in check_defs["file_exists"]:
                filepath = os.path.join(sandbox_dir, filename)
                if os.path.isfile(filepath):
                    content = open(filepath).read()
                    if pattern in content:
                        found = True
                        break
            contains_results[pattern] = found
            if not found:
                details.append(f"pattern not found in any file: '{pattern}'")
    results["file_contains"] = contains_results if contains_results else True

    # Compute all_passed
    def check_passed(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, dict):
            return all(value.values())
        return True

    all_passed = all(
        check_passed(results[k])
        for k in ["file_exists", "syntax_valid", "runs_without_error", "file_contains"]
    )
    results["all_passed"] = all_passed
    if details:
        results["details"] = "; ".join(details)

    # Write output
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    status = "PASS" if all_passed else "FAIL"
    print(f"{status}: {len(details)} issues" if details else f"{status}")
    return all_passed


HELP_TEXT = """\
Usage: run_checks.py <task_file> <sandbox_dir> <output_path>

Run deterministic verification checks for a benchmark task's sandbox output.

Arguments:
  task_file     Path to the task .md file (must contain ## Verification Checks)
  sandbox_dir   Path to the sandbox directory where the session created files
  output_path   Path to write the checks result JSON

Supported check types (parsed from task file):
  file_exists          Check if a file was created in the sandbox
  file_contains        Search for a pattern in a file ("pattern in filename")
  syntax_valid         Run language syntax checker (python, javascript, typescript)
  runs_without_error   Execute a shell command and check exit code

Outputs:
  <output_path>  JSON with per-check results, all_passed boolean, and details

Exit codes:
  0  All checks passed
  1  One or more checks failed
"""

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(HELP_TEXT)
        sys.exit(0)

    if "--validate" in sys.argv:
        if len(sys.argv) != 3:
            print(f"Usage: {sys.argv[0]} --validate <task_file>")
            sys.exit(1)
        task_file = sys.argv[2]
        with open(task_file) as f:
            task_content = f.read()
        check_defs = parse_verification_checks(task_content)
        issues = []
        for cmd in check_defs["runs_without_error"]:
            _, rejection = validate_and_split_command(cmd)
            if rejection:
                issues.append(rejection)
        if issues:
            print(f"VALIDATION FAILED: {len(issues)} issue(s)")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print(f"VALIDATION OK: {len(check_defs['runs_without_error'])} commands, "
                  f"{len(check_defs['file_exists'])} file checks, "
                  f"{len(check_defs['syntax_valid'])} syntax checks, "
                  f"{len(check_defs['file_contains'])} content checks")
            sys.exit(0)

    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <task_file> <sandbox_dir> <output_path>")
        print("Run with --help for details.")
        sys.exit(1)

    task_file, sandbox_dir, output_path = sys.argv[1:4]
    passed = run_checks(task_file, sandbox_dir, output_path)
    sys.exit(0 if passed else 1)
