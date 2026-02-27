# Determinism and Environment Fingerprint Specification

## Objective
Ensure memory learns from reproducible signal only.

## Fingerprint Fields
- Runtime image digest
- OS and kernel info (or equivalent runtime host metadata)
- Language and package manager versions
- Dependency lockfile hashes
- Executed command set hash
- Allowed env var names hash

## Determinism Gate
A run is deterministic if:
1. Fingerprint matches baseline
2. Command set matches expected plan
3. Result reproducible under retry policy

## Noise Classes (Excluded from Ledger Learning)
- DNS/network provider outage
- Registry/package index timeout
- Known flaky test threshold exceeded
- Host resource starvation unrelated to patch

## Write Rules
- `reproducible=true` required for semantic memory updates
- Non-deterministic events can be stored as telemetry but not behavioral rules
