"""OrchestratorService - the circuit breaker retry loop."""

from __future__ import annotations

import logging

from dhi.interceptor.models import ContextPayload
from dhi.interceptor.service import InterceptorService
from dhi.sandbox.models import (
    FailureClass,
    VerificationMode,
    VerificationResult,
    VerificationTier,
    ViolationEvent,
)
from dhi.veil.fingerprint import EnvironmentFingerprint
from dhi.veil.gate import DeterminismGate
from dhi.veil.ledger import VeilLedger

from .classifier import MAX_ATTEMPTS, classify
from .models import AttemptRecord, OrchestrationResult
from .prompts import build_repair_prompt

logger = logging.getLogger(__name__)


def _is_retryable_extraction_syntax_error(error: str | None) -> bool:
    if error is None:
        return False
    return "syntaxerror" in error.lower()


def _synthetic_syntax_failure(
    *,
    request_id: str,
    attempt: int,
    mode: VerificationMode,
    error: str,
) -> VerificationResult:
    """
    Build a synthetic verification result when extraction fails due to syntax.
    This keeps Epic 3 pre-handoff syntax validation while enabling Epic 4 syntax retry.
    """
    return VerificationResult(
        request_id=request_id,
        attempt=attempt,
        mode=mode,
        tier=VerificationTier.L0,
        status="fail",
        failure_class=FailureClass.syntax,
        terminal_event=None,
        exit_code=-1,
        duration_ms=0,
        stdout="",
        stderr=error,
        runtime_config={"source": "extractor"},
    )


class OrchestratorService:
    """
    Implements the bounded Circuit Breaker retry loop for autonomous code generation.

    The loop runs at most ``max_attempts=3`` times per request:
    - Attempt 1: Initial generation.
    - Attempts 2-3: Repair generation, where the LLM receives a contextualized prompt
      embedding the previous failure reason, stdout, and stderr.

    The loop halts immediately on:
    - A passing verification result.
    - A non-retryable failure class (policy, timeout, flake).
    - A terminal system violation event.
    - Exhausting the maximum attempt budget.
    """

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
        gate: DeterminismGate | None = None,
        ledger: VeilLedger | None = None,
        baseline_fingerprint: EnvironmentFingerprint | None = None,
    ) -> None:
        self._interceptor = InterceptorService(
            model_name=model_name,
            llm_provider=llm_provider,
            llm_api_base=llm_api_base,
            llm_api_key=llm_api_key,
            llm_extra_body=llm_extra_body,
            llm_timeout_s=llm_timeout_s,
            llm_max_tokens=llm_max_tokens,
            llm_temperature=llm_temperature,
            llm_top_p=llm_top_p,
        )
        self._gate = gate
        self._ledger = ledger
        self._baseline = baseline_fingerprint

    def run(
        self,
        request_id: str,
        content: str,
        files: list[str] | None = None,
        mode: VerificationMode = VerificationMode.balanced,
    ) -> OrchestrationResult:
        """Execute the circuit breaker loop and return the final orchestration result."""
        files = files or []
        original_content = content
        attempts: list[AttemptRecord] = []
        final_status = "fail"
        terminal_event: ViolationEvent | None = None

        for attempt_number in range(1, MAX_ATTEMPTS + 1):
            logger.info(
                "Orchestrator: starting attempt %d/%d for request %s",
                attempt_number,
                MAX_ATTEMPTS,
                request_id,
            )

            payload = ContextPayload(
                request_id=request_id,
                attempt=attempt_number,
                files=files,
                content=content,
            )

            response = self._interceptor.process_request(payload=payload, mode=mode)
            verification = response.verification_result

            if (
                verification is None
                and not response.extraction_success
                and _is_retryable_extraction_syntax_error(response.extraction_error)
            ):
                logger.info(
                    "Orchestrator: extraction syntax failure on attempt %d. "
                    "Treating as retryable syntax class.",
                    attempt_number,
                )
                verification = _synthetic_syntax_failure(
                    request_id=request_id,
                    attempt=attempt_number,
                    mode=mode,
                    error=response.extraction_error or "SyntaxError during extraction.",
                )

            attempts.append(
                AttemptRecord(
                    attempt=attempt_number,
                    extraction_success=response.extraction_success,
                    extraction_error=response.extraction_error,
                    verification_result=verification,
                )
            )

            if verification is None:
                logger.warning(
                    "Orchestrator: extraction failed on attempt %d, halting. Error: %s",
                    attempt_number,
                    response.extraction_error,
                )
                break

            if verification.status == "pass":
                logger.info(
                    "Orchestrator: pass on attempt %d for request %s",
                    attempt_number,
                    request_id,
                )
                final_status = "pass"
                break

            decision = classify(result=verification, current_attempt=attempt_number)
            logger.info(
                "Orchestrator: attempt %d failed - %s",
                attempt_number,
                decision.reason,
            )

            if not decision.should_retry:
                if attempt_number >= MAX_ATTEMPTS:
                    terminal_event = ViolationEvent.MaxRetriesExceeded
                elif verification.terminal_event is not None:
                    terminal_event = verification.terminal_event
                break

            content = build_repair_prompt(
                original_content=original_content,
                last_result=verification,
            )

        attempt_count = len(attempts)
        result = OrchestrationResult(
            request_id=request_id,
            attempt_count=attempt_count,
            retry_count=attempt_count - 1,
            final_status=final_status,
            terminal_event=terminal_event,
            attempts=attempts,
        )

        if self._ledger is not None and self._gate is not None:
            baseline = self._baseline or EnvironmentFingerprint.generate()
            current_fp = EnvironmentFingerprint.generate()
            gate_decision = self._gate.evaluate(result, current_fp, baseline)
            self._ledger.write(gate_decision, result, current_fp)

        return result
