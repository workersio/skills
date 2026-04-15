---
name: fuzzer
description: >
  Coverage-guided fuzzing workflow for C/C++, Rust, and Go targets.
  Runs audit-context-building to find suspicious code, writes a targeted
  harness, builds with sanitizers, runs the fuzzer, and reports crashes.
---

# Fuzzer Skill

## When to Use

Invoke when asked to fuzz a target, find memory/integer bugs via fuzzing,
write a fuzz harness, or run a fuzzing campaign on a codebase.

---

## Workflow

### Step 1 — Audit (MANDATORY — always run first, no exceptions)

**You MUST invoke the `audit-context-building` skill before writing any harness.**
Do not skip this step even if you think you already understand the code.

Goal: read the **entire codebase** — all source files — before ranking anything. Do not stop after finding the first suspicious location in one directory. Cover all modules.

Look specifically for:
- `size_t → int` or `size_t → uint32_t` narrowing casts
- Unchecked length arithmetic (additions, multiplications on sizes)
- Public API functions that accept attacker-controlled `size_t` / length parameters

Output: a ranked list of suspicious locations with `file:line` drawn from the full codebase.
Pick the top candidate for the harness.

---

### Step 2 — Write the Harness

**You MUST target the exact `file:line` ranked #1 by the audit. Do not target a different function, code path, or "more interesting" area based on your own judgment. The audit decides the target. You implement it.**

- Read the call path the audit provided
- Call the exact function in that call path
- Use the bug class it identified to pick the pattern below

Pick the pattern based on the bug class from Step 1.

**Arithmetic overflow** (`size_t→int` accumulation, unchecked addition on sizes):
The bug is in the arithmetic — not the buffer contents. Extract a `uint32_t` claimed size from fuzz bytes and pass it directly. Use a 1-byte static stub as the data pointer. Never derive the size from the actual buffer you hand over.
```c
#include <stddef.h>
#include <stdint.h>
#include <string.h>

static const uint8_t kStub[1] = {0};

/* Required by libAFLDriver.a — must be present or link fails */
int LLVMFuzzerInitialize(int *argc, char ***argv) {
    (void)argc; (void)argv;
    return 0;
}
void LLVMFuzzerCleanup(void) {}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    uint8_t n = data[0] % MAX_CALLS;
    if (n == 0 || size < 1 + (size_t)n * 4) return 0;

    TargetState *s = TargetState_Create();
    for (uint8_t i = 0; i < n; i++) {
        uint32_t claimed;
        memcpy(&claimed, data + 1 + i * 4, 4);
        target_fn(s, (size_t)claimed, kStub);  /* claimed drives the arithmetic */
    }
    TargetState_Destroy(s);
    return 0;
}
```

**Split-input** (API takes a config/size parameter + a data payload):
```c
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < N) return 0;
    /* bytes [0..N-1] → config / mode / count */
    /* bytes [N..]    → payload */
    target_fn(config, data + N, size - N);
    return 0;
}
```

**Direct call** (simple buffer + length):
```c
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < 1) return 0;
    target_fn(data, size);
    return 0;
}
```

**Rust:**
```rust
fuzz_target!(|data: &[u8]| { target_function(data); });
```

**Go:**
```go
func FuzzTarget(f *testing.F) {
    f.Fuzz(func(t *testing.T, data []byte) { target_function(data) })
}
```

---

### Step 3 — Build

Before building, locate AFL++:
```bash
which afl-clang-fast || find /usr/local /opt/homebrew /tmp -name afl-clang-fast 2>/dev/null
```
If not found, install it:
```bash
brew install afl++       # macOS
apt-get install afl++    # Debian/Ubuntu
```

**C / C++ with AFL++:**
```bash
AFL=$(which afl-clang-fast)
AFLDRIVER=$(dirname $(dirname $AFL))/lib/afl/libAFLDriver.a

# Compile target sources into instrumented static library
mkdir -p build
find <src-dir> -name "*.c" | while read f; do
  $AFL \
    -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer \
    <include-flags> -c "$f" -o "build/$(basename $f .c).o"
done
ar rcs build/libtarget.a build/*.o

# Compile harness + link
$AFL \
  -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer \
  harness.c build/libtarget.a $AFLDRIVER \
  -o build/fuzzer
```

**Rust:**
```bash
cargo fuzz build <target_name>
```

---

### Step 4 — Run

**C / C++ with AFL++:**
```bash
ASAN_OPTIONS=abort_on_error=1:detect_leaks=0:symbolize=0 \
AFL_SKIP_CPUFREQ=1 AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 \
$(which afl-fuzz) \
  -i corpus/ \
  -o findings/ \
  -- build/fuzzer
```

**Rust:**
```bash
cargo fuzz run <target_name> corpus/
```

**Go:**
```bash
go test -fuzz=FuzzTarget -fuzztime=12h ./...
```

---

### Step 5 — Report

When `findings/default/crashes/` contains files, report:

```
CRASH FOUND
  Input:   findings/default/crashes/id:000000,...
  Signal:  sig:06 (SIGABRT = sanitizer) or sig:11 (SIGSEGV)

Reproduce (with symbolized output):
  UBSAN_OPTIONS=print_stacktrace=1 \
  ASAN_OPTIONS=detect_leaks=0:print_stacktrace=1 \
  ./build/fuzzer findings/default/crashes/id:000000,...

Sanitizer output:
  <paste UBSan/ASan stacktrace here>

Root cause: <file>:<line> — <one sentence description>
```

If no crashes after the time budget: report paths found and unique inputs in corpus.

---

## Harness Rules

| Rule | Why |
|---|---|
| Return 0 always | Never abort from the harness itself |
| Never call `exit()` | Kills the fuzzer process |
| Handle all input sizes | Fuzzer generates empty / tiny / huge inputs |
| Be fast — no logging | Target 100–1000+ exec/sec |
| Same input = same output | Determinism required for crash reproduction |
| Free all resources each call | Prevents memory exhaustion over millions of runs |
| Reset global state | Isolates each iteration |

---

## Tool Selection

| Target | Fuzzer | Notes |
|---|---|---|
| C / C++ | AFL++ (`afl-clang-fast`) | Best coverage instrumentation |
| Rust | `cargo-fuzz` | Uses libFuzzer API under the hood |
| Go | `go test -fuzz` | Native, no extra tooling |
| Any binary | AFL++ black-box (`afl-fuzz @@`) | No source needed |
| Custom / research | LibAFL | Modular Rust fuzzing library |
