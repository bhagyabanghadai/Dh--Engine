from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

import dhi.main as main_module
from dhi.interceptor.models import GovernanceAuditRecord
from dhi.interceptor.service import InterceptorResponse, InterceptorService
from dhi.main import app
from dhi.orchestrator.models import OrchestrationResult
from dhi.sandbox.models import VerificationMode, VerificationResult, VerificationTier

client = TestClient(app)


def _sample_verification_result(request_id: str) -> VerificationResult:
    return VerificationResult(
        request_id=request_id,
        attempt=1,
        mode=VerificationMode.balanced,
        tier=VerificationTier.L0,
        status="pass",
        exit_code=0,
        duration_ms=10,
        stdout="",
        stderr="",
    )


def test_verify_endpoint_uses_sandbox_executor() -> None:
    with patch(
        "dhi.main.run_in_sandbox",
        return_value=_sample_verification_result("verify-1"),
    ) as mock_run:
        response = client.post(
            "/verify",
            json={
                "code": "print('ok')",
                "request_id": "verify-1",
                "attempt": 1,
                "mode": "balanced",
            },
        )

    assert response.status_code == 200
    body = response.json()
    # /verify now returns AttestationResponse: {result: ..., manifest: ...}
    assert body["result"]["request_id"] == "verify-1"
    assert body["result"]["status"] == "pass"
    assert "manifest" in body
    assert body["manifest"]["tier"] == "L0"
    mock_run.assert_called_once()


