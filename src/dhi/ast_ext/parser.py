"""Tree-sitter Python parser: initializes and exposes parse functionality."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from tree_sitter import Language, Tree

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_python_language() -> "Language":
    """Return the cached Tree-sitter Python Language object.

    The grammar is loaded once per process via tree-sitter-python's bundled SO.
    """
    try:
        import tree_sitter_python
        from tree_sitter import Language

        return Language(tree_sitter_python.language())
    except Exception as exc:
        raise RuntimeError(
            "Failed to initialize Tree-sitter Python language. "
            "Ensure 'tree-sitter-python' is installed."
        ) from exc


def parse_source(source: str) -> "Tree":
    """Parse a Python source string and return the Tree-sitter Tree.

    Args:
        source: UTF-8 string of Python source code.

    Returns:
        Parsed Tree-sitter Tree.

    Raises:
        RuntimeError: If the parser cannot be initialised.
    """
    from tree_sitter import Parser

    lang = _get_python_language()
    parser = Parser(lang)
    return parser.parse(source.encode("utf-8"))


def parse_file(path: str | Path) -> "Tree":
    """Read and parse a Python file, returning the Tree-sitter Tree.

    Args:
        path: Absolute or relative path to a `.py` file.

    Returns:
        Parsed Tree-sitter Tree.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If parsing fails.
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Source file not found: {resolved}")

    source = resolved.read_text(encoding="utf-8")
    logger.debug("Parsing file: %s (%d bytes)", resolved, len(source.encode("utf-8")))
    return parse_source(source)


def get_node_text(node: object, source_bytes: bytes) -> str:
    """Extract the raw UTF-8 text for a Tree-sitter node.

    Args:
        node: Tree-sitter Node.
        source_bytes: The original source encoded as bytes.

    Returns:
        Plain text string for the node's byte range.
    """
    typed_node = cast(Any, node)
    start_byte = int(typed_node.start_byte)
    end_byte = int(typed_node.end_byte)
    return source_bytes[start_byte:end_byte].decode("utf-8")
