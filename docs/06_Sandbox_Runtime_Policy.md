# Sandbox Runtime Policy

## Document Control
- Version: 0.1-draft
- Last Updated: 2026-02-27

## Objective
Define isolation and enforcement controls for untrusted code execution.

## Runtime Backends
- `balanced`: rootless Docker hardened container profile
- `strict`: Firecracker microVM profile (Linux hosts)

## Mode Selection
- Default mode is `balanced`.
- `strict` is enabled by explicit user flag or high-risk policy trigger.
- If strict is explicitly requested but unavailable, fail with `StrictModeUnavailable`.
- If policy requires strict and strict is unavailable, fail closed with `StrictModeRequired`.

## Default Security Posture
- Network egress: deny all by default
- Network allowlist: none by default; loopback-only fixture services allowed when configured
- Source mount: read-only
- Scratch space: ephemeral writable path only (`/tmp/dhi-scratch` equivalent)
- Privileges: least privilege, no privilege escalation

## Hard Resource Limits (Default Values)
- `balanced`:
  - Per-command timeout: 45 seconds
  - Total verification budget per request: 180 seconds
  - CPU quota: 2 vCPU
  - Memory limit: 1024 MB
  - Max processes: 256
  - Output/log cap: 10 MB
  - Scratch disk cap: 512 MB
- `strict`:
  - Per-command timeout: 60 seconds
  - Total verification budget per request: 240 seconds
  - CPU quota: 2 vCPU
  - Memory limit: 1536 MB
  - Max processes: 128
  - Output/log cap: 10 MB
  - Scratch disk cap: 512 MB

## External Dependency Policy
- Real external network calls are forbidden by default.
- External integrations must be tested via local fixtures or mock services.
- Any unallowlisted outbound call fails immediately with `NetworkAccessViolation`.

## Enforcement Events
- `NetworkAccessViolation`
- `FilesystemWriteViolation`
- `TimeoutViolation`
- `ProcessLimitViolation`
- `SyscallViolation`
- `MemoryLimitViolation`
- `OutputLimitViolation`
- `StrictModeUnavailable`
- `StrictModeRequired`

## Policy Overrides
- Overrides require explicit policy file change and audit log entry.
- Per-request overrides are disabled by default.
- Default limits above can be changed only in the checked-in policy file.

## Required Artifacts
- Runtime mode and backend (`balanced/docker` or `strict/firecracker`)
- Runtime config snapshot (limits, mounts, network policy)
- Exit status and signal
- Violation event details
