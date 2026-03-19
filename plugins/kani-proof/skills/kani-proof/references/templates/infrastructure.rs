// Shared Infrastructure for Kani Proofs
//
// Reusable macros and helpers needed across multiple proof patterns.
// Copy the pieces you need into your proof module and adapt types to your codebase.

#[cfg(kani)]
mod kani_proofs {
    use super::*;

    // ── Result-Forcing Macros ──────────────────────────────────────────
    //
    // Critical for preventing vacuous proofs. Use assert_ok! in success-path
    // proofs, assert_err! in error-path proofs.

    /// Forces the Ok path — fails the proof if the operation returns Err.
    /// Use this instead of `let _ = ...` or `if result.is_ok() { ... }`.
    macro_rules! assert_ok {
        ($result:expr, $msg:expr) => {
            match $result {
                Ok(v) => v,
                Err(_) => {
                    kani::assert(false, $msg);
                    unreachable!()
                }
            }
        };
    }

    /// Forces the Err path — fails the proof if the operation returns Ok.
    macro_rules! assert_err {
        ($result:expr, $msg:expr) => {
            match $result {
                Err(e) => e,
                Ok(_) => {
                    kani::assert(false, $msg);
                    unreachable!()
                }
            }
        };
    }

    // ── Snapshot Types ─────────────────────────────────────────────────
    //
    // For frame and error-path proofs: snapshot state before the operation
    // and compare after. Include ALL mutable fields — bugs hide in fields
    // you didn't think to check.

    // TODO: Replace with your account/entity type's fields
    struct AccountSnapshot {
        balance: u128,
        // TODO: Add all mutable fields from your account type
    }

    // TODO: Replace with your account/entity type
    fn snapshot_account(account: &Account) -> AccountSnapshot {
        AccountSnapshot {
            balance: account.balance,
            // TODO: Snapshot all fields
        }
    }

    fn assert_snapshot_eq(before: &AccountSnapshot, after: &AccountSnapshot, msg: &str) {
        kani::assert(before.balance == after.balance, msg);
        // TODO: Compare all fields
    }

    // ── Populated State Constructor ────────────────────────────────────
    //
    // Fresh/empty state makes invariants trivially true. Always construct
    // state with realistic complexity.

    // TODO: Adapt to your codebase's state structure
    fn create_populated_state() -> ProgramState {
        let mut state = ProgramState::new(test_params());

        // Add multiple active entities (at least 2 for isolation proofs)
        state.add_entity(0).unwrap();
        state.add_entity(1).unwrap();

        // Set symbolic values — NOT concrete ones
        let balance_a: u128 = kani::any();
        kani::assume(balance_a >= 100 && balance_a <= 10_000);
        state.entities[0].balance = balance_a;

        let balance_b: u128 = kani::any();
        kani::assume(balance_b >= 100 && balance_b <= 10_000);
        state.entities[1].balance = balance_b;

        // Recompute any aggregate/derived fields
        state.recompute_aggregates();

        state
    }

    // ── Integer Safety Helpers ─────────────────────────────────────────

    /// Absolute value of i128 as u128 (handles i128::MIN safely)
    fn abs_i128_to_u128(v: i128) -> u128 {
        if v == i128::MIN {
            (i128::MAX as u128) + 1
        } else if v < 0 {
            (-v) as u128
        } else {
            v as u128
        }
    }
}
