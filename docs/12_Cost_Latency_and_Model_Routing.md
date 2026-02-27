# Cost, Latency, and Model Routing Policy

## Objective
Control API cost and response time while preserving verification quality.

## Budgets
- Per-request token budget
- Per-request wall time budget
- Per-request retry budget

## Routing Policy
- Planner model (high capability): architecture and complex refactors
- Fixer model (low cost): traceback-driven repair loops
- Escalation: use planner only after fixer failure threshold

## Latency Controls
- Context pruning via graph retrieval
- Cache recent context per request window
- Parallelize independent local checks when safe

## Failure Handling
- 429/rate limit: exponential backoff with cap
- Budget exceeded: handoff with best candidate + manifest

## KPIs
- Cost/request by mode
- Tokens/request by mode
- p50/p95 response latency
- Retry distribution
