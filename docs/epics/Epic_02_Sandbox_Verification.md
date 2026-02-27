# Epic 2: Local Sandbox Verification (Balanced Runtime)
**Status**: Blocked (Requires Epic 1)
**Depends On**: Epic 1

## Goal
Execute untrusted generated Python code in a hardened local balanced runtime and return a structured verification result that matches the project verification contract.

## In Scope
- Rootless Docker-based balanced runtime
- Runtime policy enforcement and violation classification
- Verification result contract

## Out of Scope
- Strict Firecracker runtime
- Cloud model orchestration
- Retry loop

## Requirements
1. Implement sandbox executor in `src/dhi/sandbox/executor.py`.
2. Enforce balanced mode defaults:
   - Per-command timeout: 45s
   - Per-request verification budget: 180s
   - CPU quota: 2 vCPU
   - Memory limit: 1024 MB
   - Max processes: 256
   - Output/log cap: 10 MB
   - Scratch disk cap: 512 MB
3. Enforce security policy:
   - Network disabled (`none`) by default
   - Source mount read-only
   - Writes allowed only in ephemeral scratch path
4. Classify failures into canonical classes/events:
   - `TimeoutViolation`
   - `NetworkAccessViolation`
   - `FilesystemWriteViolation`
   - `ProcessLimitViolation`
   - `MemoryLimitViolation`
   - `OutputLimitViolation`
   - `SyscallViolation`
5. Return `verification_result.json` with required fields:
   - `request_id`, `attempt`, `mode`, `status`, `tier`, `failure_class`
   - `exit_code`, `duration_ms`, `stdout`, `stderr`
   - `artifacts`, `skipped_checks`, `terminal_event`

## Exit Gates (Definition of Done)
- [ ] Valid Python input returns `status=pass`.
- [ ] Syntax error input returns `status=fail` with traceback in `stderr`.
- [ ] Infinite loop input is terminated at policy timeout and classified as `TimeoutViolation`.
- [ ] Outbound network attempt fails with `NetworkAccessViolation`.
- [ ] Source write attempt outside scratch path fails with `FilesystemWriteViolation`.
- [ ] Result payload includes all required verification contract fields.

## Artifacts Produced
- Sandbox executor with enforcement
- Verification result schema-conformant payload
- Sandbox policy test suite
