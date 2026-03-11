# Staking Protocol Security Patterns

Additional vulnerability checks specific to staking, delegation, and reward distribution protocols. Load this when the codebase explorer classifies the protocol type as **staking**.

---

## Staking-Specific Vulnerabilities

### Reward Distribution Rounding
- **Pattern:** Reward-per-share calculations use integer division that accumulates rounding errors
- **Check:** Is the reward calculation scaled up sufficiently (e.g., multiply by 1e9 before dividing)? What happens when a user's reward share rounds to 0?
- **Attack:** Stake tiny amount → claim 0 rewards → repeat to prevent reward accumulation, or stake just enough to round up and extract extra
- **Grep:** `reward_per_share`, `reward_per_token`, `accumulated_reward`, `PRECISION`

### Stake/Unstake Timing Attacks
- **Pattern:** Staking just before reward distribution, unstaking immediately after
- **Check:** Is there a lockup period or warmup for new stakes? Are rewards prorated based on time staked?
- **Attack:** Deposit large stake → wait for reward epoch → claim disproportionate rewards → unstake immediately
- **Grep:** `lockup`, `cooldown`, `warmup`, `unstake_delay`, `epoch`

### Epoch Boundary Issues
- **Pattern:** State transitions at epoch boundaries create exploitable windows
- **Check:** Are reward calculations consistent across epoch transitions? Can operations be timed to land on both sides of an epoch boundary?
- **Attack:** Claim rewards at epoch N, then claim again at epoch N+1 before the reward index updates
- **Grep:** `epoch`, `last_epoch`, `update_epoch`, `epoch_boundary`

### Reward Rate Authority Manipulation
- **Pattern:** Reward emission rate can be changed by an authority without timelock
- **Check:** Who can change the reward rate? Is there a timelock or governance approval? Are there bounds on the rate?
- **Attack:** Compromised authority sets reward rate to max → drains reward pool → sets rate back to 0
- **Grep:** `reward_rate`, `emission_rate`, `set_reward`, `update_rate`

### Reward Pool Exhaustion
- **Pattern:** Reward pool can be drained faster than intended if many stakers claim simultaneously
- **Check:** Is the reward pool bounded? What happens when rewards run out — do claims fail gracefully or panic?
- **Grep:** `reward_pool`, `reward_vault`, `remaining_rewards`

### Delegation Accounting
- **Pattern:** Delegated stake accounting doesn't properly track principal vs rewards
- **Check:** Can a user unstake more than they deposited? Are delegation shares calculated correctly when the pool grows from rewards?
- **Grep:** `delegate`, `delegation`, `shares`, `principal`

## Staking-Specific Grep Patterns

```bash
grep -rn 'stake\|unstake\|deposit\|withdraw' --include='*.rs'
grep -rn 'reward\|emission\|distribute\|claim' --include='*.rs'
grep -rn 'epoch\|lockup\|cooldown\|warmup' --include='*.rs'
grep -rn 'delegate\|delegation\|validator' --include='*.rs'
grep -rn 'reward_per_share\|accumulated\|PRECISION' --include='*.rs'
```

## Key Invariants for Staking Protocols

1. **Reward conservation:** Total rewards distributed <= total rewards deposited into the reward pool
2. **Stake accounting:** Sum of all user stakes == total staked amount tracked by the program
3. **Proportional rewards:** Each user's reward share is proportional to (their stake * time staked)
4. **Withdrawal constraint:** Users cannot withdraw more than their deposited stake + earned rewards
