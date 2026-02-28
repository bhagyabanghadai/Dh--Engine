"""Tests for the VEIL Determinism Gate."""

from datetime import datetime, timezone

from dhi.orchestrator.models import AttemptRecord, OrchestrationResult
from dhi.sandbox.models import FailureClass, VerificationMode, VerificationResult, VerificationTier
from dhi.veil.fingerprint import EnvironmentFingerprint
from dhi.veil.gate import DeterminismGate


def _mock_verification(
    status: str,
    failure_class: FailureClass | None = None,
) -> VerificationResult:
    return VerificationResult(
        request_id="req-1",
        attempt=1,
        mode=VerificationMode.fast,
        tier=VerificationTier.L0,
        status=status,
        failure_class=failure_class,
        exit_code=0 if status == "pass" else 1,
        duration_ms=100,
        stdout="",
        stderr="",
    )


def _mock_orchestration(
    final_status: str,
    failure_class: FailureClass | None = None,
    retry_count: int = 0,
) -> OrchestrationResult:
    verification = _mock_verification(status=final_status, failure_class=failure_class)
    attempt = AttemptRecord(
        attempt=1,
        extraction_success=True,
        verification_result=verification,
        timestamp=datetime.now(timezone.utc),
    )
    return OrchestrationResult(
        request_id="req-1",
        attempt_count=retry_count + 1,
        retry_count=retry_count,
        final_status=final_status,
        attempts=[attempt],
    )


def test_gate_pass_deterministic_success() -> None:
    """Test that a clean pass goes through the gate as behavioral memory."""
    gate = DeterminismGate()
    fp = EnvironmentFingerprint.generate()
    result = _mock_orchestration(final_status="pass")

    decision = gate.evaluate(result, fingerprint=fp, baseline=fp)

    assert decision.passed
    assert decision.reason == "deterministic_pass"
    assert not decision.reproducible  # no retries happened


def test_gate_pass_reproducible_success() -> None:
    """Test that a pass after retries is marked reproducible."""
    gate = DeterminismGate()
    fp = EnvironmentFingerprint.generate()
    # It failed initially but eventually passed after retries
    result = _mock_orchestration(final_status="pass", retry_count=1)

    decision = gate.evaluate(result, fingerprint=fp, baseline=fp)

    assert decision.passed
    assert decision.reason == "reproducible_pass"
    assert decision.reproducible


def test_gate_fail_fingerprint_mismatch() -> None:
    """Test that mismatched environment fingerprints fail the gate."""
    gate = DeterminismGate()
    fp1 = EnvironmentFingerprint.generate()
    fp2 = EnvironmentFingerprint(
        runtime_image_digest=fp1.runtime_image_digest,
        python_version=fp1.python_version,
        lockfile_hash="different",
        command_set_hash=fp1.command_set_hash,
        env_var_names_hash=fp1.env_var_names_hash,
    )
    result = _mock_orchestration(final_status="pass")

    decision = gate.evaluate(result, fingerprint=fp1, baseline=fp2)

    assert not decision.passed
    assert decision.reason == "fingerprint_mismatch"


def test_gate_fail_noise_classes() -> None:
    """Test that noisy failures (flake, timeout, policy) fail the gate."""
    gate = DeterminismGate()
    fp = EnvironmentFingerprint.generate()

    for fail_class in [FailureClass.flake, FailureClass.timeout, FailureClass.policy]:
        result = _mock_orchestration(final_status="fail", failure_class=fail_class)
        decision = gate.evaluate(result, fingerprint=fp, baseline=fp)

        assert not decision.passed
        assert decision.reason == f"noise:{fail_class.value}"


def test_gate_pass_deterministic_failure() -> None:
    """Test that deterministic logic/syntax failures go through to memory."""
    gate = DeterminismGate()
    fp = EnvironmentFingerprint.generate()

    for fail_class in [FailureClass.syntax, FailureClass.deterministic]:
        result = _mock_orchestration(final_status="fail", failure_class=fail_class)
        decision = gate.evaluate(result, fingerprint=fp, baseline=fp)

        assert decision.passed
        assert decision.reason == f"deterministic_fail_{fail_class.value}"
