// P1: Conservation Proof Template
//
// When to use: Any operation that moves, creates, or destroys quantities —
// deposits, withdrawals, transfers, trades, fee collection.
//
// Property: An accounting equation is preserved by the operation.
//
// See also: infrastructure.rs for assert_ok!, snapshot types, and
// create_populated_state().

#[cfg(kani)]
mod kani_proofs {
    use super::*;

    // ── Template A: Forces Success, Checks Deltas (preferred) ──────────

    #[kani::proof]
    // #[kani::unwind(N)]  — add only after unwinding assertion error
    // #[kani::solver(kissat)]  — add only after timeout with default solver
    fn operation_preserves_conservation() {
        let mut state = create_populated_state();
        kani::assume(invariant(&state));

        let user: usize = kani::any();
        kani::assume(user < MAX_ENTITIES && state.is_active(user));
        let amount: u128 = kani::any();
        kani::assume(amount > 0 && amount < REASONABLE_BOUND);

        // Snapshot before
        let total_before = state.total_value();
        let user_balance_before = state.entities[user].balance;

        // Force success
        // TODO: Replace with your operation
        assert_ok!(state.operation(user, amount), "operation must succeed");

        // Conservation: accounting equation preserved
        // TODO: Replace with your invariant check
        kani::assert(invariant(&state), "invariant after operation");

        // Domain-specific: check the EXACT effect
        // TODO: Replace with your expected delta
        kani::assert(
            state.entities[user].balance == user_balance_before + amount,
            "balance must increase by exactly amount",
        );

        kani::cover!(true, "conservation verified");
    }

    // ── Template B: Universal (Ok or Err) ──────────────────────────────

    #[kani::proof]
    // #[kani::unwind(N)]  — add only after unwinding assertion error
    // #[kani::solver(kissat)]  — add only after timeout with default solver
    fn operation_conservation_regardless() {
        let mut state = create_populated_state();
        kani::assume(invariant(&state));

        let input = kani::any();
        kani::assume(valid_range(&input));

        // TODO: Replace with your operation
        let _result = state.operation(input);

        // INV holds regardless of success or failure
        // TODO: Replace with your invariant check
        kani::assert(invariant(&state), "invariant after operation");
    }
}
