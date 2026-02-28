"""Context slicer: produces dependency-aware source slices for a target symbol."""

from __future__ import annotations

import logging
from pathlib import Path

from .extractor import ASTExtractor
from .models import CallEdge, SliceRequest, SliceResult, SymbolInfo

logger = logging.getLogger(__name__)

_extractor = ASTExtractor()


def _resolve_target_symbol(
    *,
    symbols: list[SymbolInfo],
    target: str | None,
    target_line: int | None,
) -> tuple[str | None, str | None]:
    """Resolve requested target symbol name from explicit name or line number."""
    symbol_map: dict[str, SymbolInfo] = {symbol.name: symbol for symbol in symbols}

    if target:
        if target in symbol_map:
            return target, None
        # If explicit symbol is missing, still allow line fallback when provided.
        if target_line is None:
            return None, f"Symbol '{target}' not found in source file."

    if target_line is not None:
        ordered = sorted(symbols, key=lambda symbol: symbol.start_line)
        for symbol in ordered:
            if symbol.start_line <= target_line <= symbol.end_line:
                return symbol.name, None
        # Support decorator lines immediately above a definition.
        for symbol in ordered:
            delta = symbol.start_line - target_line
            if 0 < delta <= 3:
                return symbol.name, None
        return None, f"No symbol found at line {target_line}."

    return None, "Either target or target_line must be provided."


def _collect_slice(
    target: str,
    symbols: list[SymbolInfo],
    edges: list[CallEdge],
) -> SliceResult:
    """Build a ``SliceResult`` from extracted symbols and call edges."""
    symbol_map: dict[str, SymbolInfo] = {symbol.name: symbol for symbol in symbols}
    if target not in symbol_map:
        logger.warning("Target symbol '%s' not found in extracted symbols.", target)
        return SliceResult(
            target=target,
            found=False,
            error=f"Symbol '{target}' not found in source file.",
        )

    dependency_names: set[str] = set()
    for edge in edges:
        if edge.caller == target:
            dependency_names.add(edge.callee)

    included: list[SymbolInfo] = [symbol_map[target]]
    for dependency_name in dependency_names:
        if dependency_name in symbol_map and dependency_name != target:
            included.append(symbol_map[dependency_name])

    included.sort(key=lambda symbol: symbol.start_line)
    slice_source = "\n\n".join(symbol.source for symbol in included)
    slice_bytes = len(slice_source.encode("utf-8"))

    return SliceResult(
        target=target,
        found=True,
        slice_source=slice_source,
        symbol_count=len(included),
        edge_count=len(dependency_names),
        slice_size_bytes=slice_bytes,
    )


class ContextSlicer:
    """Public interface for AST-based context slicing."""

    def slice(self, request: SliceRequest) -> SliceResult:
        """Return AST-based context slice for *request* file and target."""
        file_path = Path(request.file_path)
        if request.target:
            target_display = request.target
        elif request.target_line is not None:
            target_display = f"line:{request.target_line}"
        else:
            target_display = ""

        if not file_path.exists():
            return SliceResult(
                target=target_display,
                found=False,
                error=f"File not found: {request.file_path}",
            )

        try:
            symbols, edges = _extractor.extract_file(file_path)
        except Exception as exc:
            logger.exception("AST extraction failed for file '%s': %s", request.file_path, exc)
            return SliceResult(
                target=target_display,
                found=False,
                error=f"AST extraction error: {exc}",
            )

        resolved_target, error = _resolve_target_symbol(
            symbols=symbols,
            target=request.target,
            target_line=request.target_line,
        )
        if resolved_target is None:
            return SliceResult(
                target=target_display,
                found=False,
                error=error,
            )

        result = _collect_slice(resolved_target, symbols, edges)
        logger.info(
            "Slice for '%s' in '%s': found=%s symbols=%d edges=%d bytes=%d",
            resolved_target,
            request.file_path,
            result.found,
            result.symbol_count,
            result.edge_count,
            result.slice_size_bytes,
        )
        return result

    def slice_source(self, source: str, target: str) -> SliceResult:
        """Return a context slice directly from in-memory source text."""
        try:
            symbols, edges = _extractor.extract(source)
        except Exception as exc:
            logger.exception("AST extraction failed: %s", exc)
            return SliceResult(
                target=target,
                found=False,
                error=f"AST extraction error: {exc}",
            )

        return _collect_slice(target, symbols, edges)
