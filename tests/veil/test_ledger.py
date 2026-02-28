"""Tests for the VEIL In-Process Ledger."""

from datetime import datetime, timezone

from dhi.orchestrator.models import AttemptRecord, OrchestrationResult
from dhi.sandbox.models import FailureClass, VerificationMode, VerificationResult, VerificationTier
from dhi.veil.fingerprint import EnvironmentFingerprint
from dhi.veil.gate import DeterminismGate
from dhi.veil.ledger import VeilLedger


def _mock_orchestration(
    final_status: str,
    failure_class: FailureClass | None = None,
) -> OrchestrationResult:
    verification = VerificationResult(
        request_id="req-1",
        attempt=1,
        mode=VerificationMode.fast,
        tier=VerificationTier.L0,
        status=final_status,
        failure_class=failure_class,
        exit_code=0 if final_status == "pass" else 1,
        duration_ms=100,
        stdout="",
        stderr="",
    )
    attempt = AttemptRecord(
        attempt=1,
        extraction_success=True,
        verification_result=verification,
        timestamp=datetime.now(timezone.utc),
    )
    return OrchestrationResult(
        request_id="req-1",
        attempt_count=1,
        retry_count=0,
        final_status=final_status,
        attempts=[attempt],
    )


def test_ledger_gate_pass() -> None:
    """Test that a gate pass writes both telemetry and behavioral events."""
    ledger = VeilLedger()
    gate = DeterminismGate()
    fp = EnvironmentFingerprint.generate()
    
    result = _mock_orchestration(final_status="pass")
    decision = gate.evaluate(result, fingerprint=fp, baseline=fp)
    
    ledger.write(decision=decision, result=result, fingerprint=fp)
    
    telemetry = ledger.read_telemetry()
    behavioral = ledger.read_behavioral()
    
    assert len(telemetry) == 1
    assert len(behavioral) == 1
    
    assert telemetry[0].request_id == "req-1"
    assert telemetry[0].outcome == "pass"
    
    assert behavioral[0].request_id == "req-1"
    assert behavioral[0].outcome == "pass"
    assert behavioral[0].fingerprint == fp


def test_ledger_gate_fail() -> None:
    """Test that a gate fail writes ONLY a telemetry event."""
    ledger = VeilLedger()
    gate = DeterminismGate()
    fp = EnvironmentFingerprint.generate()
    
    # Flake is a noise class, so the gate will fail it
    result = _mock_orchestration(final_status="fail", failure_class=FailureClass.flake)
    decision = gate.evaluate(result, fingerprint=fp, baseline=fp)
    
    assert not decision.passed
    
    ledger.write(decision=decision, result=result, fingerprint=fp)
    
    telemetry = ledger.read_telemetry()
    behavioral = ledger.read_behavioral()
    
    assert len(telemetry) == 1
    assert len(behavioral) == 0  # No behavioral memory for noise
    
    assert telemetry[0].outcome == "fail"
    assert telemetry[0].failure_class == FailureClass.flake
