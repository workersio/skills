---
name: scan
description: Find the highest-value test candidates for a codebase, change, or scope. Use when asked what to test next, where coverage would matter, how to prioritize testing work, or which tests would reduce user, production, support, or team risk.
metadata:
  author: workers.io
  version: "0.1.0"
---

# Scan

Find the best parts to test next, the right strategy for each, and the ROI of testing them. This is read-only: inspect the repo, existing tests, and references; do not edit files.

Use [../../references/index.md](../../references/index.md) as the reference map. Start with:

- [Behavior To Test Map](../../references/behavior-to-test-map/overview.md)
- [Risk-Based Testing](../../references/risk-based-testing/overview.md)
- [User Behavior Testing](../../references/user-behavior-testing/overview.md)
- [Test Level Selection](../../references/test-level-selection/overview.md)

Load only the additional topic files needed for the specific recommendation.

## Workflow

1. Establish product/customer context from repo evidence.
2. Inventory existing test frameworks, commands, fixtures, CI, and test layers.
3. Map high-value behavior before low-level helpers.
4. Choose the narrowest test strategy that preserves the real user or production risk.
5. Rank candidates by impact, likelihood, confidence gap, and cost.

## Output

Return a concise report:

- Scope and evidence inspected.
- Ranked candidates, ideally 3-5.
- Best next test and why it is the first investment.
- Tempting low-value tests to avoid, if any.
- Questions that would materially change the ranking.
