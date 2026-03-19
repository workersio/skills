# Audit Persistence Schemas

Formats used by the solana-audit skill for persisting audit data across sessions.

---

## Audit Log (`audit-log.jsonl`)

Append-only JSONL file. Each line is a JSON object representing one completed audit run.

**Location:** `${CLAUDE_PLUGIN_DATA}/audit-log.jsonl`

### Schema

```json
{
  "timestamp": "2026-03-18T12:00:00Z",
  "program": "program_name",
  "path": "/path/to/program",
  "framework": "Anchor | Native | Pinocchio",
  "protocol_type": "lending | dex | staking | bridge | nft | governance | generic",
  "loc": 1500,
  "instruction_count": 12,
  "depth": "standard | deep",
  "findings": {
    "critical": 0,
    "high": 2,
    "medium": 1,
    "low": 0,
    "informational": 1
  },
  "finding_ids": ["VULN-001", "VULN-002", "VULN-003", "VULN-004"],
  "taxonomy_ids": ["A-1", "S-7", "M-2", "R-3"]
}
```

### Usage

- Append one line per completed audit run
- Use to detect re-audits of the same program (compare `path` and `program` fields)
- Show the user prior audit history when re-auditing a program

---

## Accepted Risks (`accepted-risks.json`)

JSON file tracking findings the user has explicitly accepted as known risks.

**Location:** `${CLAUDE_PLUGIN_DATA}/accepted-risks.json`

### Schema

```json
[
  {
    "taxonomy_id": "A-3",
    "file": "programs/vault/src/lib.rs",
    "line": 45,
    "reason": "Admin is a governance multisig with 3/5 threshold",
    "accepted_by": "user",
    "accepted_at": "2026-03-18T12:00:00Z"
  }
]
```

### Usage

- When scanning, check each finding against accepted risks by `taxonomy_id` + `file`
- If a finding matches an accepted risk, note it in the report as "Previously Accepted" with the reason
- Still include accepted risks in the report but mark them clearly — do not silently suppress
- Users can add new accepted risks after reviewing the audit report
