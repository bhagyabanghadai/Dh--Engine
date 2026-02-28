"""Main entrypoint for the cloud interceptor orchestration pipeline."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from dhi.sandbox.executor import run_in_sandbox
from dhi.sandbox.models import VerificationMode, VerificationResult

from .extractor import extract_candidate
from .gateway import LiteLLMClient
from .governance import GovernancePipeline
from .models import ContextPayload, GovernanceAuditRecord

logger = logging.getLogger(__name__)


class InterceptorResponse(BaseModel):
    """Combined response for governance, extraction, and sandbox verification."""

    request_id: str
    audit: GovernanceAuditRecord
    llm_notes: str
    extraction_success: bool
    extraction_error: str | None
    verification_result: VerificationResult | None


class InterceptorService:
    """Orchestrates the end-to-end safe generation pipeline."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        llm_provider: str = "openai",
        llm_api_base: str | None = None,
        llm_api_key: str | None = None,
        llm_extra_body: dict[str, object] | None = None,
        llm_timeout_s: float = 120.0,
        llm_max_tokens: int | None = None,
        llm_temperature: float | None = None,
        llm_top_p: float | None = None,
    ) -> None:
        self.llm_client = LiteLLMClient(
            model_name=model_name,
            provider=llm_provider,
            api_base=llm_api_base,
            api_key=llm_api_key,
            extra_body=llm_extra_body,
            request_timeout_s=llm_timeout_s,
            max_tokens=llm_max_tokens,
            temperature=llm_temperature,
            top_p=llm_top_p,
        )

    def process_request(
        self,
        payload: ContextPayload,
        mode: VerificationMode = VerificationMode.balanced,
    ) -> InterceptorResponse:
        """Run governance, cloud generation, extraction, and sandbox verification."""
        logger.info(
            "Running governance for request %s (attempt %s)",
            payload.request_id,
            payload.attempt,
        )
        safe_payload, audit = GovernancePipeline.run(payload)

        if audit.blocked:
            reason = audit.block_reason or "Unknown governance policy block."
            logger.warning(
                "Request %s blocked by governance: %s",
                payload.request_id,
                reason,
            )
            return InterceptorResponse(
                request_id=payload.request_id,
                audit=audit,
                llm_notes="",
                extraction_success=False,
                extraction_error=f"Blocked by governance: {reason}",
                verification_result=None,
            )

        logger.info("Requesting cloud candidate for request %s", payload.request_id)
        try:
            raw_response = self.llm_client.generate_candidate(safe_payload)
        except Exception as exc:  # pragma: no cover - exercised via API tests
            error_message = str(exc) or "Unknown LLM gateway failure."
            logger.exception(
                "LLM gateway failed for request %s: %s",
                payload.request_id,
                error_message,
            )
            return InterceptorResponse(
                request_id=payload.request_id,
                audit=audit,
                llm_notes="",
                extraction_success=False,
                extraction_error=error_message,
                verification_result=None,
            )

        logger.info("Extracting candidate code for request %s", payload.request_id)
        extraction = extract_candidate(raw_response)
        if not extraction.success:
            logger.error(
                "Extraction failed for request %s: %s",
                payload.request_id,
                extraction.error,
            )
            return InterceptorResponse(
                request_id=payload.request_id,
                audit=audit,
                llm_notes=extraction.notes,
                extraction_success=False,
                extraction_error=extraction.error,
                verification_result=None,
            )

        logger.info("Submitting extracted candidate to sandbox for request %s", payload.request_id)
        verification = run_in_sandbox(
            code=extraction.code,
            request_id=payload.request_id,
            attempt=payload.attempt,
            mode=mode,
        )

        return InterceptorResponse(
            request_id=payload.request_id,
            audit=audit,
            llm_notes=extraction.notes,
            extraction_success=True,
            extraction_error=None,
            verification_result=verification,
        )
