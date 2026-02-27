# Test Strategy and Acceptance Criteria

## Objective
Define how Dhi itself is validated before release.

## Test Layers
- Unit: policy evaluators, parsers, classifiers
- Integration: component contracts and state machine transitions
- End-to-end: full loop (`prompt -> patch -> verify -> attest`)
- Security: policy bypass and injection test cases

## Mandatory Acceptance Scenarios
1. Unmocked network call triggers `NetworkAccessViolation`
2. AI-generated tests only -> flagged for human review
3. Flaky test classification prevents false deterministic learning
4. Verification manifest includes complete command evidence
5. Retry budget exhaustion triggers safe handoff

## Quality Gates
- 100% manifest coverage in successful flows
- No critical/high security test failures
- Determinism gate pass rate above agreed threshold

## Release Exit Criteria
- All mandatory scenarios passing
- Runbook validated
- Threat model review complete

