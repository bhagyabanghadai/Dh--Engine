"""Tier mapper: derive VerificationTier from a sandbox VerificationResult.

Mapping rules (in priority order):
  L2  — integration or e2e tests ran and passed
  L1  — pre-existing user unit tests ran and passed
  AI_TESTS_ONLY — only AI-authored tests ran (human review required)
  L0  — parse / lint / type checks only (no tests ran)
"""

from __future__ import annotations

from dhi.sandbox.models import VerificationResult, VerificationTier


def map_tier(result: VerificationResult) -> VerificationTier:
    """Return the highest ``VerificationTier`` achieved for *result*.

    The mapping is deterministic and based solely on the ``VerificationResult``
    fields already produced by the sandbox executor.

    Rules applied in priority order:

    1. If the runtime_config or skipped_checks signal that only AI-generated
       tests ran, return ``AI_TESTS_ONLY``.
    2. If ``runtime_config`` indicates integration or e2e tests ran, return ``L2``.
    3. If any user-owned tests passed (exit_code 0, status 'pass', no skips
       marking all tests as AI-only), return ``L1``.
    4. Fallback: ``L0`` (parse/lint/type only).
    """
    # ---- signals ----
    skipped = {s.lower() for s in result.skipped_checks}
    cfg = result.runtime_config

    ai_tests_flag: bool = (
        "ai_tests_only" in skipped
        or bool(cfg.get("ai_tests_only"))
        or _runtime_label(cfg) == "ai_tests_only"
    )
    if ai_tests_flag:
        return VerificationTier.AI_TESTS_ONLY

    integration_flag: bool = bool(cfg.get("integration_tests")) or bool(cfg.get("e2e_tests"))
    if integration_flag and result.status == "pass":
        return VerificationTier.L2

    user_tests_flag: bool = bool(cfg.get("user_tests")) or bool(cfg.get("pre_existing_tests"))
    if user_tests_flag and result.status == "pass":
        return VerificationTier.L1

    # Infer from tier field already on result (set by executor)
    if result.tier == VerificationTier.L2 and result.status == "pass":
        return VerificationTier.L2

    if result.tier == VerificationTier.L1 and result.status == "pass":
        return VerificationTier.L1

    if result.tier == VerificationTier.AI_TESTS_ONLY:
        return VerificationTier.AI_TESTS_ONLY

    return VerificationTier.L0


def _runtime_label(cfg: dict[str, object]) -> str:
    """Extract a normalised tier label string from runtime_config, or empty."""
    label = cfg.get("tier_label") or cfg.get("tier") or ""
    return str(label).lower().strip()
