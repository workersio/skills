# Advanced Kani Features

Beyond basic proof harnesses, Kani provides powerful features for modular verification, performance optimization, and debugging. Sourced from all 19 Kani blog posts and official documentation.

---

## Codebase Preparation for Kani

Before writing proofs, prepare the codebase so the SAT solver can handle it. Without these steps, proofs involving large state structs or wrapped integer types will timeout or hit unwinding limits.

### State Space Reduction

Programs with array-bounded state (accounts, validators, orders) must reduce array sizes for Kani. The solver unrolls every loop — a loop over 4096 items creates 4096x the constraints.

**Pattern:** Add `#[cfg(kani)]` const overrides:

```rust
#[cfg(kani)]
pub const MAX_ACCOUNTS: usize = 4;

#[cfg(all(not(kani), feature = "test"))]
pub const MAX_ACCOUNTS: usize = 64;

#[cfg(all(not(kani), not(feature = "test")))]
pub const MAX_ACCOUNTS: usize = 4096;
```

**How to choose the right value:** Use the smallest value that exercises all code paths. The logic of array-indexed algorithms is size-independent — proving correctness for 4 accounts proves the algorithm is correct for any size.

| Production Constant | Typical Value | Kani Value | Why |
|---|---|---|---|
| MAX_ACCOUNTS | 64-4096 | 4 | One bitmap word, all code paths exercised |
| MAX_VALIDATORS | 32-1000 | 4 | Iterator logic same at any size |
| MAX_ORDERS | 128-1024 | 4 | Queue/ring buffer logic size-independent |
| MAX_POSITIONS | 16-256 | 4 | Per-user position array |

**Impact:** Without reduction, `RiskEngine::new()` with MAX_ACCOUNTS=64 at unwind=70 causes the SAT solver to consume 500MB+ RAM and timeout after 10+ minutes. With MAX_ACCOUNTS=4, the same proof completes in seconds.

### SAT-Friendly Type Optimization

Solana BPF/SBF programs often use `[u64; 2]` arrays to represent 128-bit integers because Rust 1.77+ changed i128/u128 alignment from 8 to 16 bytes on x86_64, while BPF still uses 8-byte alignment. These opaque wrappers are exponentially harder for the SAT solver than raw primitives.

**Pattern:** Add `#[cfg(kani)]` transparent newtypes:

```rust
// ── Kani path: solver sees raw primitive ──
#[cfg(kani)]
#[repr(transparent)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct I128(i128);

#[cfg(kani)]
impl I128 {
    pub const ZERO: Self = Self(0);
    pub const MIN: Self = Self(i128::MIN);
    pub const MAX: Self = Self(i128::MAX);

    #[inline]
    pub const fn new(val: i128) -> Self { Self(val) }

    #[inline]
    pub const fn get(self) -> i128 { self.0 }

    #[inline]
    pub fn set(&mut self, val: i128) { self.0 = val; }

    #[inline]
    pub fn checked_add(self, rhs: i128) -> Option<Self> {
        self.0.checked_add(rhs).map(Self)
    }

    #[inline]
    pub fn checked_sub(self, rhs: i128) -> Option<Self> {
        self.0.checked_sub(rhs).map(Self)
    }

    #[inline]
    pub fn is_zero(self) -> bool { self.0 == 0 }

    #[inline]
    pub fn is_negative(self) -> bool { self.0 < 0 }

    #[inline]
    pub fn abs(self) -> Self { Self(self.0.abs()) }

    // ... all other methods delegating directly to i128
}

// ── BPF path: array-based for 8-byte alignment ──
#[cfg(not(kani))]
#[repr(C)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct I128([u64; 2]);

#[cfg(not(kani))]
impl I128 {
    pub const ZERO: Self = Self([0, 0]);

    #[inline]
    pub const fn new(val: i128) -> Self {
        Self([val as u64, (val >> 64) as u64])
    }

    #[inline]
    pub const fn get(self) -> i128 {
        ((self.0[1] as i128) << 64) | (self.0[0] as u128 as i128)
    }

    // ... same API, using bit-shifting internally
}
```

