"""Release gate test suite for Dhi v0.1 — Epic 8.

Covers:
  - AttestationManifest builder correctness
  - VerificationTier mapping (L0 / L1 / L2 / AI_TESTS_ONLY)
  - assert_manifest_complete guard (blocks unverified label)
  - Mandatory acceptance scenarios from architecture docs
"""

from __future__ import annotations

import pytest

from dhi.attestation.manifest import (
    AttestationManifest,
    ManifestIncompleteError,
    assert_manifest_complete,
    build_manifest,
)
from dhi.attestation.tier_mapper import map_tier
from dhi.sandbox.models import (
    FailureClass,
    VerificationMode,
    VerificationResult,
    VerificationTier,
    ViolationEvent,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    *,
    status: str = "pass",
    tier: VerificationTier = VerificationTier.L0,
    exit_code: int = 0,
    duration_ms: int = 120,
    failure_class: FailureClass | None = None,
    terminal_event: ViolationEvent | None = None,
    skipped_checks: list[str] | None = None,
    artifacts: list[str] | None = None,
    runtime_config: dict[str, object] | None = None,
    request_id: str = "req-test",
    attempt: int = 1,
    mode: VerificationMode = VerificationMode.balanced,
) -> VerificationResult:
    return VerificationResult(
        request_id=request_id,
        attempt=attempt,
        mode=mode,
        tier=tier,
        status=status,
        exit_code=exit_code,
        duration_ms=duration_ms,
        stdout="",
        stderr="",
        failure_class=failure_class,
        terminal_event=terminal_event,
        skipped_checks=skipped_checks or [],
        artifacts=artifacts or [],
        runtime_config=runtime_config or {},
    )


# ---------------------------------------------------------------------------
# E8.2 — Tier mapper
# ---------------------------------------------------------------------------


def test_tier_mapper_l0_default() -> None:
    result = _make_result(tier=VerificationTier.L0)
    assert map_tier(result) == VerificationTier.L0


def test_tier_mapper_l1_from_result_tier() -> None:
    result = _make_result(tier=VerificationTier.L1, status="pass")
    assert map_tier(result) == VerificationTier.L1


def test_tier_mapper_l2_from_result_tier() -> None:
    result = _make_result(tier=VerificationTier.L2, status="pass")
    assert map_tier(result) == VerificationTier.L2


def test_tier_mapper_l1_from_runtime_config() -> None:
    result = _make_result(
        tier=VerificationTier.L0,
        status="pass",
        runtime_config={"user_tests": True},
    )
    assert map_tier(result) == VerificationTier.L1


def test_tier_mapper_l2_from_runtime_config() -> None:
    result = _make_result(
        tier=VerificationTier.L0,
        status="pass",
        runtime_config={"integration_tests": True},
    )
    assert map_tier(result) == VerificationTier.L2


def test_tier_mapper_ai_tests_only_from_skipped() -> None:
    """AI_TESTS_ONLY tier detected via skipped_checks sentinel."""
    result = _make_result(
        tier=VerificationTier.AI_TESTS_ONLY,
        skipped_checks=["ai_tests_only"],
    )
    assert map_tier(result) == VerificationTier.AI_TESTS_ONLY


def test_tier_mapper_ai_tests_only_takes_priority_over_l1() -> None:
    """AI_TESTS_ONLY beats L1 even when user_tests flag is set."""
    result = _make_result(
        tier=VerificationTier.AI_TESTS_ONLY,
        skipped_checks=["ai_tests_only"],
        runtime_config={"user_tests": True},
    )
    assert map_tier(result) == VerificationTier.AI_TESTS_ONLY


def test_tier_mapper_l1_not_assigned_on_fail() -> None:
    """L1 is not assigned when the result is a failure."""
    result = _make_result(
        tier=VerificationTier.L1,
        status="fail",
        exit_code=1,
        failure_class=FailureClass.deterministic,
        runtime_config={"user_tests": True},
    )
    assert map_tier(result) == VerificationTier.L0


# ---------------------------------------------------------------------------
# E8.1 — Manifest builder
# ---------------------------------------------------------------------------


def test_build_manifest_populates_all_required_fields() -> None:
    result = _make_result(
        request_id="req-manifest",
        attempt=2,
        tier=VerificationTier.L1,
        status="pass",
        exit_code=0,
        duration_ms=450,
        artifacts=["logs/run.log"],
        runtime_config={"cpu": "2vCPU", "mem": "1024MB"},
    )
    manifest = build_manifest(result=result, retries_used=1)

    assert manifest.request_id == "req-manifest"
    assert manifest.attempt == 2
    assert manifest.tier == VerificationTier.L1
    assert manifest.human_review_required is False
    assert manifest.status == "pass"
    assert manifest.exit_code == 0
    assert manifest.duration_ms == 450
    assert manifest.retries_used == 1
    assert "logs/run.log" in manifest.artifact_refs
    assert manifest.runtime_config["cpu"] == "2vCPU"
    assert manifest.schema_version == "1.0"
    assert manifest.created_at is not None


