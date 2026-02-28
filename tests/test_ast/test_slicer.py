"""Tests for slicer correctness, determinism, and observability."""

from __future__ import annotations

from pathlib import Path

import pytest

from dhi.ast_ext.models import SliceRequest
from dhi.ast_ext.slicer import ContextSlicer

FIXTURE_SOURCE = """\
def helper_a(x: int) -> int:
    return x + 1


def helper_b(x: int) -> int:
    return x * 2


def unrelated() -> str:
    return "unrelated"


def target_func(n: int) -> int:
    a = helper_a(n)
    b = helper_b(a)
    return a + b
"""


@pytest.fixture()
def slicer() -> ContextSlicer:
    return ContextSlicer()


class TestSliceCorrectness:
    def test_target_is_included(self, slicer: ContextSlicer) -> None:
        result = slicer.slice_source(FIXTURE_SOURCE, "target_func")
        assert result.found
        assert "target_func" in result.slice_source

    def test_direct_dependencies_included(self, slicer: ContextSlicer) -> None:
        result = slicer.slice_source(FIXTURE_SOURCE, "target_func")
        assert result.found
        assert "helper_a" in result.slice_source
        assert "helper_b" in result.slice_source

    def test_unrelated_symbols_excluded(self, slicer: ContextSlicer) -> None:
        result = slicer.slice_source(FIXTURE_SOURCE, "target_func")
        assert result.found
        assert "def unrelated" not in result.slice_source

    def test_leaf_dependency_has_no_extra_deps(self, slicer: ContextSlicer) -> None:
        result = slicer.slice_source(FIXTURE_SOURCE, "helper_a")
        assert result.found
        assert "helper_a" in result.slice_source
        assert result.symbol_count == 1

    def test_missing_symbol_returns_found_false(self, slicer: ContextSlicer) -> None:
        result = slicer.slice_source(FIXTURE_SOURCE, "nonexistent_symbol")
        assert not result.found
        assert result.error is not None
        assert result.slice_source == ""


class TestObservabilityMetadata:
    def test_symbol_count_is_positive(self, slicer: ContextSlicer) -> None:
        result = slicer.slice_source(FIXTURE_SOURCE, "target_func")
        assert result.symbol_count >= 1

    def test_edge_count_matches_dependencies(self, slicer: ContextSlicer) -> None:
        result = slicer.slice_source(FIXTURE_SOURCE, "target_func")
        assert result.edge_count == 2

    def test_slice_size_bytes_is_nonzero(self, slicer: ContextSlicer) -> None:
        result = slicer.slice_source(FIXTURE_SOURCE, "target_func")
        assert result.found
        assert result.slice_size_bytes > 0

    def test_slice_size_bytes_matches_source(self, slicer: ContextSlicer) -> None:
        result = slicer.slice_source(FIXTURE_SOURCE, "target_func")
        assert result.found
        assert result.slice_size_bytes == len(result.slice_source.encode("utf-8"))


class TestDeterminism:
    def test_same_source_produces_identical_slice_repeatedly(self, slicer: ContextSlicer) -> None:
        slices = [slicer.slice_source(FIXTURE_SOURCE, "target_func") for _ in range(5)]
        sources = [result.slice_source for result in slices]
        assert len(set(sources)) == 1

    def test_same_file_produces_identical_slice(
        self,
        slicer: ContextSlicer,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "fixture.py"
        path.write_text(FIXTURE_SOURCE, encoding="utf-8")
        first = slicer.slice(SliceRequest(file_path=str(path), target="target_func"))
        second = slicer.slice(SliceRequest(file_path=str(path), target="target_func"))
        assert first.slice_source == second.slice_source


class TestFileBased:
    def test_file_not_found_returns_found_false(self, slicer: ContextSlicer) -> None:
        result = slicer.slice(SliceRequest(file_path="/no/such/file.py", target="foo"))
        assert not result.found
        assert result.error is not None

    def test_slice_from_real_file(self, slicer: ContextSlicer, tmp_path: Path) -> None:
        path = tmp_path / "real.py"
        path.write_text(FIXTURE_SOURCE, encoding="utf-8")
        result = slicer.slice(SliceRequest(file_path=str(path), target="target_func"))
        assert result.found
        assert "target_func" in result.slice_source

    def test_line_number_target(self, slicer: ContextSlicer, tmp_path: Path) -> None:
        path = tmp_path / "real.py"
        path.write_text(FIXTURE_SOURCE, encoding="utf-8")
        result = slicer.slice(SliceRequest(file_path=str(path), target_line=13))
        assert result.found
        assert result.target == "target_func"

    def test_invalid_line_number_returns_found_false(
        self,
        slicer: ContextSlicer,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "real.py"
        path.write_text(FIXTURE_SOURCE, encoding="utf-8")
        result = slicer.slice(SliceRequest(file_path=str(path), target_line=999))
        assert not result.found
        assert result.error is not None
