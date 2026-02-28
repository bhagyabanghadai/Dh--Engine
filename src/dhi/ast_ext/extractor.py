"""Symbol inventory and call-edge extractor using Tree-sitter AST."""

from __future__ import annotations

import logging
from collections import deque
from pathlib import Path

from .models import CallEdge, SymbolInfo
from .parser import get_node_text, parse_source

logger = logging.getLogger(__name__)


def _walk_definitions(root: object) -> tuple[list[object], list[object]]:
    """Walk *root* and collect function and class definition nodes.

    Includes:
    - top-level functions/classes
    - class methods
    - decorated functions/classes
    - async functions

    Nested closures are intentionally skipped to keep the symbol inventory flat.
    """
    fn_nodes: list[object] = []
    cls_nodes: list[object] = []
    queue: deque[object] = deque(getattr(root, "children", []))

    while queue:
        node = queue.popleft()
        node_type = str(getattr(node, "type", ""))

        if node_type == "decorated_definition":
            for child in getattr(node, "children", []):
                child_type = str(getattr(child, "type", ""))
                if child_type in {
                    "function_definition",
                    "async_function_definition",
                    "class_definition",
                }:
                    queue.appendleft(child)
            continue

        if node_type in {"function_definition", "async_function_definition"}:
            fn_nodes.append(node)
            continue

        if node_type == "class_definition":
            cls_nodes.append(node)
            for child in getattr(node, "children", []):
                if str(getattr(child, "type", "")) == "block":
                    queue.extend(getattr(child, "children", []))
            continue

        if node_type in {"module", "block"}:
            queue.extend(getattr(node, "children", []))

    return fn_nodes, cls_nodes


def _extract_name(node: object, source_bytes: bytes) -> str | None:
    """Return identifier name from a definition node."""
    for child in getattr(node, "children", []):
        if str(getattr(child, "type", "")) == "identifier":
            return get_node_text(child, source_bytes)
    return None


def _line_from_point(point: object) -> int:
    """Convert a Tree-sitter start/end point to 1-indexed line number."""
    if isinstance(point, tuple) and point:
        return int(point[0]) + 1
    try:
        return int(point[0]) + 1  # type: ignore[index]
    except Exception:
        return 1


def _find_call_names_in_node(fn_node: object, source_bytes: bytes) -> set[str]:
    """Return plain identifier names called inside *fn_node*."""
    called: set[str] = set()
    queue: deque[object] = deque(getattr(fn_node, "children", []))

    while queue:
        node = queue.popleft()
        node_type = str(getattr(node, "type", ""))

        if node_type == "call":
            func_child: object | None = None
            for child in getattr(node, "children", []):
                child_field = getattr(child, "field", None)
                child_type = str(getattr(child, "type", ""))
                if child_field == "function" or child_type in {"identifier", "attribute"}:
                    func_child = child
                    break

            if func_child is not None:
                func_child_type = str(getattr(func_child, "type", ""))
                if func_child_type == "identifier":
                    called.add(get_node_text(func_child, source_bytes))
                elif func_child_type == "attribute":
                    # For a.b() keep the left-most identifier only.
                    for sub in getattr(func_child, "children", []):
                        if str(getattr(sub, "type", "")) == "identifier":
                            called.add(get_node_text(sub, source_bytes))
                            break

        queue.extend(getattr(node, "children", []))

    return called


def _query_symbols(tree_root: object, source_bytes: bytes) -> list[SymbolInfo]:
    """Walk tree and return a deduplicated list of SymbolInfo objects."""
    fn_nodes, cls_nodes = _walk_definitions(tree_root)
    symbols: list[SymbolInfo] = []
    seen_names: set[str] = set()

    for kind_label, nodes in (("function", fn_nodes), ("class", cls_nodes)):
        for node in nodes:
            name = _extract_name(node, source_bytes)
            if name is None or name in seen_names:
                continue

            seen_names.add(name)
            start_line = _line_from_point(getattr(node, "start_point", (0, 0)))
            end_line = _line_from_point(getattr(node, "end_point", (0, 0)))

            symbols.append(
                SymbolInfo(
                    name=name,
                    kind=kind_label,
                    start_line=start_line,
                    end_line=end_line,
                    source=get_node_text(node, source_bytes),
                )
            )

    return symbols


def _query_call_edges(symbols: list[SymbolInfo]) -> list[CallEdge]:
    """Resolve direct call edges (caller -> callee) for known function symbols."""
    known_names = {s.name for s in symbols}
    edges: list[CallEdge] = []
    seen_edges: set[tuple[str, str]] = set()

    for symbol in symbols:
        if symbol.kind != "function":
            continue

        symbol_source_bytes = symbol.source.encode("utf-8")
        symbol_tree = parse_source(symbol.source)
        called_names = _find_call_names_in_node(symbol_tree.root_node, symbol_source_bytes)

        for callee_name in called_names:
            if callee_name not in known_names or callee_name == symbol.name:
                continue

            edge_key = (symbol.name, callee_name)
            if edge_key in seen_edges:
                continue

            seen_edges.add(edge_key)
            edges.append(CallEdge(caller=symbol.name, callee=callee_name))

    return edges


class ASTExtractor:
    """Orchestrates Tree-sitter parse, symbol extraction, and edge resolution."""

    def extract(self, source: str) -> tuple[list[SymbolInfo], list[CallEdge]]:
        """Parse *source* and return symbols and direct call edges."""
        source_bytes = source.encode("utf-8")
        tree = parse_source(source)
        symbols = _query_symbols(tree.root_node, source_bytes)
        edges = _query_call_edges(symbols)
        logger.debug("Extracted %d symbols and %d edges", len(symbols), len(edges))
        return symbols, edges

    def extract_file(self, path: str | Path) -> tuple[list[SymbolInfo], list[CallEdge]]:
        """Parse file at *path* and return symbols and call edges."""
        resolved = Path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Source file not found: {resolved}")
        source = resolved.read_text(encoding="utf-8")
        return self.extract(source)
