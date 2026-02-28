"""Integration tests for OrchestratorService with multi-attempt sequences."""

from __future__ import annotations

from unittest.mock import patch

from dhi.interceptor.service import InterceptorResponse
from dhi.orchestrator.models import OrchestrationResult
from dhi.orchestrator.service import OrchestratorService
from dhi.sandbox.models import (
    FailureClass,
    VerificationMode,
    VerificationResult,
    VerificationTier,
    ViolationEvent,
)


def _make_interceptor_response(
    *,
    status: str = "fail",
    failure_class: FailureClass | None = None,
    terminal_event: ViolationEvent | None = None,
    extraction_success: bool = True,
    extraction_error: str | None = None,
    attempt: int = 1,
) -> InterceptorResponse:
    from dhi.interceptor.models import GovernanceAuditRecord

    audit = GovernanceAuditRecord(request_id="req-test")

    if extraction_success:
        vresult = VerificationResult(
            request_id="req-test",
            attempt=attempt,
            mode=VerificationMode.balanced,
            tier=VerificationTier.L0,
            status=status,
            failure_class=failure_class,
            terminal_event=terminal_event,
            exit_code=0 if status == "pass" else 1,
            duration_ms=50,
            stdout="",
            stderr="error output",
        )
    else:
        vresult = None

    return InterceptorResponse(
        request_id="req-test",
        audit=audit,
        llm_notes="",
        extraction_success=extraction_success,
        extraction_error=extraction_error,
        verification_result=vresult,
    )


class TestOrchestratorService:
    """Sequence tests for the circuit breaker loop."""

    def _run(self, side_effects: list[InterceptorResponse]) -> OrchestrationResult:
        svc = OrchestratorService()
        with patch.object(svc._interceptor, "process_request", side_effect=side_effects):
            return svc.run(request_id="req-test", content="Write a hello world function")

    def test_pass_on_first_attempt(self) -> None:
        result = self._run([
            _make_interceptor_response(status="pass", attempt=1),
        ])
        assert result.final_status == "pass"
        assert result.attempt_count == 1
        assert result.retry_count == 0
        assert result.terminal_event is None

    def test_fix_on_second_attempt(self) -> None:
        result = self._run([
            _make_interceptor_response(
                status="fail",
                failure_class=FailureClass.syntax,
                attempt=1,
            ),
            _make_interceptor_response(status="pass", attempt=2),
        ])
        assert result.final_status == "pass"
        assert result.attempt_count == 2
        assert result.retry_count == 1
        assert result.terminal_event is None

    def test_max_retries_exceeded(self) -> None:
        result = self._run([
            _make_interceptor_response(
                status="fail",
                failure_class=FailureClass.syntax,
                attempt=1,
            ),
            _make_interceptor_response(
                status="fail",
                failure_class=FailureClass.syntax,
                attempt=2,
            ),
            _make_interceptor_response(
                status="fail",
                failure_class=FailureClass.syntax,
                attempt=3,
            ),
        ])
        assert result.final_status == "fail"
        assert result.attempt_count == 3
        assert result.retry_count == 2
        assert result.terminal_event == ViolationEvent.MaxRetriesExceeded

    def test_policy_halt_immediately(self) -> None:
        result = self._run([
            _make_interceptor_response(
                status="fail",
                failure_class=FailureClass.policy,
                attempt=1,
            ),
        ])
        assert result.final_status == "fail"
        assert result.attempt_count == 1
        assert result.retry_count == 0
        assert result.terminal_event is None

    def test_network_violation_halts(self) -> None:
        result = self._run([
            _make_interceptor_response(
                status="fail",
                failure_class=FailureClass.policy,
                terminal_event=ViolationEvent.NetworkAccessViolation,
                attempt=1,
            ),
        ])
        assert result.final_status == "fail"
        assert result.attempt_count == 1
        assert result.terminal_event == ViolationEvent.NetworkAccessViolation

    def test_extraction_failure_halts(self) -> None:
        result = self._run([
            _make_interceptor_response(
                extraction_success=False,
                extraction_error="Could not extract code",
                attempt=1,
            ),
        ])
        assert result.final_status == "fail"
        assert result.attempt_count == 1
        assert result.retry_count == 0

    def test_syntax_extraction_failure_retries_then_pass(self) -> None:
        result = self._run([
            _make_interceptor_response(
                extraction_success=False,
                extraction_error="SyntaxError at line 1, offset 5: invalid syntax",
                attempt=1,
            ),
            _make_interceptor_response(status="pass", attempt=2),
        ])
        assert result.final_status == "pass"
        assert result.attempt_count == 2
        assert result.retry_count == 1
        assert result.terminal_event is None
        assert result.attempts[0].verification_result is not None
        assert result.attempts[0].verification_result.failure_class == FailureClass.syntax

    def test_syntax_extraction_failure_max_retries_exceeded(self) -> None:
        result = self._run([
            _make_interceptor_response(
                extraction_success=False,
                extraction_error="SyntaxError at line 1, offset 2: invalid syntax",
                attempt=1,
            ),
            _make_interceptor_response(
                extraction_success=False,
                extraction_error="SyntaxError at line 1, offset 2: invalid syntax",
                attempt=2,
            ),
            _make_interceptor_response(
                extraction_success=False,
                extraction_error="SyntaxError at line 1, offset 2: invalid syntax",
                attempt=3,
            ),
        ])
        assert result.final_status == "fail"
        assert result.attempt_count == 3
        assert result.retry_count == 2
        assert result.terminal_event == ViolationEvent.MaxRetriesExceeded

    def test_deterministic_fail_then_pass(self) -> None:
        result = self._run([
            _make_interceptor_response(
                status="fail",
                failure_class=FailureClass.deterministic,
                attempt=1,
            ),
            _make_interceptor_response(status="pass", attempt=2),
        ])
        assert result.attempt_count == 2
        assert result.retry_count == 1

    def test_veil_integration_pass(self) -> None:
        """Verify VEIL gate and ledger are called on orchestrator finish."""
        from dhi.veil.gate import DeterminismGate
        from dhi.veil.ledger import VeilLedger

        gate = DeterminismGate()
        ledger = VeilLedger()
        svc = OrchestratorService(gate=gate, ledger=ledger)

        with patch.object(
            svc._interceptor,
            "process_request",
            return_value=_make_interceptor_response(status="pass", attempt=1),
        ):
            result = svc.run(request_id="req-veil", content="print(1)")

        assert result.final_status == "pass"

        telemetry = ledger.read_telemetry()
        behavioral = ledger.read_behavioral()

        assert len(telemetry) == 1
        assert len(behavioral) == 1
        assert telemetry[0].request_id == "req-veil"
        assert behavioral[0].request_id == "req-veil"

    def test_veil_integration_fail_noise(self) -> None:
        """Verify VEIL gate filters out noise and only records telemetry."""
        from dhi.veil.gate import DeterminismGate
        from dhi.veil.ledger import VeilLedger

        gate = DeterminismGate()
        ledger = VeilLedger()
        svc = OrchestratorService(gate=gate, ledger=ledger)

        with patch.object(
            svc._interceptor,
            "process_request",
            return_value=_make_interceptor_response(
                status="fail",
                failure_class=FailureClass.flake,
                attempt=1,
            ),
        ):
            result = svc.run(request_id="req-veil-flake", content="print(1)")

        assert result.final_status == "fail"

        telemetry = ledger.read_telemetry()
        behavioral = ledger.read_behavioral()

        assert len(telemetry) == 1
        assert len(behavioral) == 0
        assert telemetry[0].request_id == "req-veil-flake"
        assert telemetry[0].failure_class == FailureClass.flake
