# Dhi Engine

> **System 2 cognitive middleware for AI coding assistants.**

Dhi (*Sanskrit: Intellect, Wisdom, Reflection*) is an open-source middleware layer that sits between your IDE and frontier LLM APIs. Instead of returning raw model output, Dhi builds structural context from your codebase, applies deterministic governance and DLP, executes generated code in an isolated local sandbox, and returns **only verified, attested output**.

**Core rule: Dhi never claims behaviour that has not been proven by local execution.**

---

## Architecture at a Glance

```
IDE request
    │
    ▼
┌──────────────────────────────────────────────┐
│  Interceptor (Smart Client)                  │
│  • AST slice + dependency graph              │
│  • DLP redaction + secret scan               │
│  • VEIL ledger retrieval                     │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
             Frontier LLM API
             (OpenAI / NVIDIA / custom)
                     │
                     ▼
┌──────────────────────────────────────────────┐
│  Orchestrator (Circuit Breaker)              │
│  • Bounded retry loop (max 3)                │
│  • Determinism gate → VEIL ledger write      │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────┐
│  Sandbox (Proof Gate)                        │
│  • Ephemeral isolated runtime                │
│  • Network blocked by default                │
│  • Typed VerificationResult + attestation    │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
          Verified patch + attestation manifest
                 returned to IDE
```

**Core execution pipeline:**  
`request → context → DLP → candidate → sandbox → retry≤3 → attest → handoff`

---

## Project Status

**Pre-alpha · Epics 1–8 implemented**

| Epic | Feature | Endpoint |
|------|---------|----------|
| 1 | Baseline scaffold & quality gates | `GET /health` |
| 2 | Local sandbox verification | `POST /verify` |
| 3 | Cloud interceptor orchestration | `POST /intercept` |
| 4 | Circuit breaker retry loop | `POST /orchestrate` |
| 5 | AST extraction & dependency slicing | *(internal)* |
| 6 | Determinism gate & VEIL memory writes | *(internal)* |
| 7 | Governance, DLP & secret redaction | *(internal)* |
| 8 | Attestation manifests & release gates | `GET /manifest/{id}` |

---

## Requirements

