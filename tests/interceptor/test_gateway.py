from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from dhi.interceptor.gateway import LiteLLMClient
from dhi.interceptor.models import ContextPayload


def test_litellm_client_success() -> None:
    client = LiteLLMClient(model_name="test-model")
    payload = ContextPayload(
        request_id="req-1",
        attempt=1,
        files=["main.py"],
        content="Fix this bug",
    )

    mock_response = Mock()
    mock_message = Mock()
    mock_message.content = '{"language": "python", "code": "print(1)", "notes": ""}'
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    with patch("dhi.interceptor.gateway.completion", return_value=mock_response) as mock_completion:
        result = client.generate_candidate(payload)

    mock_completion.assert_called_once()
    _, kwargs = mock_completion.call_args
    assert kwargs["model"] == "test-model"
    assert kwargs["timeout"] == 120.0
    assert kwargs["response_format"] == {"type": "json_object"}
    assert len(kwargs["messages"]) == 2
    assert result == '{"language": "python", "code": "print(1)", "notes": ""}'


def test_litellm_client_exception() -> None:
    client = LiteLLMClient()
    payload = ContextPayload(request_id="req-1", attempt=1, content="Fix this bug")

    with patch("dhi.interceptor.gateway.completion", side_effect=Exception("API Down")):
        with pytest.raises(RuntimeError, match="LLM Gateway Request Failed"):
            client.generate_candidate(payload)


def test_litellm_client_nvidia_provider_uses_dynamic_config() -> None:
    client = LiteLLMClient(
        model_name="moonshotai/kimi-k2.5",
        provider="nvidia",
        api_key="nvidia-test-key",
        extra_body={"chat_template_kwargs": {"thinking": True}},
    )
    payload = ContextPayload(
        request_id="req-nvidia-1",
        attempt=1,
        files=["main.py"],
        content="Fix this bug",
    )

    mock_response = Mock()
    mock_message = Mock()
    mock_message.content = '{"language": "python", "code": "print(2)", "notes": ""}'
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    with patch("dhi.interceptor.gateway.completion", return_value=mock_response) as mock_completion:
        result = client.generate_candidate(payload)

    mock_completion.assert_called_once()
    _, kwargs = mock_completion.call_args
    assert kwargs["model"] == "moonshotai/kimi-k2.5"
    assert kwargs["timeout"] == 120.0
    assert kwargs["api_base"] == "https://integrate.api.nvidia.com/v1"
    assert kwargs["api_key"] == "nvidia-test-key"
    assert kwargs["extra_body"] == {"chat_template_kwargs": {"thinking": True}}
    assert "response_format" not in kwargs
    assert result == '{"language": "python", "code": "print(2)", "notes": ""}'


def test_litellm_client_nvidia_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    client = LiteLLMClient(model_name="moonshotai/kimi-k2.5", provider="nvidia")
    payload = ContextPayload(request_id="req-1", attempt=1, content="Fix this bug")

    with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
        client.generate_candidate(payload)


def test_litellm_client_passes_optional_generation_config() -> None:
    client = LiteLLMClient(
        model_name="test-model",
        request_timeout_s=45.0,
        max_tokens=512,
        temperature=0.2,
        top_p=0.9,
    )
    payload = ContextPayload(request_id="req-2", attempt=1, content="Fix this bug")

    mock_response = Mock()
    mock_message = Mock()
    mock_message.content = '{"language": "python", "code": "print(3)", "notes": ""}'
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    with patch("dhi.interceptor.gateway.completion", return_value=mock_response) as mock_completion:
        _ = client.generate_candidate(payload)

    _, kwargs = mock_completion.call_args
    assert kwargs["timeout"] == 45.0
    assert kwargs["max_tokens"] == 512
    assert kwargs["temperature"] == 0.2
    assert kwargs["top_p"] == 0.9
