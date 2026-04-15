<div align="center">
  <img src="header.jpg" alt="Agent Skills for Software Reliability and Correctness — Claude Code plugins by workers.io" width="100%">

  <br>
  <br>

  <p>
    <strong>Claude Code Skills for Software Correctness</strong>
    <br>
    Formal verification, model checking, security auditing, proof repair, and benchmarking — as slash commands.
  </p>

</div>

<br>

## Contents

- [Quick Start](#quick-start)
- [Plugins](#plugins)
  - [fuzzer](#fuzzer) — Coverage-guided fuzzing for C/C++, Rust, and Go
  - [kani-proof](#kani-proof) — Model checking for Rust and Solana
  - [solana-audit](#solana-audit) — Smart contract security audits
  - [axiom](#axiom) — Lean 4 proof verification and repair
  - [skill-benchmark](#skill-benchmark) — Measure whether a skill actually helps
  - [workers-app-tester](#workers-app-tester) — Mobile application security testing
  - [save](#save) — Convert sessions into reusable agents
- [Repository Structure](#repository-structure)
- [Contributing](#contributing)
- [License](#license)

<br>

## Quick Start

Install every plugin in one command:

```bash
npx skills add workersio/spec
```

Individual plugins can be selected during installation. Once installed, invoke any skill by name inside Claude Code:

```
/fuzzer            Coverage-guided fuzzing with audit-driven harness design
/kani-proof        Write bounded model checker proofs for Rust and Solana
/solana-audit      Run a structured smart contract security audit
/axiom             Verify and repair Lean 4 proofs
/skill-benchmark   Benchmark a skill with controlled eval sessions
/workers-app-tester   Pentest an Android app on a rooted device
/save              Save the current session as a reusable agent
```

<br>

## Plugins

### fuzzer

Coverage-guided fuzzing workflow for C/C++, Rust, and Go targets. Runs a deep audit-context-building pass first to locate suspicious code, then writes a targeted harness, builds with sanitizers, runs the fuzzer, and reports crashes with reproducers.

**Use case** — Find memory safety bugs, integer overflows, and logic faults in native code through coverage-guided fuzzing driven by prior code understanding.

```
/fuzzer
```

<details>
<summary>What's included</summary>
<br>

- `fuzzer` skill — end-to-end harness authoring, build, run, and triage workflow
- `audit-context-building` skill — line-by-line analysis using First Principles, 5 Whys, and 5 Hows to locate fuzz targets
- Function-analyzer agent and reference docs for completeness, output requirements, and worked micro-analysis examples

</details>

---

### kani-proof

Writes [Kani](https://github.com/model-checking/kani) bounded model checker proofs for Rust and Solana programs. Generates proof harnesses, loop invariants, and property checks. Includes reference docs for proof patterns, invariant design, coverage workflows, Kani features, and Anchor program verification.

**Use case** — Prove absence of panics, arithmetic overflows, and unsafe memory access in Rust code. Verify Solana program logic with bounded inputs.

```
/kani-proof
```

<details>
<summary>What's included</summary>
<br>

- Proof pattern references for common Rust constructs
- Invariant design guides for loops and recursion
- Coverage workflow for measuring proof completeness
- Anchor-specific verification patterns for Solana programs
- Kani feature reference (stubs, contracts, harness configuration)

</details>

---

### solana-audit

Structured security audits for Solana smart contracts covering 25 vulnerability types. Walks through each attack vector systematically — from missing signer checks and PDA validation to re-initialization attacks and arithmetic overflows.

**Use case** — Audit Solana programs before deployment. Identify vulnerabilities across the full attack surface for on-chain programs.

```
/solana-audit
```

<details>
<summary>What's included</summary>
<br>

- Per-vulnerability reference docs for all 25 audit categories
- Audit checklist for systematic coverage
- Cheatsheet for quick reference during review
- Exploit case studies from real-world incidents

</details>

---

### axiom

Verify, check, transform, and repair [Lean 4](https://lean-lang.org/) proofs using the Axiom (Axle) API and CLI. Submits proof terms to the Axiom kernel for type-checking and returns structured verification results.

**Use case** — Machine-check mathematical proofs and formal specifications. Validate and repair proof steps during interactive theorem proving.

```
/axiom
```

---

### skill-benchmark

Benchmark any agent skill to measure whether it actually improves performance. Runs isolated eval sessions with and without the target skill, grades outputs via layered grading (deterministic checks + LLM-as-judge), analyzes behavioral signals, and generates a comparison report with a USE / DON'T USE verdict.

**Use case** — Objectively measure whether a skill helps or hurts on a specific class of tasks before committing to it.

```
/skill-benchmark
```

<details>
<summary>What's included</summary>
<br>

- Runner agent for executing controlled eval sessions
- Grader agent with layered grading (deterministic + LLM-as-judge)
- Reporter agent for generating comparison reports
- Scripts for stream parsing, transcript analysis, and check execution
- Configuration reference and directory structure docs

</details>

---

### workers-app-tester

Penetration test Android applications on a rooted device. Drives the UI over ADB, intercepts HTTPS traffic through mitmproxy, bypasses SSL pinning with Frida, decompiles APKs for static analysis, and runs security checks for IDORs, auth issues, data exposure, and hardcoded secrets.

**Use case** — Security test mobile applications for common vulnerabilities before release.

```
/workers-app-tester
```

<details>
<summary>What's included</summary>
<br>

- UI parsing and automation scripts for ADB
- Traffic capture and analysis tooling via mitmproxy
- Universal SSL pinning bypass with Frida
- Static analysis through APK decompilation

</details>

---

### save

Converts Claude Code conversations into reusable agents. Analyzes the current session — the original task, every correction, tool calls, and final output — and distills it into an agent file saved to `.claude/agents/`. Agents are invocable with `@agent-name` in future sessions and shared through version control. No server, no API, no accounts.

**Use case** — Capture a working workflow once, replay it forever.

```
/save
```

<br>

## Repository Structure

```
.claude-plugin/marketplace.json       Root marketplace catalog
plugins/
  fuzzer/                              Coverage-guided fuzzing workflow
    .claude-plugin/plugin.json
    skills/fuzzer/SKILL.md
    skills/audit-context-building/SKILL.md
    skills/audit-context-building/agents/
    skills/audit-context-building/resources/
  kani-proof/                          Bounded model checking for Rust
    .claude-plugin/plugin.json
    skills/kani-proof/SKILL.md
    skills/kani-proof/references/
  solana-audit/                        Solana smart contract audits
    .claude-plugin/plugin.json
    skills/solana-audit/SKILL.md
    skills/solana-audit/references/
  axiom/                               Lean 4 proof verification
    .claude-plugin/plugin.json
    skills/axiom/SKILL.md
  skill-benchmark/                     Benchmark agent skills
    .claude-plugin/plugin.json
    skills/skill-benchmark/SKILL.md
    skills/skill-benchmark/scripts/
    skills/skill-benchmark/agents/
    skills/skill-benchmark/references/
  workers-app-tester/                  Mobile app security testing
    .claude-plugin/plugin.json
    skills/workers-app-tester/SKILL.md
    skills/workers-app-tester/scripts/
    skills/workers-app-tester/references/
  save/                                Session-to-agent converter
    .claude-plugin/plugin.json
    skills/save/SKILL.md
```

Each plugin is self-contained under `plugins/` with its own manifest and skill definitions. The root `marketplace.json` registers all plugins for discovery via `npx skills`.

<br>

## Contributing

Contributions welcome. To add a new plugin:

1. Create a directory under `plugins/`
2. Add a `.claude-plugin/plugin.json` manifest
3. Define skills under `skills/<skill-name>/SKILL.md`
4. Register the plugin in `.claude-plugin/marketplace.json`

See any existing plugin for the expected structure.

<br>

## License

[MIT](LICENSE)
