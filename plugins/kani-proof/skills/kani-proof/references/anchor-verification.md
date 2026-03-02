# Anchor Program Verification with OtterSec

[OtterSec's solana-verify](https://github.com/otter-sec/solana-verify) provides annotation-driven Kani verification for Anchor programs. Instead of hand-writing proof harnesses, you annotate your existing code and harnesses are auto-generated.

**Reference:** [Formally Verifying Solana Programs](https://osec.io/blog/2023-01-26-formally-verifying-solana-programs/)

---

## When to Use This Approach

- **Anchor programs** where you want quick instruction-level verification
- **Input validation proofs** — proving that certain inputs always succeed or always fail
- **Account invariants** — proving properties that hold across all instructions
- Complement with hand-written harnesses for system-level properties (conservation, isolation)

---

## Setup

### 1. Replace anchor-lang with onchor

> **Note:** The onchor fork is pinned to an older Anchor version (~0.26). Check compatibility with your project's Anchor version (current Anchor is 0.31+). API differences may require adjustments.

```toml
# Cargo.toml — replace this:
anchor-lang = "0.26.0"

# With this:
anchor-lang = { package = "onchor", git = "git@github.com:otter-sec/verify.git" }
```

### 2. Add verification crate

```bash
cargo add otter-solana-verify
```

### 3. Check toolchain requirements

Kani works with stable Rust (1.58+) — nightly is NOT required by Kani itself. However, the `onchor` fork may have its own toolchain requirements. Check the onchor repo for the recommended toolchain version.

```toml
# rust-toolchain.toml — only if required by onchor
[toolchain]
channel = "nightly"
```

---

## The Three Macros

### `#[succeeds_if(condition)]`

Proves that when the condition is true, the instruction ALWAYS succeeds (returns Ok).

```rust
#[succeeds_if(ctx.accounts.user.balance >= amount)]
pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
    require!(ctx.accounts.user.balance >= amount, MyError::InsufficientBalance);
    ctx.accounts.user.balance -= amount;
    Ok(())
}
```

**Auto-generated harness (simplified):**
```rust
#[kani::proof]
#[kani::unwind(100)]
fn succeeds_if_withdraw() {
    let ctx: ConcreteContext<WithdrawAccounts> = kani::any();
    let amount: u64 = kani::any();

    // Assume account invariants hold initially
    kani::assume(ctx.accounts.__pre_invariants());

    // Assume the specified precondition
    kani::assume(ctx.accounts.user.balance >= amount);

    // Execute instruction
    let result = withdraw(ctx, amount);

    // Assert it succeeds
    kani::assert(result.is_ok(), "function failed when precondition was met");
}
```

### `#[errors_if(condition)]`

Proves that when the condition is true, the instruction ALWAYS fails (returns Err).

```rust
#[errors_if(ctx.accounts.user.balance < amount)]
pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
    require!(ctx.accounts.user.balance >= amount, MyError::InsufficientBalance);
    ctx.accounts.user.balance -= amount;
    Ok(())
}
```

### `#[invariant(expression)]`

Defines a property that must ALWAYS hold on an account struct — checked before and after every instruction.

```rust
#[account]
#[invariant(self.threshold >= 1 && self.threshold <= self.members.len())]
pub struct Multisig {
    pub threshold: u8,
    pub members: Vec<Pubkey>,
}
```

**What this generates:**
```rust
impl Multisig {
    pub fn _check_invariant(&self) -> bool {
        self.threshold >= 1 && self.threshold <= self.members.len()
    }
}
```

This method is called automatically in all generated harnesses — before the instruction (via `__pre_invariants()`) and after (via `__post_invariants()`).

---

## Complete Example: Squads Multisig

```rust
use onchor::prelude::*;
use otter_solana_verify::*;

// Account with invariant
#[account]
#[invariant(!self.keys.is_empty() && self.threshold >= 1 && (self.threshold as usize) <= self.keys.len())]
pub struct Ms {
    pub threshold: u16,
    pub authority_index: u32,
    pub transaction_index: u32,
    pub keys: Vec<Pubkey>,
}

#[derive(Accounts)]
pub struct MsCreate<'info> {
    #[account(init, space = 8 + Ms::INIT_SPACE)]
    pub multisig: Account<'info, Ms>,
    #[account(mut)]
    pub creator: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[program]
pub mod squads_multisig {
    use super::*;

    // Proves: valid threshold + non-empty members → create succeeds
    #[succeeds_if(
        (threshold as usize) <= members.len()
        && threshold != 0
        && members.len() <= u16::MAX as usize
    )]
    pub fn create(
        ctx: Context<MsCreate>,
        threshold: u16,
        members: Vec<Pubkey>,
    ) -> Result<()> {
        require!(!members.is_empty(), MultisigError::EmptyMembers);
        require!(threshold >= 1, MultisigError::InvalidThreshold);
        require!(
            (threshold as usize) <= members.len(),
            MultisigError::InvalidThreshold
        );

        let multisig = &mut ctx.accounts.multisig;
        multisig.threshold = threshold;
        multisig.keys = members;
        multisig.authority_index = 0;
        multisig.transaction_index = 0;

        Ok(())
    }

    // Proves: single member remaining → remove_member fails
    #[errors_if(ctx.accounts.multisig.keys.len() <= 1)]
    // Proves: multiple members → remove_member succeeds
    #[succeeds_if(ctx.accounts.multisig.keys.len() > 1)]
    pub fn remove_member(
        ctx: Context<MsAuth>,
        member: Pubkey,
    ) -> Result<()> {
        let multisig = &mut ctx.accounts.multisig;
        require!(multisig.keys.len() > 1, MultisigError::CannotRemoveLastMember);

        multisig.keys.retain(|k| k != &member);

        // Adjust threshold if it exceeds new member count
        if (multisig.threshold as usize) > multisig.keys.len() {
            multisig.threshold = multisig.keys.len() as u16;
        }

        Ok(())
    }
}
```

### What Kani Verifies

Running `cargo kani --features kani` on this program generates and verifies:

1. **`succeeds_if_create`** — When threshold <= members.len() and threshold > 0 and members fit in u16, create returns Ok
2. **`errors_if_remove_member`** — When only 1 member remains, remove_member returns Err
3. **`succeeds_if_remove_member`** — When > 1 member, remove_member returns Ok
4. **`verify_create`** — Ms invariant (threshold >= 1, threshold <= keys.len()) holds after create
5. **`verify_remove_member`** — Ms invariant holds after remove_member

---

## How It Works Under the Hood

### ConcreteContext with kani::Arbitrary

The `onchor` fork makes Anchor's `Context` type derive `kani::Arbitrary`:

```rust
#[cfg(any(kani, feature = "kani"))]
impl<T: kani::Arbitrary> kani::Arbitrary for ConcreteContext<T> {
    fn any() -> Self {
        Self {
            program_id: kani::any(),
            accounts: kani::any(),
            remaining_accounts: Vec::from([]),
            ..
        }
    }
}
```

This lets Kani create fully symbolic contexts — exploring all possible account states.

### Pre/Post Invariant Checking

The `#[derive(Accounts)]` macro generates invariant check methods:

```rust
impl WithdrawAccounts {
    pub fn __pre_invariants(&self) -> bool {
        self.user.account._check_invariant()
    }

    pub fn __post_invariants(&self) -> bool {
        self.user.account._check_invariant()
    }
}
```

These are called in every generated harness to ensure account invariants hold before and after instruction execution.

---

## Limitations

1. **Requires forked anchor-lang** — `onchor` must be kept in sync with upstream Anchor. Version pinned to 0.26.0.

2. **Cannot verify CPI calls** — cross-program invocations involve the Solana runtime which can't be symbolically executed. Use supplementary `require!()` assertions or hand-written harnesses with stubs.

3. **Cannot verify account deserialization** — the symbolic model skips Borsh/custom deserialization. Type confusion bugs need separate analysis.

4. **Instruction-level only** — proves properties of individual instructions, not cross-instruction properties like "total supply is conserved across any sequence of instructions."

5. **Path explosion** — complex instructions with many branching account validations can cause Kani to time out. Use `#[kani::unwind()]` bounds carefully.

---

## Hand-Written vs. Auto-Generated: When to Use Which

| Property | Auto-Generated (OtterSec) | Hand-Written |
|---|---|---|
| Input validation | Yes — `succeeds_if`, `errors_if` | Overkill |
| Account invariants | Yes — `#[invariant]` | Overkill |
| Authorization checks | Yes — `errors_if(!is_authority)` | Overkill |
| Conservation of funds | No — cross-instruction | Yes — P1 pattern |
| User isolation (frame proofs) | No — requires multi-account setup | Yes — P2 pattern |
| Arithmetic safety | Partially — catches panics | Yes — P7 with partitioned ranges |
| Economic invariants | No — requires system-level reasoning | Yes — P10 inductive proofs |
| Inductive proofs | No — always uses concrete construction | Yes — fully symbolic state |

**Recommendation:** Use OtterSec for quick wins (instruction-level safety), then add hand-written harnesses for the critical financial properties that matter most.
