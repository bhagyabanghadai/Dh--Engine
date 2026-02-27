# Epic 7: Governance, DLP, and Prompt-Injection Defense
**Status**: Blocked (Requires Epics 1-6)
**Depends On**: Epics 1, 2, 3, 4, 5, 6

## Goal
Enforce hard data-governance controls before cloud egress and define fail-closed responses for secret exposure and policy bypass attempts.

## In Scope
- Path access policy
- Secret scanning and redaction
- Severity classification and response handling
- Egress audit logging

## Out of Scope
- Enterprise IAM integrations
- Multi-tenant policy UI

## Requirements
1. Implement path allowlist/denylist policy engine for context extraction.
2. Implement secret detection:
   - Confirmed secret patterns (critical)
   - High-entropy suspicious tokens (high)
3. Enforce response policy:
   - Critical: fail closed, block cloud call, emit `SecretLeakDetected`, show explicit user alert
   - High: redact and continue with warning
4. Ensure policy/system instructions are non-overridable by repository text.
5. Log egress metadata for every cloud request:
   - `request_id`, `file_count`, `redaction_count`, `bytes_sent`

## Exit Gates (Definition of Done)
- [ ] Confirmed secret in candidate context blocks cloud call and surfaces explicit user warning.
- [ ] High-entropy non-confirmed token is redacted and logged with warning.
- [ ] Path-denied files are never included in outbound payload.
- [ ] Injection-like repo strings do not alter policy execution.

## Artifacts Produced
- Governance policy module
- DLP scanner/redactor
- Egress audit trail and policy tests