def test_build_manifest_ai_tests_only_sets_human_review() -> None:
    """AI_TESTS_ONLY must always have human_review_required=True."""
    result = _make_result(
        tier=VerificationTier.AI_TESTS_ONLY,
        skipped_checks=["ai_tests_only"],
    )
    manifest = build_manifest(result=result)

    assert manifest.tier == VerificationTier.AI_TESTS_ONLY
    assert manifest.human_review_required is True


def test_build_manifest_with_explicit_commands() -> None:
    result = _make_result()
    manifest = build_manifest(result=result, commands_run=["pytest tests/", "ruff check ."])
    assert manifest.commands_run == ["pytest tests/", "ruff check ."]


# ---------------------------------------------------------------------------
# E8.3 — assert_manifest_complete guard
# ---------------------------------------------------------------------------


def test_assert_manifest_complete_passes_for_valid() -> None:
    result = _make_result(tier=VerificationTier.L0, status="pass")
    manifest = build_manifest(result=result)
    returned = assert_manifest_complete(manifest)
    assert returned is manifest


def test_assert_manifest_complete_raises_for_none() -> None:
    """Verified label must be blocked when manifest is None."""
    with pytest.raises(ManifestIncompleteError, match="missing"):
        assert_manifest_complete(None)


def test_assert_manifest_complete_raises_for_empty_request_id() -> None:
    result = _make_result(request_id="req-empty-id")
    manifest = build_manifest(result=result)
    # Corrupt the field to simulate a bad manifest
    manifest_dict = manifest.model_dump()
    manifest_dict["request_id"] = ""
    bad_manifest = AttestationManifest(**manifest_dict)
    with pytest.raises(ManifestIncompleteError, match="request_id"):
        assert_manifest_complete(bad_manifest)


# ---------------------------------------------------------------------------
# Mandatory acceptance scenarios (from docs/15_Team_and_Execution_Plan.md §8)
# ---------------------------------------------------------------------------


def test_scenario_network_access_violation_classified() -> None:
    """Network egress attempt → NetworkAccessViolation + policy failure class."""
    result = _make_result(
        status="fail",
        exit_code=1,
        terminal_event=ViolationEvent.NetworkAccessViolation,
        failure_class=FailureClass.policy,
    )
    manifest = build_manifest(result=result)

    assert manifest.terminal_event == ViolationEvent.NetworkAccessViolation
    assert manifest.failure_class == FailureClass.policy
    assert manifest.status == "fail"


def test_scenario_filesystem_write_violation_classified() -> None:
    """Read-only source write attempt → FilesystemWriteViolation."""
    result = _make_result(
        status="fail",
        exit_code=1,
        terminal_event=ViolationEvent.FilesystemWriteViolation,
        failure_class=FailureClass.policy,
    )
    manifest = build_manifest(result=result)
    assert manifest.terminal_event == ViolationEvent.FilesystemWriteViolation


def test_scenario_timeout_classified() -> None:
    """Timeout / hang → TimeoutViolation + timeout failure class."""
    result = _make_result(
        status="fail",
        exit_code=1,
        terminal_event=ViolationEvent.TimeoutViolation,
        failure_class=FailureClass.timeout,
    )
    manifest = build_manifest(result=result)
    assert manifest.terminal_event == ViolationEvent.TimeoutViolation
    assert manifest.failure_class == FailureClass.timeout


def test_scenario_ai_tests_only_requires_human_review_marker() -> None:
    """AI-authored tests only → AI_TESTS_ONLY tier + human_review_required=True."""
    result = _make_result(
        tier=VerificationTier.AI_TESTS_ONLY,
        skipped_checks=["ai_tests_only"],
        status="pass",
        exit_code=0,
    )
    manifest = build_manifest(result=result)

    assert manifest.tier == VerificationTier.AI_TESTS_ONLY
    assert manifest.human_review_required is True


def test_scenario_retry_budget_cap_reflected_in_manifest() -> None:
    """Retry budget cap of 3 → retries_used=2 on final attempt."""
    result = _make_result(
        request_id="req-retry",
        attempt=3,
        status="fail",
        exit_code=1,
        failure_class=FailureClass.deterministic,
    )
    manifest = build_manifest(result=result, retries_used=2)

    assert manifest.retries_used == 2
    assert manifest.attempt == 3


def test_scenario_manifest_includes_commands_exit_codes_durations() -> None:
    """Manifest includes verifiable execution evidence."""
    result = _make_result(
        status="pass",
        exit_code=0,
        duration_ms=387,
        tier=VerificationTier.L1,
    )
    manifest = build_manifest(
        result=result,
        commands_run=["pytest tests/ -x", "ruff check src/"],
    )

    assert len(manifest.commands_run) == 2
    assert manifest.exit_code == 0
    assert manifest.duration_ms == 387


def test_scenario_no_verified_label_without_manifest() -> None:
    """Cannot attach 'verified' label to response without complete manifest."""
    with pytest.raises(ManifestIncompleteError):
        assert_manifest_complete(None)
