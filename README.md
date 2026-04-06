# workers.io plugins

A collection of Claude Code plugins by [workers.io](https://workers.io).

---

## Plugins

### save

Converts Claude Code conversations into reusable agents. The plugin analyzes your session -- the original task, every correction you made, tool calls, and the final output -- and distills it into an agent file saved to `.claude/agents/`. Agents are invocable with `@agent-name` in any future conversation and shared through version control. No server, no API, no accounts.

### kani-proof

Writes Kani bounded model checker proofs for Solana and Rust programs. Includes reference docs covering proof patterns, invariant design, coverage workflows, Kani features, and Anchor verification.

### solana-audit

Structured Solana smart contract security audits across 25 vulnerability types. Includes reference docs for each vulnerability, a cheatsheet, audit checklist, and exploit case studies.

### axiom

Verify, check, transform, and repair Lean 4 proofs using the Axiom (Axle) API and CLI.

### skill-benchmark

Benchmark any agent skill to measure whether it actually improves performance. Runs isolated eval sessions with and without the skill, grades outputs via layered grading (deterministic checks + LLM-as-judge), analyzes behavioral signals, and generates a comparison report with a USE / DON'T USE verdict.

### workers-app-tester

Pentest Android apps on a rooted device. The agent drives the UI over ADB, intercepts HTTPS traffic through mitmproxy, bypasses SSL pinning with Frida, decompiles APKs for static analysis, and runs security checks for IDORs, auth issues, data exposure, and hardcoded secrets. Includes bundled scripts for UI parsing, traffic capture, traffic analysis, and a universal SSL bypass.

---

## Install

```bash
npx skills add workersio/spec
```

This installs all plugins from the repository. Individual plugins can be selected during installation.

---

## Repository structure

```
plugins/
  save/                            # Convert sessions into reusable agents
    .claude-plugin/plugin.json
    skills/save/SKILL.md
  kani-proof/                      # Kani bounded model checker proofs
    .claude-plugin/plugin.json
    skills/kani-proof/SKILL.md
    skills/kani-proof/references/
  solana-audit/                    # Solana smart contract audits
    .claude-plugin/plugin.json
    skills/solana-audit/SKILL.md
    skills/solana-audit/references/
  axiom/                           # Lean 4 proof verification via Axiom
    .claude-plugin/plugin.json
    skills/axiom/SKILL.md
  skill-benchmark/                   # Benchmark any agent skill
    .claude-plugin/plugin.json
    skills/skill-benchmark/SKILL.md
    skills/skill-benchmark/scripts/
    skills/skill-benchmark/agents/
    skills/skill-benchmark/references/
  workers-app-tester/                # Android app pentesting
    .claude-plugin/plugin.json
    skills/workers-app-tester/SKILL.md
    skills/workers-app-tester/scripts/
    skills/workers-app-tester/references/
```

Each plugin lives under `plugins/` with its own `.claude-plugin/plugin.json` manifest and `skills/` directory. The root `.claude-plugin/marketplace.json` catalogs all plugins for marketplace discovery.

---

## License

MIT
