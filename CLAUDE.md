# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

https://github.com/workersio/spec

## What This Project Does

A collection of Claude Code plugins by workers.io. Each plugin is a self-contained directory under `plugins/` with a manifest and one or more skills. The root `.claude-plugin/marketplace.json` catalogs all plugins for marketplace discovery. Users install via `npx skills add workersio/spec`.

## Plugins

### save (`plugins/save/`)

Converts Claude Code conversations into reusable agents. Analyzes the current session and distills it into an agent file saved to `.claude/agents/{name}.md`, invocable via `@{name}`.

- **Skill**: `skills/save/SKILL.md` (`/save`)
- **Manifest**: `plugins/save/.claude-plugin/plugin.json`

### kani-proof (`plugins/kani-proof/`)

Writes Kani bounded model checker proofs for Solana and Rust programs. Includes reference docs for proof patterns, invariant design, coverage workflows, and Anchor verification.

- **Skill**: `skills/kani-proof/SKILL.md` (`/kani-proof`)
- **Manifest**: `plugins/kani-proof/.claude-plugin/plugin.json`

### solana-audit (`plugins/solana-audit/`)

Structured Solana smart contract security audits across 25 vulnerability types with reference docs, cheatsheet, audit checklist, and exploit case studies.

- **Skill**: `skills/solana-audit/SKILL.md` (`/solana-audit`)
- **Manifest**: `plugins/solana-audit/.claude-plugin/plugin.json`

### axiom (`plugins/axiom/`)

Verify, check, transform, and repair Lean 4 proofs using the Axiom (Axle) API and CLI.

- **Skill**: `skills/axiom-verify/SKILL.md` (`/axiom`)
- **Manifest**: `plugins/axiom/.claude-plugin/plugin.json`

### skill-benchmark (`plugins/skill-benchmark/`)

Benchmark any agent skill to measure whether it actually improves performance. Runs eval sessions with and without the skill, grades via layered grading (deterministic checks + LLM-as-judge), and generates a comparison report.

- **Skill**: `skills/skill-benchmark/SKILL.md` (`/skill-benchmark`)
- **Manifest**: `plugins/skill-benchmark/.claude-plugin/plugin.json`
- **Scripts**: `skills/skill-benchmark/scripts/` (parse_stream.py, analyze_transcript.py, run_checks.py)
- **Agents**: `skills/skill-benchmark/agents/` (runner.md, grader.md, reporter.md)
- **References**: `skills/skill-benchmark/references/` (CONFIG.md, DIRECTORY-STRUCTURE.md)

## Architecture

```
.claude-plugin/marketplace.json    # Root marketplace catalog (all plugins)
plugins/
  <plugin-name>/
    .claude-plugin/plugin.json     # Plugin manifest
    skills/
      <skill-name>/SKILL.md        # Skill definition
```

Each plugin is independent. To add a new plugin, create its directory under `plugins/`, add a manifest, define its skills, and register it in the root `marketplace.json`.
