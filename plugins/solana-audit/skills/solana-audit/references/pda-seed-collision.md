# S-3: PDA Seed Collision [HIGH]

Program Derived Address (PDA) seeds lack sufficient discriminating fields, causing different logical entities (e.g., different users' vaults) to map to the same PDA. An attacker can read, overwrite, or close another user's account, or the program fails to create accounts for distinct users.

---

## Preconditions

For this vulnerability to be exploitable, ALL of the following must hold:

1. **A PDA is derived with seeds that do not uniquely identify the entity** (e.g., `seeds = [b"vault"]` is the same for all users)
2. **Multiple distinct entities are expected to have separate PDA accounts** (e.g., per-user vaults, per-market positions, per-token pools)
3. **An attacker can influence which entity a PDA resolves to**, or the first user to create the PDA prevents all subsequent users from creating theirs
4. **The program does not have an alternative uniqueness mechanism** (e.g., a separate index or mapping)

## Vulnerable Pattern

### Global PDA Used for Per-User State (Vulnerable)

```rust
use anchor_lang::prelude::*;

#[account]
pub struct UserVault {
    pub authority: Pubkey,
    pub balance: u64,
}

#[derive(Accounts)]
pub struct CreateVault<'info> {
    #[account(
        init,
        payer = user,
        space = 8 + 32 + 8,
        // VULNERABLE: seeds only contain the literal "vault".
        // All users derive the SAME PDA address.
        // First user to create it owns it; all others fail or share it.
        seeds = [b"vault"],
        bump,
    )]
    pub vault: Account<'info, UserVault>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}
```

### Insufficient Seeds in Multi-Dimensional PDA (Vulnerable)

```rust
#[derive(Accounts)]
pub struct CreatePosition<'info> {
    #[account(
        init,
        payer = user,
        space = 8 + std::mem::size_of::<Position>(),
        // VULNERABLE: seeds include user but not the market.
        // User can only have ONE position across ALL markets.
        // Creating a position in market B overwrites/collides with market A.
        seeds = [b"position", user.key().as_ref()],
        bump,
    )]
    pub position: Account<'info, Position>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub market: Account<'info, Market>,
    pub system_program: Program<'info, System>,
}

#[account]
pub struct Position {
    pub user: Pubkey,
    pub market: Pubkey,
    pub amount: u64,
    pub entry_price: u64,
}
```

### Variable-Length Seed Concatenation Collision (Vulnerable)

```rust
#[derive(Accounts)]
pub struct CreateRecord<'info> {
    #[account(
        init,
        payer = user,
        space = 8 + std::mem::size_of::<Record>(),
        // VULNERABLE: Two variable-length seeds without a separator.
        // "AB" + "CD" has the same seed bytes as "A" + "BCD" or "ABC" + "D".
        // seeds = [b"record", name_a.as_bytes(), name_b.as_bytes()]
        // If name_a = "foo" and name_b = "bar" => seeds = [b"record", b"foobar"]
        // If name_a = "foob" and name_b = "ar"  => seeds = [b"record", b"foobar"]  COLLISION!
        seeds = [b"record", name_a.as_bytes(), name_b.as_bytes()],
        bump,
    )]
    pub record: Account<'info, Record>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}
```

### Native Solana Program (Vulnerable)

```rust
use solana_program::pubkey::Pubkey;

pub fn derive_vault_address(program_id: &Pubkey) -> (Pubkey, u8) {
    // VULNERABLE: Global seeds — one vault for the entire program.
    // Any user interacting with "the vault" shares the same account.
    Pubkey::find_program_address(
        &[b"vault"],
        program_id,
    )
}

pub fn derive_escrow_address(
    program_id: &Pubkey,
    user: &Pubkey,
    // Missing: token_mint, escrow_id, or other discriminator
) -> (Pubkey, u8) {
    // VULNERABLE: User can only have one escrow.
    // If the protocol supports multiple escrows per user, they collide.
    Pubkey::find_program_address(
        &[b"escrow", user.as_ref()],
        program_id,
    )
}
```

## Detection Heuristics

### Grep Patterns

```bash
# Find all PDA seed definitions in Anchor programs
rg "seeds\s*=\s*\[" --type rust -n

# Find find_program_address calls in native programs
rg "find_program_address|create_program_address" --type rust -n

# Find seeds that look too simple (single literal)
rg 'seeds\s*=\s*\[b"[a-z_]+"' --type rust -n

# Look for seeds without .key() references (missing user/mint pubkey)
rg "seeds\s*=\s*\[" --type rust -A 3 -n
```

### Manual Review Steps

1. **Catalog every PDA derivation** in the program (both `seeds = [...]` in Anchor and `find_program_address` in native code).
2. **For each PDA, determine the logical entity it represents**:
   - Global singleton (program config, global state): `seeds = [b"config"]` is fine.
   - Per-user account: Must include `user.key().as_ref()` in seeds.
   - Per-user-per-market account: Must include both `user.key().as_ref()` and `market.key().as_ref()`.
   - Per-token: Must include `mint.key().as_ref()`.
3. **Check that seeds uniquely identify the entity**. Ask: "Can two distinct entities resolve to the same PDA address?"
4. **Check variable-length seed fields** for concatenation collisions. Two adjacent variable-length fields without a separator or fixed-length encoding can collide.
5. **Verify seed validation in instruction handlers**. The seeds used to derive the PDA should match the actual parameters (e.g., if `user.key()` is in the seeds, ensure it is the actual signer's key, not an arbitrary passed-in key).

## False Positives

The following patterns are **not vulnerable** and should be excluded:

- **Intentionally global PDAs**: Program config, fee collector, protocol treasury, global pause state. These are designed to be singletons:
  ```rust
  seeds = [b"global_config"]  // intentionally one per program
  ```
- **Seeds include all necessary discriminators** for the entity type:
  ```rust
  // Per-user-per-market position: fully qualified
  seeds = [b"position", user.key().as_ref(), market.key().as_ref()]
  ```
- **Counter-based seeds**: Programs that use an incrementing counter for uniqueness:
  ```rust
  seeds = [b"order", user.key().as_ref(), &order_id.to_le_bytes()]
  ```
- **Fixed-length seed fields**: When all seed components are fixed-length (e.g., 32-byte pubkeys, 8-byte u64 encodings), concatenation collision is impossible.
- **Seeds validated by has_one or constraint**: When the seed pubkeys are cross-checked against stored state:
  ```rust
  #[account(
      seeds = [b"vault", authority.key().as_ref()],
      bump = vault.bump,
      has_one = authority,
  )]
  pub vault: Account<'info, Vault>,
  ```

## Remediation

### Per-User PDA (Fixed)

```rust
#[derive(Accounts)]
pub struct CreateVault<'info> {
    #[account(
        init,
        payer = user,
        space = 8 + 32 + 8 + 1,
        // FIX: Include user pubkey in seeds to ensure per-user uniqueness
        seeds = [b"vault", user.key().as_ref()],
        bump,
    )]
    pub vault: Account<'info, UserVault>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[account]
pub struct UserVault {
    pub authority: Pubkey,
    pub balance: u64,
    pub bump: u8,
}
```

### Per-User-Per-Market PDA (Fixed)

```rust
#[derive(Accounts)]
pub struct CreatePosition<'info> {
    #[account(
        init,
        payer = user,
        space = 8 + std::mem::size_of::<Position>(),
        // FIX: Include both user AND market in seeds
        seeds = [b"position", user.key().as_ref(), market.key().as_ref()],
        bump,
    )]
    pub position: Account<'info, Position>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub market: Account<'info, Market>,
    pub system_program: Program<'info, System>,
}
```

### Variable-Length Seed Fields (Fixed)

```rust
#[derive(Accounts)]
#[instruction(name_a: String, name_b: String)]
pub struct CreateRecord<'info> {
    #[account(
        init,
        payer = user,
        space = 8 + std::mem::size_of::<Record>(),
        // FIX: Use fixed-length hashes of variable-length inputs,
        // or separate variable-length fields with a length prefix / delimiter.
        seeds = [
            b"record",
            &anchor_lang::solana_program::hash::hash(name_a.as_bytes()).to_bytes()[..16],
            &anchor_lang::solana_program::hash::hash(name_b.as_bytes()).to_bytes()[..16],
        ],
        bump,
    )]
    pub record: Account<'info, Record>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}
```

### Native Solana Program (Fixed)

```rust
pub fn derive_vault_address(program_id: &Pubkey, user: &Pubkey) -> (Pubkey, u8) {
    // FIX: Include user pubkey in seeds
    Pubkey::find_program_address(
        &[b"vault", user.as_ref()],
        program_id,
    )
}

pub fn derive_escrow_address(
    program_id: &Pubkey,
    user: &Pubkey,
    token_mint: &Pubkey,
    escrow_id: u64,
) -> (Pubkey, u8) {
    // FIX: Include all discriminating fields
    Pubkey::find_program_address(
        &[
            b"escrow",
            user.as_ref(),
            token_mint.as_ref(),
            &escrow_id.to_le_bytes(),
        ],
        program_id,
    )
}
```

### Key Principle

PDA seeds must include enough fields to uniquely identify the entity they represent. For per-user accounts, include the user's pubkey. For per-user-per-asset accounts, include both user and asset pubkeys. For variable-length fields, use hashing or fixed-length encoding to prevent concatenation collisions. Always ask: "Can two distinct entities in this program resolve to the same PDA?"
