# Epic 8: Attestation, Verification Tiers, and Release Gates
**Status**: Blocked (Requires Epics 1-7)
**Depends On**: Epics 1, 2, 3, 4, 5, 6, 7

## Goal
Finalize trust contract by producing auditable attestation manifests with correct verification tiers and enforce release-quality acceptance gates.

## In Scope
- Attestation manifest builder
- Tier mapping (`L0`, `L1`, `L2`, `AI_TESTS_ONLY`)
- Release acceptance suite for v0.1

## Out of Scope
- Production deployment automation
- Multi-provider compliance exports

## Requirements
1. Build `attestation_manifest.json` generator with required fields:
   - IDs and timestamps
   - Commands, exit codes, durations
   - Tier achieved
   - Retries, skipped checks, failure class, terminal event
   - Artifact references
2. Implement tier mapping rules:
   - `L0`: parse/lint/type checks
   - `L1`: pre-existing unit tests
   - `L2`: pre-existing integration/e2e tests
   - `AI_TESTS_ONLY`: AI-authored tests only, with human review required label
3. Add release gate suite covering mandatory scenarios from architecture docs.
4. Block "verified" response labels when manifest is incomplete.

## Exit Gates (Definition of Done)
- [ ] Every successful response includes complete attestation manifest.
- [ ] Tier assignment is correct in integration tests.
- [ ] `AI_TESTS_ONLY` always includes human-review-required marker.
- [ ] Mandatory acceptance scenarios pass as a single gate suite.

## Artifacts Produced
- Attestation manifest module
- Tier classifier module
- Release gate test suite and checklist
