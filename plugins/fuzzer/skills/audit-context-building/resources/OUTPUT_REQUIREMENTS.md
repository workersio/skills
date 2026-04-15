# Output Requirements

For EACH analyzed function, output MUST include:

**1. Purpose** -- 2-3 sentences minimum. Role in system + impact on state/security.

**2. Inputs & Assumptions** -- All parameters (explicit + implicit), preconditions, trust assumptions. Each input: type, source, trust level. Minimum 3 assumptions.

**3. Outputs & Effects** -- Returns, state writes, external interactions, events, postconditions. Minimum 3 effects.

**4. Block-by-Block Analysis** -- For EACH block: What, Why here, Assumptions, Depends on, First Principles/5 Whys/5 Hows (at least ONE per block). Complex blocks (>5 lines): First Principles AND 5 Whys or 5 Hows.

**5. Cross-Function Dependencies** -- Internal calls, external calls (with risk analysis), callers, shared state, invariant couplings. Minimum 3 relationships.

## Quality Thresholds

- Minimum 3 invariants per function
- Minimum 5 assumptions across all sections
- Minimum 3 risk considerations for external interactions
- At least 1 First Principles application
- At least 3 combined 5 Whys / 5 Hows

## Format

- Markdown headers for major sections
- Bullet points for lists
- Code blocks with language annotation
- Line number references: `L45`, `lines 98-102`
- Horizontal rules between blocks
