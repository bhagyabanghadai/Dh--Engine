"""Tests for interceptor gateway AST slice integration (Epic 5 gate)."""

from __future__ import annotations

from pathlib import Path

import dhi.interceptor.gateway as gateway_module
from dhi.interceptor.gateway import _build_context
from dhi.interceptor.models import ContextPayload

SAMPLE_PYTHON = """\
def helper(x: int) -> int:
    return x * 2


def main_func(n: int) -> int:
    return helper(n)
"""


def test_build_context_with_ast_slice_enabled(tmp_path: Path) -> None:
    """When AST slicing is enabled and target exists, context uses AST slice."""
    py_file = tmp_path / "code.py"
    py_file.write_text(SAMPLE_PYTHON, encoding="utf-8")

    original = gateway_module.AST_SLICE_ENABLED
    gateway_module.AST_SLICE_ENABLED = True

    payload = ContextPayload(
        request_id="test-001",
        attempt=1,
        files=[str(py_file)],
        content="main_func",
    )

    try:
        context = _build_context(payload)
    finally:
        gateway_module.AST_SLICE_ENABLED = original

    assert "[AST Slice]" in context
    assert "main_func" in context
    assert "helper" in context


def test_build_context_uses_ast_slice_for_natural_prompt(tmp_path: Path) -> None:
    """Natural-language prompts mentioning symbol names should still slice."""
    py_file = tmp_path / "code.py"
    py_file.write_text(SAMPLE_PYTHON, encoding="utf-8")

    original = gateway_module.AST_SLICE_ENABLED
    gateway_module.AST_SLICE_ENABLED = True

    payload = ContextPayload(
        request_id="test-001b",
        attempt=1,
        files=[str(py_file)],
        content="Refactor main_func to improve naming and readability.",
    )

    try:
        context = _build_context(payload)
    finally:
        gateway_module.AST_SLICE_ENABLED = original

    assert "[AST Slice]" in context
    assert "main_func" in context


def test_build_context_defaults_to_first_symbol_when_no_match(tmp_path: Path) -> None:
    """Retry-like prompts with no symbol mention should still use sliced context."""
    py_file = tmp_path / "code.py"
    py_file.write_text(SAMPLE_PYTHON, encoding="utf-8")

    original = gateway_module.AST_SLICE_ENABLED
    gateway_module.AST_SLICE_ENABLED = True

    payload = ContextPayload(
        request_id="test-001c",
        attempt=2,
        files=[str(py_file)],
        content="## PREVIOUS ATTEMPT FAILED - REPAIR REQUIRED\nPlease fix it.",
    )

    try:
        context = _build_context(payload)
    finally:
        gateway_module.AST_SLICE_ENABLED = original

    assert "[AST Slice]" in context


def test_build_context_supports_line_number_target(tmp_path: Path) -> None:
    """Line-number first line should resolve to containing symbol."""
    py_file = tmp_path / "code.py"
    py_file.write_text(SAMPLE_PYTHON, encoding="utf-8")

    original = gateway_module.AST_SLICE_ENABLED
    gateway_module.AST_SLICE_ENABLED = True

    payload = ContextPayload(
        request_id="test-001d",
        attempt=1,
        files=[str(py_file)],
        content="line 5\nImprove this function",
    )

    try:
        context = _build_context(payload)
    finally:
        gateway_module.AST_SLICE_ENABLED = original

    assert "[AST Slice]" in context
    assert "main_func" in context


def test_build_context_falls_back_when_ast_disabled(tmp_path: Path) -> None:
    """When AST slicing is disabled, raw content is returned unchanged."""
    py_file = tmp_path / "code.py"
    py_file.write_text(SAMPLE_PYTHON, encoding="utf-8")

    original = gateway_module.AST_SLICE_ENABLED
    gateway_module.AST_SLICE_ENABLED = False

    payload = ContextPayload(
        request_id="test-002",
        attempt=1,
        files=[str(py_file)],
        content="some raw content",
    )

    try:
        context = _build_context(payload)
    finally:
        gateway_module.AST_SLICE_ENABLED = original

    assert context == "some raw content"


def test_build_context_falls_back_when_no_files() -> None:
    """When no files are provided the raw content is returned."""
    original = gateway_module.AST_SLICE_ENABLED
    gateway_module.AST_SLICE_ENABLED = True

    payload = ContextPayload(
        request_id="test-003",
        attempt=1,
        files=[],
        content="no file raw content",
    )

    try:
        context = _build_context(payload)
    finally:
        gateway_module.AST_SLICE_ENABLED = original

    assert context == "no file raw content"


def test_build_context_falls_back_for_explicit_missing_symbol(tmp_path: Path) -> None:
    """Explicit symbol requests that miss should preserve raw content fallback."""
    py_file = tmp_path / "code.py"
    py_file.write_text(SAMPLE_PYTHON, encoding="utf-8")

    original = gateway_module.AST_SLICE_ENABLED
    gateway_module.AST_SLICE_ENABLED = True

    payload = ContextPayload(
        request_id="test-004",
        attempt=1,
        files=[str(py_file)],
        content="completely_nonexistent_func",
    )

    try:
        context = _build_context(payload)
    finally:
        gateway_module.AST_SLICE_ENABLED = original

    assert context == "completely_nonexistent_func"
