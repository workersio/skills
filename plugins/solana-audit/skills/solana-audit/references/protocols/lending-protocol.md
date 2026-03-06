# Lending Protocol Security Patterns

Additional vulnerability checks specific to lending, borrowing, and collateral management protocols. Load this when the codebase explorer classifies the protocol type as **lending**.

---

## Lending-Specific Vulnerabilities

### Collateral Valuation Manipulation
- **Pattern:** Collateral value derived from a manipulable price source (AMM spot price, thin oracle market)
- **Check:** Is the oracle robust? TWAP vs spot? Multi-oracle? Staleness + confidence validated?
- **Attack:** Flash-loan inflate collateral value → borrow maximum → repay flash loan → walk away with borrowed funds
- **Cross-ref:** Mango Markets ($114M) — unrealized PnL counted as collateral

### Liquidation Threshold Gaming
- **Pattern:** Health factor calculation has precision issues or can be manipulated just above/below threshold
- **Check:** Is health factor computed with sufficient decimal precision? Are liquidation incentives bounded?
- **Attack:** Manipulate price to put position barely underwater → self-liquidate for the liquidation bonus → profit from the bonus exceeding the position loss
- **Grep:** `health_factor`, `collateral_ratio`, `liquidation_threshold`, `liquidation_bonus`

### Interest Rate Manipulation
- **Pattern:** Interest rate model depends on utilization ratio that can be manipulated
- **Check:** Can a large deposit/withdrawal swing the utilization ratio within a single transaction?
- **Attack:** Deposit large amount → crash utilization → borrow at low rate → withdraw deposit
- **Grep:** `interest_rate`, `utilization`, `borrow_rate`, `supply_rate`

### Bad Debt Accumulation
- **Pattern:** Positions can become undercollateralized without being liquidated
- **Check:** Is there a mechanism to handle bad debt? Are liquidation incentives sufficient to attract liquidators?
- **Attack:** Create many small positions → let them go underwater → bad debt socializes to lenders
- **Grep:** `bad_debt`, `shortfall`, `insurance_fund`, `socialized`

### Unrealized PnL as Collateral
- **Pattern:** Unrealized gains from open positions count toward borrowing power
- **Check:** Can unrealized PnL be inflated by manipulating the underlying price?
- **Attack:** Open position → manipulate price → borrow against unrealized profit → price reverts
- **Cross-ref:** Mango Markets — exact exploit pattern

### Reserve/Insurance Fund Drain
- **Pattern:** Protocol reserve used to cover shortfalls can be drained through repeated small exploits
- **Check:** Are reserve withdrawals gated? Is there a minimum reserve ratio enforced?

## Lending-Specific Grep Patterns

```bash
grep -rn 'collateral\|health_factor\|ltv\|loan_to_value' --include='*.rs'
grep -rn 'liquidat\|underwater\|shortfall\|bad_debt' --include='*.rs'
grep -rn 'borrow\|repay\|interest_rate\|utilization' --include='*.rs'
grep -rn 'oracle.*price\|price.*oracle\|valuation' --include='*.rs'
grep -rn 'insurance\|reserve_fund\|backstop' --include='*.rs'
```

## Key Invariants for Lending Protocols

1. **Solvency:** Total borrows <= total collateral value (at current prices) at all times
2. **Health:** No position should remain below liquidation threshold without being liquidatable
3. **Interest conservation:** Interest accrued to borrowers == interest distributed to lenders (minus protocol fees)
4. **Withdrawal constraint:** Users cannot withdraw collateral that would put their position below the minimum health factor
