# Fuzz Testing / Continuous Fuzzing

## Strategy Map

### Purpose
Exercise input-handling boundaries with generated or mutated inputs to find crashes, hangs, memory errors, parser failures, and invariant violations.

### Reliability Goal
Reduce robustness and security risk in code that processes untrusted, malformed, high-volume, or complex structured input.

### When This Strategy Applies
- The change touches parsers, decoders, serializers, protocol handlers, file formats, compression, regexes, normalization, URL/path handling, image/media processing, or unsafe/native code.
- A deterministic harness can call the behavior quickly with generated input.
- A crash, timeout, sanitizer finding, or invariant violation is a meaningful failure.
- Continuous fuzzing infrastructure or seed corpus already exists, or the target is high-risk enough to justify adding it.

### When This Strategy Does Not Apply
- No clear input boundary or oracle exists.
- The behavior depends on live services, real time, global state, or irreversible side effects.
- The only assertion is vague and expensive.
- The target is ordinary CRUD logic better covered by examples, properties, contract, or integration tests.
- The team cannot triage minimized crashes or maintain seed corpora.

### Signals To Inspect First
- Input parsers, public deserialization APIs, untrusted uploads, protocol messages, seeds/corpora, sanitizer builds, OSS-Fuzz/ClusterFuzz config, fuzz target naming, crash artifacts, timeout thresholds, memory limits, and previous malformed-input bugs.

### Test Design Principles
- A fuzz target should be small, deterministic, fast, and side-effect controlled.
- The oracle can be crash-free execution, sanitizer cleanliness, parse/serialize invariant, resource bound, or business invariant.
- Seed corpora should include real and boundary examples, not only random bytes.
- Crashes become regression tests by adding minimized inputs.
- Continuous fuzzing needs ownership, deduplication, minimization, and triage.

### Good Test Characteristics
- Harnesses isolate one input boundary and reset state each run.
- Sanitizers or runtime checks are enabled where supported.
- Timeouts and resource limits catch hangs and pathological inputs.
- Crashes are minimized, stored, and replayed in deterministic tests.
- Short PR fuzz runs are paired with longer scheduled campaigns for high-risk code.

### Poor Test Characteristics
- A broad application boot fuzzes everything and diagnoses nothing.
- The target writes to shared databases or external services.
- Crashes are ignored because they are “just fuzz input.”
- Generated inputs never reach parser states because no seed corpus exists.
- Fuzzing is claimed as security coverage for authorization or business logic without a relevant oracle.

### Execution Pattern
- Identify the input boundary and failure oracle.
- Build a minimal deterministic harness around public behavior.
- Seed with valid, invalid, boundary, and regression inputs.
- Run a short local/CI fuzz pass and replay any failures.
- Minimize and deduplicate crashes.
- Add minimized inputs to regression corpus or ordinary tests.
- Schedule longer continuous fuzzing for high-risk targets.

### Examples
- Weak: fuzz an HTTP server through a live port with random bytes and no artifact capture. Stronger: fuzz the request parser or route-normalizer function directly, assert controlled errors, enable sanitizers, and store minimized crashing inputs.
- Weak: fuzz authorization decisions with random users but no expected policy. Stronger: use property tests or model-based tests for policy invariants; reserve fuzzing for malformed token or parser robustness.

### Validation
- Run the fuzz target for the repository’s standard short duration.
- Replay minimized failures outside the fuzzer.
- Confirm regression corpus cases fail before the fix when applicable and pass after.
- Check the target is deterministic and free of external side effects.
- Inspect coverage/corpus growth as a diagnostic, not a proof of completeness.

### Failure Modes
- Harnesses are too slow or broad for CI.
- Nondeterminism creates irreproducible crashes.
- No oracle means bugs are missed except crashes.
- Corpus and artifacts are not retained.
- Fuzzing is used where risk is authorization, integration, or performance rather than input robustness.

## Overview

Fuzz testing feeds many generated inputs into a deterministic harness to find crashes, hangs, memory errors, parser bugs, invariant violations, and unsafe handling of untrusted data. Continuous fuzzing keeps that search running over time and turns minimized crashes into regressions.

Fuzzing is strongest when the input boundary is clear, the harness is fast, failures are reproducible, and the oracle is at least “no crash, no timeout, controlled error,” preferably with semantic invariants.

## Best Fit

Use fuzzing for parsers, decoders, serializers, file formats, URL/path handling, protocol handlers, decompression, cryptography wrappers, query languages, config loaders, API request validators, and any boundary that accepts untrusted or structured input.

Use continuous fuzzing when the code changes often, has security exposure, or has a history of input-handling defects. Seed corpora and minimized crash artifacts are part of the product; keep them reviewed and versioned.

## Candidate Matrix

| Target | Harness Should Check |
| --- | --- |
| Parser/decoder | No crash/hang; valid inputs round trip or normalize; invalid inputs fail safely. |
| Serializer | Round trip, canonicalization, compatibility, size limits. |
| URL/path handling | No traversal, confusion, panic, or unsafe normalization. |
| Protocol/message handler | State and length limits; controlled rejection; no resource exhaustion. |
| Image/archive/document input | No memory corruption, decompression bomb, infinite loop, or unsafe extraction. |
| API validation | Reject malformed payloads predictably; preserve auth and tenant boundaries. |
| CLI/config input | Stable exit behavior, bounded output, controlled errors, no hidden filesystem/network effects. |
| Query builders/expression languages | Parameterization, tenant predicates, parse/print round trips, no authorization predicate loss. |
| Permission/policy combinations | Deny-by-default, monotonicity, lower-privilege roles never exceed allowed constraints. |
| Stateful workflows | Generated command sequences preserve state invariants after every transition. |
| Native extension/FFI boundary | No memory corruption, invalid lifetime, marshaling, or sanitizer failure. |

