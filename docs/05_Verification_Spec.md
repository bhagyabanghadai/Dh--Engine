# Verification Specification

## Objective
Define precise verification behavior and output semantics.

## Verification Tiers
- L0: parse, lint, static type checks
- L1: pre-existing user-authored unit tests
- L2: pre-existing user-authored integration/e2e tests
- AI_TESTS_ONLY: only AI-authored tests passed (requires human review)

## Rules
- Tier claim must be backed by executed command logs and exit codes
- Missing/Skipped checks must be explicitly recorded with reason
- No "verified" label without manifest

## Retry Policy
- Max attempts: 3 (default)
- Retry only for retryable classes: syntax, deterministic failure
- Do not retry policy violations until context/policy adjusted

## Flake Handling
- Flake threshold policy: configurable by project
- Flaky failures are tagged and excluded from deterministic memory write

## Manifest Requirements
- Request/candidate IDs
- Commands, durations, exit codes
- Tier achieved
- Skipped checks and reasons
- Artifacts and paths
- Final disposition (pass/fail/handoff)
