# Tools

For fuzz testing, the key tool types are coverage-guided fuzzers, language-native fuzz test runners, and CI orchestration for corpus/crash retention. Choose the language-native option when it exists, AFL++ for native/binary targets, and ClusterFuzzLite when the main need is continuous fuzzing in CI rather than a local fuzzing campaign.

## AFL++

- Use for: High-throughput coverage-guided fuzzing of C/C++ libraries, CLI parsers, file-format handlers, and binary-oriented targets.
- Languages/ecosystem: C, C++, native binaries; also useful for many projects that can expose a command-line harness.
- Why it is trusted: AFL++ has official quick-start guidance for source-available, binary-only, network, and GUI targets, with standard afl-cc / afl-fuzz workflows and crash replay guidance.
- Official docs: https://aflplus.plus/docs/
- Good usage pattern: Build an instrumented target, seed it with small valid inputs, and cap unattended runs with AFL++ environment controls. AFL_EXIT_ON_TIME exits after no new paths are found for the configured seconds.

```
mkdir -p seeds findings
printf '{"schema":1,"items":[]}\n' > seeds/valid.json
CC=afl-cc CXX=afl-c++ cmake -S . -B build -DENABLE_FUZZING=ON
cmake --build build --target json_parser_fuzz
AFL_NO_UI=1 AFL_EXIT_ON_TIME=300 \
  afl-fuzz -i seeds -o findings -- ./build/json_parser_fuzz @@
```

## ClusterFuzzLite

- Use for: Continuous fuzzing in CI, especially PR fuzzing plus scheduled longer batch fuzzing.
- Languages/ecosystem: CI orchestration for fuzz targets; supports GitHub Actions, GitLab, Google Cloud Build, and Prow workflows.
- Why it is trusted: It provides first-class modes for code-change fuzzing, batch fuzzing, corpus pruning, coverage reports, and continuous builds, with official GitHub Actions examples.
- Official docs: https://google.github.io/clusterfuzzlite/
- Good usage pattern: Use PR fuzzing for fast feedback, then add scheduled batch fuzzing later to build a stronger corpus.

```
name: ClusterFuzzLite PR fuzzing
on:
  pull_request:
    paths: ['**']
permissions: read-all
jobs:
  fuzz:
    runs-on: ubuntu-latest
    steps:
      - name: Build fuzzers
        uses: google/clusterfuzzlite/actions/build_fuzzers@v1
        with:
          language: c++
          github-token: ${{ secrets.GITHUB_TOKEN }}
          sanitizer: address
      - name: Run fuzzers
        uses: google/clusterfuzzlite/actions/run_fuzzers@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          mode: code-change
          fuzz-seconds: 600
          sanitizer: address
          output-sarif: true
```

## Go Fuzzing

- Use for: Fuzzing Go package APIs directly inside normal go test workflows.
- Languages/ecosystem: Go standard toolchain, testing.F, go test -fuzz.
- Why it is trusted: Go fuzzing is built into the standard toolchain from Go 1.18, uses coverage guidance, and stores failing inputs as regression corpus entries run by future go test executions.
- Official docs: https://go.dev/doc/security/fuzz/
- Good usage pattern: Keep fuzz tests deterministic, seed realistic examples with f.Add, and use -fuzztime for CI-bounded runs.

```
package query
import (
	"net/url"
	"reflect"
	"testing"
)
func FuzzParseQueryRoundTrip(f *testing.F) {
	f.Add("user=alice&role=admin")
	f.Add("q=a%2Bb&empty=")
	f.Fuzz(func(t *testing.T, raw string) {
		values, err := url.ParseQuery(raw)
		if err != nil {
			return
		}
		reparsed, err := url.ParseQuery(values.Encode())
		if err != nil {
			t.Fatalf("encoded query is not parseable: %v", err)
		}
		if !reflect.DeepEqual(values, reparsed) {
			t.Fatalf("round trip changed values: %#v != %#v", values, reparsed)
		}
	})
}
// CI smoke run:
// go test ./... -run=FuzzParseQueryRoundTrip -fuzz=FuzzParseQueryRoundTrip -fuzztime=60s
```

## cargo-fuzz

- Use for: Coverage-guided fuzzing of Rust crates, especially parsers, codecs, protocol handlers, and unsafe-code boundaries.
- Languages/ecosystem: Rust, Cargo, libFuzzer via libfuzzer_sys.
- Why it is trusted: The Rust Fuzz Book documents cargo fuzz init, checked-in fuzz targets under fuzz/fuzz_targets, and cargo fuzz run <target> using libFuzzer.
- Official docs: https://rust-fuzz.github.io/book/cargo-fuzz.html
- Good usage pattern: Keep the harness narrow, reject invalid inputs cheaply, assert semantic invariants, and run a bounded libFuzzer session in CI.

```
#![no_main]
#[macro_use]
extern crate libfuzzer_sys;
use serde_json::Value;
fuzz_target!(|data: &[u8]| {
    if let Ok(value) = serde_json::from_slice::<Value>(data) {
        let encoded = serde_json::to_vec(&value).unwrap();
        assert!(serde_json::from_slice::<Value>(&encoded).is_ok());
    }
});
// CI smoke run:
// cargo fuzz run serde_json_roundtrip -- -max_total_time=60
```

## Jazzer

- Use for: Coverage-guided fuzzing of JVM libraries, parsers, deserializers, and security-sensitive Java/Kotlin/Scala code.
- Languages/ecosystem: JVM, JUnit 5, Maven, Gradle, Bazel.
- Why it is trusted: Jazzer is a coverage-guided in-process JVM fuzzer based on libFuzzer and has official JUnit integration with @FuzzTest, regression mode, and fuzzing mode via JAZZER_FUZZ=1.
- Official docs: https://github.com/CodeIntelligenceTesting/jazzer
- Good usage pattern: Write fuzz tests beside unit tests, constrain generated inputs with Jazzer annotations, and let crash inputs become regression cases.

```
import com.code_intelligence.jazzer.junit.FuzzTest;
import com.code_intelligence.jazzer.mutation.annotation.NotNull;
import com.code_intelligence.jazzer.mutation.annotation.WithUtf8Length;
import java.net.URI;
import java.net.URISyntaxException;
import static org.junit.jupiter.api.Assertions.assertEquals;
class UriFuzzTest {
  @FuzzTest
  void normalizedUriStaysParseable(
      @NotNull @WithUtf8Length(min = 1, max = 2048) String input) {
    try {
      URI normalized = new URI(input).normalize();
      assertEquals(normalized, new URI(normalized.toString()));
    } catch (URISyntaxException ignored) {
      // Invalid URIs are acceptable; crashes and invariant failures are not.
    }
  }
}
// Fuzzing mode:
// JAZZER_FUZZ=1 mvn test
```