| Tool | Version |
|------|---------|
| Python | ≥ 3.11 |
| [uv](https://github.com/astral-sh/uv) | latest |
| Docker | required for sandbox (`/verify`) |

---

## Quick Start

### 1 · Install dependencies

```powershell
uv sync --extra dev
```

### 2 · Configure environment

```powershell
Copy-Item .env.example .env
# Then edit .env and fill in your API key(s)
```

Minimum required for cloud features:

```env
# OpenAI (default)
OPENAI_API_KEY=sk-...

# NVIDIA NIM (optional)
NVIDIA_API_KEY=nvapi-...
NVIDIA_API_BASE=https://integrate.api.nvidia.com/v1
```

### 3 · Run quality gates

```powershell
uv run ruff check .
uv run mypy src tests
uv run pytest -q
```

> Integration tests (sandbox) require Docker and are marked `integration`.  
> Run them explicitly: `uv run pytest -m integration`

### 4 · Start the server

```powershell
uv run uvicorn dhi.main:app --reload --app-dir src
```

Interactive API docs available at: **http://127.0.0.1:8000/docs**

---

## API Reference

### `GET /health`

Returns service liveness.

```powershell
curl http://127.0.0.1:8000/health
```

```json
{"status": "ok", "service": "dhi", "version": "0.1.0-dev"}
```

---

### `POST /verify`

Runs code in a local sandbox and returns a typed `VerificationResult` + attestation manifest.

```powershell
curl -X POST http://127.0.0.1:8000/verify `
  -H "Content-Type: application/json" `
  -d '{"code": "print(1 + 1)", "request_id": "demo-verify-1"}'
```

---

### `POST /intercept`

Full pipeline: AST context → DLP → cloud generation → sandbox verification.

```powershell
curl -X POST http://127.0.0.1:8000/intercept `
  -H "Content-Type: application/json" `
  -d '{
    "request_id": "demo-1",
    "attempt": 1,
    "files": ["src/main.py"],
    "content": "Refactor this function safely"
  }'
```

**NVIDIA NIM example:**

```powershell
curl -X POST http://127.0.0.1:8000/intercept `
  -H "Content-Type: application/json" `
  -d '{
    "request_id": "demo-nvidia-1",
    "attempt": 1,
    "files": ["src/main.py"],
    "content": "Refactor this function safely",
    "model_name": "moonshotai/kimi-k2.5",
    "llm_provider": "nvidia",
    "llm_extra_body": {"chat_template_kwargs": {"thinking": true}}
  }'
```

---

### `POST /orchestrate`

Bounded circuit-breaker loop (max 3 attempts). Writes to the VEIL ledger on reproducible outcomes.

```powershell
curl -X POST http://127.0.0.1:8000/orchestrate `
  -H "Content-Type: application/json" `
  -d '{
    "request_id": "demo-orch-1",
    "files": ["src/main.py"],
    "content": "Write a correct fibonacci implementation"
  }'
```

---

### `GET /manifest/{request_id}`

Returns the attestation manifest for a completed request (stored in-process for v0.1).

```powershell
curl http://127.0.0.1:8000/manifest/demo-orch-1
```

---

## Dynamic LLM Configuration

All cloud endpoints (`/intercept`, `/orchestrate`) accept per-request LLM overrides:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model_name` | string | `gpt-4o` | Model identifier |
| `llm_provider` | `openai` \| `nvidia` \| `custom` | `openai` | Provider routing |
| `llm_api_base` | string? | `null` | Override base URL |
| `llm_api_key` | string? | `null` | Per-request API key |
| `llm_extra_body` | object | `{}` | Provider-specific payload fields |
| `llm_timeout_s` | float | `120` | Request timeout (1–600 s) |
| `llm_max_tokens` | int? | `null` | Cap generation length |
| `llm_temperature` | float? | `null` | Sampling temperature (0–2) |
| `llm_top_p` | float? | `null` | Nucleus sampling (0–1) |

Invalid `llm_provider` values are rejected with HTTP `422`.

---

## Verification Tiers

Each sandbox run produces a tiered verification result:

| Tier | Meaning |
|------|---------|
| **L0** | Parse, lint, and static type checks passed |
| **L1** | User-authored unit tests passed |
| **L2** | User-authored integration/e2e tests passed |
| **AI-only** | Only AI-generated tests passed — flagged for human review |

---

## Key Design Contracts

- **Sandbox default-deny:** All outbound network is blocked unless policy-allowlisted. Any violation terminates the run with `NetworkAccessViolation`.
- **Read-only source mount:** Repository is mounted read-only in the sandbox; writes go to ephemeral scratch paths only.
- **DLP before cloud call:** Secret scanning and AST-based redaction run deterministically before any content leaves the machine.
- **Determinism gate:** VEIL ledger writes occur only when the environment fingerprint is stable and the failure class is reproducible. Transient faults (DNS, flaky tests) are classified as noise.
- **Bounded repair:** The circuit breaker enforces a hard cap of 3 retry attempts before handing off to the developer.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Dhi_Vision.md](./Dhi_Vision.md) | Project vision, philosophy, and non-negotiable contracts |
| [docs/00_Documentation_Map.md](./docs/00_Documentation_Map.md) | Full documentation index |
| [docs/epics/](./docs/epics/) | Epic-level implementation specs (1–8) |
| [docs/10_Threat_Model.md](./docs/10_Threat_Model.md) | Threat model |
| [docs/06_Sandbox_Runtime_Policy.md](./docs/06_Sandbox_Runtime_Policy.md) | Sandbox policy spec |

---

## Contributing

This project uses strict quality gates. Before submitting a PR:

```powershell
uv run ruff check .          # lint
uv run mypy src tests        # type checking (strict mode)
uv run pytest -q             # unit tests
```

All three must pass with zero errors.

---

## License

MIT — see `LICENSE` for details.
