# Threat Model

## Document Control
- Version: 0.1-draft
- Last Updated: 2026-02-27

## Objective
Document credible threats, detection thresholds, and mandatory mitigations.

## Assets
- Source code
- Secrets and credentials
- Build/test infrastructure
- Verification integrity
- Ledger integrity

## Threat Actors
- Malicious dependency author
- External attacker via poisoned repository content
- Internal misuse or policy misconfiguration

## Abuse Paths
1. Prompt injection in comments to alter policy
2. Secret exfiltration via cloud context payload
3. Sandbox escape attempt from generated code
4. Ledger poisoning via flaky or non-deterministic failures
5. False verification claim in UI

## Detection Thresholds and Response Policy
- Severity `critical` (fail closed):
  - Confirmed secret patterns detected before cloud egress (for example AWS keys, private keys, OAuth client secrets).
  - Attempt to bypass runtime policy controls.
  - Response: block request, do not call cloud API, emit `SecretLeakDetected` or policy violation event, and show explicit user alert.
- Severity `high` (continue with guardrails):
  - High-entropy suspicious tokens without confirmed secret pattern.
  - Injection-like instructions in repo text.
  - Response: redact suspicious tokens, continue with strict context minimization, emit warning in manifest.
- Severity `medium` (continue with audit):
  - Non-sensitive policy anomalies or incomplete metadata.
  - Response: continue, record audit warning.

## Mitigations
- Deterministic sanitization and DLP before egress
- Runtime default-deny and violation kill policy
- Determinism gate before ledger writes
- Signed or hashed verification manifests
- Audit logs for policy overrides and data egress
- Non-overridable control prompt layer separated from repository context

## Residual Risks
- Unknown runtime escape vulnerabilities
- Human override misuse
- Upstream API outages impacting availability

## Review Cadence
- Update threat model per release or major architecture change
- Re-run abuse-path tabletop test every quarter
