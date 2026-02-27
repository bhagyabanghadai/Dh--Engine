from fastapi import FastAPI
from pydantic import BaseModel

from dhi.sandbox.executor import run_in_sandbox
from dhi.sandbox.models import VerificationMode, VerificationResult

app = FastAPI(title="Dhi Engine", version="0.1.0-dev")


class VerifyRequest(BaseModel):
    """Request body for the /verify endpoint."""

    code: str
    request_id: str = "anonymous"
    attempt: int = 1
    mode: VerificationMode = VerificationMode.balanced


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Core baseline health endpoint as required by Epic 1."""
    return {
        "status": "ok",
        "service": "dhi",
        "version": "0.1.0-dev",
    }


@app.post("/verify")
async def verify(req: VerifyRequest) -> VerificationResult:
    """
    Submit code for local sandbox verification.

    Runs code in an isolated Docker container, enforces security policy,
    and returns a fully-populated VerificationResult manifest.
    No claims are made without local proof.
    """
    return run_in_sandbox(
        code=req.code,
        request_id=req.request_id,
        attempt=req.attempt,
        mode=req.mode,
    )
