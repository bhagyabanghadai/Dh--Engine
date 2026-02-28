"""LiteLLM gateway integration for outbound cloud generation requests."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping
from typing import Any

try:
    from litellm import completion
except Exception:  # pragma: no cover - optional dependency in tests
    completion = None

from dhi.ast_ext.extractor import ASTExtractor
from dhi.ast_ext.models import SliceRequest, SymbolInfo
from dhi.ast_ext.slicer import ContextSlicer

from .models import ContextPayload

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are Dhi, an advanced AI software engineer.
You will be provided with context files and a user request context.
Your task is to analyze the context and return a secure, robust code solution.
You MUST format your entire response as a single, valid JSON object containing exactly three keys:
{
  "language": "python",
  "code": "print('hello')",
  "notes": "My reasoning and explanation."
}
DO NOT wrap the code value inside markdown fences within the JSON property.
Your response must be parseable by standard JSON parsers.
""".strip()

# Feature flag: set to True to enable AST-sliced context in default path.
AST_SLICE_ENABLED: bool = True

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LINE_PREFIX_PATTERN = re.compile(r"^line\s+(\d+)$", re.IGNORECASE)
_DEFAULT_NVIDIA_API_BASE = "https://integrate.api.nvidia.com/v1"
_SUPPORTED_PROVIDERS = {"openai", "nvidia", "custom"}
_DEFAULT_LLM_TIMEOUT_S = 120.0

_slicer = ContextSlicer()
_extractor = ASTExtractor()


def _read_mapping_value(obj: object, key: str) -> object:
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)


def _extract_content(response: object) -> str:
    choices = _read_mapping_value(response, "choices")
    if not isinstance(choices, list) or not choices:
        return ""

    first_choice = choices[0]
    message = _read_mapping_value(first_choice, "message")
    content = _read_mapping_value(message, "content")
    return content if isinstance(content, str) else ""


def _extract_explicit_target_or_line(content: str) -> tuple[str | None, int | None]:
    stripped = content.strip()
    if not stripped:
        return None, None

    first_line = stripped.splitlines()[0].strip()
    if _IDENTIFIER_PATTERN.fullmatch(first_line):
        return first_line, None

    if first_line.isdigit():
        return None, int(first_line)

    match = _LINE_PREFIX_PATTERN.fullmatch(first_line)
    if match is not None:
        return None, int(match.group(1))

    return None, None


def _infer_target_from_prompt(symbols: list[SymbolInfo], content: str) -> str | None:
    matches: list[tuple[int, int, int, str]] = []
    for symbol in symbols:
        pattern = re.compile(rf"\b{re.escape(symbol.name)}\b")
        match = pattern.search(content)
        if match is None:
            continue
        matches.append((match.start(), -len(symbol.name), symbol.start_line, symbol.name))

    if not matches:
        return None

    matches.sort()
    return matches[0][3]


def _select_default_target(symbols: list[SymbolInfo]) -> str | None:
    if not symbols:
        return None
    return min(symbols, key=lambda symbol: symbol.start_line).name


def _build_slice_request(file_path: str, content: str) -> SliceRequest | None:
    try:
        symbols, _ = _extractor.extract_file(file_path)
    except Exception as exc:
        logger.exception("AST symbol extraction failed for '%s': %s", file_path, exc)
        return None

    explicit_target, explicit_line = _extract_explicit_target_or_line(content)

    if explicit_target is not None:
        known_names = {symbol.name for symbol in symbols}
        if explicit_target in known_names:
            return SliceRequest(file_path=file_path, target=explicit_target)
        # Explicit symbol request that does not exist should fall back to raw prompt.
        return None

    if explicit_line is not None:
        return SliceRequest(file_path=file_path, target_line=explicit_line)

    inferred_target = _infer_target_from_prompt(symbols, content)
    if inferred_target is not None:
        return SliceRequest(file_path=file_path, target=inferred_target)

    default_target = _select_default_target(symbols)
    if default_target is not None:
        return SliceRequest(file_path=file_path, target=default_target)

    return None


