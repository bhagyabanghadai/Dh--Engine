"""
Violation classifier — Task 2.3 (Pod B: backend-security-coder).

Maps container exit signals + stderr content to canonical ViolationEvent
and FailureClass pairs. All classifications are deterministic — no LLMs,
no heuristics. Only pattern matching on known signals and error strings.
"""

from dhi.sandbox.models import FailureClass, ViolationEvent


def classify(
    *,
    exit_code: int,
    stdout: str,
    stderr: str,
    timed_out: bool,
) -> tuple[ViolationEvent | None, FailureClass | None]:
    """
    Classify a sandbox execution result into a (ViolationEvent, FailureClass) pair.

    Returns:
        (None, None)                               — clean pass
        (ViolationEvent.TimeoutViolation, FailureClass.timeout)
        (ViolationEvent.NetworkAccessViolation, FailureClass.policy)
        (ViolationEvent.FilesystemWriteViolation, FailureClass.policy)
        (ViolationEvent.MemoryLimitViolation, FailureClass.policy)
        (None, FailureClass.syntax)                — SyntaxError in stderr
        (None, FailureClass.deterministic)         — generic logical failure
    """
    # --- Priority 1: Timeout (checked first — SIGKILL at limit) ---
    if timed_out:
        return ViolationEvent.TimeoutViolation, FailureClass.timeout

    # --- Priority 2: Clean pass ---
    if exit_code == 0:
        return None, None

    stderr_lower = stderr.lower()
    stdout_lower = stdout.lower()
    combined = stderr_lower + stdout_lower

    # --- Priority 3: Network access violation ---
    # Network errors surface as socket/connection errors when network_mode=none
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

    # --- Priority 4: Filesystem write violation (read-only mount) ---
    fs_signals = (
        "read-only file system",
        "[errno 30]",
        "erofs",  # Error Read-Only FileSystem kernel code
    )
    if any(sig in combined for sig in fs_signals):
        return ViolationEvent.FilesystemWriteViolation, FailureClass.policy

    # --- Priority 5: Memory limit (OOM kill — exit code 137 = SIGKILL) ---
    if exit_code == 137 and (
        "killed" in combined or "out of memory" in combined or not stderr.strip()
    ):
        return ViolationEvent.MemoryLimitViolation, FailureClass.policy

    # --- Priority 6: Python SyntaxError ---
    if "syntaxerror" in stderr_lower or "indentationerror" in stderr_lower:
        return None, FailureClass.syntax

    # --- Priority 7: Generic deterministic failure (non-zero exit, no policy breach) ---
    if exit_code != 0:
        return None, FailureClass.deterministic

    # Should never reach here given priority checks above
    return None, None
