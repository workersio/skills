# Tools

For Property-Based Testing, the useful tool capabilities are generators/arbitraries, repeated randomized checks, shrinking to minimal counterexamples, deterministic replay, and integration with the project’s normal test runner. Choose primarily by language and runner fit; choose secondarily by how well the library supports custom generators, CI run-count controls, and stateful/model-based tests. PBT libraries commonly separate generated inputs from assertions and are usually used alongside ordinary unit tests, not instead of them.

## Hypothesis

- Use for: Python property tests in pytest/unittest suites, especially for data validation, parsers, serializers, and numeric edge cases.
- Languages/ecosystem: Python; commonly paired with pytest.
- Why it is trusted: Hypothesis documents per-test settings, suite profiles, environment-selected profiles, strategies, and shrinking/replay behavior.
- Official docs: https://hypothesis.readthedocs.io/en/latest/
- Good usage pattern:

```
from hypothesis import given, settings, strategies as st
from app.tags import normalize_tags
tag_lists = st.lists(st.text(min_size=0, max_size=30), max_size=50)
@given(tag_lists)
@settings(max_examples=300, deadline=None)
def test_normalize_tags_is_idempotent(raw_tags):
    once = normalize_tags(raw_tags)
    assert normalize_tags(once) == once
    assert once == sorted(set(once))
    assert all(t and t == t.strip().lower() for t in once)
```

## fast-check

- Use for: JavaScript/TypeScript property tests in Jest, Vitest, Mocha, Node, or browser-oriented test suites.
- Languages/ecosystem: JavaScript and TypeScript; test-runner agnostic.
- Why it is trusted: Its docs cover arbitraries, seeded deterministic runs, configurable run counts, shrinking, and compatibility with major JS/TS test frameworks.
- Official docs: https://fast-check.dev/docs/introduction/getting-started/
- Good usage pattern:

```
import fc from 'fast-check';
import { expect, test } from 'vitest';
import { parseMoneyCents } from './money';
fc.configureGlobal({ numRuns: Number(process.env.FC_NUM_RUNS ?? 250) });
test('parseMoneyCents round-trips formatted cents', () => {
  fc.assert(
    fc.property(fc.integer({ min: 0, max: 1_000_000 }), (cents) => {
      const text = `$${(cents / 100).toFixed(2)}`;
      expect(parseMoneyCents(text)).toBe(cents);
    }),
  );
});
```

## jqwik

- Use for: JVM property tests that should run naturally on the JUnit Platform.
- Languages/ecosystem: Java, Kotlin, and other JVM languages; pair with JUnit/AssertJ assertions as needed.
- Why it is trusted: The user guide documents @Property, @ForAll, default 1000 tries, shrinking, edge-case generation, property defaults, and JUnit Platform dependencies.
- Official docs: https://jqwik.net/docs/current/user-guide.html
- Good usage pattern:

```
import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.constraints.IntRange;
import org.junit.jupiter.api.Assertions;
class MoneyProperties {
    @Property(tries = 500)
    void parseCentsRoundTrips(
        @ForAll @IntRange(min = 0, max = 1_000_000) int cents
    ) {
        String text = String.format("$%d.%02d", cents / 100, cents % 100);
        Assertions.assertEquals(cents, Money.parseCents(text));
    }
}
```

## proptest

- Use for: Rust property tests where explicit strategies, shrinking, and regression replay should run under cargo test.
- Languages/ecosystem: Rust; pair with normal unit/integration tests.
- Why it is trusted: The crate docs expose the core strategy, assertion, and proptest! APIs; the official book documents configurable case counts and persisted regression seeds for CI replay.
- Official docs: https://proptest-rs.github.io/proptest/proptest/index.html
- Good usage pattern:

```
use proptest::prelude::*;
fn normalize_ids(mut ids: Vec<u32>) -> Vec<u32> {
    ids.sort_unstable();
    ids.dedup();
    ids
}
proptest! {
    #![proptest_config(ProptestConfig::with_cases(512))]
    #[test]
    fn normalize_ids_is_idempotent(
        ids in prop::collection::vec(0u32..10_000, 0..200)
    ) {
        let once = normalize_ids(ids);
        let twice = normalize_ids(once.clone());
        prop_assert_eq!(&once, &twice);
        prop_assert!(once.windows(2).all(|w| w[0] < w[1]));
    }
}
```

## FsCheck

- Use for: .NET property tests, especially F# or C# suites that already use xUnit or NUnit.
- Languages/ecosystem: .NET; F#, C#, VB; integrates with xUnit and NUnit.
- Why it is trusted: The docs cover built-in runners, QuickCheckThrowOnFailure, xUnit/NUnit integrations, configurable MaxTest, shrinking output, and replay seeds.
- Official docs: https://fscheck.github.io/FsCheck/
- Good usage pattern:

```
using System.Linq;
using FsCheck;
using Xunit;
public class SlugProperties
{
    [Fact]
    public void NormalizeSlugIsIdempotent()
    {
        var config = Config.QuickThrowOnFailure
            .WithMaxTest(300)
            .WithQuietOnSuccess(true);
        Prop.ForAll<string>(input =>
        {
            var once = Slug.Normalize(input ?? "");
            return Slug.Normalize(once) == once
                && once.All(c =>
                    c == '-' || ('a' <= c && c <= 'z') || ('0' <= c && c <= '9'));
        }).Check(config);
    }
}
```
