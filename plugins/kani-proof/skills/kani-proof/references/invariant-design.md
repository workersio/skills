# Designing Layered Invariants

How to design the invariant structure that makes formal verification tractable for stateful programs. Examples use DeFi (risk engine) as the primary domain, but the methodology applies to any program with mutable state and conservation properties.

## Contents
- [Why Layered Invariants](#why-layered-invariants)
- [The Five Layers](#the-five-layers) — structural, aggregates, accounting, mode, per-entity
- [Composing canonical_inv()](#composing-canonical_inv)
- [Performance-Aware Invariant Tiers](#performance-aware-invariant-tiers) — lightweight, targeted, comprehensive
- [Delta Properties vs. Loops](#delta-properties-vs-loops)
- [Cone of Influence Analysis](#cone-of-influence-analysis)
- [Representation Invariant Pattern](#representation-invariant-pattern)
- [Common Mistakes](#common-invariant-design-mistakes)

---

## Why Layered Invariants

A **monolithic invariant** that checks everything at once causes solver explosion — Kani spends exponential time exploring the combined constraint space.

**Decomposing into layers** lets each proof assume only the layers it needs, reducing solver burden dramatically. A deposit proof doesn't need to re-verify freelist acyclicity — it assumes structural integrity and only proves accounting preservation.

---

## The Five Layers

### Layer 1: Structural Integrity

Data structure consistency — the container itself is well-formed, independent of the values stored.

**General example: slot allocator**
```rust
fn inv_structural(state: &ProgramState) -> bool {
    // S0: num_used within bounds
    if state.num_used as usize > MAX_ITEMS { return false; }

    // S1: free_head is valid (sentinel or within bounds)
    if state.free_head != u16::MAX && (state.free_head as usize) >= MAX_ITEMS {
        return false;
    }

    // S2: Freelist acyclicity — bounded walk with visited array
    {
        let mut visited = [false; MAX_ITEMS];
        let mut cursor = state.free_head;
        let mut count: usize = 0;
        while cursor != u16::MAX {
            let idx = cursor as usize;
            if idx >= MAX_ITEMS { return false; }
            if visited[idx] { return false; }        // cycle detected
            if state.is_used(idx) { return false; }  // free node in used set
            visited[idx] = true;
            count += 1;
            if count > MAX_ITEMS { return false; }
            cursor = state.slots[idx].next_free;
        }
    }

    true
}
```

**Example: DeFi risk engine**
```rust
fn inv_structural(engine: &RiskEngine) -> bool {
    // S0: Configuration matches compile-time constant
    if engine.params.max_accounts != MAX_ACCOUNTS { return false; }

    // S1: num_used within bounds
    if engine.num_used_accounts as usize > MAX_ACCOUNTS { return false; }

    // S2: free_head is valid (sentinel or within bounds)
    if engine.free_head != u16::MAX && (engine.free_head as usize) >= MAX_ACCOUNTS {
        return false;
    }

    // S3: Freelist acyclicity — bounded walk with visited array.
    // This is CRITICAL: a cycle in the freelist causes infinite loops in add_user/close_account.
    // Walk the freelist, tracking visited nodes. If we revisit one, there's a cycle.
    {
        let mut visited = [false; MAX_ACCOUNTS];
        let mut cursor = engine.free_head;
        let mut count: usize = 0;
        while cursor != u16::MAX {
            let idx = cursor as usize;
            if idx >= MAX_ACCOUNTS { return false; }   // out of bounds
            if visited[idx] { return false; }           // cycle detected
            if engine.is_used(idx) { return false; }    // free node in used set = corruption
            visited[idx] = true;
            count += 1;
            if count > MAX_ACCOUNTS { return false; }   // safety: more nodes than slots
            cursor = engine.accounts[idx].next_free;
        }
        // Optional: count + num_used should equal MAX_ACCOUNTS
        // (every slot is either used or on the freelist)
    }

    // S4: Crank cursors within bounds (ALL of them, including liq_cursor)
    if engine.crank_cursor as usize >= MAX_ACCOUNTS { return false; }
    if engine.gc_cursor as usize >= MAX_ACCOUNTS { return false; }
    if engine.liq_cursor as usize >= MAX_ACCOUNTS { return false; }

    true
}
```

> **IMPORTANT:** Do NOT replace the freelist walk with a placeholder like `freelist_is_valid(engine)`. The bounded walk with visited array IS the implementation. The reference uses exactly this pattern — walking with a `[bool; MAX_ACCOUNTS]` visited set and checking for cycles, out-of-bounds, and used-set overlap.

**When to assume:** Almost always. Every proof should assume structural integrity.

### Layer 2: Aggregate Coherence

Cached O(1) aggregates match the entity-level sums they represent.

**General example: slot allocator**
```rust
fn inv_aggregates(state: &ProgramState) -> bool {
    let mut sum_weight: u128 = 0;
    for idx in 0..MAX_ITEMS {
        if state.is_used(idx) {
            sum_weight += state.slots[idx].weight;
        }
    }
    state.total_weight == sum_weight
}
```

**Example: DeFi risk engine**
```rust
fn inv_aggregates(engine: &RiskEngine) -> bool {
    let mut sum_capital: u128 = 0;
    let mut sum_pnl_pos: u128 = 0;
    let mut sum_abs_pos: u128 = 0;

    for idx in 0..MAX_ACCOUNTS {
        if engine.is_used(idx) {
            let acct = &engine.accounts[idx];
            sum_capital += acct.capital.get();
            if acct.pnl.get() > 0 {
                sum_pnl_pos += acct.pnl.get() as u128;
            }
            sum_abs_pos += abs_i128_to_u128(acct.position_size.get());
        }
    }

    engine.c_tot.get() == sum_capital
        && engine.pnl_pos_tot.get() == sum_pnl_pos
        && engine.total_open_interest.get() == sum_abs_pos
}
```

**When to assume:** Proofs that depend on aggregate values (conservation, total supply).
**When to prove:** Any operation that modifies individual accounts should prove aggregates are updated correctly.

### Layer 3: Accounting / Conservation

The core conservation invariant — quantities are preserved across operations.

**General example: slot allocator**
```rust
fn inv_accounting(state: &ProgramState) -> bool {
    // Every slot is either used or on the freelist
    state.num_used as usize + state.num_free as usize == MAX_ITEMS
}
```

**Example: DeFi risk engine**
```rust
fn inv_accounting(engine: &RiskEngine) -> bool {
    // Primary conservation: vault >= total_capital + insurance
    let (solvent, _deficit) = RiskEngine::signed_residual(
        engine.vault.get(),
        engine.c_tot.get(),
        engine.insurance_fund.balance.get(),
    );
    solvent
}
```

**Common conservation invariants:**
- `allocated + free == total_capacity`
- `sum(weights) == total_weight`
- `parent.children_count == children.len()`
- `vault_balance >= sum(user_deposits) + protocol_fees`
- `total_supply == sum(all_token_balances)`
- `total_staked + total_unstaked == total_tokens`
- `sum(long_positions) == sum(short_positions)` (for perpetuals)

### Layer 4: Mode / Configuration

Runtime parameters are within valid ranges. State machine is in a valid mode.

**General example: slot allocator**
```rust
fn inv_mode(state: &ProgramState) -> bool {
    state.max_capacity > 0
        && state.max_capacity <= MAX_ITEMS
        && matches!(state.status, Status::Active | Status::Paused | Status::Closed)
}
```

**Example: DeFi risk engine**
```rust
fn inv_mode(engine: &RiskEngine) -> bool {
    engine.params.maintenance_margin_bps > 0
        && engine.params.maintenance_margin_bps < 10_000
        && engine.params.liquidation_fee_bps <= engine.params.maintenance_margin_bps
        && engine.params.max_leverage > 0
}
```

### Layer 5: Per-Entity

Individual entity constraints that must hold for every active entity.

**General example: slot allocator**
```rust
fn inv_per_entity(state: &ProgramState) -> bool {
    for idx in 0..MAX_ITEMS {
        if state.is_used(idx) {
            let slot = &state.slots[idx];

            // PE1: weight is non-zero for used slots
            if slot.weight == 0 { return false; }

            // PE2: no sentinel values in fields that get negated
            if slot.delta == i64::MIN { return false; }
        }
    }
    true
}
```

**Example: DeFi risk engine**
```rust
fn inv_per_entity(engine: &RiskEngine) -> bool {
    for idx in 0..MAX_ACCOUNTS {
        if engine.is_used(idx) {
            let acct = &engine.accounts[idx];

            // PA1: reserved_pnl cannot exceed max(pnl, 0)
            // You can't reserve more PnL than your positive PnL balance.
            // If PnL is negative, reserved must be 0.
            let max_reservable = if acct.pnl.get() > 0 { acct.pnl.get() as u128 } else { 0 };
            if acct.reserved_pnl.get() > max_reservable { return false; }

            // PA2: No sentinel values in fields that get abs'd/negated
            // i128::MIN cannot be negated without overflow
            if acct.pnl.get() == i128::MIN { return false; }
            if acct.position_size.get() == i128::MIN { return false; }

            // PA3: Warmup slope is not the sentinel value
            // u128::MAX is used as a sentinel for "uninitialized"
            if acct.warmup_slope_per_step.get() == u128::MAX { return false; }

            // PA4: Entry price sanity (0 is valid for flat positions)
            // If position is non-zero, entry price must be positive
            if acct.position_size.get() != 0 && acct.entry_price == 0 { return false; }
        }
    }
    true
}
```

> **IMPORTANT:** PA1 is the most commonly missed check. The reference implementation explicitly bounds `reserved_pnl` by `max(pnl, 0)`. Without PA1, proofs cannot detect PnL reservation bugs where more PnL is claimed than exists.

---

## Composing canonical_inv()

**General example: slot allocator**
```rust
fn canonical_inv(state: &ProgramState) -> bool {
    inv_structural(state)     // Layer 1: data structure well-formedness
        && inv_aggregates(state)  // Layer 2: cached totals match sums
        && inv_accounting(state)  // Layer 3: allocated + free == capacity
        && inv_mode(state)        // Layer 4: parameter validity
        && inv_per_entity(state)  // Layer 5: per-entity constraints
}
```

**Example: DeFi risk engine**
```rust
fn canonical_inv(engine: &RiskEngine) -> bool {
    inv_structural(engine)      // Layer 1: data structure well-formedness
        && inv_aggregates(engine)   // Layer 2: cached totals match sums
        && inv_accounting(engine)   // Layer 3: vault >= c_tot + insurance
        && inv_mode(engine)         // Layer 4: parameter validity
        && inv_per_entity(engine)   // Layer 5: per-entity constraints
}
```

**ALL 5 layers are mandatory.** The most commonly forgotten is `inv_mode()` — without it, proofs may assume invalid parameters (zero margin, zero leverage) which produces vacuous results.

For inductive proofs (P10a), work with raw primitives instead — see proof-patterns.md P10a.

---

## Performance-Aware Invariant Tiers

Don't use `canonical_inv()` in every proof. Different proof types need different invariant depths. Using the comprehensive invariant everywhere causes solver timeouts.

### Three Tiers

| Tier | Function | Cost | Use In |
|---|---|---|---|
| **Lightweight** | `valid_state()` | Cheap | Fast proofs, setup validation, frame proofs |
| **Targeted** | `conservation_fast_no_funding()` | Cheap | Conservation-specific proofs (no open positions) |
| **Comprehensive** | `canonical_inv()` | Expensive | Full INV preservation proofs |

### Lightweight: `valid_state()`

Basic structural bounds and per-entity checks. Intentionally omits expensive operations:
- No aggregate recomputation (sum over all accounts)
- No matcher array memcmp
- No complete freelist walk with cycle detection
- No N1 boundary conditions (test those in dedicated proofs)

```rust
fn valid_state(engine: &RiskEngine) -> bool {
    engine.num_used_accounts <= MAX_ACCOUNTS as u16
        && engine.crank_cursor < MAX_ACCOUNTS as u16
        // ... minimal structural checks
        // Intentionally omits: aggregate sums, N1 boundary, matcher checks
}
```

### Targeted: `conservation_fast_no_funding()`

Checks ONLY the core conservation inequality. Lightweight, focused, fast.

```rust
fn conservation_fast_no_funding(engine: &RiskEngine) -> bool {
    let (solvent, _) = RiskEngine::signed_residual(
        engine.vault.get(),
        engine.c_tot.get(),
        engine.insurance_fund.balance.get(),
    );
    solvent  // vault >= c_tot + insurance
}
```

### Which Tier to Use

| Proof Type | Invariant Tier | Why |
|---|---|---|
| `fast_*` proofs | `valid_state()` + targeted check | Fast feedback, seconds per proof |
| `fast_i2_*` conservation | `conservation_fast_no_funding()` | Only checks what matters |
| `fast_frame_*` isolation | `valid_state()` only | Frame proofs check field equality, not invariant |
| Full INV preservation | `canonical_inv()` | Comprehensive but slower |
| Mathematical inductive (P10a) | None — uses raw primitives | No struct, no invariant function needed |

---

## Delta Properties vs. Loops

### The Problem

Verifying `inv_aggregates()` requires a loop over all accounts. With `#[kani::unwind(33)]`, Kani unrolls this loop 33 times, creating 33x the constraints. For inductive proofs, this defeats the purpose.

### The Solution: Delta Assertions

Instead of re-summing, prove that the aggregate was updated correctly:

```rust
// LOOP-BASED (slow, bounded):
kani::assert(inv_aggregates(&engine), "aggregates correct");

// DELTA-BASED (fast, inductive):
let old_capital = engine.accounts[idx].capital.get();
engine.deposit(idx, amount);
let new_capital = engine.accounts[idx].capital.get();

kani::assert(
    engine.c_tot.get() == c_tot_before + (new_capital - old_capital),
    "c_tot delta correct"
);
```

**Why this works:** If the aggregate was correct before (assumed via `kani::assume(inv_aggregates)`) and the delta is correct, then the aggregate is correct after. No loop needed.

**This is the key to upgrading from STRONG to INDUCTIVE proofs.**

---

## Cone of Influence Analysis

**Principle:** Only constrain the fields a function actually reads and writes. Leave everything else fully symbolic.

### Example

If `deposit()` only touches:
- Reads: `accounts[idx].capital`, `vault`, `c_tot`
- Writes: `accounts[idx].capital`, `vault`, `c_tot`, `accounts[idx].warmup_slope_per_step`

Then your proof should:
- `kani::assume()` constraints on capital, vault, c_tot (the reads)
- Assert properties on capital, vault, c_tot, warmup_slope (the writes)
- Leave all other fields (pnl, position_size, funding_index, etc.) fully symbolic

This maximizes generality — the proof covers all possible values of the unconstrained fields.

---

## Representation Invariant Pattern

A general pattern for any Rust type, not just DeFi programs (from Kani blog posts).

### Define the Invariant

```rust
impl MyType {
    fn is_valid(&self) -> bool {
        self.len <= self.cap
            && is_power_of_two(self.cap)
            && self.head < self.cap
            && self.tail < self.cap
    }
}
```

### Prove Operations Preserve It

```rust
#[kani::proof]
fn push_preserves_invariant() {
    let mut obj: MyType = kani::any();
    kani::assume(obj.is_valid());       // Start valid

    let value: u64 = kani::any();
    obj.push(value);

    assert!(obj.is_valid());            // Still valid after
}
```

### Prove Constructors Establish It

```rust
#[kani::proof]
fn new_creates_valid_instance() {
    let cap: usize = kani::any();
    kani::assume(cap > 0 && cap <= 1024);

    let obj = MyType::new(cap);

    assert!(obj.is_valid());
}
```

**Together, these prove:** every reachable instance satisfies the invariant (by induction on the sequence of operations).

---

## Common Invariant Design Mistakes

1. **Invariant too strong** — includes properties that aren't preserved by all operations. The proof fails because the invariant is wrong, not the code.

2. **Invariant too weak** — doesn't capture the property you actually care about. The proof passes but doesn't prove what you think.

3. **Invariant has loops** — loops in the invariant function require unwind bounds, limiting the proof to bounded sizes. Use delta properties instead.

4. **Forgetting to separate layers** — a single `is_valid()` that checks everything means every proof pays the cost of every check. Separate into layers.

5. **Circular dependencies** — layer A assumes layer B, which assumes layer A. Break the cycle by ordering layers: structural → aggregates → accounting → per-entity.