**Both paths must implement identical APIs:** `new()`, `get()`, `set()`, `checked_add/sub/mul/div()`, `saturating_add/sub()`, `abs()`, `is_zero()`, `is_negative()`, plus trait impls for `From<i128>`, `From<i64>`, `PartialOrd`, `Ord`, `Default`, `Debug`, `Display`, and arithmetic operators (`Add`, `Sub`, `Mul`, `Neg`, `AddAssign`, `SubAssign`).

Apply the same pattern for `U128`:

```rust
#[cfg(kani)]
#[repr(transparent)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct U128(u128);

#[cfg(not(kani))]
#[repr(C)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct U128([u64; 2]);
```

**Performance impact:** Transparent newtypes reduce solver time from timeout (>10min) to seconds for proofs involving 128-bit arithmetic. The solver treats `I128(i128)` as a single 128-bit value instead of reasoning about 128 individual bits through shift/mask operations.

### Cargo.toml Kani Configuration

Add Kani metadata to your `Cargo.toml` (or workspace root for workspaces):

```toml
[workspace.metadata.kani.flags]
tests = true
default-unwind = "10"
```

| Field | Purpose |
|---|---|
| `tests = true` | Enables `#[cfg(test)]` modules during Kani verification |
| `default-unwind = "10"` | Default loop unwind bound; individual harnesses override with `#[kani::unwind(N)]` |

> **Note:** Unstable features (such as stubbing or function contracts) are enabled via `-Z` flags on the command line (e.g., `cargo kani -Z stubbing`), not through Cargo.toml metadata.

**Choosing the unwind bound:** Set `default-unwind` to `MAX_ACCOUNTS` (after Kani reduction) + margin. For `MAX_ACCOUNTS = 4`, `default-unwind = "10"` is usually sufficient. Without state-space reduction (e.g., `MAX_ACCOUNTS = 64`), you would need a much higher bound, which is significantly slower.

### no_std Setup

For `#![no_std]` crates (common in Solana programs), add at the crate root:

```rust
#[cfg(kani)]
extern crate kani;
```

Kani compiles with std internally, but the extern crate declaration is needed to access the `kani::` API (`kani::any()`, `kani::assert()`, etc.).

If the crate uses `#![cfg_attr(not(test), no_std)]`, note that the `kani` cfg flag is independent of `test` — both may need to be handled:

```rust
#![cfg_attr(all(not(test), not(kani)), no_std)]

#[cfg(kani)]
extern crate kani;
```

---

## Function Contracts

> **Note:** Function contracts are EXPERIMENTAL. You must pass `-Z function-contracts` to `cargo kani`.

Function contracts enable **modular verification** — verify each function independently, then compose them. This is critical for complex programs where verifying everything at once causes solver explosion.

### Three Contract Clauses

```rust
/// Precondition: caller must guarantee this
#[kani::requires(max != 0 && min != 0)]
/// Postcondition: function guarantees this on return
#[kani::ensures(|result| max % *result == 0 && min % *result == 0 && *result != 0)]
fn gcd(mut max: u64, mut min: u64) -> u64 {
    if max < min {
        std::mem::swap(&mut max, &mut min);
    }
    loop {
        let remainder = max % min;
        if remainder == 0 { return min; }
        max = min;
        min = remainder;
    }
}

/// Proves the contract holds for all valid inputs
#[kani::proof_for_contract(gcd)]
fn verify_gcd_contract() {
    let max: u64 = kani::any();
    let min: u64 = kani::any();
    gcd(max, min);
}
```

### Using Verified Contracts as Stubs

Once a contract is proven, use it as a stub in other proofs to avoid re-verifying the callee:

```rust
/// This proof calls gcd() but doesn't re-verify it —
/// uses the proven contract instead
#[kani::proof]
#[kani::stub_verified(gcd)]
fn verify_caller_of_gcd() {
    let a: u64 = kani::any();
    let b: u64 = kani::any();
    kani::assume(a != 0 && b != 0);
    let result = gcd(a, b);
    // Contract guarantees result divides both a and b
    assert!(a % result == 0);
}
```

### Memory Modification Contracts

```rust
#[kani::requires(ptr.is_valid())]
#[kani::modifies(ptr)]    // Declares which memory may be written
#[kani::ensures(|_| unsafe { *ptr == new_value })]
unsafe fn write_value(ptr: *mut u64, new_value: u64) {
    *ptr = new_value;
}
```

### When to Use Contracts

- **Recursive functions** — contracts enable inductive verification without unbounded unrolling
- **Complex call chains** — verify each layer independently
- **Library functions** — define the contract once, callers use `stub_verified`
- **CPI in Solana** — define contracts for cross-program calls, stub during verification

---

## Stubbing

Replace functions during verification with simpler models. Three use cases:

### 1. Unsupported Features (FFI, CPI, Inline Assembly)

```rust
// Solana CPI calls can't be symbolically executed — stub them
#[cfg(kani)]
fn stub_transfer(_program_id: &Pubkey, _accounts: &[AccountInfo], _amount: u64) -> ProgramResult {
    // Model: transfer can succeed or fail
    if kani::any() { Ok(()) } else { Err(ProgramError::InsufficientFunds) }
}

#[kani::proof]
#[kani::stub(spl_token::instruction::transfer, stub_transfer)]
fn verify_withdrawal() {
    // Proof can now run without the real SPL token program
}
```

### 2. Performance (Replace Expensive Computation)

```rust
// Factorial via recursion is slow to verify — use lookup table
const FACT: [u64; 21] = [1, 1, 2, 6, 24, 120, 720, 5040, /*...*/];

#[cfg(kani)]
fn stub_factorial(n: u64) -> Option<u64> {
    if (n as usize) < FACT.len() { Some(FACT[n as usize]) } else { None }
}

#[kani::proof]
#[kani::unwind(22)]
#[kani::stub(factorial, stub_factorial)]
fn verify_choose() {
    let n: u64 = kani::any();
    let k: u64 = kani::any();
    kani::assume(n > 0 && n < 21 && k > 0 && k < 21 && n >= k);
    assert_eq!(choose(n, k), choose(n, n - k));
}
// Result: 15+ minutes → 13.6 seconds
```

### 3. External Dependencies (System Calls, Time)

```rust
// Stub system clock for deterministic verification
#[cfg(kani)]
mod stubs {
    static mut LAST_SECONDS: i64 = 0;

    pub unsafe extern "C" fn clock_gettime(
        _clock_id: libc::clockid_t,
        tp: *mut libc::timespec
    ) -> libc::c_int {
        unsafe {
            let next = kani::any_where(|&n| n >= LAST_SECONDS);
            (*tp).tv_sec = LAST_SECONDS;
            LAST_SECONDS = next;
        }
        0
    }
}

#[kani::proof]
#[kani::stub(libc::clock_gettime, stubs::clock_gettime)]
fn verify_rate_limiter() {
    let mut bucket: TokenBucket = kani::any();
    bucket.auto_replenish();
    assert!(bucket.is_valid());
}
```

### Stubbing Pitfalls

**UNSOUND STUB (DO NOT DO):**
```rust
// This stub only returns Ok — ignores the Err path entirely!
fn stub_deserialize<T: kani::Arbitrary>(_data: &[u8]) -> Result<T> {
    Ok(kani::any())  // UNSOUND: real function can return Err
}
```

**SOUND STUB:**
```rust
fn stub_deserialize<T: kani::Arbitrary>(_data: &[u8]) -> Result<T> {
    if kani::any() { Ok(kani::any()) } else { Err(Error::InvalidData) }
}
```

**Rule:** The stub must be an over-approximation of the original — every value the original can produce, the stub must also be able to produce.

---

## Solver Selection