def _build_context(payload: ContextPayload) -> str:
    """Return context string used in the outbound LLM prompt."""
    if not AST_SLICE_ENABLED or not payload.files:
        return payload.content

    file_path = payload.files[0]
    request = _build_slice_request(file_path=file_path, content=payload.content)
    if request is None:
        return payload.content

    try:
        result = _slicer.slice(request)
        if result.found:
            logger.info(
                "AST slice active for request %s: symbol_count=%d edge_count=%d "
                "slice_size_bytes=%d",
                payload.request_id,
                result.symbol_count,
                result.edge_count,
                result.slice_size_bytes,
            )
            return (
                f"[AST Slice] target={result.target} "
                f"symbols={result.symbol_count} edges={result.edge_count} "
                f"bytes={result.slice_size_bytes}\n\n"
                f"{result.slice_source}"
            )

        logger.warning(
            "AST slice found=False for request %s target='%s': %s; "
            "falling back to raw content.",
            payload.request_id,
            result.target,
            result.error,
        )
    except Exception as exc:
        logger.exception(
            "AST slice raised for request %s, falling back to raw content: %s",
            payload.request_id,
            exc,
        )

    return payload.content


class LiteLLMClient:
    """Wrapper around LiteLLM completion to produce raw candidate text."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        provider: str = "openai",
        api_base: str | None = None,
        api_key: str | None = None,
        extra_body: dict[str, object] | None = None,
        request_timeout_s: float = _DEFAULT_LLM_TIMEOUT_S,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ) -> None:
        self.model_name = model_name
        self.provider = provider.strip().lower()
        if self.provider not in _SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported LLM provider '{provider}'. "
                f"Supported providers: {sorted(_SUPPORTED_PROVIDERS)}"
            )
        self.api_base = api_base
        self.api_key = api_key
        self.extra_body = dict(extra_body or {})
        self.request_timeout_s = request_timeout_s
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.kwargs = kwargs

    def generate_candidate(self, payload: ContextPayload) -> str:
        """Send governed context to configured LLM and return raw content."""
        if completion is None:
            raise RuntimeError("LiteLLM is not installed. Add 'litellm' to dependencies.")

        context = _build_context(payload)

        prompt = f"Request ID: {payload.request_id}\n\n"
        if payload.files:
            prompt += "CONTEXT FILES:\n"
            prompt += ", ".join(payload.files) + "\n\n"

        prompt += "CONTEXT CONTENT:\n"
        prompt += context

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt.strip()},
        ]

        completion_kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "timeout": self.request_timeout_s,
        }
        completion_kwargs.update(self.kwargs)

        if self.max_tokens is not None:
            completion_kwargs["max_tokens"] = self.max_tokens
        if self.temperature is not None:
            completion_kwargs["temperature"] = self.temperature
        if self.top_p is not None:
            completion_kwargs["top_p"] = self.top_p

        # Most providers we use support strict JSON response formatting.
        # NVIDIA's OpenAI-compatible endpoint may reject this argument, so
        # we disable it there and rely on the extraction fallback path.
        if self.provider != "nvidia":
            completion_kwargs["response_format"] = {"type": "json_object"}

        if self.extra_body:
            completion_kwargs["extra_body"] = self.extra_body

        try:
            completion_kwargs.update(self._provider_kwargs())
            response = completion(**completion_kwargs)
        except Exception as err:
            raise RuntimeError(f"LLM Gateway Request Failed: {err}") from err

        return _extract_content(response)

    def _provider_kwargs(self) -> dict[str, Any]:
        provider_kwargs: dict[str, Any] = {}

        if self.provider == "nvidia":
            api_base = self.api_base or os.getenv("NVIDIA_API_BASE") or _DEFAULT_NVIDIA_API_BASE
            api_key = self.api_key or os.getenv("NVIDIA_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "NVIDIA_API_KEY is required when llm_provider='nvidia'."
                )
            provider_kwargs["api_base"] = api_base
            provider_kwargs["api_key"] = api_key
            return provider_kwargs

        if self.api_base:
            provider_kwargs["api_base"] = self.api_base
        if self.api_key:
            provider_kwargs["api_key"] = self.api_key
        return provider_kwargs
