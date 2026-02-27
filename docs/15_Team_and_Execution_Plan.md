# Dhi: Team Structure and End-to-End Execution Plan (v0.1)

## Document Control
- Version: 0.1-draft
- Status: Locked for implementation
- Last Updated: 2026-02-27
- Scope: v0.1 only

## 1. Execution Model
Dhi implementation follows one bounded loop:
`request -> context -> candidate -> verify -> retry (max 3) -> attest -> handoff`

This plan is decision-complete for v0.1. No open architectural decisions remain in this file.

## 2. Locked v0.1 Stack
- Backend: Python 3.11 + FastAPI
- Parser: Tree-sitter
- Graph store: Kuzu (embedded)
- Ledger store: SQLite (WAL)
- Balanced runtime: rootless Docker hardened profile
- Strict runtime: Firecracker microVM (Linux hosts)
- Default mode: `balanced`

## 3. Team Pods and Ownership

| Pod | Owns | Does Not Own | First Deliverable |
|---|---|---|---|
| Pod A: Control Plane | Request lifecycle, orchestration state machine, model routing, retry logic, attestation assembly | Runtime isolation internals, graph indexing implementation | FastAPI app with orchestration skeleton |
| Pod B: Sandbox and Security | Runtime policy enforcement, limits, violation classification, verifier execution artifacts | Prompt engineering, memory scoring | Balanced executor with read-only mount and timeout policy |
| Pod C: Graph and Memory | Tree-sitter extraction, Kuzu indexing/query, VEIL persistence and scoring | Runtime kill-policy implementation | Parse a `.py` file and persist symbols into Kuzu |

## 4. Cross-Pod Interface Contracts
All artifacts must include `request_id`, `attempt`, `created_at`, and `schema_version`.

- `context_payload.json` (Producer: Pod C, Consumer: Pod A)
- `verification_result.json` (Producer: Pod B, Consumer: Pod A and Pod C)
- `attestation_manifest.json` (Producer: Pod A, Consumer: UI/CLI)
- `ledger_event.json` (Producer: Pod C, only after determinism gate pass)

Required enums:
- `mode`: `fast | balanced | strict`
- `tier`: `L0 | L1 | L2 | AI_TESTS_ONLY`
- `failure_class`: `syntax | policy | timeout | flake | deterministic`
- `terminal_event`: `MaxRetriesExceeded | StrictModeUnavailable | StrictModeRequired`

## 5. Runtime Mode Policy in Delivery Plan
- Default mode is `balanced`.
- `strict` runs only when explicitly requested or when high-risk policy triggers.
- High-risk triggers include auth, payments, cryptography, secret handling, and production migration code paths.
- Strict fallback is fail-closed:
If strict is required/requested and unavailable, stop execution with `StrictModeUnavailable` or `StrictModeRequired`. Never downgrade silently.

## 6. Hard Runtime Limits (Default Values)
Balanced mode:
- Per-command timeout: 45s
- Per-request verification budget: 180s
- CPU quota: 2 vCPU
- Memory limit: 1024 MB
- Max processes: 256
- Output/log cap: 10 MB
- Scratch disk cap: 512 MB

Strict mode:
- Per-command timeout: 60s
- Per-request verification budget: 240s
- CPU quota: 2 vCPU
- Memory limit: 1536 MB
- Max processes: 128
- Output/log cap: 10 MB
- Scratch disk cap: 512 MB

Network and filesystem:
- Egress default: deny all
- Source mount: read-only
- Unallowlisted outbound attempt: `NetworkAccessViolation`

## 7. Phase Plan with Exit Gates

### Phase 1 (Week 1): Baseline Scaffold
Deliverables:
- Python project initialized with `uv`
- `pyproject.toml` with `ruff`, `mypy`, `pytest`
- Module layout under `src/dhi/`
- FastAPI health endpoint

Exit gates:
- Lint/type/test checks are green
- Health endpoint returns 200
- Package layout matches agreed modules

### Phase 2 (Week 2): Vertical Slice M2
Deliverables:
- Cloud planner stub call
- Local verifier execution path
- Manifest response to API caller

Exit gates:
- End-to-end run produces command evidence, exit codes, durations, artifacts
- Validation command is meaningful (not `assert True` only)
- No output labeled verified without manifest

### Phase 3 (Week 3): Circuit Breaker M3
Deliverables:
- Retry loop using classified failure feedback
- Max retry counter enforcement

Exit gates:
- Deterministic failing case terminates at 3 attempts
- Terminal state recorded as `MaxRetriesExceeded`
- No unbounded loop possible

### Phase 4 (Week 4): AST and Graph Query
Deliverables:
- Tree-sitter extraction for Python symbols
- Kuzu ingestion and query API
- Interceptor graph lookup before cloud call

Exit gates:
- Related symbol query works for target function/class
- Context payload includes traceable symbol/edge set

### Phase 5 (Week 5): VEIL and Determinism M4
Deliverables:
- Environment fingerprint generation
- Determinism write gate
- VEIL event persistence

Exit gates:
- Deterministic runs write memory events
- Non-deterministic runs are telemetry-only and do not alter behavioral memory

### Phase 6 (Week 6): Polish and v0.1 Release
Deliverables:
- CLI entrypoint `python -m dhi run`
- E2E runs on 5 local Python projects
- Finalized verification output format

Exit gates:
- Mandatory acceptance scenarios all pass
- Release checklist complete
- Runbook handoff completed

## 8. Mandatory Acceptance Scenarios
- Unallowlisted network call fails with `NetworkAccessViolation`
- Read-only source write attempt fails with filesystem violation
- Timeout/hang classified and enforced
- AI-authored tests only yields `AI_TESTS_ONLY` with human review required
- Retry budget cap enforced at 3
- Determinism mismatch blocks VEIL behavioral write
- Manifest includes commands, exit codes, durations, skipped checks, and tier

## 9. Risk Controls and Escalation
- Critical secret exposure before cloud egress: fail closed, block request, alert user
- Policy violation in runtime: kill process immediately and classify event
- Repeated strict-mode unavailability: escalate to platform owner for environment remediation

## 10. Release Readiness Checklist
- Contracts aligned with docs 01, 02, 05, 06, 07, and 10
- No unresolved TODOs in phase gates
- All schema fields mapped in implementation tickets
- ASCII/encoding clean document
