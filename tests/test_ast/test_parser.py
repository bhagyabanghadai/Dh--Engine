"""Tests for the Tree-sitter AST parser module (parser.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

SIMPLE_PYTHON = """\
def greet(name: str) -> str:
    return f"Hello, {name}!"


class Greeter:
    def say_hi(self) -> str:
        return greet("World")
"""


def test_parse_source_returns_tree() -> None:
    from dhi.ast_ext.parser import parse_source

    tree = parse_source(SIMPLE_PYTHON)
    assert tree is not None
    assert tree.root_node is not None


def test_parse_source_root_has_children() -> None:
    from dhi.ast_ext.parser import parse_source

    tree = parse_source(SIMPLE_PYTHON)
    assert tree.root_node.child_count > 0


def test_parse_source_empty_string() -> None:
    from dhi.ast_ext.parser import parse_source

    tree = parse_source("")
    assert tree is not None
    assert tree.root_node is not None


def test_parse_file_raises_for_missing_file() -> None:
    from dhi.ast_ext.parser import parse_file

    with pytest.raises(FileNotFoundError):
        parse_file("/nonexistent/path/file.py")


def test_parse_file_parses_real_file(tmp_path: Path) -> None:
    from dhi.ast_ext.parser import parse_file

    path = tmp_path / "sample.py"
    path.write_text(SIMPLE_PYTHON, encoding="utf-8")
    tree = parse_file(str(path))
    assert tree.root_node.child_count > 0


def test_get_node_text_returns_correct_slice() -> None:
    from dhi.ast_ext.parser import get_node_text, parse_source

    source = "x = 42\n"
    tree = parse_source(source)
    source_bytes = source.encode("utf-8")
    text = get_node_text(tree.root_node, source_bytes)
    assert "42" in text


def test_language_loads_only_once() -> None:
    """Calling _get_python_language() multiple times returns the same object."""
    from dhi.ast_ext.parser import _get_python_language

    lang1 = _get_python_language()
    lang2 = _get_python_language()
    assert lang1 is lang2
