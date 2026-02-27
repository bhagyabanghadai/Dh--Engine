# Dhī Engine

> System 2 cognitive middleware for AI coding assistants.

Dhī (meaning Intellect, Wisdom, or Reflection) is an open-source cognitive middleware designed to transform how AI interacts with code. Instead of serving as a simple "try-hard student" autocomplete tool, Dhī provides a robust, enterprise-grade architecture that surrounds the AI with a "mind." 

It slows down the execution cycle, simulates consequences, and learns from proven mistakes in real-time, verifying every change against local deterministic proof before making claims to the user.

## The Three Pillars of Local Intelligence

1. **The Map (The Eyes): AST & Structural Graph Slicing**
   - Built with Tree-sitter and embedded Kùzu graph DB.
   - Extracts functions, classes, and execution paths dynamically. 
   - Replaces naive semantic RAG with precise, logic-aware dependency slicing so the cloud LLM only sees exact structural context.

2. **The Memory (The Prefrontal Cortex): VEIL Temporal Persistence**
   - Backed by an embedded SQLite WAL store.
   - Records "Lessons Learned" when the AI makes autonomous fixes.
   - Only writes to the ledger when a deterministic, reproducible local test proves the fix succeeded.

3. **The Verification Sandbox (The Hands): Zero-Trust Executions**
   - Bounded execution loop using rootless Docker (Balanced Mode) or Firecracker MicroVMs (Strict Mode).
   - "Default Deny" policy: No external egress, read-only filesystem mounts, strict CPU/RAM limits, and wall-clock timeouts.
   - Outputs strict JSON Manifests (Contracts) proving exact exit codes, stdout/stderr, and skipped checks.

## Architecture

Dhī operates on a "Smart Client, Genius Cloud" model. Heavy AI reasoning is outsourced to boundary-pushing cloud models (Claude 3.5 Sonnet, GPT-4o) via API keys, while the Context Mapping, Sandbox Execution, and Deductive Memory happen strictly within the client's local machine.

The primary execution loop is completely locked down for v0.1:
`request -> context -> candidate -> verify -> retry (max 3) -> attest -> handoff`

## Getting Started

Currently, Dhī is in the **pre-alpha design phase (M1 - Contracts Locked)**. We are stepping into **Epic 1** to scaffold the baseline FastAPI control plane and Python environment using `uv`.

For a comprehensive breakdown of the project scope, threat model, and technical decisions, read the architecture documentation:

- [Project Vision & Contracts](./Dhi_Vision.md)
- [Documentation Map](./docs/00_Documentation_Map.md)
- [Detailed Execution Epics](./docs/epics)

---
*Dhī guarantees "no claims without proof." The AI cannot hallucinate success without a local verification manifest proving it passed the sandbox rules.*
