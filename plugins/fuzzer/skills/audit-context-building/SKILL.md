---
name: audit-context-building
description: >
  Deep codebase analysis for building architectural context before vulnerability
  or bug finding. Uses line-by-line analysis with First Principles, 5 Whys, and
  5 Hows. Use when deep comprehension is needed before security auditing,
  architecture review, or threat modeling.
---

# Deep Context Builder Skill

## 1. Purpose

This skill governs **how Claude thinks** during the context-building phase of an audit.

When active, Claude will:
- Perform **line-by-line / block-by-block** code analysis by default.
- Apply **First Principles**, **5 Whys**, and **5 Hows** at micro scale.
- Continuously link insights -> functions -> modules -> entire system.
- Maintain a stable, explicit mental model that evolves with new evidence.
- Identify invariants, assumptions, flows, and reasoning hazards.

This skill defines a structured analysis format and runs **before** the vulnerability-hunting phase.

---

## 2. When to Use This Skill

Use when:
- Deep comprehension is needed before bug or vulnerability discovery.
- You want bottom-up understanding instead of high-level guessing.
- Reducing hallucinations, contradictions, and context loss is critical.
- Preparing for security auditing, architecture review, or threat modeling.

Do **not** use for:
- Vulnerability findings
- Fix recommendations
- Exploit reasoning
- Severity/impact rating

---

## 3. How This Skill Behaves

When active, Claude will:
- Default to **ultra-granular analysis** of each block and line.
- Apply micro-level First Principles, 5 Whys, and 5 Hows.
- Build and refine a persistent global mental model.
- Update earlier assumptions when contradicted ("Earlier I thought X; now Y.").
- Periodically anchor summaries to maintain stable context.
- Avoid speculation; express uncertainty explicitly when needed.

Goal: **deep, accurate understanding**, not conclusions.

---

## Rationalizations (Do Not Skip)

| Rationalization | Why It's Wrong | Required Action |
|-----------------|----------------|-----------------|
| "I get the gist" | Gist-level understanding misses edge cases | Line-by-line analysis required |
| "This function is simple" | Simple functions compose into complex bugs | Apply 5 Whys anyway |
| "I'll remember this invariant" | You won't. Context degrades. | Write it down explicitly |
| "External call is probably fine" | External = adversarial until proven otherwise | Jump into code or model as hostile |
| "I can skip this helper" | Helpers contain assumptions that propagate | Trace the full call chain |
| "This is taking too long" | Rushed context = hallucinated vulnerabilities later | Slow is fast |

---

## 4. Phase 1 -- Initial Orientation (Bottom-Up Scan)

Before deep analysis, perform a minimal mapping:

1. **Detect the tech stack** -- identify languages, frameworks, databases, auth providers, package managers.
2. Identify major modules/files/contracts.
3. Note obvious public/external entrypoints (HTTP routes, RPC handlers, CLI commands, webhooks).
4. Identify likely actors (users, admins, services, external integrations).
5. Identify important storage (database tables, state structs, config, env vars).
6. Build a preliminary structure without assuming behavior.

This establishes anchors for detailed analysis.

---

## 5. Phase 2 -- Ultra-Granular Function Analysis (Default Mode)

Every non-trivial function receives full micro analysis.

### 5.1 Per-Function Microstructure Checklist

For each function:

1. **Purpose**
   - Why the function exists and its role in the system.

2. **Inputs & Assumptions**
   - Parameters and implicit inputs (state, sender, env).
   - Preconditions and constraints.

3. **Outputs & Effects**
   - Return values.
   - State/storage writes.
   - Events/messages.
   - External interactions.

4. **Block-by-Block / Line-by-Line Analysis**
   For each logical block:
   - What it does.
   - Why it appears here (ordering logic).
   - What assumptions it relies on.
   - What invariants it establishes or maintains.
   - What later logic depends on it.

   Apply per-block:
   - **First Principles**
   - **5 Whys**
   - **5 Hows**

---

### 5.2 Cross-Function & External Flow Analysis

When encountering calls, **continue the same micro-first analysis across boundaries.**

#### Internal Calls
- Jump into the callee immediately.
- Perform block-by-block analysis of relevant code.
- Track flow of data, assumptions, and invariants:
  caller -> callee -> return -> caller.
- Note if callee logic behaves differently in this specific call context.

#### External Calls -- Two Cases

**Case A -- External Call to Code That Exists in the Codebase**
Treat as an internal call:
- Jump into the target function.
- Continue block-by-block micro-analysis.
- Propagate invariants and assumptions seamlessly.
- Consider edge cases based on the *actual* code, not a black-box guess.

**Case B -- External Call Without Available Code (True External / Black Box)**
Analyze as adversarial:
- Describe payload/parameters sent.
- Identify assumptions about the target.
- Consider all outcomes: failure, incorrect return values, unexpected state changes, misbehavior.

#### Continuity Rule
Treat the entire call chain as **one continuous execution flow**.
Never reset context.
All invariants, assumptions, and data dependencies must propagate across calls.

---

### 5.3 Complete Analysis Example

See [FUNCTION_MICRO_ANALYSIS_EXAMPLE.md](resources/FUNCTION_MICRO_ANALYSIS_EXAMPLE.md) for a complete walkthrough.

---

### 5.4 Output Requirements

Structure output following [OUTPUT_REQUIREMENTS.md](resources/OUTPUT_REQUIREMENTS.md).

Quality thresholds:
- Minimum 3 invariants per function
- Minimum 5 assumptions documented
- Minimum 3 risk considerations for external interactions
- At least 1 First Principles application
- At least 3 combined 5 Whys/5 Hows applications

---

### 5.5 Completeness Checklist

Verify against [COMPLETENESS_CHECKLIST.md](resources/COMPLETENESS_CHECKLIST.md) before concluding.

---

## 6. Phase 3 -- Global System Understanding

After sufficient micro-analysis:

1. **State & Invariant Reconstruction** -- Map reads/writes of each state variable. Derive multi-function invariants.
2. **Workflow Reconstruction** -- Identify end-to-end flows. Track state transforms. Record persistent assumptions.
3. **Trust Boundary Mapping** -- Actor -> entrypoint -> behavior. Identify untrusted input paths.
4. **Complexity & Fragility Clustering** -- Functions with many assumptions, high branching, coupled state changes.

---

## 7. Stability & Consistency Rules

- **Never reshape evidence to fit earlier assumptions.** Update the model and state corrections explicitly.
- **Periodically anchor key facts.** Summarize invariants, state relationships, actor roles, workflows.
- **Avoid vague guesses.** Use "Unclear; need to inspect X." instead of "It probably..."
- **Cross-reference constantly.** Connect new insights to previous state, flows, and invariants.

---

## 8. Subagent Usage

Use the **`function-analyzer`** agent for per-function deep analysis of dense or complex functions, long data-flow chains, cryptographic logic, or state machines.

---

## 9. Non-Goals

While active, Claude should NOT: identify vulnerabilities, propose fixes, generate PoCs, model exploits, or assign severity.

This is **pure context building** only.
