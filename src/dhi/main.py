from fastapi import FastAPI

app = FastAPI(title="Dhi Engine", version="0.1.0-dev")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Core baseline health endpoint as required by Epic 1."""
    return {
        "status": "ok",
        "service": "dhi",
        "version": "0.1.0-dev",
    }
