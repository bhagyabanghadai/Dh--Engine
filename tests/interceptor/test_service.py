from __future__ import annotations

from unittest.mock import patch

from dhi.interceptor.models import ContextPayload
from dhi.interceptor.service import InterceptorService
from dhi.sandbox.models import VerificationMode, VerificationResult, VerificationTier


def test_interceptor_service_success() -> None:
    service = InterceptorService()
    payload = ContextPayload(
        request_id="req-1",
        attempt=1,
        files=["main.py"],
        content="Fix this bug",
    )

    with (
        patch.object(service.llm_client, "generate_candidate") as mock_gen,
        patch("dhi.interceptor.service.run_in_sandbox") as mock_sandbox,
    ):
        mock_gen.return_value = '{"language": "python", "code": "print(1)", "notes": "ok"}'

        mock_verif_result = VerificationResult(
            request_id="req-1",
            attempt=1,
            mode=VerificationMode.balanced,
            tier=VerificationTier.L0,
            status="pass",
            exit_code=0,
            duration_ms=100,
            stdout="",
            stderr="",
        )
        mock_sandbox.return_value = mock_verif_result

        response = service.process_request(payload)

    assert response.request_id == "req-1"
    assert response.audit.blocked is False
    assert response.extraction_success is True
    assert response.verification_result is not None
    assert response.verification_result.status == "pass"


def test_interceptor_service_blocked_by_governance() -> None:
    service = InterceptorService()
    payload = ContextPayload(
        request_id="req-blocked",
        attempt=1,
        files=[".env"],
        content="test",
    )

    response = service.process_request(payload)

    assert response.audit.blocked is True
    assert response.audit.block_reason is not None
    assert "denylist violation" in response.audit.block_reason.lower()
    assert response.extraction_success is False


def test_interceptor_service_blocks_confirmed_secret_before_gateway_call() -> None:
    service = InterceptorService()
    payload = ContextPayload(
        request_id="req-secret-blocked",
        attempt=1,
        files=["src/app.py"],
        content="Leaked key: AKIAIOSFODNN7EXAMPLE",
    )

    with patch.object(service.llm_client, "generate_candidate") as mock_gen:
        response = service.process_request(payload)

    assert response.audit.blocked is True
    assert response.audit.secret_leak_detected is True
    assert response.audit.block_reason is not None
    assert "SecretLeakDetected" in response.audit.block_reason
    assert response.extraction_success is False
    assert response.extraction_error is not None
    assert "Blocked by governance" in response.extraction_error
    mock_gen.assert_not_called()


def test_interceptor_service_extraction_failure() -> None:
    service = InterceptorService()
    payload = ContextPayload(request_id="req-fail", attempt=1, content="safe content")

    with patch.object(service.llm_client, "generate_candidate") as mock_gen:
        mock_gen.return_value = "I am an AI, I don't write code."
        response = service.process_request(payload)

    assert response.audit.blocked is False
    assert response.extraction_success is False
    assert response.extraction_error is not None
    assert "Could not extract code" in response.extraction_error


def test_interceptor_service_gateway_failure_returns_structured_error() -> None:
    service = InterceptorService()
    payload = ContextPayload(request_id="req-gateway", attempt=1, content="safe content")

    with (
        patch.object(
            service.llm_client,
            "generate_candidate",
            side_effect=RuntimeError("LLM Gateway Request Failed: API Down"),
        ),
        patch("dhi.interceptor.service.run_in_sandbox") as mock_sandbox,
    ):
        response = service.process_request(payload)

    assert response.audit.blocked is False
    assert response.extraction_success is False
    assert response.extraction_error is not None
    assert "LLM Gateway Request Failed" in response.extraction_error
    assert response.verification_result is None
    mock_sandbox.assert_not_called()
