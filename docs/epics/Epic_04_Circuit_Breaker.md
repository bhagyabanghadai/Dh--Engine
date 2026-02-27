# Epic 4: Circuit Breaker and Autonomous Retry
**Status**: Blocked (Requires Epics 1, 2, and 3)
**Depends On**: Epics 1, 2, 3

## Goal
Implement bounded self-repair loop that retries only retryable failures and halts safely with explicit terminal state.

## In Scope
- Retry state machine
- Retry eligibility matrix
- Max attempt enforcement
- Final terminal/error contracts

## Out of Scope
- Graph-aware context retrieval
- VEIL memory persistence

## Retry Semantics (Locked)
- `max_attempts = 3` total attempts per request (attempts 1, 2, 3).
- Equivalent `max_retries = 2` after initial attempt.
- Any attempt beyond 3 is prohibited.

## Requirements
1. Implement orchestration loop in control plane:
   - `candidate_generated -> verification_running -> fail/pass -> retry_or_halt`
2. Implement deterministic repair prompt template using exact failure details.
3. Retry only for retryable failure classes:
   - `syntax`
   - `deterministic`
4. Do not retry for non-retryable classes/events:
   - `policy`
   - `timeout`
   - `flake` above threshold
   - `NetworkAccessViolation`
   - `StrictModeUnavailable`
   - `StrictModeRequired`
5. Emit terminal event on final fail:
   - `MaxRetriesExceeded`
6. Final response includes:
   - `attempt_count`
   - `retry_count`
   - `final_status`
   - `terminal_event` when applicable

## Exit Gates (Definition of Done)
- [ ] Known bad generation triggers retry flow.
- [ ] Fix on attempt 2 returns `retry_count=1` and pass manifest.
- [ ] Unfixable deterministic failure halts at attempt 3 with `MaxRetriesExceeded`.
- [ ] Non-retryable policy/timeout violations halt immediately.
- [ ] No code path allows unbounded retries.

## Artifacts Produced
- Circuit breaker state machine implementation
- Retry eligibility classifier
- Retry flow tests and terminal-state tests