## When Not To Use

Avoid fuzzing when there is no deterministic harness, no meaningful input boundary, no reproducible failure path, or no owner to triage findings. Do not replace semantic tests with fuzzing; fuzzers are excellent at finding surprising cases but still need clear oracles.

For deterministic business invariants over valid data, property-based testing may be a better first tool. For production abuse cases involving auth, rate limits, and tenant boundaries, pair fuzzing with security tests.

## Harness Design Notes

| Problem | Better Design |
| --- | --- |
| Target starts a server, browser, database, or real payment system per input. | Fuzz the parser, validator, request decoder, or policy decision below the full workflow. |
| Most random inputs die at the first byte. | Add valid seeds, dictionaries, grammar-aware generation, custom mutators, or structured generators. |
| “No crash” is too weak for business logic. | Add invariants, differential checks, metamorphic properties, schema validation, or model agreement. |
| Failures depend on input order or hidden state. | Reset globals/caches, isolate filesystem paths, fake time/randomness, and avoid live network calls. |
| Corpus grows until CI slows down. | Minimize crashers, prune corpus, separate short PR fuzzing from longer scheduled runs. |
| Sanitizer/toolchain build differs from normal builds. | Document build mode, sanitizer, compiler flags, and reproducer command with every finding. |

## Signals

| Strong Signal | Use With Judgment | Avoid |
| --- | --- | --- |
| Code parses bytes, text, files, URLs, protocols, or external payloads. | Existing examples can seed a corpus but oracle is weak. | Random input only reaches parse errors and no deeper code. |
| Past crashes, hangs, CVEs, malformed input bugs, or panic fixes. | Slow harness can be optimized or isolated. | Nondeterministic harness with time/network/shared state. |
| Sanitizers or coverage-guided fuzzers are already configured. | Structured input needs grammar or custom mutator. | Treating “no crash today” as proof of safety. |
| OpenAPI, GraphQL, protobuf, JSON Schema, or fixtures describe inputs. | Schema may be stale or incomplete. | Fuzzing without route/auth/data scoping. |

## Workflow

1. Choose one input boundary and build a small deterministic harness.
2. Add seed corpus from valid examples, regressions, edge cases, and protocol fixtures.
3. Run locally with sanitizers or coverage guidance when available.
4. Minimize crashes and commit regression seeds when useful.
5. Add CI or scheduled continuous fuzzing only after local harnesses are stable.
6. Track findings with owner, artifact, minimized input, command, and fix status.

## Continuous Fuzzing Shape

| Stage | Purpose |
| --- | --- |
| Local run | Prove the harness is deterministic, fast, and reproduces failures. |
| Short PR/CIFuzz run | Catch obvious regressions in changed code with retained crash artifacts. |
| Nightly/batch run | Explore deeper paths, grow corpus, and run expensive sanitizers. |
| Corpus pruning | Keep CI affordable and preserve the inputs that add coverage or regression value. |
| Regression replay | Re-run minimized crash inputs as ordinary tests when practical. |

## Examples

| Weak | Stronger |
| --- | --- |
| Generate random bytes and ignore every parse error. | Assert valid generated messages round trip and invalid bytes fail with controlled errors. |
| Fuzz through a full live service. | Fuzz the parser/validator directly with fake clocks, no network, and bounded resources. |
| Fix crash but discard input. | Add minimized crash input to corpus or regression tests. |
| Snapshot every fuzzed API response. | Assert policy outcomes, schema conformance, and no 500s for validation failures. |
| Use mutation-only fuzzing for a complex grammar with no seeds. | Seed valid examples and add a grammar/custom mutator so the fuzzer reaches deep logic. |

## Packages And Libraries

| Ecosystem | Tools |
| --- | --- |
| C/C++/Rust | libFuzzer, AFL++, honggfuzz, sanitizers, cargo-fuzz. |
| Go | Native fuzzing in go test. |
| JVM | Jazzer, JQF/Zest for coverage-guided fuzzing. |
| Python | Atheris, Hypothesis for property-style generated inputs. |
| JavaScript/TypeScript | Jazzer.js, fast-check for semantic generation, OSS-Fuzz support where applicable. |
| Continuous Platforms | OSS-Fuzz, ClusterFuzzLite, CIFuzz/GitHub Actions integrations, OneFuzz-style setups. |

## Source Anchors

- libFuzzer frames the core pattern as fast, in-process, coverage-guided fuzzing of a target function.
- Go fuzzing treats seed corpora, minimized failing inputs, and replay through normal tests as part of the workflow.
- OSS-Fuzz, ClusterFuzz, ClusterFuzzLite, and CIFuzz separate short change-focused fuzzing from longer batch fuzzing, corpus pruning, minimization, and triage.
- Sanitizers such as ASan, UBSan, and TSan make fuzzing more valuable for memory, undefined behavior, and race defects, but they add build/runtime cost.

## Quality Bar

- Harness is deterministic, fast, isolated, and bounded.
- Seeds include valid examples, malformed inputs, boundaries, and prior failures.
- Crashes include minimized input, reproducer command, sanitizer output when relevant, and owner.
- Semantic invariants are added where “does not crash” is too weak.
- Continuous fuzzing has triage policy and does not create unowned alert noise.
