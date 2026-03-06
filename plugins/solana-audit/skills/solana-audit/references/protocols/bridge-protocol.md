# Bridge Protocol Security Patterns

Additional vulnerability checks specific to cross-chain bridges, message passing, and relayer systems. Load this when the codebase explorer classifies the protocol type as **bridge**.

---

## Bridge-Specific Vulnerabilities

### Message Verification Bypass
- **Pattern:** Cross-chain message verification relies on a program account (verifier) that is not properly validated
- **Check:** Is the verification program address hardcoded or validated against a known ID? Can a user substitute a fake verifier?
- **Attack:** Deploy a fake verification program that always returns "verified" → forge cross-chain messages → mint/unlock arbitrary tokens
- **Cross-ref:** Wormhole ($326M) — exact exploit pattern. Attacker substituted a fake secp256k1 verification program.
- **Grep:** `verify`, `signature`, `guardian`, `verifier`, `secp256k1`

### Replay Attacks
- **Pattern:** Processed cross-chain messages can be replayed to trigger duplicate actions
- **Check:** Is there a nonce or sequence number that prevents replay? Is the nonce stored on-chain and checked before processing? Is the nonce scoped per source chain?
- **Attack:** Submit the same valid message multiple times → trigger duplicate mints/unlocks
- **Grep:** `nonce`, `sequence`, `processed`, `consumed`, `replay`

### Guardian/Relayer Collusion
- **Pattern:** Bridge security depends on a threshold of honest guardians/relayers
- **Check:** What is the threshold (e.g., 2/3, 13/19)? Can the guardian set be rotated? Who controls rotation? Is there a timelock on guardian changes?
- **Attack:** Compromise enough guardians to exceed threshold → forge messages
- **Grep:** `guardian`, `relayer`, `threshold`, `quorum`, `guardian_set`

### Chain Finality Assumptions
- **Pattern:** Bridge processes messages from source chain before finality is guaranteed
- **Check:** Does the bridge wait for sufficient confirmations? Is there a finality delay? Can messages be submitted from reorganized/reverted blocks?
- **Attack:** Submit message based on a block that gets reorganized → message processed on destination but source transaction reverted
- **Grep:** `finality`, `confirmation`, `block_height`, `slot`, `finalized`

### Token Mint/Unlock Accounting
- **Pattern:** Wrapped token minting on the destination doesn't match locking on the source
- **Check:** Is the mint amount exactly equal to the locked amount (accounting for fees)? Can more tokens be minted than locked?
- **Attack:** Forge or manipulate message to inflate the mint amount → extract more tokens than deposited
- **Grep:** `mint`, `lock`, `unlock`, `wrap`, `bridge_amount`

### Message Ordering
- **Pattern:** Bridge assumes messages are processed in order but doesn't enforce it
- **Check:** Are messages processed strictly in sequence? What happens if message N+1 is processed before message N?
- **Attack:** Skip a message that reduces balance, process a later message that depends on the higher balance
- **Grep:** `sequence`, `order`, `message_id`, `batch`

### Rate Limiting and Circuit Breakers
- **Pattern:** No limit on bridge throughput allows rapid drain if verification is compromised
- **Check:** Is there a rate limit on transfers? A maximum per-transaction amount? A circuit breaker that pauses on anomalous volume?
- **Grep:** `rate_limit`, `max_transfer`, `circuit_breaker`, `pause`, `emergency`

## Bridge-Specific Grep Patterns

```bash
grep -rn 'verify\|signature\|guardian\|relayer' --include='*.rs'
grep -rn 'nonce\|sequence\|replay\|consumed' --include='*.rs'
grep -rn 'chain_id\|source_chain\|destination' --include='*.rs'
grep -rn 'mint\|lock\|unlock\|wrap\|bridge' --include='*.rs'
grep -rn 'threshold\|quorum\|guardian_set' --include='*.rs'
grep -rn 'rate_limit\|circuit_breaker\|pause\|emergency' --include='*.rs'
```

## Key Invariants for Bridge Protocols

1. **Conservation:** Tokens locked on source chain == tokens minted on destination chain (minus fees)
2. **No replay:** Each cross-chain message is processed exactly once
3. **Verification integrity:** Every processed message was signed by a valid quorum of guardians
4. **Ordering:** Messages are processed in the correct sequence (if ordering matters)
5. **Rate safety:** Transfer volume stays within safe limits even if verification is partially compromised
