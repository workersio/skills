# Solana Audit Checklist

Per-instruction validation checklist + syntactic grep commands. Apply to every instruction in the program under review.

---

## Syntactic Scan Commands

Run these grep commands against the program source to build the initial candidate list. Each hit maps to a vulnerability ID for further investigation.

### Authentication & Authorization (A-1 to A-5)
```bash
# A-1: Missing signer check — AccountInfo used as authority without Signer type
grep -rn 'AccountInfo' --include='*.rs' | grep -v 'Signer'
grep -rn 'is_signer' --include='*.rs'

# A-2: Missing owner check — deserialization without owner validation
grep -rn 'try_from_slice\|try_deserialize\|from_account_info' --include='*.rs'
grep -rn '\.owner' --include='*.rs'

# A-3: Missing authority validation — signer not compared to stored key
grep -rn 'authority\|admin\|owner' --include='*.rs'
grep -rn 'has_one' --include='*.rs'

# A-4/A-5: Privilege escalation / access control
grep -rn 'set_authority\|update_authority\|set_admin' --include='*.rs'
grep -rn 'init\b' --include='*.rs' | grep -v 'init_if_needed'
```

### Account & State Management (S-1 to S-8)
```bash
# S-1: Uninitialized account usage
grep -rn 'AccountInfo' --include='*.rs' | grep -v 'Account<'
grep -rn 'is_initialized\|discriminator' --include='*.rs'

# S-2: Duplicate mutable accounts
grep -rn 'fn .*source.*dest\|fn .*from.*to' --include='*.rs'

# S-3: PDA seed collision — seeds without user-specific component
grep -rn 'seeds\s*=' --include='*.rs'
grep -rn 'find_program_address' --include='*.rs'

# S-4: Bump canonicalization
grep -rn 'create_program_address' --include='*.rs'
grep -rn 'bump' --include='*.rs'

# S-5: Type cosplay — manual deserialization without discriminator
grep -rn 'try_from_slice\|deserialize' --include='*.rs' | grep -v 'Account<'

# S-6: Account closure — missing data zeroing
grep -rn 'close\|lamports.*borrow_mut\|\.fill(0)' --include='*.rs'

# S-7: Reinitialization
grep -rn 'init_if_needed' --include='*.rs'
grep -rn 'is_initialized\s*=\s*true\|set_initialized' --include='*.rs'

# S-8: Rent exemption
grep -rn 'rent\|is_exempt\|minimum_balance' --include='*.rs'
```

### Cross-Program Invocation (C-1 to C-3)
```bash
# C-1: Arbitrary CPI target
grep -rn 'invoke\|invoke_signed' --include='*.rs'
grep -rn 'program_id.*key\|program\.key' --include='*.rs'

# C-2: CPI signer escalation
grep -rn 'invoke_signed' --include='*.rs'
grep -rn 'signer_seeds\|signers_seeds' --include='*.rs'

# C-3: Unvalidated remaining_accounts
grep -rn 'remaining_accounts' --include='*.rs'
```

### Arithmetic & Math (M-1 to M-4)
```bash
# M-1: Integer overflow/underflow — raw arithmetic without checked ops
grep -rn '[^a-z_][\+\-\*][^>]' --include='*.rs' | grep -v 'checked_\|saturating_\|wrapping_\|\/\/'

# M-2: Division precision loss
grep -rn '[^/]\/[^/\*]' --include='*.rs' | grep -v 'checked_div'

# M-3: Unsafe casting
grep -rn 'as u64\|as u32\|as u128\|as i64\|as i128\|as u16\|as u8' --include='*.rs'

# M-4: Rounding errors
grep -rn 'total_shares\|total_supply\|exchange_rate\|price_per_share' --include='*.rs'
```

### Logic & Economic (L-1 to L-4)
```bash
# L-1: Oracle manipulation
grep -rn 'oracle\|price_feed\|pyth\|switchboard\|chainlink' --include='*.rs'
grep -rn 'get_price\|price_account\|twap\|staleness' --include='*.rs'

# L-2: Missing slippage check
grep -rn 'swap\|trade\|exchange' --include='*.rs'
grep -rn 'min_amount_out\|max_amount_in\|slippage' --include='*.rs'

# L-3: Flash loan vulnerability
grep -rn 'flash\|borrow.*repay\|clock\|slot' --include='*.rs'

# L-4: Front-running
grep -rn 'commit.*reveal\|deadline\|expiry' --include='*.rs'
```

### Token-Specific (T-1 to T-3)
```bash
# T-1: SPL token account validation
grep -rn 'TokenAccount\|token::mint\|token::authority' --include='*.rs'
grep -rn '\.mint\b' --include='*.rs'

# T-2: Token-2022 extensions
grep -rn 'token_2022\|token-2022\|spl_token_2022\|transfer_fee\|transfer_hook' --include='*.rs'

# T-3: Token freeze check
grep -rn 'is_frozen\|freeze_authority\|FreezeAccount' --include='*.rs'
```

