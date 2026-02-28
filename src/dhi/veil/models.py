"""VEIL Event Models for Memory and Telemetry."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from dhi.sandbox.models import FailureClass
from dhi.veil.fingerprint import EnvironmentFingerprint


class VeilEventType(str, Enum):
    """The type of VEIL event being recorded."""

    telemetry = "telemetry"
    behavioral = "behavioral"


class GateDecision(BaseModel):
    """The result of evaluating a run through the Determinism Gate."""

    passed: bool
    reason: str
    reproducible: bool


class _BaseVeilEvent(BaseModel):
    """Common fields for all VEIL events."""

    request_id: str
    timestamp: datetime
    outcome: str = Field(description="'pass' or 'fail'")
    failure_class: FailureClass | None
    attempt_count: int
    duration_ms: int


class TelemetryEvent(_BaseVeilEvent):
    """
    Lightweight event always written to record execution telemetry.
    These events are not used for learning behavioral rules if the run was noisy.
    """

    event_type: Literal[VeilEventType.telemetry] = VeilEventType.telemetry


class BehavioralEvent(_BaseVeilEvent):
    """
    Rich event written only when a run passes the Determinism Gate.
    These events form the episodic memory that is distilled into semantic memory.
    """

    event_type: Literal[VeilEventType.behavioral] = VeilEventType.behavioral
    fingerprint: EnvironmentFingerprint
