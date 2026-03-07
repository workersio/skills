# DEX / AMM Protocol Security Patterns

Additional vulnerability checks specific to decentralized exchanges and automated market makers. Load this when the codebase explorer classifies the protocol type as **dex**.

---

## DEX-Specific Vulnerabilities

### Sandwich Attack Vectors
- **Pattern:** Swap instructions without enforced slippage protection
- **Check:** Does every swap instruction have a `min_amount_out` parameter? Is it enforced (not just accepted)?
- **Attack:** Front-run victim's swap → execute victim's swap at worse price → back-run to capture profit
- **Critical:** A `min_amount_out` of 0 (or no parameter at all) means zero protection
- **Grep:** `min_amount_out`, `max_amount_in`, `slippage`, `price_impact`

### LP Token Inflation/Deflation
- **Pattern:** LP share calculation allows minting 0 shares for a non-zero deposit
- **Check:** Is there a `require!(lp_tokens > 0)` guard after share calculation? What happens with the first deposit (empty pool)?
- **Attack:** Rounding drain — deposit dust amounts that mint 0 LP tokens, inflating existing LP token value
- **Cross-ref:** Neodyme Rounding Bug ($2.6B at risk in SPL Token Lending)
- **Grep:** `lp_token`, `total_supply`, `shares`, `mint_to`

### Pool Ratio Manipulation
- **Pattern:** Pool state (reserves, prices) readable and manipulable within a single transaction
- **Check:** Are there any operations that read pool state for economic decisions? Can that state be manipulated beforehand?
- **Attack:** Flash loan → imbalance pool → execute operation at favorable rate → rebalance pool
- **Grep:** `reserve_a`, `reserve_b`, `pool_balance`, `constant_product`

### Constant-Product Invariant Violations
- **Pattern:** AMM curve math doesn't perfectly maintain k = x * y
- **Check:** After every swap, is the invariant rechecked? Are fees applied before or after the invariant check?
- **Attack:** Exploit rounding in curve math to extract value over many small trades
- **Grep:** `invariant`, `constant_product`, `k_value`, `curve`

### Fee Calculation Precision
- **Pattern:** Fee amounts calculated with integer division that favors one party
- **Check:** Does fee calculation round in the protocol's favor (up) or the user's favor (down)?
- **Attack:** Many small trades where fees round to 0 → trades executed fee-free
- **Grep:** `fee`, `fee_rate`, `protocol_fee`, `fee_amount`

### Concentrated Liquidity Issues
- **Pattern:** Tick-based AMMs (CLMM) with complex position management
- **Check:** Are tick boundaries handled correctly? Can positions be created at invalid ticks? Are rewards distributed proportionally to active liquidity only?
- **Grep:** `tick`, `tick_array`, `position`, `liquidity`, `sqrt_price`

## DEX-Specific Grep Patterns

```bash
grep -rn 'swap\|exchange\|trade' --include='*.rs'
grep -rn 'pool\|reserve\|liquidity\|amm' --include='*.rs'
grep -rn 'lp_token\|shares\|mint_to\|burn' --include='*.rs'
grep -rn 'fee\|fee_rate\|protocol_fee' --include='*.rs'
grep -rn 'tick\|sqrt_price\|concentrated' --include='*.rs'
grep -rn 'slippage\|min_amount\|max_amount\|price_impact' --include='*.rs'
```

## Key Invariants for DEX Protocols

1. **Curve invariant:** k = x * y (or equivalent) holds after every swap, deposit, and withdrawal
2. **LP conservation:** LP tokens minted/burned correspond exactly to value deposited/withdrawn
3. **Fee consistency:** All trades pay the correct fee; fees accrue to protocol and LPs correctly
4. **No free trades:** Every swap moves the price; no sequence of operations can extract value without cost
5. **Withdrawal safety:** LPs receive proportional share of both tokens on withdrawal
