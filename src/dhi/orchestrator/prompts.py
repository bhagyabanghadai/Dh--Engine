"""Deterministic repair prompt builder for retry attempts."""

from __future__ import annotations

from dhi.sandbox.models import FailureClass, VerificationResult

# Maximum number of characters taken from stdout/stderr so we do not bloat context.
_MAX_OUTPUT_CHARS = 2_000


def _truncate(text: str, limit: int = _MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[TRUNCATED]"


def _failure_guidance(failure_class: FailureClass | None) -> str:
    guidance = {
        FailureClass.syntax: (
            "The previous code had a SYNTAX ERROR. "
            "Review the error output carefully and emit clean, syntactically valid Python."
        ),
        FailureClass.deterministic: (
            "The previous code produced a DETERMINISTIC LOGICAL FAILURE "
            "(consistent wrong output or exception). "
            "Do not change the overall approach - instead fix the specific "
            "logical error shown in the error output."
        ),
    }
    return guidance.get(
        failure_class,  # type: ignore[arg-type]
        "The previous attempt failed. Analyze the error output and produce a corrected solution.",
    )


def build_repair_prompt(
    original_content: str,
    last_result: VerificationResult,
) -> str:
    """
    Construct a targeted repair prompt embedding original context, failure
    classification, and execution evidence for the next attempt.

    The generated string replaces the `content` field of a ``ContextPayload`` on retry.
    """
    guidance = _failure_guidance(last_result.failure_class)

    sections: list[str] = [
        "## PREVIOUS ATTEMPT FAILED - REPAIR REQUIRED",
        "",
        f"**Failure class:** {last_result.failure_class or 'unknown'}",
        f"**Attempt number:** {last_result.attempt}",
        "",
        "### Guidance",
        guidance,
        "",
    ]

    if last_result.stdout.strip():
        sections += [
            "### Captured stdout",
            "```",
            _truncate(last_result.stdout),
            "```",
            "",
        ]

    if last_result.stderr.strip():
        sections += [
            "### Captured stderr",
            "```",
            _truncate(last_result.stderr),
            "```",
            "",
        ]

    sections += [
        "---",
        "",
        "## Original Request",
        original_content,
    ]

    return "\n".join(sections)
