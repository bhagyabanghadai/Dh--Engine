"""Tests for the AST symbol and call-edge extractor (extractor.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dhi.ast_ext.extractor import ASTExtractor

FIXTURE_SOURCE = """\
def add(a: int, b: int) -> int:
    return a + b


def multiply(a: int, b: int) -> int:
    return a * b


def compute(x: int) -> int:
    result = add(x, 10)
    doubled = multiply(result, 2)
    return doubled


class Calculator:
    def run(self) -> int:
        return compute(5)
"""


DECORATED_SOURCE = """\
@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@decorator
class Wrapped:
    pass
"""


@pytest.fixture()
def extractor() -> ASTExtractor:
    return ASTExtractor()


def test_extracts_top_level_functions(extractor: ASTExtractor) -> None:
    symbols, _ = extractor.extract(FIXTURE_SOURCE)
    names = [symbol.name for symbol in symbols]
    assert "add" in names
    assert "multiply" in names
    assert "compute" in names


def test_extracts_class(extractor: ASTExtractor) -> None:
    symbols, _ = extractor.extract(FIXTURE_SOURCE)
    class_symbols = [symbol for symbol in symbols if symbol.kind == "class"]
    assert any(symbol.name == "Calculator" for symbol in class_symbols)


def test_extracts_decorated_definitions(extractor: ASTExtractor) -> None:
    symbols, _ = extractor.extract(DECORATED_SOURCE)
    names = {symbol.name for symbol in symbols}
    assert "health_check" in names
    assert "Wrapped" in names


def test_symbol_kinds_are_correct(extractor: ASTExtractor) -> None:
    symbols, _ = extractor.extract(FIXTURE_SOURCE)
    kind_map = {symbol.name: symbol.kind for symbol in symbols}
    assert kind_map["add"] == "function"
    assert kind_map["compute"] == "function"
    assert kind_map["Calculator"] == "class"


def test_symbol_line_numbers_are_positive(extractor: ASTExtractor) -> None:
    symbols, _ = extractor.extract(FIXTURE_SOURCE)
    for symbol in symbols:
        assert symbol.start_line >= 1
        assert symbol.end_line >= symbol.start_line


def test_symbol_source_contains_def(extractor: ASTExtractor) -> None:
    symbols, _ = extractor.extract(FIXTURE_SOURCE)
    for symbol in symbols:
        assert "def " in symbol.source or "class " in symbol.source


def test_no_duplicate_symbols(extractor: ASTExtractor) -> None:
    symbols, _ = extractor.extract(FIXTURE_SOURCE)
    names = [symbol.name for symbol in symbols]
    assert len(names) == len(set(names)), "Duplicate symbol names found"


def test_extracts_call_edges(extractor: ASTExtractor) -> None:
    _, edges = extractor.extract(FIXTURE_SOURCE)
    callee_names = {edge.callee for edge in edges if edge.caller == "compute"}
    assert "add" in callee_names
    assert "multiply" in callee_names


def test_edges_only_reference_known_symbols(extractor: ASTExtractor) -> None:
    symbols, edges = extractor.extract(FIXTURE_SOURCE)
    known_names = {symbol.name for symbol in symbols}
    for edge in edges:
        assert edge.caller in known_names, f"Unknown caller: {edge.caller}"
        assert edge.callee in known_names, f"Unknown callee: {edge.callee}"


def test_empty_source_produces_no_symbols(extractor: ASTExtractor) -> None:
    symbols, edges = extractor.extract("")
    assert symbols == []
    assert edges == []


def test_extract_file_reads_path(extractor: ASTExtractor, tmp_path: Path) -> None:
    path = tmp_path / "calc.py"
    path.write_text(FIXTURE_SOURCE, encoding="utf-8")
    symbols, _ = extractor.extract_file(str(path))
    assert len(symbols) > 0
    assert any(symbol.name == "add" for symbol in symbols)


def test_extract_file_raises_for_missing(extractor: ASTExtractor) -> None:
    with pytest.raises(FileNotFoundError):
        extractor.extract_file("/does/not/exist.py")
