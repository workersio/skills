---
name: doctor
description: Diagnose test-suite health problems in a codebase or scope. Use when asked to audit tests, review suite quality, find flaky or low-value tests, inspect CI test health, or explain why a test suite is slow, noisy, or low-signal.
metadata:
  author: workers.io
  version: "0.1.0"
---

# Doctor

Run a read-only test-suite health scan and report likely concerns with evidence. Do not edit, delete, rewrite, quarantine, or disable tests.

Use [../../references/index.md](../../references/index.md) as the reference map. Start with:

- [Test Suite Health Diagnostics](../../references/test-suite-health-diagnostics/overview.md)
- [Flaky Test Detection and Management](../../references/flaky-test-detection-and-management/overview.md)
- [Test Feedback Loops](../../references/test-feedback-loops/overview.md)
- [Test Automation Pyramid](../../references/test-automation-pyramid/overview.md)

Load targeted references for level, oracle, doubles, data, security, performance, resilience, fuzzing, property, mutation, or regression concerns when those risks appear.

## Workflow

1. Identify repository root, language/framework stack, test runners, CI systems, naming conventions, and test layers.
2. Inventory suite shape and test commands.
3. Scan for weak assertions, excessive mocking, flaky timing, shared state, broad snapshots, slow tests, skipped/quarantined tests, and missing critical-risk coverage.
4. Inspect CI and monitoring signals when available.
5. Grade reliability, speed, signal, diagnostic value, maintainability, risk coverage, and monitoring.

## Output

Return a concise doctor report:

- Scope, stack, frameworks, CI, evidence inspected, and whether tests were run.
- Overall grade and confidence.
- Top concerns with severity, confidence, evidence, why it matters, and suggested action.
- Rubric scores.
- Suite-shape gaps, bad test smells, monitoring gaps, quick wins, and material follow-up questions.
