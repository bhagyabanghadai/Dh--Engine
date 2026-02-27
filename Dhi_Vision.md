# Project Dhi: The Cognitive Middleware for AI Coding

## 1. Executive Summary
Dhi (meaning Intellect, Wisdom, or Reflection) is an open-source cognitive middleware designed to improve how AI interacts with code. It is inspired by the idea that current AI models are often strong pattern matchers, but weak at reliable real-world engineering.

Instead of only predicting the next line of code (System 1), Dhi adds a control layer (System 2) between the IDE and frontier LLM APIs (for example Claude, OpenAI, Gemini). Dhi analyzes structural dependencies, applies project-specific memory, and verifies behavior in a locally isolated sandbox before output is shown to the developer.

**Absolute rule: Dhi only claims behavior that is proven by executed local checks.**

## 2. The Core Philosophy: System 2 in Practice
* **Reflection over Reflex:** Before writing code, Dhi estimates downstream impact from project structure and usage links.
* **Verified Knowledge:** LLM output is treated as a hypothesis until local execution proves it.
* **Continuous Local Learning:** Dhi learns from proven failures and successful remediations without training the base model on private source code.

## 3. The Architecture: Smart Client, Genius Cloud
Dhi uses a split architecture: cloud reasoning with local proof.

* **Interceptor (Smart Client):** Captures the IDE request, builds deterministic local context, retrieves relevant ledger signals, and composes the cloud prompt.
* **Cloud Brain (Genius Cloud):** Frontier models produce implementation plans and patches.
* **Local Bouncer (Proof Gate):** Untested output is executed in a local sandbox. Failed output never reaches the developer. Errors feed a bounded repair loop.

## 4. The Three Pillars of Local Intelligence

### A. The Structural Map (Eyes)
Naive file-level context is replaced with structural retrieval.
* **Mechanism:** Tree-sitter parses code to AST and symbol relationships, indexed into a local graph database (for example Neo4j or Kuzu).
* **Graph RAG:** Retrieval targets only the changed symbol and connected callers/callees/schemas, minimizing token footprint while preserving architectural context.

### B. The Experiential Ledger (Memory / VEIL)
Session-only memory is replaced by persistent, verified memory.
* **Mechanism:** Temporal ledger of proven execution outcomes and fix attempts.
* **Learning model:** Episodic events can be compressed into semantic rules, with time decay and conflict resolution (current codebase evidence always overrides stale memory).

### C. The Verification Sandbox (Hands)
Code is trusted only after execution.
* **Mechanism:** Strictly isolated ephemeral runtimes (container or microVM tiers depending on policy mode).
* **Outcome:** Each run produces machine-readable verification artifacts used for decisions and attestation.

---

## 5. Non-Negotiable Contracts (Security and Reliability Manifesto)
Dhi enforces explicit protocol contracts. Model Context Protocol (MCP) is a communication layer, not a security boundary.

### Contract 1: Governance and Privacy (Untrusted Input Rule)
Local repository content (code, comments, tests, third-party dependencies) is treated as untrusted input.
* **No LLM sanitizers as primary control:** Sanitization is deterministic-first.
* **Deterministic controls before cloud calls:**
  * **Path allowlists and denylists:** Policy decides which files are eligible for extraction.
  * **AST slicing with selective redaction:** Remove comments by default; preserve semantics-required literals (for example routes, SQL structure, config keys) while redacting secrets and high-risk literal payloads.
  * **Pre-flight secret scanning and DLP:** Regex and entropy rules replace matched values with `<REDACTED_SECRET>`.
* **Retention policy:** Bounded local retention for context cache and ledger records with auditable data-egress logs.

### Contract 2: Runtime Security (Default-Deny Sandbox)
Untested code runs under strict OS and hypervisor isolation.
* **Default-deny egress enforced by runtime:** All outbound network calls are blocked unless explicitly allowlisted by policy.
* **Network violation contract:** Any unallowlisted outbound attempt fails the run with `NetworkAccessViolation`.
* **Read-only source mount:** Repository is mounted read-only. Writes are allowed only in ephemeral scratch paths.
* **Resource controls:** Hard limits for wall time, CPU, memory, process count, and syscall profile.
* **Kill on violation:** Policy violations terminate execution immediately and produce a classified failure event.

### Contract 3: Determinism (Signal Over Noise)
VEIL must learn from stable evidence.
* **Environment fingerprint fields (minimum):**
  * Base runtime image digest
  * Toolchain versions (for example node/python/java and package manager)
  * Dependency lockfile hashes
  * Build and test command set with versions
  * Approved environment-variable allowlist hash
* **Deterministic-write gate for VEIL:** Ledger writes occur only when fingerprint matches and failure class is reproducible. Transient infrastructure faults (for example DNS failure, registry timeout, flaky-test threshold breach) are marked noise and excluded from memory rules.

### Contract 4: Tiered Verification (Proven Provenance)
Verification is tiered, explicit, and auditable.
* **Tier L0:** Parse, lint, and static type checks passed.
* **Tier L1:** Pre-existing user-authored unit tests passed.
* **Tier L2:** Pre-existing user-authored integration or end-to-end tests passed.
* **AI-tests-only flag:** If only AI-authored tests passed, output is labeled: `Passed AI-generated tests: human review required`.
* **Deliverable manifest:** Final payload must include commands executed, artifacts, skipped checks with reason, retry count, timeout and hang status, flake classification, and achieved verification tier.

---

## 6. Engineering Resilience and API Tax Control
Iterative repair loops can multiply cloud calls. Dhi enforces bounded orchestration.
* **Circuit breaker:** State machine enforces max repair attempts (for example 3) before human handoff.
* **Failure classification:** Errors are labeled (syntax, policy violation, timeout/hang, flaky, deterministic fail) to avoid wasteful retry loops.
* **Tiered model routing:** Expensive models for architecture-heavy drafts; cheap and fast models for traceback-constrained fix iterations.
* **Context caching:** Reuse recent structural retrieval results to reduce token and latency overhead.

## 7. Developer Experience (UX)
The IDE workflow stays the same, but the interaction model shifts from instant completion to asynchronous verified delivery.

* **Ask:** `/dhi refactor auth.js to use OAuth`
* **Progress stages (visible):**
  * `[Dhi] Building structural context and applying DLP redaction`
  * `[Dhi] Requesting cloud implementation plan`
  * `[Dhi] Executing local sandbox (network disabled, source read-only)`
  * `[Dhi] L1 unit tests failed (flake=false), retrying within policy budget`
  * `[Dhi] Verification complete at Tier L1`
* **Reveal:** Dhi returns patch output with verification provenance and artifacts, not unverified code claims.
