# Epic 1: Baseline Scaffold & CI/CD
**Status**: Ready for Execution

## Goal
Establish the physical repository, the Python environment, and the foundational API structure. This is the bedrock that all future pods will build upon. There is no AI logic or Sandboxing in this epic.

## Requirements
1. **Toolchain:** Initialize the project using `uv` (for strict, fast dependency resolution).
2. **Quality Gates:** Configure `pyproject.toml` with:
   - `ruff` (for linting and formatting)
   - `mypy` (for strict static type checking)
   - `pytest` (for unit testing)
3. **Module Layout:** Create the exact folder structure defined in the architectural spec:
   - `src/dhi/interceptor/`
   - `src/dhi/sandbox/`
   - `src/dhi/veil/`
   - `src/dhi/graph/`
4. **The Code:** Implement a minimal `FastAPI` application with a single `/health` endpoint.
5. **The Test:** Write a `pytest` that verifies the `/health` endpoint returns a `200 OK` status and a verifiable JSON payload.

## Exit Gates (Definition of Done)
This Epic is not complete until the following gates pass locally:
- [ ] `uv sync` installs all dependencies deterministically.
- [ ] `ruff check .` returns 0 warnings.
- [ ] `mypy .` returns 0 type errors.
- [ ] `pytest` passes with 100% success.
- [ ] The FastAPI server can be booted locally and curled successfully.
