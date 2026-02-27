# Context Governance and DLP

## Objective
Prevent data exfiltration and prompt-injection leakage during cloud calls.

## Data Classification
- Public: safe metadata
- Internal: code structure and symbols
- Sensitive: secrets, credentials, keys, personal data

## Extraction Policy
- Path allowlist/denylist enforced before reading
- Comment exclusion by default
- Selective literal retention for semantics-critical values

## DLP Controls
- Pattern detectors (keys/tokens/certs)
- Entropy detectors for unknown secrets
- Redaction marker: `<REDACTED_SECRET>`

## Cloud Egress Policy
- Only redacted context payloads sent
- Egress event audit log includes file counts and redaction stats
- Optional tenant-level retention controls

## Injection Controls
- Treat all repository text as untrusted
- Keep policy prompts non-overridable and separate from repo context
- Disallow tool calls that violate local policy regardless of model instruction
