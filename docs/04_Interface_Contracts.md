# Interface Contracts

## Purpose
Specify interfaces between subsystems.

## Core Interfaces

### 1. Request Envelope
```json
{
  "request_id": "uuid",
  "timestamp": "iso8601",
  "user_prompt": "string",
  "mode": "fast|balanced|strict",
  "repo_root": "path"
}
```

### 2. Context Payload
```json
{
  "request_id": "uuid",
  "files": ["path"],
  "symbols": ["symbol_id"],
  "graph_edges": [{"from": "id", "to": "id", "type": "calls"}],
  "redaction_report": {"secrets_redacted": 0}
}
```

### 3. Patch Candidate
```json
{
  "request_id": "uuid",
  "candidate_id": "uuid",
  "diff": "unified_diff",
  "rationale": "string",
  "expected_checks": ["lint", "unit"]
}
```

### 4. Verification Result
```json
{
  "request_id": "uuid",
  "candidate_id": "uuid",
  "status": "pass|fail",
  "tier": "L0|L1|L2|AI_TESTS_ONLY",
  "failure_class": "syntax|policy|timeout|flake|deterministic",
  "attempt": 1,
  "artifacts": ["path"]
}
```

### 5. Ledger Event
```json
{
  "event_id": "uuid",
  "request_id": "uuid",
  "fingerprint_hash": "sha256",
  "reproducible": true,
  "signal_type": "success|failure",
  "summary": "string"
}
```

## Contract Rules
- All interfaces must include `request_id`
- Verification can only claim tiers that were actually executed
- Ledger write requires deterministic gate pass
