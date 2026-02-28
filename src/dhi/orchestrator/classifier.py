"""Retry eligibility classifier for the Circuit Breaker."""

from __future__ import annotations

from dhi.sandbox.models import FailureClass, VerificationResult, ViolationEvent

# Failure classes that allow retry
RETRYABLE_FAILURE_CLASSES: frozenset[FailureClass] = frozenset({
    FailureClass.syntax,
    FailureClass.deterministic,
})

# Violation events that always trigger an immediate halt — no retry
UNRETRYABLE_VIOLATION_EVENTS: frozenset[ViolationEvent] = frozenset({
    ViolationEvent.NetworkAccessViolation,
    ViolationEvent.StrictModeUnavailable,
    ViolationEvent.StrictModeRequired,
    ViolationEvent.FilesystemWriteViolation,
    ViolationEvent.SyscallViolation,
    ViolationEvent.ProcessLimitViolation,
    ViolationEvent.MemoryLimitViolation,
    ViolationEvent.OutputLimitViolation,
})

MAX_ATTEMPTS = 3


class RetryDecision:
    """Encapsulates a retry eligibility decision with its reason."""

    def __init__(self, *, should_retry: bool, reason: str) -> None:
        self.should_retry = should_retry
        self.reason = reason

    def __bool__(self) -> bool:
        return self.should_retry

    def __repr__(self) -> str:
        return f"RetryDecision(should_retry={self.should_retry}, reason={self.reason!r})"


def classify(
    result: VerificationResult,
    current_attempt: int,
) -> RetryDecision:
    """
    Determine whether a failed verification result warrants a retry.

    Rules (evaluated in priority order):
    1. Passed results never retry.
    2. Attempts >= MAX_ATTEMPTS: halt with MaxRetriesExceeded.
    3. Terminal policy violation events: halt immediately.
    4. Non-retryable failure classes (policy, timeout): halt.
    5. Flake: halt (no threshold support in v0.1 — always halt).
    6. Retryable failure classes (syntax, deterministic): retry.
    7. Unknown failure class or unclassified fail: halt (fail-closed).
    """

    # 1. Pass → no retry needed
    if result.status == "pass":
        return RetryDecision(should_retry=False, reason="Verification passed. No retry needed.")

    # 2. Hard attempt ceiling
    if current_attempt >= MAX_ATTEMPTS:
        return RetryDecision(
            should_retry=False,
            reason=f"Max attempts reached ({MAX_ATTEMPTS}). Emitting MaxRetriesExceeded.",
        )

    # 3. Unretryable terminal violation events
    if result.terminal_event is not None:
        if result.terminal_event in UNRETRYABLE_VIOLATION_EVENTS:
            return RetryDecision(
                should_retry=False,
                reason=f"Terminal violation event '{result.terminal_event}' is non-retryable.",
            )

    # 4 & 5. Check failure class
    fc = result.failure_class
    if fc is None:
        return RetryDecision(
            should_retry=False,
            reason="No failure_class set on failed result. Halting (fail-closed).",
        )

    if fc in RETRYABLE_FAILURE_CLASSES:
        return RetryDecision(
            should_retry=True,
            reason=f"Failure class '{fc}' is retryable. Scheduling attempt {current_attempt + 1}.",
        )

    # Non-retryable: policy, timeout, flake
    return RetryDecision(
        should_retry=False,
        reason=f"Failure class '{fc}' is non-retryable. Halting.",
    )