def test_intercept_endpoint_uses_interceptor_service() -> None:
    audit = GovernanceAuditRecord(
        request_id="intercept-1",
        timestamp=datetime.now(timezone.utc),
        file_count=1,
        redaction_count=0,
        prompt_minimized=False,
        blocked=False,
        block_reason=None,
    )
    fake_response = InterceptorResponse(
        request_id="intercept-1",
        audit=audit,
        llm_notes="ok",
        extraction_success=True,
        extraction_error=None,
        verification_result=_sample_verification_result("intercept-1"),
    )

    with patch.object(
        InterceptorService,
        "process_request",
        return_value=fake_response,
    ) as mock_process:
        response = client.post(
            "/intercept",
            json={
                "request_id": "intercept-1",
                "attempt": 1,
                "files": ["src/app.py"],
                "content": "Refactor function foo",
                "mode": "balanced",
                "model_name": "gpt-4o",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "intercept-1"
    assert body["extraction_success"] is True
    assert body["verification_result"]["status"] == "pass"

    mock_process.assert_called_once()
    kwargs = mock_process.call_args.kwargs
    assert kwargs["payload"].request_id == "intercept-1"
    assert kwargs["mode"] == VerificationMode.balanced


def test_intercept_endpoint_passes_dynamic_llm_config() -> None:
    audit = GovernanceAuditRecord(
        request_id="intercept-llm-config",
        timestamp=datetime.now(timezone.utc),
        file_count=1,
        redaction_count=0,
        prompt_minimized=False,
        blocked=False,
        block_reason=None,
    )
    fake_response = InterceptorResponse(
        request_id="intercept-llm-config",
        audit=audit,
        llm_notes="ok",
        extraction_success=False,
        extraction_error="LLM Gateway Request Failed: simulated",
        verification_result=None,
    )

    with patch("dhi.main.InterceptorService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.process_request.return_value = fake_response

        response = client.post(
            "/intercept",
            json={
                "request_id": "intercept-llm-config",
                "attempt": 1,
                "files": ["src/app.py"],
                "content": "Refactor function foo",
                "mode": "balanced",
                "model_name": "moonshotai/kimi-k2.5",
                "llm_provider": "nvidia",
                "llm_api_base": "https://integrate.api.nvidia.com/v1",
                "llm_api_key": "dummy-key",
                "llm_extra_body": {"chat_template_kwargs": {"thinking": True}},
                "llm_timeout_s": 75.0,
                "llm_max_tokens": 1024,
                "llm_temperature": 0.3,
                "llm_top_p": 0.95,
            },
        )

    assert response.status_code == 200
    mock_service_cls.assert_called_once()
    ctor_kwargs = mock_service_cls.call_args.kwargs
    assert ctor_kwargs["model_name"] == "moonshotai/kimi-k2.5"
    assert ctor_kwargs["llm_provider"] == "nvidia"
    assert ctor_kwargs["llm_api_base"] == "https://integrate.api.nvidia.com/v1"
    assert ctor_kwargs["llm_api_key"] == "dummy-key"
    assert ctor_kwargs["llm_extra_body"] == {"chat_template_kwargs": {"thinking": True}}
    assert ctor_kwargs["llm_timeout_s"] == 75.0
    assert ctor_kwargs["llm_max_tokens"] == 1024
    assert ctor_kwargs["llm_temperature"] == 0.3
    assert ctor_kwargs["llm_top_p"] == 0.95


def test_orchestrate_endpoint_uses_orchestrator_service() -> None:
    fake_response = OrchestrationResult(
        request_id="orch-1",
        attempt_count=1,
        retry_count=0,
        final_status="pass",
        terminal_event=None,
        attempts=[],
    )

    with patch("dhi.main.OrchestratorService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.run.return_value = fake_response
        response = client.post(
            "/orchestrate",
            json={
                "request_id": "orch-1",
                "files": ["src/app.py"],
                "content": "Fix this function",
                "mode": "balanced",
                "model_name": "gpt-4o",
                "llm_provider": "openai",
                "llm_timeout_s": 80.0,
                "llm_max_tokens": 2048,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "orch-1"
    assert body["final_status"] == "pass"
    assert body["attempt_count"] == 1

    mock_service_cls.assert_called_once()
    ctor_kwargs = mock_service_cls.call_args.kwargs
    assert ctor_kwargs["model_name"] == "gpt-4o"
    assert ctor_kwargs["llm_provider"] == "openai"
    assert ctor_kwargs["llm_timeout_s"] == 80.0
    assert ctor_kwargs["llm_max_tokens"] == 2048
    assert ctor_kwargs["gate"] is main_module._VEIL_GATE
    assert ctor_kwargs["ledger"] is main_module._VEIL_LEDGER
    assert ctor_kwargs["baseline_fingerprint"] is main_module._VEIL_BASELINE_FINGERPRINT

    mock_service.run.assert_called_once()
    kwargs = mock_service.run.call_args.kwargs
    assert kwargs["request_id"] == "orch-1"
    assert kwargs["mode"] == VerificationMode.balanced


def test_intercept_endpoint_handles_gateway_failure() -> None:
    with patch("dhi.interceptor.gateway.completion", side_effect=Exception("api down")):
        response = client.post(
            "/intercept",
            json={
                "request_id": "intercept-gateway-fail",
                "attempt": 1,
                "files": ["src/app.py"],
                "content": "Do anything",
                "mode": "balanced",
                "model_name": "gpt-4o",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["extraction_success"] is False
    assert body["verification_result"] is None
    assert "LLM Gateway Request Failed" in body["extraction_error"]


def test_intercept_endpoint_blocks_confirmed_secret_before_gateway_call() -> None:
    with patch("dhi.interceptor.gateway.completion") as mock_completion:
        response = client.post(
            "/intercept",
            json={
                "request_id": "intercept-secret-block",
                "attempt": 1,
                "files": ["src/app.py"],
                "content": "AWS key leak: AKIAIOSFODNN7EXAMPLE",
                "mode": "balanced",
                "model_name": "gpt-4o",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["extraction_success"] is False
    assert body["audit"]["blocked"] is True
    assert body["audit"]["secret_leak_detected"] is True
    assert "SecretLeakDetected" in (body["audit"]["block_reason"] or "")
    assert "Blocked by governance" in (body["extraction_error"] or "")
    mock_completion.assert_not_called()


def test_orchestrate_endpoint_handles_gateway_failure() -> None:
    with patch("dhi.interceptor.gateway.completion", side_effect=Exception("api down")):
        response = client.post(
            "/orchestrate",
            json={
                "request_id": "orch-gateway-fail",
                "files": ["src/app.py"],
                "content": "Do anything",
                "mode": "balanced",
                "model_name": "gpt-4o",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["final_status"] == "fail"
    assert body["attempt_count"] == 1
    assert body["retry_count"] == 0


def test_intercept_endpoint_rejects_invalid_llm_provider() -> None:
    response = client.post(
        "/intercept",
        json={
            "request_id": "invalid-provider-intercept",
            "attempt": 1,
            "files": ["src/app.py"],
            "content": "Do anything",
            "mode": "balanced",
            "model_name": "gpt-4o",
            "llm_provider": "invalid-provider",
        },
    )
    assert response.status_code == 422


def test_orchestrate_endpoint_rejects_invalid_llm_provider() -> None:
    response = client.post(
        "/orchestrate",
        json={
            "request_id": "invalid-provider-orch",
            "files": ["src/app.py"],
            "content": "Do anything",
            "mode": "balanced",
            "model_name": "gpt-4o",
            "llm_provider": "invalid-provider",
        },
    )
    assert response.status_code == 422
