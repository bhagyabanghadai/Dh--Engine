from __future__ import annotations

from dhi.sandbox.executor import _decode_stream, _summarize_capped_stream


def test_decode_stream_returns_utf8_prefix() -> None:
    raw = ("a" * 128).encode("utf-8")
    decoded = _decode_stream(raw)
    assert decoded == "a" * 128


def test_summarize_capped_stream_adds_metadata_marker() -> None:
    raw = ("b" * (20 * 1024)).encode("utf-8")
    summary = _summarize_capped_stream(raw, stream_name="stdout")
    assert "[TRUNCATED_STDOUT" in summary
    assert "original_bytes=" in summary
    assert "preview_bytes=" in summary
