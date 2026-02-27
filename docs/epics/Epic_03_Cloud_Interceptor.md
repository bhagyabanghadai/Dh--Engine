# Epic 3: Cloud Interceptor and Safe Generation
**Status**: Blocked (Requires Epics 1 and 2)
**Depends On**: Epics 1, 2

## Goal
Accept user prompt, build safe outbound context, call cloud LLM, parse response deterministically, and hand candidate code to sandbox verification.

## In Scope
- Cloud gateway integration
- Context governance before egress
- Candidate extraction and validation
- Integration with sandbox verifier

## Out of Scope
- Autonomous retries
- AST dependency slicing (advanced path in Epic 5)
- VEIL writes

## Requirements
1. Implement LLM gateway abstraction in `src/dhi/interceptor/` using `litellm`.
2. Build pre-egress governance pipeline:
   - Path allowlist and denylist enforcement
   - Secret scan and DLP redaction (`<REDACTED_SECRET>`)
   - Prompt-injection-aware context minimization
   - Egress audit record (`request_id`, file_count, redaction_count)
3. Use structured model output contract (JSON object) as primary extraction method:
   - `language`
   - `code`
   - `notes`
4. Use markdown code-fence parser only as fallback when structured response is unavailable.
5. Validate extracted code payload is non-empty and syntactically parseable before sandbox handoff.
6. Send candidate directly to Epic 2 executor and return combined response.

## Exit Gates (Definition of Done)
- [ ] User prompt triggers cloud API call through gateway abstraction.
- [ ] Outbound context is scanned and audited before API request.
- [ ] Structured response parsing succeeds for primary path.
- [ ] Fallback parser works for fenced code responses.
- [ ] Extracted code is always passed to sandbox verifier.
- [ ] API response includes sandbox verification result, not raw model text only.

## Artifacts Produced
- Cloud interceptor with governance gate
- Egress audit logs
- Candidate extraction module with tests
