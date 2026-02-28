"""Attestation manifest builder for Dhi v0.1.

Produces auditable ``AttestationManifest`` records from sandbox
``VerificationResult`` artifacts.  Every successful response must carry
a complete manifest; the manifest is the trust contract proof.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from dhi.sandbox.models import (
    FailureClass,
    VerificationMode,
    VerificationResult,
    VerificationTier,
    ViolationEvent,
)

# Schema version increments when any field is added or renamed.
MANIFEST_SCHEMA_VERSION = "1.0"

# Sentinel tier string used before a manifest is attached to a response.
_UNVERIFIED_LABEL = "UNVERIFIED"


class ManifestIncompleteError(Exception):
    """Raised when caller tries to emit a 'verified' response without a manifest."""


class AttestationManifest(BaseModel):
    """Full trust contract proof for one completed request attempt.

    All fields are required.  A downstream consumer that receives a response
    without a manifest MUST treat the result as *unverified*.
    """

    # --- Identity ---
    request_id: str = Field(description="Unique ID from the originating request")
    attempt: int = Field(ge=1, le=3, description="Attempt number that produced this manifest")
    schema_version: str = Field(
        default=MANIFEST_SCHEMA_VERSION, description="Manifest schema version"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of manifest creation",
    )

    # --- Verification tier ---
    tier: VerificationTier = Field(description="Highest tier of evidence achieved")
    human_review_required: bool = Field(
        description=(
            "True when tier is AI_TESTS_ONLY. "
            "Response MUST NOT be labelled 'verified' without human sign-off."
        )
    )

    # --- Execution evidence ---
    mode: VerificationMode = Field(description="Runtime isolation mode used")
    exit_code: int = Field(description="Container exit code")
    duration_ms: int = Field(ge=0, description="Wall-clock duration in milliseconds")

    # --- Commands run ---
    commands_run: list[str] = Field(
        default_factory=list,
        description="Ordered list of commands executed inside the sandbox",
    )

    # --- Outcome ---
    status: str = Field(description="'pass' or 'fail'")
    failure_class: FailureClass | None = Field(
        default=None, description="Failure class; None on pass"
    )
    terminal_event: ViolationEvent | None = Field(
        default=None, description="Terminal violation event if execution was killed"
    )

    # --- Retry context ---
    retries_used: int = Field(ge=0, description="Number of retry attempts consumed (0-2)")

    # --- Skipped checks and artifacts ---
    skipped_checks: list[str] = Field(
        default_factory=list,
        description="Named checks that were intentionally omitted from this run",
    )
    artifact_refs: list[str] = Field(
        default_factory=list,
        description="Paths to produced artifacts (logs, snapshots, coverage files)",
    )

    # --- Runtime config snapshot ---
    runtime_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of runtime policy applied (limits, mounts, network policy)",
    )


def build_manifest(
    *,
    result: VerificationResult,
    retries_used: int = 0,
    commands_run: list[str] | None = None,
) -> AttestationManifest:
    """Construct a complete ``AttestationManifest`` from a ``VerificationResult``.

    Args:
        result: The canonical sandbox verification result.
        retries_used: How many retries were consumed before this result (0–2).
        commands_run: Optional explicit command list. Falls back to inferring
            from ``result.runtime_config`` when omitted.

    Returns:
        A fully populated ``AttestationManifest``.
    """
    from dhi.attestation.tier_mapper import map_tier  # local import avoids circularity

    tier = map_tier(result)

    return AttestationManifest(
        request_id=result.request_id,
        attempt=result.attempt,
        tier=tier,
        human_review_required=(tier == VerificationTier.AI_TESTS_ONLY),
        mode=result.mode,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        commands_run=commands_run or _infer_commands(result),
        status=result.status,
        failure_class=result.failure_class,
        terminal_event=result.terminal_event,
        retries_used=retries_used,
        skipped_checks=list(result.skipped_checks),
        artifact_refs=list(result.artifacts),
        runtime_config=dict(result.runtime_config),
    )


def assert_manifest_complete(manifest: AttestationManifest | None) -> AttestationManifest:
    """Raise ``ManifestIncompleteError`` if manifest is missing or incomplete.

    Call this before attaching a *'verified'* label to any response.
    """
    if manifest is None:
        raise ManifestIncompleteError(
            "Cannot label response as 'verified': attestation manifest is missing. "
            "All verified responses require a complete AttestationManifest."
        )

    required_non_empty = [
        ("request_id", manifest.request_id),
        ("status", manifest.status),
    ]
    for field_name, value in required_non_empty:
        if not value:
            raise ManifestIncompleteError(
                f"Cannot label response as 'verified': manifest field '{field_name}' is empty."
            )

    if manifest.human_review_required:
        # We don't block — but the caller must propagate this flag.
        pass

    return manifest


def _infer_commands(result: VerificationResult) -> list[str]:
    """Best-effort reconstruction of commands from runtime_config."""
    cfg = result.runtime_config
    if not cfg:
        return []
    cmds: list[str] = []
    if cmd := cfg.get("command"):
        cmds.append(str(cmd))
    return cmds
