"""Candidate extraction pipeline for cloud LLM responses."""

from __future__ import annotations

import ast
import json
import logging
import re
from json import JSONDecodeError

from pydantic import ValidationError

from .models import ExtractionResult, LLMResponse

logger = logging.getLogger(__name__)

_FENCE_PATTERN = re.compile(r"```(?P<lang>[A-Za-z0-9_+-]*)\n(?P<code>.*?)```", re.DOTALL)


def validate_python_code(code: str) -> str | None:
    """Return syntax error details when Python code is invalid, otherwise ``None``."""
    if not code.strip():
        return "Candidate code is completely empty."

    try:
        ast.parse(code)
    except SyntaxError as err:
        return f"SyntaxError at line {err.lineno}, offset {err.offset}: {err.msg}"
    except Exception as err:
        return f"Parse error: {err}"

    return None


def _strip_json_fence(response_text: str) -> str:
    stripped = response_text.strip()
    if stripped.startswith("```json") and stripped.endswith("```"):
        stripped = stripped.removeprefix("```json")
        stripped = stripped.removesuffix("```")
    return stripped.strip()


def _parse_structured_response(response_text: str) -> LLMResponse | None:
    cleaned = _strip_json_fence(response_text)
    try:
        parsed = json.loads(cleaned)
    except JSONDecodeError:
        return None

    try:
        return LLMResponse.model_validate(parsed)
    except ValidationError:
        logger.debug("Structured response JSON did not match schema.")
        return None


def _build_result_from_candidate(
    *,
    code: str,
    language: str,
    notes: str,
    fallback_used: bool,
) -> ExtractionResult:
    language_normalized = language.strip().lower()
    validation_error: str | None = None

    if not code.strip():
        validation_error = "Candidate code is completely empty."
    elif language_normalized == "python":
        validation_error = validate_python_code(code)

    if validation_error is not None:
        return ExtractionResult(
            success=False,
            code=code,
            language=language_normalized,
            notes=notes,
            fallback_used=fallback_used,
            error=validation_error,
        )

    return ExtractionResult(
        success=True,
        code=code,
        language=language_normalized,
        notes=notes,
        fallback_used=fallback_used,
    )


def _parse_markdown_fallback(response_text: str) -> ExtractionResult:
    match = _FENCE_PATTERN.search(response_text)
    if match is None:
        return ExtractionResult(
            success=False,
            code="",
            fallback_used=True,
            error="Could not extract code via JSON or Markdown blocks.",
        )

    language = match.group("lang") or "python"
    code = match.group("code").strip()
    return _build_result_from_candidate(
        code=code,
        language=language,
        notes="",
        fallback_used=True,
    )


def extract_candidate(response_text: str) -> ExtractionResult:
    """Extract candidate code from LLM output using JSON first, markdown fallback second."""
    if not response_text or not response_text.strip():
        return ExtractionResult(
            success=False,
            code="",
            error="Raw LLM response was empty.",
        )

    structured = _parse_structured_response(response_text)
    if structured is not None:
        return _build_result_from_candidate(
            code=structured.code,
            language=structured.language,
            notes=structured.notes,
            fallback_used=False,
        )

    logger.debug("Primary JSON extraction failed, using markdown fallback parser.")
    return _parse_markdown_fallback(response_text)