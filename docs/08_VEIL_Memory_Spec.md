# VEIL Memory Specification

## Objective
Define memory model, scoring, decay, and conflict resolution.

## Memory Types
- Episodic: per-run observations
- Semantic: compressed reusable rules

## Event Schema (Logical)
- Event metadata: ids, time, request link
- Context: symbols/files/checks
- Outcome: success/failure class
- Evidence: artifact references
- Determinism flag

## Scoring
- Base score from recency and reproducibility
- Boost for repeated confirmed patterns
- Decay over time to avoid stale lock-in

## Conflict Resolution
- Structural/verification evidence overrides memory
- New deterministic evidence demotes contradictory stale rules

## Compaction
- Periodic summarization job converts repeated episodic patterns into semantic rules
- Preserve source event links for auditability

## Retention
- Configurable TTL by event type
- Hard-delete expired raw events per governance policy
