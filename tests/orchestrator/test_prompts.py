from __future__ import annotations

from dhi.orchestrator.prompts import build_repair_prompt
from dhi.sandbox.models import FailureClass, VerificationMode, VerificationResult, VerificationTier


def _make_result(
    *,
    failure_class: FailureClass | None = FailureClass.syntax,
    stdout: str = "",
    stderr: str = "",
) -> VerificationResult:
    return VerificationResult(
        request_id="req-1",
        attempt=1,
        mode=VerificationMode.balanced,
        tier=VerificationTier.L0,
        status="fail",
        failure_class=failure_class,
        exit_code=1,
        duration_ms=50,
        stdout=stdout,
        stderr=stderr,
    )


def test_repair_prompt_contains_original_request() -> None:
    original = "Please write a function to sort a list."
    result = _make_result()
    prompt = build_repair_prompt(original_content=original, last_result=result)
    assert original in prompt


def test_repair_prompt_contains_failure_class() -> None:
    result = _make_result(failure_class=FailureClass.deterministic)
    prompt = build_repair_prompt(original_content="task", last_result=result)
    assert "deterministic" in prompt.lower()


def test_repair_prompt_injects_stderr() -> None:
    result = _make_result(stderr="NameError: name 'x' is not defined")
    prompt = build_repair_prompt(original_content="task", last_result=result)
    assert "NameError" in prompt


def test_repair_prompt_injects_stdout() -> None:
    result = _make_result(stdout="AssertionError: expected 42 got 41")
    prompt = build_repair_prompt(original_content="task", last_result=result)
    assert "AssertionError" in prompt


def test_repair_prompt_truncates_long_output() -> None:
    big_stderr = "x" * 5000
    result = _make_result(stderr=big_stderr)
    prompt = build_repair_prompt(original_content="task", last_result=result)
    assert "[TRUNCATED]" in prompt


def test_repair_prompt_no_stdout_section_when_empty() -> None:
    result = _make_result(stdout="", stderr="error line")
    prompt = build_repair_prompt(original_content="task", last_result=result)
    # Should have stderr section but not stdout header
    assert "Captured stdout" not in prompt
    assert "Captured stderr" in prompt
