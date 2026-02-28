"""Tests for VEIL Event Models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from dhi.sandbox.models import FailureClass
from dhi.veil.fingerprint import EnvironmentFingerprint
from dhi.veil.models import (
    BehavioralEvent,
    GateDecision,
    TelemetryEvent,
    VeilEventType,
)


def test_telemetry_event_valid() -> None:
    """Test valid TelemetryEvent instantiation."""
    event = TelemetryEvent(
        request_id="req-123",
        timestamp=datetime.now(timezone.utc),
        outcome="fail",
        failure_class=FailureClass.timeout,
        attempt_count=2,
        duration_ms=1500,
    )
    assert event.event_type == VeilEventType.telemetry
    assert event.request_id == "req-123"
    assert event.outcome == "fail"


def test_behavioral_event_valid() -> None:
    """Test valid BehavioralEvent instantiation."""
    fp = EnvironmentFingerprint.generate()
    event = BehavioralEvent(
        request_id="req-456",
        timestamp=datetime.now(timezone.utc),
        outcome="pass",
        failure_class=None,
        attempt_count=1,
        duration_ms=500,
        fingerprint=fp,
    )
    assert event.event_type == VeilEventType.behavioral
    assert event.request_id == "req-456"
    assert event.outcome == "pass"
    assert event.fingerprint == fp


def test_invalid_event_type() -> None:
    """Test that setting the wrong event type fails validation."""
    with pytest.raises(ValidationError):
        TelemetryEvent(
            event_type=VeilEventType.behavioral,  # type: ignore
            request_id="req-123",
            timestamp=datetime.now(timezone.utc),
            outcome="fail",
            failure_class=FailureClass.timeout,
            attempt_count=2,
            duration_ms=1500,
        )


def test_gate_decision() -> None:
    """Test GateDecision dataclass/model."""
    decision = GateDecision(
        passed=False,
        reason="noise:flake",
        reproducible=False,
    )
    assert not decision.passed
    assert decision.reason == "noise:flake"
    assert not decision.reproducible
