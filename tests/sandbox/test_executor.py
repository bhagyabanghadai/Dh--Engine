"""
Sandbox policy test suite.

Covers Epic 2 exit gates and deterministic classifier behavior.
"""

from __future__ import annotations

import pytest

from dhi.sandbox.classifier import classify
from dhi.sandbox.models import FailureClass, ViolationEvent


class TestClassifier:
    """Unit tests for deterministic violation classification."""

    def test_clean_pass_returns_none_pair(self) -> None:
        event, cls = classify(exit_code=0, stdout="ok", stderr="", timed_out=False)
        assert event is None
        assert cls is None

    def test_timeout_takes_priority(self) -> None:
        event, cls = classify(exit_code=0, stdout="", stderr="", timed_out=True)
        assert event == ViolationEvent.TimeoutViolation
        assert cls == FailureClass.timeout

    def test_output_cap_violation_is_policy_failure(self) -> None:
        event, cls = classify(
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            output_capped=True,
        )
        assert event == ViolationEvent.OutputLimitViolation
        assert cls == FailureClass.policy

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
        event, cls = classify(
            exit_code=1,
            stdout="",
            stderr=stderr_snippet,
            timed_out=False,
        )
        assert event == ViolationEvent.FilesystemWriteViolation
        assert cls == FailureClass.policy

    def test_process_limit_violation_classified(self) -> None:
        event, cls = classify(
            exit_code=1,
            stdout="",
            stderr="fork: retry: Resource temporarily unavailable",
            timed_out=False,
        )
        assert event == ViolationEvent.ProcessLimitViolation
        assert cls == FailureClass.policy

    def test_syscall_violation_classified(self) -> None:
        event, cls = classify(
            exit_code=1,
            stdout="",
            stderr="Operation not permitted",
            timed_out=False,
        )
        assert event == ViolationEvent.SyscallViolation
        assert cls == FailureClass.policy

    def test_oom_classified_as_memory_limit(self) -> None:
        event, cls = classify(
            exit_code=137,
            stdout="",
            stderr="Killed",
            timed_out=False,
        )
        assert event == ViolationEvent.MemoryLimitViolation
        assert cls == FailureClass.policy

    def test_syntax_error_classified(self) -> None:
        event, cls = classify(
            exit_code=1,
            stdout="",
            stderr="SyntaxError: invalid syntax",
            timed_out=False,
        )
        assert event is None
        assert cls == FailureClass.syntax

    def test_generic_failure_classified_as_deterministic(self) -> None:
        event, cls = classify(
            exit_code=1,
            stdout="",
            stderr="AssertionError: expected 1 got 2",
            timed_out=False,
        )
        assert event is None
        assert cls == FailureClass.deterministic


@pytest.mark.integration
class TestSandboxExecutor:
    """Integration tests that run real Docker containers."""

    @pytest.fixture(autouse=True)
    def _require_docker(self) -> None:
        docker = pytest.importorskip("docker")
        try:
            client = docker.from_env()
            client.ping()
            client.images.get("dhi-sandbox:latest")
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"Docker integration prerequisites unavailable: {exc}")

    def test_valid_python_returns_pass(self) -> None:
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
        assert result.request_id == "test-pass"
        assert result.attempt == 1
        assert result.duration_ms >= 0

    def test_syntax_error_returns_fail_with_traceback(self) -> None:
        from dhi.sandbox.executor import run_in_sandbox

        result = run_in_sandbox(
            code="def f(  # broken",
            request_id="test-syntax",
            attempt=1,
        )
        assert result.status == "fail"
        assert result.failure_class == FailureClass.syntax
        assert "SyntaxError" in result.stderr or "syntaxerror" in result.stderr.lower()

    def test_infinite_loop_triggers_timeout(self) -> None:
        from dhi.sandbox.executor import run_in_sandbox

        result = run_in_sandbox(
            code="while True: pass",
            request_id="test-timeout",
            attempt=1,
        )
        assert result.status == "fail"
        assert result.terminal_event == ViolationEvent.TimeoutViolation
        assert result.failure_class == FailureClass.timeout
        assert result.duration_ms <= 50_000

    def test_network_call_blocked(self) -> None:
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
        from dhi.sandbox.executor import run_in_sandbox

        code = (
            "with open('/source/hacked.txt', 'w') as f:\n"
            "    f.write('escaped')\n"
        )
        result = run_in_sandbox(code=code, request_id="test-fs-write", attempt=1)
        assert result.status == "fail"
        assert result.terminal_event == ViolationEvent.FilesystemWriteViolation
        assert result.failure_class == FailureClass.policy
