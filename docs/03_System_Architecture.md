# System Architecture

## Purpose
Define core components, boundaries, and data flow.

## Components
- IDE Adapter: Captures prompt and user intent
- Context Builder: AST slicing + policy filtering
- Graph Engine: Symbol/dependency retrieval
- Planner: Cloud model orchestration
- Patch Engine: Patch generation and apply plan
- Verifier: Isolated execution and test runner
- Ledger (VEIL): Deterministic memory store
- Attestor: Verification manifest generator

## Trust Boundaries
- Boundary A: IDE/Repo -> Context Builder (untrusted input)
- Boundary B: Local system -> Cloud APIs (governed egress)
- Boundary C: Untested code -> Verifier runtime (hostile execution)

## High-Level Flow
1. User submits request
2. Context Builder retrieves policy-allowed context
3. Planner generates patch candidate
4. Verifier executes checks in isolated runtime
5. On fail: classify + bounded retry
6. On pass: Attestor emits manifest
7. Ledger writes deterministic event

## Deployment Modes
- Fast: minimal checks
- Balanced: default dev mode
- Strict: highest assurance, broader checks, tighter policy

## State Machine
- `received`
- `context_ready`
- `candidate_generated`
- `verification_running`
- `verification_failed` (retry or handoff)
- `verification_passed`
- `attested`
- `completed`

## Architecture Decisions Needed
- Graph DB backend
- Runtime backend (container vs microVM per mode)
- Artifact storage path and retention
