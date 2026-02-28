"""Pydantic models for the AST extraction and slicing pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class SymbolInfo(BaseModel):
    """A single extracted symbol (class or function) from a Python file."""

    name: str = Field(description="Symbol name (function or class identifier)")
    kind: str = Field(description="Symbol kind: 'function' or 'class'")
    start_line: int = Field(description="1-indexed start line in source file")
    end_line: int = Field(description="1-indexed end line in source file")
    source: str = Field(description="Raw source text of the symbol body")


class CallEdge(BaseModel):
    """A directed call edge: caller symbol -> callee name."""

    caller: str = Field(description="Name of the calling function or class method")
    callee: str = Field(description="Name of the function being called")


class SliceRequest(BaseModel):
    """Request for a dependency slice from a source file."""

    file_path: str = Field(description="Absolute path to the Python source file")
    target: str | None = Field(
        default=None,
        description="Target function/class name to slice from",
    )
    target_line: int | None = Field(
        default=None,
        ge=1,
        description="1-indexed line number to resolve into a target symbol",
    )

    @model_validator(mode="after")
    def _validate_target_or_line(self) -> "SliceRequest":
        if not self.target and self.target_line is None:
            raise ValueError("Either 'target' or 'target_line' must be provided.")
        return self


class SliceResult(BaseModel):
    """Output of the context slicer for a given target symbol."""

    target: str = Field(description="The requested target symbol name")
    found: bool = Field(description="Whether the target symbol was found in the file")
    slice_source: str = Field(
        default="",
        description="Concatenated source of target symbol and its direct dependencies",
    )
    symbol_count: int = Field(
        default=0,
        description="Number of symbols included in the slice",
    )
    edge_count: int = Field(
        default=0,
        description="Number of call edges resolved in the slice",
    )
    slice_size_bytes: int = Field(
        default=0,
        description="Byte size of the slice_source string (UTF-8)",
    )
    error: str | None = Field(
        default=None,
        description="Error message if slicing failed",
    )
