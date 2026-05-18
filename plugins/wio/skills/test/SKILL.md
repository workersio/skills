---
name: test
description: Write one focused high-value test for a selected behavior, code path, or regression risk. Use when asked to add a test, improve a specific test, cover a bug, or validate a change with a meaningful automated test.
metadata:
  author: workers.io
  version: "0.1.0"
---

# Test

Write tests only when they protect meaningful behavior. A useful test reduces future user errors, production incidents, support work, debugging time, review time, or release risk.

Use [../../references/index.md](../../references/index.md) as the reference map. Load only the topic files needed for the selected behavior, especially:

- [Test Level Selection](../../references/test-level-selection/overview.md)
- [Test Oracles And Assertions](../../references/test-oracles-and-assertions/overview.md)
- [Test Data And Fixtures](../../references/test-data-and-fixtures/overview.md)
- [Mocking And Test Doubles](../../references/mocking-and-test-doubles/overview.md)
- [Test Feedback Loops](../../references/test-feedback-loops/overview.md)

## Workflow

1. Establish the product/user risk from repo evidence before writing a test.
2. Inspect existing tests, framework conventions, fixtures, commands, and CI shape.
3. Select the narrowest test level that preserves the real failure mechanism.
4. Define the protected behavior, regression it catches, oracle, setup, and validation command before editing.
5. Write one focused test using repo-native style and existing helpers.
6. Validate with the smallest relevant command. If it is unsafe or unclear, state that instead of guessing.
7. Apply the value gate before finalizing: `KEEP`, `REDO`, or `REMOVE`.

## Output

Finish with:

- Behavior protected.
- Why this test is worth keeping.
- Files changed.
- Validation command and result, or why it was not run.
- Verdict: `KEEP`, `REDO`, or `REMOVE`.
- Remaining risk.
