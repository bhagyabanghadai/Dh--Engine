"""
Verification result schema for the Dhi sandbox contract.

All fields are required. No optional fields in the verification contract —
every execution must account for every field.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VerificationMode(str, Enum):
    """Runtime isolation mode for the sandbox."""

    fast = "fast"
    balanced = "balanced"
    strict = "strict"


class VerificationTier(str, Enum):
    """
    Verification tier indicating the quality of proof.
    AI_TESTS_ONLY means human review is required before trusting the result.
    """

    L0 = "L0"  # syntax / lint / type checks only
    L1 = "L1"  # pre-existing user tests passed
    L2 = "L2"  # integration / e2e passed
    AI_TESTS_ONLY = "AI_TESTS_ONLY"  # AI-generated tests, human review required


class FailureClass(str, Enum):
    """Canonical failure classification for retry eligibility decisions."""

    syntax = "syntax"          # Retryable: Python syntax / import errors
    policy = "policy"          # Non-retryable: security policy violation
    timeout = "timeout"        # Non-retryable: wall-clock or budget exceeded
    flake = "flake"            # Conditional retry: non-deterministic failure
    deterministic = "deterministic"  # Retryable: consistent logical failure


class ViolationEvent(str, Enum):
    """
    Canonical runtime violation event names.
    These are emitted when the sandbox kills the process due to a policy breach.
    """

    NetworkAccessViolation = "NetworkAccessViolation"
    FilesystemWriteViolation = "FilesystemWriteViolation"
    TimeoutViolation = "TimeoutViolation"
    ProcessLimitViolation = "ProcessLimitViolation"
    MemoryLimitViolation = "MemoryLimitViolation"
    OutputLimitViolation = "OutputLimitViolation"
    SyscallViolation = "SyscallViolation"
    StrictModeUnavailable = "StrictModeUnavailable"
    StrictModeRequired = "StrictModeRequired"
    MaxRetriesExceeded = "MaxRetriesExceeded"


class VerificationResult(BaseModel):
    """
    The canonical verification contract payload.
    Every field is required — no None values allowed in a well-formed result.
    Downstream consumers (Circuit Breaker, VEIL, UI) rely on all fields.
    """

    # Identity
    request_id: str = Field(description="Unique identifier for this request")
    attempt: int = Field(ge=1, le=3, description="Current attempt number (1-3)")
    schema_version: str = Field(default="1.0", description="Contract schema version")

    # Mode and tier
    mode: VerificationMode = Field(description="Runtime isolation mode used")
    tier: VerificationTier = Field(description="Verification tier achieved")

    # Outcome
    status: str = Field(description="Pass or fail: 'pass' | 'fail'")
    failure_class: FailureClass | None = Field(
        default=None,
        description="Failure classification; None when status is 'pass'",
    )
    terminal_event: ViolationEvent | None = Field(
        default=None,
        description="Terminal violation event if execution was killed by policy",
    )

    # Execution evidence — all required, empty string if not applicable
    exit_code: int = Field(description="Container exit code")
    duration_ms: int = Field(ge=0, description="Wall-clock duration in milliseconds")
    stdout: str = Field(description="Captured standard output (may be empty)")
    stderr: str = Field(description="Captured standard error (may be empty)")

    # Audit
    artifacts: list[str] = Field(
        default_factory=list,
        description="Paths to produced artifacts (logs, snapshots, etc.)",
    )
    skipped_checks: list[str] = Field(
        default_factory=list,
        description="Names of checks skipped in this run",
    )
    runtime_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of the runtime policy applied (limits, mounts, network)",
    )