The SAT solver choice affects verification time. The default solver is **CaDiCaL**.

Supported solvers: `cadical` (default), `kissat`, `minisat`, `z3`, `bitwuzla`, `cvc5`.

```rust
#[kani::proof]
#[kani::solver(kissat)]     // Try if default CaDiCaL is slow on this harness
fn my_harness() { ... }

#[kani::proof]
#[kani::solver(minisat)]    // Legacy solver
fn my_harness_2() { ... }

#[kani::proof]
#[kani::solver(bin="cryptominisat5")]  // Custom solver binary
fn my_harness_3() { ... }
```

**Note:** CaDiCaL became the default solver. The s2n-quic project saw an 85% reduction in verification runtime when switching from MiniSat to CaDiCaL. Since CaDiCaL is now the default, you get this benefit automatically.

**Recommendation:** Use the default (CaDiCaL) unless a specific harness is slow — then try `kissat` or `minisat` as alternatives.

---

## Coverage with kani::cover!()

`kani::cover!()` checks if a condition CAN be satisfied — the inverse of assertions.

### Prevent Vacuous Proofs

```rust
#[kani::proof]
fn deposit_preserves_conservation() {
    let amount: u128 = kani::any();
    kani::assume(amount > 0 && amount < 5_000);

    let result = engine.deposit(amount);

    kani::assert(canonical_inv(&engine), "INV preserved");

    // Verify the proof actually exercises the deposit path
    kani::cover!(result.is_ok());   // Must be SATISFIED
    kani::cover!(result.is_err());  // Must be SATISFIED (if error path exists)
}
```

If `kani::cover!()` returns **UNSATISFIABLE**, your `kani::assume()` constraints are too restrictive or contradictory — the proof is vacuous.

### Detect Dead Code

```rust
match addr {
    IpAddr::V4(v4) => handle_v4(v4),
    IpAddr::V6(v6) => {
        if v6 == Ipv6Addr::LOCALHOST {
            kani::cover!();  // UNSATISFIABLE = this code is unreachable
        }
    }
}
```

### Validate Input Coverage

```rust
fn any_slice(arr: &[i32]) -> &[i32] {
    let start: usize = kani::any();
    let end: usize = kani::any();
    kani::assume(end <= arr.len());  // Note: <= not <
    kani::assume(start <= end);

    let slice = &arr[start..end];

    kani::cover!(slice.is_empty());           // Can we get empty slices?
    kani::cover!(slice.len() == arr.len());   // Can we get the full array?

    slice
}
```

**Pitfall:** Using `end < arr.len()` instead of `end <= arr.len()` prevents testing the last element — `kani::cover!()` would catch this.

---

## Concrete Playback

> **Note:** Concrete playback is EXPERIMENTAL. You must pass `-Z concrete-playback` to `cargo kani`.

When Kani finds a FAILURE, extract concrete values that reproduce the bug.

### Print Mode
```bash
cargo kani -Z concrete-playback --harness my_harness --concrete-playback=print
```
Output: concrete values as byte arrays that can be used in a unit test.

### Inplace Mode
```bash
cargo kani -Z concrete-playback --harness my_harness --concrete-playback=inplace
```
Inserts a `#[test]` function directly into your source code with the counterexample values. You can then debug it with standard Rust tooling, breakpoints, and println.

### Example Generated Test
```rust
#[test]
fn kani_concrete_playback_my_harness() {
    let a: i32 = 2147483647;  // i32::MAX — the counterexample
    let b: i32 = 1;
    let result = integer_average(a, b);
    // This will panic with overflow, reproducing the Kani FAILURE
}
```

---

## Partitioned Verification

For large input spaces (especially multiplication), the SAT solver can time out. Split verification into partitions.

### When to Partition
- Multiplication of large integers (BDD representation is exponential — Bryant 1986)
- Operations with i128/u128 inputs
- Any harness that times out with full `kani::any()` ranges

