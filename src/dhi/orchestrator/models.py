"""Pydantic models for the Orchestrator (Circuit Breaker) module."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from dhi.sandbox.models import VerificationResult, ViolationEvent


class AttemptRecord(BaseModel):
    """An immutable snapshot of a single generation and verification attempt."""

    attempt: int
    extraction_success: bool
    extraction_error: str | None = None
    verification_result: VerificationResult | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrchestrationResult(BaseModel):
    """The final aggregated outcome of the complete circuit breaker loop."""

    request_id: str

    # Attempt tracking
    attempt_count: int = Field(ge=1, le=3, description="How many attempts were made")
    retry_count: int = Field(ge=0, le=2, description="Number of retries (attempts minus 1)")

    # Final outcome
    final_status: str = Field(description="'pass' or 'fail'")
    terminal_event: ViolationEvent | None = Field(
        default=None,
        description="Populated when a non-retryable terminal event occurred",
    )

    # History
    attempts: list[AttemptRecord] = Field(
        default_factory=list,
        description="Full history of all attempts made",
    )
