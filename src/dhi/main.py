from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from dhi.attestation.manifest import AttestationManifest, assert_manifest_complete, build_manifest
from dhi.interceptor.models import ContextPayload
from dhi.interceptor.service import InterceptorResponse, InterceptorService
from dhi.orchestrator.models import OrchestrationResult
from dhi.orchestrator.service import OrchestratorService
from dhi.sandbox.executor import run_in_sandbox
from dhi.sandbox.models import VerificationMode, VerificationResult
from dhi.veil.fingerprint import EnvironmentFingerprint
from dhi.veil.gate import DeterminismGate
from dhi.veil.ledger import VeilLedger

app = FastAPI(title="Dhi Engine", version="0.1.0-dev")

LLMProvider = Literal["openai", "nvidia", "custom"]

# Shared VEIL components for the API runtime.
_VEIL_GATE = DeterminismGate()
_VEIL_LEDGER = VeilLedger()
_VEIL_BASELINE_FINGERPRINT = EnvironmentFingerprint.generate()

# In-process manifest store: request_id -> AttestationManifest
# (per-process only; production deployments should use a persistent store)
_MANIFEST_STORE: dict[str, AttestationManifest] = {}


class VerifyRequest(BaseModel):
    """Request body for the /verify endpoint."""

    code: str
    request_id: str = "anonymous"
    attempt: int = 1
    mode: VerificationMode = VerificationMode.balanced


class InterceptRequest(BaseModel):
    """Request body for the /intercept endpoint."""

    request_id: str = "anonymous"
    attempt: int = 1
    files: list[str] = Field(default_factory=list)
    content: str
    mode: VerificationMode = VerificationMode.balanced
    model_name: str = "gpt-4o"
    llm_provider: LLMProvider = "openai"
    llm_api_base: str | None = None
    llm_api_key: str | None = None
    llm_extra_body: dict[str, object] = Field(default_factory=dict)
    llm_timeout_s: float = Field(default=120.0, gt=0.0, le=600.0)
    llm_max_tokens: int | None = Field(default=None, gt=0, le=32768)
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    llm_top_p: float | None = Field(default=None, gt=0.0, le=1.0)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Core baseline health endpoint as required by Epic 1."""
    return {
        "status": "ok",
        "service": "dhi",
        "version": "0.1.0-dev",
    }


class AttestationResponse(BaseModel):
    """Sandbox result combined with attestation manifest."""

    result: VerificationResult
    manifest: AttestationManifest


@app.post("/verify")
async def verify(req: VerifyRequest) -> AttestationResponse:
    """Submit code for local sandbox verification and return proof artifact."""
    result = run_in_sandbox(
        code=req.code,
        request_id=req.request_id,
        attempt=req.attempt,
        mode=req.mode,
    )
    manifest = build_manifest(result=result)
    assert_manifest_complete(manifest)
    _MANIFEST_STORE[req.request_id] = manifest
    return AttestationResponse(result=result, manifest=manifest)


@app.post("/intercept")
async def intercept(req: InterceptRequest) -> InterceptorResponse:
    """Run governance + cloud generation + extraction + sandbox verification."""
    service = InterceptorService(
        model_name=req.model_name,
        llm_provider=req.llm_provider,
        llm_api_base=req.llm_api_base,
        llm_api_key=req.llm_api_key,
        llm_extra_body=req.llm_extra_body,
        llm_timeout_s=req.llm_timeout_s,
        llm_max_tokens=req.llm_max_tokens,
        llm_temperature=req.llm_temperature,
        llm_top_p=req.llm_top_p,
    )
    payload = ContextPayload(
        request_id=req.request_id,
        attempt=req.attempt,
        files=req.files,
        content=req.content,
    )
    return service.process_request(payload=payload, mode=req.mode)


@app.get("/manifest/{request_id}")
async def get_manifest(request_id: str) -> AttestationManifest:
    """Retrieve the attestation manifest for a completed request.

    Returns 404 when no manifest has been stored for *request_id*.
    Manifests are stored in-process; they survive only for the lifetime
    of the server process (sufficient for v0.1 single-node deployments).
    """
    manifest = _MANIFEST_STORE.get(request_id)
    if manifest is None:
        raise HTTPException(
            status_code=404,
            detail=f"No attestation manifest found for request_id='{request_id}'",
        )
    return manifest


class OrchestrateRequest(BaseModel):
    """Request body for the /orchestrate endpoint (circuit breaker loop)."""

    request_id: str = "anonymous"
    files: list[str] = Field(default_factory=list)
    content: str
    mode: VerificationMode = VerificationMode.balanced
    model_name: str = "gpt-4o"
    llm_provider: LLMProvider = "openai"
    llm_api_base: str | None = None
    llm_api_key: str | None = None
    llm_extra_body: dict[str, object] = Field(default_factory=dict)
    llm_timeout_s: float = Field(default=120.0, gt=0.0, le=600.0)
    llm_max_tokens: int | None = Field(default=None, gt=0, le=32768)
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    llm_top_p: float | None = Field(default=None, gt=0.0, le=1.0)


@app.post("/orchestrate")
async def orchestrate(req: OrchestrateRequest) -> OrchestrationResult:
    """Run the full autonomous retry circuit breaker (up to 3 attempts)."""
    service = OrchestratorService(
        model_name=req.model_name,
        llm_provider=req.llm_provider,
        llm_api_base=req.llm_api_base,
        llm_api_key=req.llm_api_key,
        llm_extra_body=req.llm_extra_body,
        llm_timeout_s=req.llm_timeout_s,
        llm_max_tokens=req.llm_max_tokens,
        llm_temperature=req.llm_temperature,
        llm_top_p=req.llm_top_p,
        gate=_VEIL_GATE,
        ledger=_VEIL_LEDGER,
        baseline_fingerprint=_VEIL_BASELINE_FINGERPRINT,
    )
    return service.run(
        request_id=req.request_id,
        content=req.content,
        files=req.files,
        mode=req.mode,
    )
