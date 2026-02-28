from __future__ import annotations

import os
from pathlib import Path

import pytest

import dhi.env as env_module


def test_load_dotenv_reads_local_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("NVIDIA_API_KEY=test-key\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setattr(env_module, "_ENV_LOADED", False)

    env_module.load_dotenv()
    assert os.getenv("NVIDIA_API_KEY") == "test-key"


def test_load_dotenv_does_not_override_existing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("NVIDIA_API_KEY=file-key\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NVIDIA_API_KEY", "existing-key")
    monkeypatch.setattr(env_module, "_ENV_LOADED", False)

    env_module.load_dotenv()
    assert os.getenv("NVIDIA_API_KEY") == "existing-key"
