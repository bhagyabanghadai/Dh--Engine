# Epic 4: The Circuit Breaker & Autonomous Retry
**Status**: Blocked (Requires Epics 1, 2, & 3)

## Goal
Implement the autonomous self-repair loop. When the Sandbox rejects LLM-generated code, Dhi must take the error traceback, append it to a new prompt, and ask the LLM to fix it—halting if it fails 3 times.

## Requirements
1. **The State Machine:** Write the Orchestration Loop in `FastAPI`. 
2. **The Fix Prompt:** Compile a deterministic "Repair Prompt" template: *"Your code failed with this exact error: {traceback}. Fix the bug."*
3. **The Retry Limits:** Implement a hard-coded integer counter. `MAX_RETRIES = 3`. 
4. **Error Classification:** Write logic that reads the Sandbox output. If the failure is a `TimeoutViolation` or `NetworkAccessViolation`, halt immediately. Only retry on standard test/syntax failures.

## Exit Gates (Definition of Done)
- [ ] Sending a prompt that forces the AI to write bad code triggers the retry loop.
- [ ] Dhi successfully parses the error, resubmits it, and validates the fixed code on Attempt 2.
- [ ] The final manifest returned to the user shows `"retry_count": 1` and provides the final verified code.
- [ ] Simulating an unfixable structural failure results in Dhi halting exactly at 3 retries and returning a `MaxRetriesExceeded` error to the user.
