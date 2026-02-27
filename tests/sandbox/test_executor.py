"""
Sandbox policy test suite — Task 2.5 (Pod B/A QA: python-testing-patterns).

Covers all 5 exit gates from Epic 2 spec. Uses parametrize for clarity.
Tests against the classifier directly (unit) — full executor tests require
Docker to be available and are marked with @pytest.mark.integration.
"""

import pytest

from dhi.sandbox.classifier import classify
from dhi.sandbox.models import FailureClass, ViolationEvent

# ---------------------------------------------------------------------------
# Unit tests for the violation classifier (no Docker required)
# ---------------------------------------------------------------------------


class TestClassifier:
    """Unit tests for the deterministic violation classifier."""

    def test_clean_pass_returns_none_pair(self) -> None:
        """Exit 0, no timed_out → both values are None."""
        event, cls = classify(exit_code=0, stdout="ok", stderr="", timed_out=False)
        assert event is None
        assert cls is None

    def test_timeout_takes_priority(self) -> None:
        """timed_out flag always maps to TimeoutViolation regardless of exit code."""
        event, cls = classify(exit_code=0, stdout="", stderr="", timed_out=True)
        assert event == ViolationEvent.TimeoutViolation
        assert cls == FailureClass.timeout

    @pytest.mark.parametrize(
        "stderr_snippet",
        [
            "Network is unreachable",
            "Name or service not known",
            "socket.gaierror",
            "errno 101",
        ],
    )
    def test_network_violation_classified(self, stderr_snippet: str) -> None:
        """Network error strings → NetworkAccessViolation + policy class."""
        event, cls = classify(
            exit_code=1,
            stdout="",
            stderr=stderr_snippet,
            timed_out=False,
        )
        assert event == ViolationEvent.NetworkAccessViolation
        assert cls == FailureClass.policy

    @pytest.mark.parametrize(
        "stderr_snippet",
        [
            "Read-only file system",
            "[Errno 30]",
            "erofs",
        ],
    )
    def test_filesystem_write_violation_classified(self, stderr_snippet: str) -> None:
        """Read-only FS error strings → FilesystemWriteViolation + policy class."""
        event, cls = classify(
            exit_code=1,
            stdout="",
            stderr=stderr_snippet,
            timed_out=False,
        )
        assert event == ViolationEvent.FilesystemWriteViolation
        assert cls == FailureClass.policy

    def test_oom_classified_as_memory_limit(self) -> None:
        """Exit 137 (SIGKILL) without a clear error → MemoryLimitViolation."""
        event, cls = classify(
            exit_code=137,
            stdout="",
            stderr="Killed",
            timed_out=False,
        )
        assert event == ViolationEvent.MemoryLimitViolation
        assert cls == FailureClass.policy

    def test_syntax_error_classified(self) -> None:
        """SyntaxError in stderr → syntax failure class, no terminal event."""
        event, cls = classify(
            exit_code=1,
            stdout="",
            stderr="SyntaxError: invalid syntax",
            timed_out=False,
        )
        assert event is None
        assert cls == FailureClass.syntax

    def test_generic_failure_classified_as_deterministic(self) -> None:
        """Non-zero exit with no policy signal → deterministic failure class."""
        event, cls = classify(
            exit_code=1,
            stdout="",
            stderr="AssertionError: expected 1 got 2",
            timed_out=False,
        )
        assert event is None
        assert cls == FailureClass.deterministic


# ---------------------------------------------------------------------------
# Integration tests — require Docker (marked so CI can skip if unavailable)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSandboxExecutor:
    """
    Integration tests that run real Docker containers.
    Require: docker ps succeeds, dhi-sandbox:latest image exists.
    Run with: pytest -m integration
    Skip in CI without Docker: pytest -m "not integration"
    """

    def test_valid_python_returns_pass(self) -> None:
        """Exit gate 1: Valid code path returns status=pass."""
        from dhi.sandbox.executor import run_in_sandbox

        result = run_in_sandbox(
            code='print("hello from dhi")',
            request_id="test-pass",
            attempt=1,
        )
        assert result.status == "pass"
        assert result.exit_code == 0
        assert result.terminal_event is None
        assert result.failure_class is None
        # Verify all required contract fields are present
        assert result.request_id == "test-pass"
        assert result.attempt == 1
        assert result.duration_ms >= 0

    def test_syntax_error_returns_fail_with_traceback(self) -> None:
        """Exit gate 2: Broken code returns status=fail with SyntaxError in stderr."""
        from dhi.sandbox.executor import run_in_sandbox

        result = run_in_sandbox(
            code="def f(  # broken",
            request_id="test-syntax",
            attempt=1,
        )
        assert result.status == "fail"
        assert result.failure_class == FailureClass.syntax
        assert "SyntaxError" in result.stderr or "SyntaxError" in result.stderr.lower()

    def test_infinite_loop_triggers_timeout(self) -> None:
        """Exit gate 3: Infinite loop must be killed and classified as TimeoutViolation."""
        from dhi.sandbox.executor import run_in_sandbox

        result = run_in_sandbox(
            code="while True: pass",
            request_id="test-timeout",
            attempt=1,
        )
        assert result.status == "fail"
        assert result.terminal_event == ViolationEvent.TimeoutViolation
        assert result.failure_class == FailureClass.timeout
        # Should complete within the timeout window + small buffer
        assert result.duration_ms <= 50_000  # 50 seconds

    def test_network_call_blocked(self) -> None:
        """Exit gate 4: Outbound network attempt fails with NetworkAccessViolation."""
        from dhi.sandbox.executor import run_in_sandbox

        code = (
            "import urllib.request\n"
            'urllib.request.urlopen("http://httpbin.org/get", timeout=5)\n'
        )
        result = run_in_sandbox(code=code, request_id="test-network", attempt=1)
        assert result.status == "fail"
        assert result.terminal_event == ViolationEvent.NetworkAccessViolation
        assert result.failure_class == FailureClass.policy

    def test_filesystem_write_blocked(self) -> None:
        """Exit gate 5: Write to read-only source mount fails with FilesystemWriteViolation."""
        from dhi.sandbox.executor import run_in_sandbox

        code = (
            "with open('/source/hacked.txt', 'w') as f:\n"
            "    f.write('escaped')\n"
        )
        result = run_in_sandbox(code=code, request_id="test-fs-write", attempt=1)
        assert result.status == "fail"
        assert result.terminal_event == ViolationEvent.FilesystemWriteViolation
        assert result.failure_class == FailureClass.policy
