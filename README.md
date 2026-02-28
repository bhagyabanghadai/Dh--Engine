# Dhi Engine

> System 2 cognitive middleware for AI coding assistants.

Dhi (meaning Intellect, Wisdom, or Reflection) is an open-source cognitive middleware designed to improve how AI interacts with code. Instead of acting as a simple autocomplete tool, Dhi wraps AI generation in structure, policy, and proof.

## Core Execution Loop

`request -> context -> candidate -> verify -> retry (max 3) -> attest -> handoff`

## Current Status

The project is in pre-alpha with Epics 1-4 implemented:
- Epic 1: baseline scaffold (`/health`, quality gates)
- Epic 2: local sandbox verification (`/verify`)
- Epic 3: cloud interceptor orchestration (`/intercept`)
- Epic 4: circuit breaker retry orchestration (`/orchestrate`)

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

5. Verify interceptor endpoint:

```powershell
curl -X POST http://127.0.0.1:8000/intercept -H "Content-Type: application/json" -d "{\"request_id\":\"demo-1\",\"attempt\":1,\"files\":[\"src/main.py\"],\"content\":\"Refactor this function safely\"}"
```

6. Verify orchestrator endpoint (bounded retries):

```powershell
curl -X POST http://127.0.0.1:8000/orchestrate -H "Content-Type: application/json" -d "{\"request_id\":\"demo-orch-1\",\"files\":[\"src/main.py\"],\"content\":\"Write a correct fibonacci implementation\"}"
```

## Dynamic LLM Provider Config

Both `/intercept` and `/orchestrate` accept dynamic LLM config fields:
- `model_name`: model id to call
- `llm_provider`: `openai`, `nvidia`, or `custom`
- `llm_api_base`: optional override for OpenAI-compatible base URL
- `llm_api_key`: optional per-request API key
- `llm_extra_body`: optional provider-specific payload fields
- `llm_timeout_s`: request timeout sent to LiteLLM (default `120`)
- `llm_max_tokens`: optional token cap for generation latency/cost control
- `llm_temperature`: optional sampling temperature
- `llm_top_p`: optional nucleus sampling parameter

Create a local key file at the project root:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and set your key(s), for example:

```env
NVIDIA_API_KEY=your_real_key_here
NVIDIA_API_BASE=https://integrate.api.nvidia.com/v1
```

NVIDIA example (similar to your reference call):

```powershell
curl -X POST http://127.0.0.1:8000/intercept `
  -H "Content-Type: application/json" `
  -d "{\"request_id\":\"demo-nvidia-1\",\"attempt\":1,\"files\":[\"src/main.py\"],\"content\":\"Refactor this function safely\",\"model_name\":\"moonshotai/kimi-k2.5\",\"llm_provider\":\"nvidia\",\"llm_extra_body\":{\"chat_template_kwargs\":{\"thinking\":true}}}"
```

You can set `NVIDIA_API_KEY` in the environment, or pass `llm_api_key` directly.
Invalid `llm_provider` values are rejected with HTTP `422`.

## Architecture Docs

- [Project Vision and Contracts](./Dhi_Vision.md)
- [Documentation Map](./docs/00_Documentation_Map.md)
- [Execution Epics](./docs/epics)
