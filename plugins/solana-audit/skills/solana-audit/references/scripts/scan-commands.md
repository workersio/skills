# Consolidated Syntactic Scan Commands

Run all commands below against the target program directory. Collect results by category. This pre-scan replaces Pass 1 (syntactic scan) across all scanner agents, freeing them to focus on semantic analysis.

---

## Category A: Authentication & Authorization

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

## Category S: Account & State Management

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

## Category C: Cross-Program Invocation

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

## Category M: Arithmetic & Math

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

## Category L: Logic & Economic

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

## Category T: Token-Specific

```bash
# T-1: SPL token account validation
grep -rn 'TokenAccount\|token::mint\|token::authority' --include='*.rs'
grep -rn '\.mint\b' --include='*.rs'

# T-2: Token-2022 extensions
grep -rn 'token_2022\|token-2022\|spl_token_2022\|transfer_fee\|transfer_hook' --include='*.rs'

# T-3: Token freeze check
grep -rn 'is_frozen\|freeze_authority\|FreezeAccount' --include='*.rs'
```

## Category R: Runtime & Deployment

```bash
# R-1: Upgrade authority
grep -rn 'upgrade_authority\|set_authority\|BPFUpgradeableLoader' --include='*.rs'

# R-2: Rent exemption (program-level)
grep -rn 'system_instruction::create_account' --include='*.rs'

# R-3: Build verification
grep -l 'Anchor.toml' . 2>/dev/null
grep -rn 'solana-verify\|verifiable' --include='*.toml'
```

---

## Summary

After running all commands, count hits per category:

| Category | IDs | Expected Hit Types |
|----------|-----|--------------------|
| A: Auth & Authorization | A-1..A-5 | AccountInfo without Signer, missing owner checks, authority fields |
| S: Account & State | S-1..S-8 | Unvalidated deserialization, PDA seeds, init patterns, closures |
| C: CPI | C-1..C-3 | invoke/invoke_signed calls, remaining_accounts usage |
| M: Arithmetic | M-1..M-4 | Raw arithmetic ops, division, as casts, share calculations |
| L: Logic & Economic | L-1..L-4 | Oracle refs, swap/trade without slippage, flash patterns |
| T: Token | T-1..T-3 | Token account validation, Token-2022 usage, freeze checks |
| R: Runtime | R-1..R-3 | Upgrade authority, account creation, build config |

Pass these results to all scanner agents with a note: **"Pass 1 (syntactic scan) has been performed. Results below. Proceed directly to Pass 2 — Semantic Review."**
