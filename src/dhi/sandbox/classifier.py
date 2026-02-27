"""
Violation classifier for sandbox execution outcomes.

Maps container exit signals + stderr content to canonical ViolationEvent
and FailureClass pairs. Classification is deterministic and based only on
known signals and error strings.
"""

from dhi.sandbox.models import FailureClass, ViolationEvent


def classify(
    *,
    exit_code: int,
    stdout: str,
    stderr: str,
    timed_out: bool,
    output_capped: bool = False,
) -> tuple[ViolationEvent | None, FailureClass | None]:
    """
    Classify a sandbox execution result into a (ViolationEvent, FailureClass) pair.

    Returns:
        (None, None)                               - clean pass
        (ViolationEvent.TimeoutViolation, FailureClass.timeout)
        (ViolationEvent.NetworkAccessViolation, FailureClass.policy)
        (ViolationEvent.FilesystemWriteViolation, FailureClass.policy)
        (ViolationEvent.ProcessLimitViolation, FailureClass.policy)
        (ViolationEvent.OutputLimitViolation, FailureClass.policy)
        (ViolationEvent.SyscallViolation, FailureClass.policy)
        (ViolationEvent.MemoryLimitViolation, FailureClass.policy)
        (None, FailureClass.syntax)                - SyntaxError in stderr
        (None, FailureClass.deterministic)         - generic logical failure
    """
    # Priority 1: timeout
    if timed_out:
        return ViolationEvent.TimeoutViolation, FailureClass.timeout

    # Priority 2: output/log cap breach
    if output_capped:
        return ViolationEvent.OutputLimitViolation, FailureClass.policy

    # Priority 3: clean pass
    if exit_code == 0:
        return None, None

    stderr_lower = stderr.lower()
    stdout_lower = stdout.lower()
    combined = stderr_lower + stdout_lower

    # Priority 4: network access violation
    network_signals = (
        "network is unreachable",
        "name or service not known",
        "connection refused",
        "socket.gaierror",
        "errno 101",  # ENETUNREACH
        "errno 111",  # ECONNREFUSED
        "[errno 110]",  # ETIMEDOUT
    )
    if any(sig in combined for sig in network_signals):
        return ViolationEvent.NetworkAccessViolation, FailureClass.policy

    # Priority 5: filesystem write violation
    fs_signals = (
        "read-only file system",
        "[errno 30]",
        "erofs",
    )
    if any(sig in combined for sig in fs_signals):
        return ViolationEvent.FilesystemWriteViolation, FailureClass.policy

    # Priority 6: process limit violation
    process_limit_signals = (
        "resource temporarily unavailable",
        "can't start new thread",
        "cannot allocate memory",
        "fork: retry",
        "pids limit",
    )
    if any(sig in combined for sig in process_limit_signals):
        return ViolationEvent.ProcessLimitViolation, FailureClass.policy

    # Priority 7: syscall/seccomp violation
    syscall_signals = (
        "seccomp",
        "operation not permitted",
        "permission denied",
        "bad system call",
    )
    if any(sig in combined for sig in syscall_signals):
        return ViolationEvent.SyscallViolation, FailureClass.policy

    # Priority 8: memory limit (OOM kill)
    if exit_code == 137 and (
        "killed" in combined or "out of memory" in combined or not stderr.strip()
    ):
        return ViolationEvent.MemoryLimitViolation, FailureClass.policy

    # Priority 9: Python syntax error
    if "syntaxerror" in stderr_lower or "indentationerror" in stderr_lower:
        return None, FailureClass.syntax

    # Priority 10: generic deterministic failure
    if exit_code != 0:
        return None, FailureClass.deterministic

    return None, None
