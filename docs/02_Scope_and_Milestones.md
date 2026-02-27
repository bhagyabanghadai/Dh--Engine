# Scope and Milestones

## Document Control
- Version: 0.1-draft
- Last Updated: 2026-02-27

## Release Scope

### v0.1 (Foundation)
- Interceptor + cloud planning
- Local verifier with runtime policy enforcement
- Tiered verification output (L0/L1/L2)
- Basic VEIL event logging with deterministic gate
- Locked stack: Python 3.11 + FastAPI control plane, Tree-sitter parsing, Kuzu embedded graph store, SQLite ledger store

### v0.2 (Stability)
- Graph-based impact retrieval
- Failure classification improvements
- Cost/latency budgets + model routing policy
- Expanded test integrations

### v0.3 (Scale)
- Advanced memory summarization and decay tuning
- Multi-repo or mono-repo scale handling
- Team governance and policy profiles

## Milestones
1. M1: Contracts finalized (Architecture, Runtime, Verification, Determinism)
2. M2: Vertical slice demo (`prompt -> patch -> verify -> attest`)
3. M3: Retry loop with bounded self-repair
4. M4: Memory write/read with decay and conflict resolution
5. M5: Operational readiness (runbook, alerts, incident playbooks)

## Exit Criteria Per Milestone
- M1: All contracts reviewed and approved
- M2: At least 5 end-to-end scenarios pass with manifests
- M3: Retry loop capped and stable under induced failures
- M4: VEIL writes only from reproducible runs
- M5: On-call runbook validated in tabletop exercise

## Dependencies
- IDE integration path
- Cloud API credentials and quotas
- Balanced mode runtime: rootless Docker available locally
- Strict mode runtime: Firecracker available on Linux hosts (or strict mode unavailable)

## Out of Scope for v0.1
- Auto-PR creation across remote CI providers
- Full policy DSL authoring UI

## Mode Trigger Policy (v0.1)
- Default mode is `balanced`.
- `strict` is activated when user explicitly selects it (CLI/IDE flag) or when policy marks a request as high-risk.
- High-risk triggers include paths/features touching auth, payments, cryptography, secret management, or production migration scripts.