---

## Per-Instruction Validation Checklist

### Account Validation

For **every account** accepted by an instruction, verify:

- [ ] **Owner check** — Is the account's owner program verified? (Native: `account.owner == &expected_program_id`; Anchor: `Account<'info, T>` auto-checks)
- [ ] **Signer check** — If the account authorizes an action, is it verified as a signer?
- [ ] **Writable check** — If the account is modified, is it marked mutable? Can a readonly account be passed where mutable is expected?
- [ ] **Initialization check** — Is the account confirmed to be initialized before reading its data?
- [ ] **Type discriminator** — Does the account include and verify a type discriminator? (Anchor 8-byte discriminator is automatic for `Account<>`)
- [ ] **PDA derivation** — If a PDA, are the seeds and bump verified? Is the bump canonical?
- [ ] **Key comparison** — If the account should match a stored pubkey (e.g., vault authority), is `account.key == stored_key` checked?

### Instruction Logic

For **every instruction handler**, verify:

- [ ] **Arithmetic safety** — All math uses `checked_*` or `saturating_*` operations. No raw `+`, `-`, `*`, `/` on unbounded values.
- [ ] **Casting safety** — All `as` type casts are safe (value fits in target type) or use `try_into()`
- [ ] **State transitions** — Are valid state transitions enforced? Can an account skip states?
- [ ] **Reentrancy** — After a CPI call, is account state re-read/re-validated? (CPI can modify accounts passed to it)
- [ ] **Duplicate accounts** — If two accounts of the same type are accepted, is `a.key != b.key` enforced?
- [ ] **Return value handling** — Are CPI return values and error codes properly checked?
- [ ] **Boundary conditions** — What happens with amount=0, max values, empty collections?

### CPI Validation

For **every CPI call** (`invoke` / `invoke_signed`):

- [ ] **Target validation** — Is the CPI target program hardcoded or validated against expected program ID?
- [ ] **Signer scope** — Does `invoke_signed` only grant authority for the intended operation?
- [ ] **Account passthrough** — Are accounts passed to CPI properly validated before the call?
- [ ] **Post-CPI state** — After CPI returns, is local state re-loaded? (CPI may have mutated shared accounts)

### Token Operations

For **every token transfer, mint, or burn**:

- [ ] **Mint validation** — Token accounts verified against expected mint
- [ ] **Authority validation** — Token authority is the expected PDA or signer
- [ ] **Amount validation** — Transfer amount is computed safely (no overflow, correct decimals)
- [ ] **Balance sufficiency** — Sufficient balance exists before transfer (SPL will reject, but early check aids error messages)
- [ ] **Token-2022 awareness** — If supporting Token-2022, handle transfer fees, hooks, permanent delegates

### Program-Level

After reviewing all instructions:

- [ ] **Upgrade authority** — Is the upgrade authority appropriately managed (multisig, governance, or revoked)?
- [ ] **Initialization completeness** — Can the program be used in an uninitialized or partially initialized state?
- [ ] **Instruction ordering** — Can instructions be called in an unexpected order to achieve unintended state?
- [ ] **Flash loan resilience** — Can program state be manipulated and restored within a single transaction?
- [ ] **MEV / front-running** — Are economic operations susceptible to sandwich attacks?
- [ ] **Event emission** — Are critical state changes logged for off-chain monitoring?
- [ ] **Error handling** — Do error codes provide useful information without leaking sensitive state?

---

## Severity Calibration

| Severity | Criteria | Examples |
|---|---|---|
| **CRITICAL** | Direct fund loss, exploitable by anyone, no user action needed | A-1 (missing signer), A-4 (privilege escalation), C-1 (arbitrary CPI), L-1 (oracle manipulation) |
| **HIGH** | Fund loss with preconditions, state corruption, authorization bypass | A-2 (missing owner), A-3 (authority validation), S-2 (duplicate accounts), M-1 (overflow), L-2 (slippage) |
| **MEDIUM** | Limited impact, requires specific conditions, economic rather than direct loss | S-4 (bump canonicalization), M-2 (precision loss), M-3 (unsafe casting), L-4 (front-running) |
| **LOW** | Minimal impact, operational issues, unlikely exploitation | S-8 (rent exemption), T-3 (freeze check), R-2 (rent) |
| **INFORMATIONAL** | Best practice violations, no direct security impact | R-3 (unverified build), missing events, code quality |

### Cross-References

- For detailed per-vulnerability analysis: see individual files in `references/` (e.g., [missing-signer-check.md](missing-signer-check.md))
- For real-world exploit examples: see [exploit-case-studies.md](exploit-case-studies.md)
- For Anchor-specific patterns: see [anchor-specific.md](anchor-specific.md)
- For quick keyword lookup: see [CHEATSHEET.md](CHEATSHEET.md)
