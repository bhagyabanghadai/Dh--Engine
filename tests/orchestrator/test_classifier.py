from __future__ import annotations

import pytest

from dhi.orchestrator.classifier import MAX_ATTEMPTS, classify
from dhi.sandbox.models import (
    FailureClass,
    VerificationMode,
    VerificationResult,
    VerificationTier,
    ViolationEvent,
)


def _make_result(
    *,
    status: str = "fail",
    failure_class: FailureClass | None = None,
    terminal_event: ViolationEvent | None = None,
    attempt: int = 1,
) -> VerificationResult:
    return VerificationResult(
        request_id="test-req",
        attempt=attempt,
        mode=VerificationMode.balanced,
        tier=VerificationTier.L0,
        status=status,
        failure_class=failure_class,
        terminal_event=terminal_event,
        exit_code=0 if status == "pass" else 1,
        duration_ms=100,
        stdout="out",
        stderr="err",
    )


def test_pass_never_retries() -> None:
    result = _make_result(status="pass")
    decision = classify(result=result, current_attempt=1)
    assert decision.should_retry is False
    assert "passed" in decision.reason.lower()


def test_max_attempts_halts() -> None:
    result = _make_result(failure_class=FailureClass.syntax)
    decision = classify(result=result, current_attempt=MAX_ATTEMPTS)
    assert decision.should_retry is False
    assert "max attempts" in decision.reason.lower()


def test_below_max_attempts_syntax_retries() -> None:
    result = _make_result(failure_class=FailureClass.syntax)
    decision = classify(result=result, current_attempt=1)
    assert decision.should_retry is True


@pytest.mark.parametrize("fc", [FailureClass.syntax, FailureClass.deterministic])
def test_retryable_classes(fc: FailureClass) -> None:
    result = _make_result(failure_class=fc)
    decision = classify(result=result, current_attempt=1)
    assert decision.should_retry is True


@pytest.mark.parametrize("fc", [FailureClass.policy, FailureClass.timeout, FailureClass.flake])
def test_non_retryable_classes(fc: FailureClass) -> None:
    result = _make_result(failure_class=fc)
    decision = classify(result=result, current_attempt=1)
    assert decision.should_retry is False


@pytest.mark.parametrize(
    "event",
    [
        ViolationEvent.NetworkAccessViolation,
        ViolationEvent.StrictModeUnavailable,
        ViolationEvent.StrictModeRequired,
        ViolationEvent.FilesystemWriteViolation,
        ViolationEvent.SyscallViolation,
    ],
)
def test_halt_on_violation_events(event: ViolationEvent) -> None:
    result = _make_result(
        failure_class=FailureClass.policy,
        terminal_event=event,
    )
    decision = classify(result=result, current_attempt=1)
    assert decision.should_retry is False
    assert "non-retryable" in decision.reason.lower()


def test_no_failure_class_halts() -> None:
    result = _make_result(status="fail", failure_class=None)
    decision = classify(result=result, current_attempt=1)
    assert decision.should_retry is False
    assert "fail-closed" in decision.reason.lower()
