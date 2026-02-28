"""VEIL In-Process Ledger Storage."""

from __future__ import annotations

from datetime import datetime, timezone

from dhi.orchestrator.models import OrchestrationResult
from dhi.sandbox.models import FailureClass
from dhi.veil.fingerprint import EnvironmentFingerprint
from dhi.veil.models import BehavioralEvent, GateDecision, TelemetryEvent


class VeilLedger:
    """
    In-process, list-backed event store for VEIL.
    Writes telemetry for all runs, and behavioral events only for runs
    that pass the Determinism Gate.
    """

    def __init__(self) -> None:
        self._telemetry: list[TelemetryEvent] = []
        self._behavioral: list[BehavioralEvent] = []

    def write(
        self,
        decision: GateDecision,
        result: OrchestrationResult,
        fingerprint: EnvironmentFingerprint,
    ) -> None:
        """
        Write the orchestration outcome to the ledger.
        Always records Telemetry.
        Records Behavioral memory if `decision.passed` is True.
        """
        now = datetime.now(timezone.utc)
        
        # Extract fields from the last attempt if available
        failure_class: FailureClass | None = None
        duration_ms = 0
        if result.attempts:
            # sum durations to get total wall-clock time in sandbox
            duration_ms = sum(
                a.verification_result.duration_ms
                for a in result.attempts
                if a.verification_result
            )
            # get the final failure class
            last_verif = result.attempts[-1].verification_result
            if last_verif:
                failure_class = last_verif.failure_class

        # 1. Always write Telemetry
        telemetry_event = TelemetryEvent(
            request_id=result.request_id,
            timestamp=now,
            outcome=result.final_status,
            failure_class=failure_class,
            attempt_count=result.attempt_count,
            duration_ms=duration_ms,
        )
        self._telemetry.append(telemetry_event)

        # 2. Conditionally write Behavioral Memory
        if decision.passed:
            behavioral_event = BehavioralEvent(
                request_id=result.request_id,
                timestamp=now,
                outcome=result.final_status,
                failure_class=failure_class,
                attempt_count=result.attempt_count,
                duration_ms=duration_ms,
                fingerprint=fingerprint,
            )
            self._behavioral.append(behavioral_event)

    def read_telemetry(self) -> list[TelemetryEvent]:
        """Return all recorded telemetry events."""
        return list(self._telemetry)

    def read_behavioral(self) -> list[BehavioralEvent]:
        """Return all recorded behavioral memory events."""
        return list(self._behavioral)
