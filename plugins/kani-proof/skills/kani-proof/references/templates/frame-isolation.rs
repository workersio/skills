// P2: Frame / Isolation Proof Template
//
// When to use: Multi-entity systems where one entity's operation must not
// affect others.
//
// Property: After operating on entity A, all other entities remain completely
// unchanged.
//
// See also: infrastructure.rs for assert_ok!, snapshot types, and
// create_populated_state().

#[cfg(kani)]
mod kani_proofs {
    use super::*;

    #[kani::proof]
    // #[kani::unwind(N)]  — add only after unwinding assertion error
    // #[kani::solver(kissat)]  — add only after timeout with default solver
    fn operation_only_mutates_target() {
        let mut state = create_populated_state();

        let target: usize = kani::any();
        let bystander: usize = kani::any();
        kani::assume(target != bystander);
        kani::assume(target < MAX_ENTITIES && state.is_active(target));
        kani::assume(bystander < MAX_ENTITIES && state.is_active(bystander));

        // Snapshot bystander — ALL fields
        // TODO: Replace with your snapshot function
        let snap_before = snapshot_account(&state.entities[bystander]);

        // Execute on target
        let amount: u128 = kani::any();
        kani::assume(amount > 0 && amount <= 5_000);
        // TODO: Replace with your operation
        assert_ok!(state.operation(target, amount), "operation must succeed");

        // Bystander completely unchanged
        let snap_after = snapshot_account(&state.entities[bystander]);
        assert_snapshot_eq(&snap_before, &snap_after, "bystander must be unchanged");

        kani::cover!(true, "isolation verified");
    }
}
