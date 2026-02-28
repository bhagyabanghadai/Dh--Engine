"""Environment Fingerprint Generator for VEIL Memory."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict


def _sha256_file(filepath: Path | str) -> str:
    """Compute SHA-256 of a file, returning empty string if it doesn't exist."""
    path = Path(filepath)
    if not path.is_file():
        return ""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _sha256_string(s: str) -> str:
    """Compute lowercase hex SHA-256 of a UTF-8 string."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class EnvironmentFingerprint(BaseModel):
    """
    Deterministic snapshot of the environment that produced a run.
    Used by VEIL to ensure memory learns only from reproducible signal.
    """

    model_config = ConfigDict(frozen=True)

    runtime_image_digest: str
    python_version: str
    lockfile_hash: str
    command_set_hash: str
    env_var_names_hash: str

    @classmethod
    def generate(
        cls,
        sandbox_dockerfile: str = "Dockerfile.sandbox",
        lockfile: str = "uv.lock",
        commands: list[str] | None = None,
        allowed_env_vars: list[str] | None = None,
    ) -> EnvironmentFingerprint:
        """
        Generate a fingerprint from the current runtime environment.
        In the application, this is called once at startup or per-request.
        """
        # Read the sandbox Dockerfile as a proxy for the image digest
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        
        dockerfile_path = root_dir / sandbox_dockerfile
        image_digest = _sha256_file(dockerfile_path)

        lockfile_path = root_dir / lockfile
        lock_hash = _sha256_file(lockfile_path)

        # Hash the commands to ensure the same plan was executed
        cmds = commands or []
        cmd_blob = "\n".join(cmds)
        cmd_hash = _sha256_string(cmd_blob)

        # Hash JUST the names of the env vars, not their values (which might contain secrets)
        env_vars = allowed_env_vars or list(os.environ.keys())
        env_vars_sorted = sorted(env_vars)
        env_blob = "\n".join(env_vars_sorted)
        env_hash = _sha256_string(env_blob)

        return cls(
            runtime_image_digest=image_digest,
            python_version=sys.version,
            lockfile_hash=lock_hash,
            command_set_hash=cmd_hash,
            env_var_names_hash=env_hash,
        )
