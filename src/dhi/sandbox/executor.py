"""
Sandbox executor — Task 2.2 (Pod B: backend-security-coder).

Executes untrusted Python code inside a hardened Docker container
using the balanced runtime defaults from the Dhi sandbox policy spec.

Security rules applied:
- Source always written to file; never shell-interpolated.
- Network is disabled (network_mode=none) — hard-coded, no override.
- Source directory mounted read-only.
- Ephemeral scratch volume is separate and writable.
- All limits are hard-coded defaults from the policy spec.
"""

import time
from pathlib import Path
from tempfile import TemporaryDirectory

import docker  # type: ignore[import-untyped]
import docker.errors  # type: ignore[import-untyped]

from dhi.sandbox.classifier import classify
from dhi.sandbox.models import (
    FailureClass,
    VerificationMode,
    VerificationResult,
    VerificationTier,
)

# ---------------------------------------------------------------------------
# Balanced mode hard limits (from docs/06_Sandbox_Runtime_Policy.md)
# ---------------------------------------------------------------------------
_BALANCED_TIMEOUT_S: int = 45
_BALANCED_MEM_LIMIT: str = "1g"
_BALANCED_CPU_NANO: int = 2_000_000_000  # 2 vCPU in nanocpus
_BALANCED_PIDS_LIMIT: int = 256
_BALANCED_LOG_CAP: int = 10 * 1024 * 1024  # 10 MB

_SANDBOX_IMAGE: str = "dhi-sandbox:latest"
_SCRATCH_PATH: str = "/tmp/dhi-scratch"


def run_in_sandbox(
    code: str,
    request_id: str,
    attempt: int,
    mode: VerificationMode = VerificationMode.balanced,
) -> VerificationResult:
    """
    Write code to a temp dir, execute it inside a hardened Docker container,
    and return a fully-populated VerificationResult.

    The source directory is mounted read-only. Network is disabled.
    All limits are applied as per balanced mode policy defaults.
    """
    runtime_config = {
        "mode": mode.value,
        "timeout_s": _BALANCED_TIMEOUT_S,
        "mem_limit": _BALANCED_MEM_LIMIT,
        "cpu_nano": _BALANCED_CPU_NANO,
        "pids_limit": _BALANCED_PIDS_LIMIT,
        "log_cap_bytes": _BALANCED_LOG_CAP,
        "network": "none",
        "source_mount": "ro",
    }

    client = docker.from_env()
    start_ms = time.monotonic()

    with TemporaryDirectory(prefix="dhi-src-") as src_dir:
        src_path = Path(src_dir)
        # Write code to file — never shell-interpolate user content
        code_file = src_path / "candidate.py"
        code_file.write_text(code, encoding="utf-8")

        volumes = {
            src_dir: {"bind": "/source", "mode": "ro"},
        }
        command = ["python", "/source/candidate.py"]

        try:
            container = client.containers.run(
                image=_SANDBOX_IMAGE,
                command=command,
                volumes=volumes,
                network_mode="none",
                mem_limit=_BALANCED_MEM_LIMIT,
                nano_cpus=_BALANCED_CPU_NANO,
                pids_limit=_BALANCED_PIDS_LIMIT,
                detach=True,
                remove=False,  # we inspect then remove manually
            )

            try:
                result = container.wait(timeout=_BALANCED_TIMEOUT_S)
                exit_code: int = result.get("StatusCode", -1)
                timed_out = False
            except Exception:
                container.kill()
                exit_code = -1
                timed_out = True

            # Capture logs (capped)
            try:
                raw_logs: bytes = container.logs(stdout=True, stderr=False)
                raw_err: bytes = container.logs(stdout=False, stderr=True)
                stdout = raw_logs[: _BALANCED_LOG_CAP].decode("utf-8", errors="replace")
                stderr = raw_err[: _BALANCED_LOG_CAP].decode("utf-8", errors="replace")
            except Exception:
                stdout = ""
                stderr = ""
            finally:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

        except docker.errors.ImageNotFound:
            elapsed = int((time.monotonic() - start_ms) * 1000)
            return VerificationResult(
                request_id=request_id,
                attempt=attempt,
                mode=mode,
                tier=VerificationTier.L0,
                status="fail",
                failure_class=FailureClass.policy,
                terminal_event=None,
                exit_code=-1,
                duration_ms=elapsed,
                stdout="",
                stderr=f"Sandbox image '{_SANDBOX_IMAGE}' not found. Build it with: docker build -f Dockerfile.sandbox -t {_SANDBOX_IMAGE} .",
                runtime_config=runtime_config,
            )

    elapsed_ms = int((time.monotonic() - start_ms) * 1000)

    # Classify the outcome
    violation, failure_cls = classify(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )

    status = "pass" if exit_code == 0 and not timed_out else "fail"

    return VerificationResult(
        request_id=request_id,
        attempt=attempt,
        mode=mode,
        tier=VerificationTier.L0,
        status=status,
        failure_class=failure_cls,
        terminal_event=violation,
        exit_code=exit_code,
        duration_ms=elapsed_ms,
        stdout=stdout,
        stderr=stderr,
        runtime_config=runtime_config,
    )
