from typing import Dict

from fastapi import FastAPI

app = FastAPI(title="Dhī Engine", version="0.1.0-dev")

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Core baseline health endpoint as required by Epic 1.
    """
    return {
        "status": "ok",
        "service": "dhi",
        "version": "0.1.0-dev"
    }
