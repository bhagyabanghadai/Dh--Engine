# Epic 1: Baseline Scaffold and CI/CD
**Status**: Ready for Execution
**Depends On**: None

## Goal
Create a deterministic Python baseline for Dhi so all later epics build on a stable and testable foundation.

## In Scope
- Project bootstrap with `uv`
- Quality tooling (`ruff`, `mypy`, `pytest`)
- Core module layout
- Minimal FastAPI app with `/health`
- CI command baseline

## Out of Scope
- Sandbox execution
- Cloud model calls
- Retry logic
- AST graphing
- VEIL memory writes

## Requirements
1. Toolchain initialization with `uv` and locked dependency graph.
2. `pyproject.toml` configured with:
   - `ruff` for linting
   - `mypy` for type checking
   - `pytest` for testing
3. Required module layout:
   - `src/dhi/interceptor/`
   - `src/dhi/sandbox/`
   - `src/dhi/veil/`
   - `src/dhi/graph/`
4. Minimal FastAPI app exposes `GET /health` with JSON payload:
   - `status`: `ok`
   - `service`: `dhi`
   - `version`: `0.1.0-dev`
5. Add unit test verifying `/health` returns `200` and expected JSON schema.
6. Add baseline scripts/commands in project docs or task runner for:
   - `uv run ruff check .`
   - `uv run mypy src tests`
   - `uv run pytest -q`

## Exit Gates (Definition of Done)
- [ ] `uv sync --extra dev` succeeds deterministically.
- [ ] `uv run ruff check .` returns zero errors.
- [ ] `uv run mypy src tests` returns zero errors.
- [ ] `uv run pytest -q` passes.
- [ ] FastAPI app boots locally and `/health` returns expected payload.
- [ ] No encoding artifacts in created files.

## Artifacts Produced
- Baseline FastAPI service
- Repeatable local quality gate commands
- Test harness for health endpoint
