# Product Requirements Document (PRD)

## Document Control
- Product: Dhi
- Version: 0.1-draft
- Status: Draft
- Owner: Founding Engineering
- Last Updated: 2026-02-27

## Problem Statement
AI coding assistants produce unverified output, weak project awareness, and poor memory across sessions.

## Product Goal
Provide a middleware layer that routes cloud reasoning through local proof so generated code is context-aware, policy-compliant, and auditable.

## Target Users
- Individual developers
- Small engineering teams
- Security-conscious organizations

## Primary Jobs To Be Done
- Refactor code with impact awareness
- Implement requested features while preserving architecture
- Repair failing code using bounded autonomous loops

## Non-Goals (v0.1)
- Full autonomous repo-wide migrations
- Unbounded internet-enabled execution
- Automatic merge without human approval

## Functional Requirements
- FR1: Intercept IDE prompt and compile local structural context
- FR2: Route planning to cloud model and capture proposed patch
- FR3: Verify patch in local isolated runtime before reveal
- FR4: Retry failed patches up to policy budget
- FR5: Emit verification manifest with explicit tier/result
- FR6: Persist deterministic outcome events to VEIL

## Non-Functional Requirements
- NFR1: Security-first default-deny runtime
- NFR2: Deterministic reproducibility gates for memory writes
- NFR3: Observable stage-by-stage progress in UI
- NFR4: Token/time budget enforcement per request

## Locked v0.1 Technical Decisions
- Backend service: Python 3.11 + FastAPI
- Parser/indexing: Tree-sitter
- Local graph store: Kuzu (embedded)
- Ledger store: SQLite (WAL mode) for deterministic local persistence
- Balanced runtime backend: rootless Docker container profile
- Strict runtime backend: Firecracker microVM profile (Linux host)
- Default execution mode: `balanced`

## Success Metrics
- Verification Integrity: 100% of responses include attestation
- Repair Efficiency: >= 60% of failed first drafts fixed within retry budget
- Trust Metric: < 1% false verification claims
- Latency Targets: p50 <= 45s balanced mode, p95 <= 180s strict mode

## Risks
- Prompt injection via repository text
- Flaky test feedback loops
- API-rate limit failures under heavy retry

## Deferred Decisions (Post-v0.1)
- Multi-language service split (Python-only vs mixed Python/TypeScript control plane)
- Team-scale graph backend migration criteria (Kuzu -> Neo4j)
- Remote verifier worker pool architecture
