"""Minimal .env loader for local developer secrets."""

from __future__ import annotations

import os
from pathlib import Path

_ENV_LOADED = False


def load_dotenv(*, override: bool = False) -> None:
    """Load the first .env file found from the current directory upward."""
    global _ENV_LOADED
    if _ENV_LOADED and not override:
        return

    env_path = _find_env_file()
    if env_path is None:
        _ENV_LOADED = True
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue

        value = value.strip()
        if len(value) >= 2 and (
            (value[0] == "'" and value[-1] == "'")
            or (value[0] == '"' and value[-1] == '"')
        ):
            value = value[1:-1]

        if override or key not in os.environ:
            os.environ[key] = value

    _ENV_LOADED = True


def _find_env_file() -> Path | None:
    cwd = Path.cwd()
    for base in [cwd, *cwd.parents]:
        candidate = base / ".env"
        if candidate.is_file():
            return candidate
    return None

