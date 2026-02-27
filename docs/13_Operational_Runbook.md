# Operational Runbook

## Objective
Define day-2 operations and incident response.

## Observability
- Metrics: success rate, retries, failure classes, policy violations
- Logs: request trace, verification logs, egress audit
- Alerts: verification claim mismatch, repeated policy violations, latency spikes

## Incident Playbooks
1. Cloud API outage
2. Sandbox runtime instability
3. DLP false negative/positive surge
4. Ledger corruption or mismatch

## Recovery Procedures
- Degrade mode from strict->balanced->safe fallback
- Disable autonomous retries globally if instability detected
- Restore from last known-good ledger snapshot

## On-Call Checklist
- Confirm incident scope
- Contain risk (disable risky paths)
- Communicate status and ETA
- Post-incident review with action items
