"""Tests for the VEIL Environment Fingerprint Generator."""

import sys

from dhi.veil.fingerprint import EnvironmentFingerprint


def test_fingerprint_generation() -> None:
    """Test that we can generate a fingerprint and all fields are populated."""
    fp = EnvironmentFingerprint.generate()

    assert fp.runtime_image_digest != ""
    assert fp.python_version.startswith(f"{sys.version_info.major}.{sys.version_info.minor}")
    assert fp.lockfile_hash != ""
    assert fp.command_set_hash != ""
    assert fp.env_var_names_hash != ""


def test_fingerprint_determinism() -> None:
    """Test that two generations in the same process yield identical hashes."""
    fp1 = EnvironmentFingerprint.generate()
    fp2 = EnvironmentFingerprint.generate()

    assert fp1 == fp2
    assert fp1.runtime_image_digest == fp2.runtime_image_digest
    assert fp1.python_version == fp2.python_version
    assert fp1.lockfile_hash == fp2.lockfile_hash
    assert fp1.command_set_hash == fp2.command_set_hash
    assert fp1.env_var_names_hash == fp2.env_var_names_hash


def test_fingerprint_inequality() -> None:
    """Test that differing fields result in unequal fingerprints."""
    fp1 = EnvironmentFingerprint.generate()
    fp2 = EnvironmentFingerprint(
        runtime_image_digest=fp1.runtime_image_digest,
        python_version=fp1.python_version,
        lockfile_hash="different_hash",
        command_set_hash=fp1.command_set_hash,
        env_var_names_hash=fp1.env_var_names_hash,
    )

    assert fp1 != fp2
