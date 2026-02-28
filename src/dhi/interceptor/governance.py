"""Pre-egress governance pipeline for cloud interceptor requests."""

from __future__ import annotations

import logging
import re

from .dlp import redact_high_entropy
from .models import ContextPayload, GovernanceAuditRecord

logger = logging.getLogger(__name__)

# Files containing these fragments are always blocked from egress.
DENYLISTED_PATH_SNIPPETS = (
    ".env",
    "secrets.yaml",
    "id_rsa",
    "credentials.json",
    ".pem",
)

# Only these path shapes are allowed in v0.1 payload metadata.
ALLOWED_PATH_PATTERNS = (
    re.compile(r"^(src|tests|docs)/.+"),
    re.compile(r"^[A-Za-z0-9_.-]+\.(py|md|toml|json|ya?ml)$"),
)

# Secret patterns with deterministic replacement.
AWS_ACCESS_KEY_PATTERN = re.compile(r"(?i)\bAKIA[0-9A-Z]{16}\b")
TOKEN_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)(\b(?:secret|token|api_key|password)\b\s*[:=]\s*[\"']?)([A-Za-z0-9/+=._-]{16,80})([\"']?)"
)
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----",
    flags=re.MULTILINE,
)

SECRET_LEAK_BLOCK_REASON = (
    "SecretLeakDetected: confirmed secret pattern detected in context. Cloud egress blocked."
)


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    return normalized.removeprefix("./")


def _is_absolute_or_traversal(path: str) -> bool:
    if not path:
        return True

    if path.startswith("/") or re.match(r"^[A-Za-z]:/", path):
        return True

    return ".." in [part for part in path.split("/") if part]


def enforce_path_rules(files: list[str]) -> str | None:
    """Return a block reason if any path violates allow or deny policy."""
    for file_path in files:
        normalized = _normalize_path(file_path)
        lower_path = normalized.lower()

        if _is_absolute_or_traversal(normalized):
            return f"Path traversal violation: {file_path}"

        if any(fragment in lower_path for fragment in DENYLISTED_PATH_SNIPPETS):
            return f"Path denylist violation: {file_path} is restricted."

        if not any(pattern.match(normalized) for pattern in ALLOWED_PATH_PATTERNS):
            return f"Path allowlist violation: {file_path} is not allowed."

    return None


def redact_secrets(content: str) -> tuple[str, int]:
    """Redact known secret patterns and return clean content plus redaction count."""
    redaction_count = 0
    cleaned = content

    cleaned, count = AWS_ACCESS_KEY_PATTERN.subn("<REDACTED_SECRET>", cleaned)
    redaction_count += count

    def _token_replacer(match: re.Match[str]) -> str:
        prefix = match.group(1)
        suffix = match.group(3)
        return f"{prefix}<REDACTED_SECRET>{suffix}"

    cleaned, count = TOKEN_ASSIGNMENT_PATTERN.subn(_token_replacer, cleaned)
    redaction_count += count

    cleaned, count = PRIVATE_KEY_PATTERN.subn("<REDACTED_SECRET>", cleaned)
    redaction_count += count

    return cleaned, redaction_count


def minimize_context(content: str) -> tuple[str, bool]:
    """Apply prompt-injection phrase stripping and size minimization."""
    minimized = False
    cleaned = content

    injection_phrases = (
        # Classic jailbreaks
        "Ignore all previous instructions",
        "system prompt",
        "You are a simulated",
        # Persona override attempts
        "Act as",
        "DAN mode",
        "developer mode",
        "jailbreak mode",
        "pretend you are",
        "pretend to be",
        # Policy override attempts
        "override your",
        "override your instructions",
        "your new instructions",
        "forget your instructions",
        "disregard your",
        # Privilege escalation
        "ignore your training",
        "you have no restrictions",
    )

    for phrase in injection_phrases:
        if phrase.lower() in cleaned.lower():
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            cleaned = pattern.sub("[REMOVED_INJECTION_ATTEMPT]", cleaned)
            minimized = True

    max_chars = 50_000
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n\n...[CONTEXT TRUNCATED BY POLICY]..."
        minimized = True

    return cleaned, minimized


def _log_egress_audit(audit: GovernanceAuditRecord) -> None:
    logger.info(
        "EgressAudit request_id=%s file_count=%d redaction_count=%d "
        "high_entropy_redaction_count=%d bytes_sent=%d blocked=%s",
        audit.request_id,
        audit.file_count,
        audit.redaction_count,
        audit.high_entropy_redaction_count,
        audit.bytes_sent,
        audit.blocked,
    )


class GovernancePipeline:
    """Orchestrates pre-egress policy checks."""

    @staticmethod
    def run(payload: ContextPayload) -> tuple[ContextPayload, GovernanceAuditRecord]:
        """Run policy checks and return ``(safe_payload, audit_record)``."""
        audit = GovernanceAuditRecord(
            request_id=payload.request_id,
            file_count=len(payload.files),
        )

        # --- 1. Path enforcement (hard block) ---
        block_reason = enforce_path_rules(payload.files)
        if block_reason is not None:
            audit.blocked = True
            audit.block_reason = block_reason
            logger.warning(
                "GovernanceBlocked request_id=%s reason=%r",
                payload.request_id,
                block_reason,
            )
            _log_egress_audit(audit)
            return payload, audit

        # --- 2. Known-pattern secret redaction ---
        safe_content, redaction_count = redact_secrets(payload.content)
        audit.redaction_count = redaction_count

        if redaction_count > 0:
            audit.secret_leak_detected = True
            logger.critical(
                "SecretLeakDetected request_id=%s confirmed_redactions=%d",
                payload.request_id,
                redaction_count,
            )
            audit.blocked = True
            audit.block_reason = SECRET_LEAK_BLOCK_REASON
            safe_content, was_minimized = minimize_context(safe_content)
            audit.prompt_minimized = was_minimized
            safe_payload = ContextPayload(
                request_id=payload.request_id,
                attempt=payload.attempt,
                files=payload.files,
                content=safe_content,
            )
            _log_egress_audit(audit)
            return safe_payload, audit

        # --- 3. High-entropy token redaction ---
        safe_content, entropy_count = redact_high_entropy(safe_content)
        audit.high_entropy_redaction_count = entropy_count

        if entropy_count > 0:
            logger.warning(
                "HighEntropyTokensRedacted request_id=%s entropy_redactions=%d",
                payload.request_id,
                entropy_count,
            )

        # --- 4. Injection minimization ---
        safe_content, was_minimized = minimize_context(safe_content)
        audit.prompt_minimized = was_minimized

        # --- 5. Build safe payload ---
        safe_payload = ContextPayload(
            request_id=payload.request_id,
            attempt=payload.attempt,
            files=payload.files,
            content=safe_content,
        )

        # --- 6. Egress byte accounting ---
        audit.bytes_sent = len(safe_payload.content.encode())

        # --- 7. Structured egress audit log ---
        _log_egress_audit(audit)

        return safe_payload, audit
