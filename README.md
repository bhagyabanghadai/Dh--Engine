# Dhi Engine

> System 2 cognitive middleware for AI coding assistants.

Dhi (meaning Intellect, Wisdom, or Reflection) is an open-source cognitive middleware designed to improve how AI interacts with code. Instead of acting as a simple autocomplete tool, Dhi wraps AI generation in structure, policy, and proof.

## Core Execution Loop

`request -> context -> candidate -> verify -> retry (max 3) -> attest -> handoff`

## Current Status

The project is in pre-alpha and currently focused on Epic 1 baseline scaffolding.

## Epic 1 Local Setup

1. Create/update the environment:

```powershell
uv sync --extra dev
```

2. Run quality gates:

```powershell
uv run ruff check .
uv run mypy src tests
uv run pytest -q
```

3. Run the service:

```powershell
uv run uvicorn dhi.main:app --reload --app-dir src
```

4. Verify health endpoint:

```powershell
curl http://127.0.0.1:8000/health
```

Expected JSON:

```json
{"status":"ok","service":"dhi","version":"0.1.0-dev"}
```

## Architecture Docs

- [Project Vision and Contracts](./Dhi_Vision.md)
- [Documentation Map](./docs/00_Documentation_Map.md)
- [Execution Epics](./docs/epics)
