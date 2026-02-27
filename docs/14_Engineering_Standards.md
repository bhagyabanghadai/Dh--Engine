# Engineering Standards

## Objective
Establish implementation and delivery standards before code starts.

## Repository Standards
- Clear module boundaries by subsystem
- Schema/versioning strategy for manifests and events
- Minimal public interfaces with explicit contracts

## Code Quality
- Lint/typecheck required in CI
- Deterministic tests for policy and verification logic
- Security-sensitive paths require code owner review

## Branch and Review Policy
- Feature branches per milestone
- PR template must include security and verification impact section
- No merge without passing mandatory acceptance scenarios

## Release Policy
- Semantic versioning
- Changelog entry per release
- Backward compatibility notes for interface/schema changes

## Documentation Policy
- Any contract change requires doc update in same PR
- Architecture decision records for major design changes
