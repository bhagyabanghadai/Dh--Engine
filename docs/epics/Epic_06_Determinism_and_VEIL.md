# Epic 6: Determinism Gate and VEIL Memory Writes
**Status**: Blocked (Requires Epics 1-5)
**Depends On**: Epics 1, 2, 3, 4, 5

## Goal
Allow VEIL to learn only from reproducible signal by implementing deterministic fingerprinting and gated ledger writes.

## In Scope
- Environment fingerprint generation
- Reproducibility checks
- VEIL event schema and storage write path

## Out of Scope
- Advanced memory ranking or semantic summarization

## Requirements
1. Implement environment fingerprint with minimum fields:
   - Runtime image digest
   - Python/toolchain versions
   - Dependency lockfile hash
   - Command-set hash
   - Allowed env var names hash
2. Implement deterministic-write gate:
   - Ledger behavioral writes only if fingerprint matches baseline and result is reproducible.
3. Classify and exclude noise classes from behavioral memory:
   - DNS/network outages
   - Package registry timeouts
   - Flake threshold breach
4. Persist two record types:
   - Telemetry event (always, for observability)
   - Behavioral memory event (only if deterministic gate passes)

## Exit Gates (Definition of Done)
- [ ] Deterministic pass/fail runs create behavioral VEIL events.
- [ ] Non-deterministic failures are telemetry-only and do not alter behavior memory.
- [ ] Fingerprint mismatch blocks behavioral write with explicit reason.
- [ ] VEIL persistence tests pass for write/read paths.

## Artifacts Produced
- Fingerprint generator
- Determinism gate module
- VEIL event schema implementation and tests
