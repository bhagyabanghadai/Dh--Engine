"""Determinism Gate for VEIL Memory Writes."""

from __future__ import annotations

from dhi.orchestrator.models import OrchestrationResult
from dhi.sandbox.models import FailureClass
from dhi.veil.fingerprint import EnvironmentFingerprint
from dhi.veil.models import GateDecision


class DeterminismGate:
    """
    Evaluates Orchestration execution results to determine if they contain
    actionable deterministic signal that VEIL memory should learn from.
    """

    def evaluate(
        self,
        result: OrchestrationResult,
        fingerprint: EnvironmentFingerprint,
        baseline: EnvironmentFingerprint,
    ) -> GateDecision:
        """
        Evaluate the run.
        1. Checks fingerprint parity.
        2. Filters out noise classes (timeout, flake, policy).
        3. Allows deterministic passes and deterministic failures.
        """
        if fingerprint != baseline:
            return GateDecision(
                passed=False,
                reason="fingerprint_mismatch",
                reproducible=False,
            )

        # To find the last noise class, look at the last attempt's verification result
        if not result.attempts:
            # Should not happen in a valid orchestration, but safe fallback
            return GateDecision(passed=False, reason="no_attempts", reproducible=False)

        last_verif = result.attempts[-1].verification_result
        if last_verif is None:
            return GateDecision(passed=False, reason="extraction_failed", reproducible=False)

        if result.final_status == "fail":
            fail_class = last_verif.failure_class
            if fail_class in (FailureClass.flake, FailureClass.timeout, FailureClass.policy):
                return GateDecision(
                    passed=False,
                    reason=f"noise:{fail_class.value}",
                    reproducible=False,
                )
            
            # Syntax / deterministic errors are useful negative signal for VEIL
            return GateDecision(
                passed=True,
                reason=f"deterministic_fail_{fail_class.value if fail_class else 'none'}",
                reproducible=False,
            )

        # outcome is "pass"
        is_reproducible = result.retry_count > 0
        return GateDecision(
            passed=True,
            reason="reproducible_pass" if is_reproducible else "deterministic_pass",
            reproducible=is_reproducible,
        )
