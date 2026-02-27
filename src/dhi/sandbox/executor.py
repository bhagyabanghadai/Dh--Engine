"""
Sandbox executor for balanced-mode verification.

Executes untrusted Python code inside a hardened Docker container with
policy defaults from the runtime spec.
"""

from __future__ import annotations

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
    ViolationEvent,
)

# Balanced mode hard limits
_BALANCED_TIMEOUT_S = 45
_BALANCED_TOTAL_BUDGET_S = 180
_BALANCED_MEM_LIMIT = "1g"
_BALANCED_CPU_NANO = 2_000_000_000  # 2 vCPU in nanocpus
_BALANCED_PIDS_LIMIT = 256
_BALANCED_LOG_CAP = 10 * 1024 * 1024  # 10 MB
_BALANCED_SCRATCH_CAP_BYTES = 512 * 1024 * 1024  # 512 MB

_SANDBOX_IMAGE = "dhi-sandbox:latest"
_SOURCE_PATH = "/source"
_SCRATCH_PATH = "/tmp/dhi-scratch"


def _base_runtime_config(mode: VerificationMode) -> dict[str, object]:
    return {
        "mode": mode.value,
        "timeout_s": _BALANCED_TIMEOUT_S,
        "total_budget_s": _BALANCED_TOTAL_BUDGET_S,
        "mem_limit": _BALANCED_MEM_LIMIT,
        "cpu_nano": _BALANCED_CPU_NANO,
        "pids_limit": _BALANCED_PIDS_LIMIT,
        "log_cap_bytes": _BALANCED_LOG_CAP,
        "scratch_cap_bytes": _BALANCED_SCRATCH_CAP_BYTES,
        "network": "none",
        "source_mount": "ro",
        "rootfs": "ro",
        "scratch_mount": _SCRATCH_PATH,
    }


def _failure_result(
    *,
    request_id: str,
    attempt: int,
    mode: VerificationMode,
    runtime_config: dict[str, object],
    start_monotonic: float,
    stderr: str,
    failure_class: FailureClass = FailureClass.policy,
    terminal_event: ViolationEvent | None = None,
) -> VerificationResult:
    elapsed = int((time.monotonic() - start_monotonic) * 1000)
    return VerificationResult(
        request_id=request_id,
        attempt=attempt,
        mode=mode,
        tier=VerificationTier.L0,
        status="fail",
        failure_class=failure_class,
        terminal_event=terminal_event,
        exit_code=-1,
        duration_ms=elapsed,
        stdout="",
        stderr=stderr,
        runtime_config=runtime_config,
    )


def run_in_sandbox(
    code: str,
    request_id: str,
    attempt: int,
    mode: VerificationMode = VerificationMode.balanced,
) -> VerificationResult:
    """Execute candidate code in the balanced sandbox and return verification result."""
    runtime_config = _base_runtime_config(mode)
    start_monotonic = time.monotonic()

    # Epic 2 supports balanced mode only.
    if mode != VerificationMode.balanced:
        return _failure_result(
            request_id=request_id,
            attempt=attempt,
            mode=mode,
            runtime_config=runtime_config,
            start_monotonic=start_monotonic,
            stderr="Only balanced mode is available in Epic 2.",
            terminal_event=ViolationEvent.StrictModeUnavailable,
        )

    try:
        client = docker.from_env()
        # Fail fast if daemon is unreachable.
        client.ping()
    except docker.errors.DockerException as exc:
        return _failure_result(
            request_id=request_id,
            attempt=attempt,
            mode=mode,
            runtime_config=runtime_config,
            start_monotonic=start_monotonic,
            stderr=f"Docker daemon unavailable: {exc}",
            terminal_event=ViolationEvent.StrictModeUnavailable,
        )

    effective_timeout_s = min(_BALANCED_TIMEOUT_S, _BALANCED_TOTAL_BUDGET_S)

    with TemporaryDirectory(prefix="dhi-src-") as src_dir:
        src_path = Path(src_dir)
        code_file = src_path / "candidate.py"
        code_file.write_text(code, encoding="utf-8")

        volumes = {
            src_dir: {"bind": _SOURCE_PATH, "mode": "ro"},
        }

        command = ["python", f"{_SOURCE_PATH}/candidate.py"]
        output_capped = False

        try:
            container = client.containers.run(
                image=_SANDBOX_IMAGE,
                command=command,
                volumes=volumes,
                network_mode="none",
                mem_limit=_BALANCED_MEM_LIMIT,
                nano_cpus=_BALANCED_CPU_NANO,
                pids_limit=_BALANCED_PIDS_LIMIT,
                read_only=True,
                tmpfs={
                    _SCRATCH_PATH: (
                        f"rw,noexec,nosuid,size={_BALANCED_SCRATCH_CAP_BYTES},mode=1777"
                    )
                },
                environment={"PYTHONDONTWRITEBYTECODE": "1"},
                detach=True,
                remove=False,
            )

            try:
                result = container.wait(timeout=effective_timeout_s)
                exit_code = int(result.get("StatusCode", -1))
                timed_out = False
            except Exception:
                container.kill()
                exit_code = -1
                timed_out = True

            try:
                raw_stdout = container.logs(stdout=True, stderr=False)
                raw_stderr = container.logs(stdout=False, stderr=True)
                output_capped = (
                    len(raw_stdout) > _BALANCED_LOG_CAP
                    or len(raw_stderr) > _BALANCED_LOG_CAP
                )
                stdout = raw_stdout[:_BALANCED_LOG_CAP].decode("utf-8", errors="replace")
                stderr = raw_stderr[:_BALANCED_LOG_CAP].decode("utf-8", errors="replace")
            except docker.errors.DockerException:
                stdout = ""
                stderr = "Failed to retrieve container logs."
            finally:
                try:
                    container.remove(force=True)
                except docker.errors.DockerException:
                    pass

        except docker.errors.ImageNotFound:
            return _failure_result(
                request_id=request_id,
                attempt=attempt,
                mode=mode,
                runtime_config=runtime_config,
                start_monotonic=start_monotonic,
                stderr=(
                    "Sandbox image not found. Build with: "
                    f"docker build -f Dockerfile.sandbox -t {_SANDBOX_IMAGE} ."
                ),
            )
        except docker.errors.DockerException as exc:
            return _failure_result(
                request_id=request_id,
                attempt=attempt,
                mode=mode,
                runtime_config=runtime_config,
                start_monotonic=start_monotonic,
                stderr=f"Sandbox runtime failure: {exc}",
            )

    elapsed_ms = int((time.monotonic() - start_monotonic) * 1000)

    # Enforce total request budget defensively.
    if elapsed_ms > _BALANCED_TOTAL_BUDGET_S * 1000:
        timed_out = True

    violation, failure_cls = classify(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        output_capped=output_capped,
    )

    status = "pass" if violation is None and failure_cls is None else "fail"

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