### Pattern
```rust
macro_rules! generate_partitioned_harness {
    ($name:ident, $min:expr, $max:expr) => {
        #[kani::proof]
        #[kani::solver(cadical)]
        fn $name() {
            let a: u128 = kani::any();
            let b: u128 = kani::any();
            kani::assume(a >= $min && a <= $max);
            kani::assume(b >= $min && b <= $max);
            let _ = checked_multiply(a, b);
        }
    }
}

generate_partitioned_harness!(near_zero, 0u128, 1000u128);
generate_partitioned_harness!(near_max, u128::MAX - 1000, u128::MAX);
generate_partitioned_harness!(mid_range, u128::MAX / 4, u128::MAX / 2);
generate_partitioned_harness!(boundary, u64::MAX as u128 - 100, u64::MAX as u128 + 100);
```

### Critical Ranges to Cover
- Near zero (underflow detection)
- Maximum/minimum boundary values
- Halfway points toward extremes
- Type boundary crossings (e.g., around u64::MAX for u128 operations)

---

## Bolero Integration (Dual-Mode Harnesses)

Write one harness that works as both a fuzz test and a formal proof.

```rust
#[test]
#[cfg_attr(kani, kani::proof, kani::solver(kissat))]
fn verify_packet_decode() {
    bolero::check!()
        .with_type::<(u64, u32)>()
        .cloned()
        .for_each(|(largest_pn, truncated_pn)| {
            let rfc_value = rfc_decoder(largest_pn, truncated_pn);
            let actual_value = decode_packet_number(largest_pn, truncated_pn);
            assert_eq!(actual_value, rfc_value);
        });
}
```

**Run modes:**
```bash
cargo test                                        # Regular unit test
cargo bolero test verify_packet_decode            # Fuzz test
cargo bolero test verify_packet_decode --engine kani  # Formal proof
```

**Result:** s2n-quic caught a packet number decoding bug in 2.9 seconds with Kani that 16M+ fuzz iterations missed.

---

## CI Integration

### GitHub Actions

```yaml
name: Kani Verification
on: [pull_request, push]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: model-checking/kani-github-action@v1
```

### Best Practices
- Run lightweight proofs with unit tests on every PR
- Schedule compute-intensive verification nightly
- Block merge on critical verification failures
- "The sooner verification runs, the better" — early feedback catches bugs cheaply

---

## Loop Unwinding

`#[kani::unwind(N)]` bounds how many times Kani unrolls loops. Set N = max possible iterations + 1.

```rust
#[kani::proof]
#[kani::unwind(33)]  // Max 32 iterations + 1 for the exit check
fn verify_buffer_scan() {
    const MAX_SIZE: usize = 32;
    let buffer: [u8; MAX_SIZE] = kani::any();
    let slice = kani::slice::any_slice_of_array(&buffer);

    let result = scan_buffer(slice);
    assert!(result.is_valid());
}
```

**If you see "unwinding assertion failed":** increase the unwind bound. If the loop is truly unbounded, add `kani::assume()` constraints or use function contracts with `#[kani::stub_verified]`.

---

## Arbitrary Trait for Custom Types

For types where all fields implement `Arbitrary`, use the derive macro:

```rust
#[cfg_attr(kani, derive(kani::Arbitrary))]
struct MyStruct {
    field_a: u64,
    field_b: bool,
}
```

For types that need custom symbolic generation, implement the trait manually:

```rust
#[cfg(kani)]
impl kani::Arbitrary for Duration {
    fn any() -> Self {
        let centuries: i16 = kani::any();
        let nanoseconds: u64 = kani::any();
        Duration::from_parts(centuries, nanoseconds)
    }
}

#[cfg(kani)]
impl kani::Arbitrary for TokenBucket {
    fn any() -> Self {
        TokenBucket {
            budget: kani::any(),
            max_budget: kani::any(),
            last_replenish: kani::any(),
            rate_per_second: kani::any(),
        }
    }
}
```

Then use directly: `let bucket: TokenBucket = kani::any();`

This is essential for inductive proofs (P10) where you need fully symbolic state.
