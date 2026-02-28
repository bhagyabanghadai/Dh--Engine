"""Pydantic models for the cloud interceptor module."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ContextPayload(BaseModel):
    """Inbound payload containing request metadata and context."""

    request_id: str = Field(description="Unique identifier for this request")
    attempt: int = Field(ge=1, le=3, description="Current attempt number (1-3)")
    files: list[str] = Field(default_factory=list, description="Context file paths")
    content: str = Field(description="Prompt plus context content")


class GovernanceAuditRecord(BaseModel):
    """Audit record for pre-egress governance checks."""

    request_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    file_count: int = 0
    redaction_count: int = 0
    high_entropy_redaction_count: int = 0
    prompt_minimized: bool = False
    blocked: bool = Field(default=False, description="Whether egress was blocked")
    block_reason: str | None = None
    secret_leak_detected: bool = Field(
        default=False,
        description="True when a confirmed secret pattern was found and redacted (CRITICAL)",
    )
    bytes_sent: int = Field(
        default=0,
        description="Length in bytes of the outbound payload content after governance processing",
    )

    @property
    def redactions_made(self) -> int:
        """Backward-compatible alias used by earlier drafts."""
        return self.redaction_count


class LLMResponse(BaseModel):
    """Structured JSON response expected from the LLM."""

    language: str
    code: str
    notes: str


class ExtractionResult(BaseModel):
    """Result of extracting candidate code from the LLM output."""

    success: bool
    code: str
    language: str | None = None
    notes: str = ""
    fallback_used: bool = False
    error: str | None = None


class CandidatePayload(BaseModel):
    """Validated candidate code ready for sandbox handoff."""

    request_id: str
    code: str
    notes: str
    audit_record: GovernanceAuditRecord