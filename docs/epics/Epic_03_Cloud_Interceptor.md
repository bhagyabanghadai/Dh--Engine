# Epic 3: The Cloud Interceptor & Generation
**Status**: Blocked (Requires Epics 1 & 2)

## Goal
Establish the outbound connection to the Genius Cloud. Dhi must take a prompt, send it to a frontier LLM via API, and successfully parse the returned code chunk.

## Requirements
1. **LLM Gateway Integration:** Use `litellm` in `src/dhi/interceptor/` to abstract the API calls (allowing switching between Claude/Gemini/OpenAI easily).
2. **The System Prompt:** Compile the deterministic system prompt that instructs the AI on how to format its code responses so Dhi can seamlessly extract them.
3. **The Extraction Logic:** Build a reliable regex/parser that separates the LLM's conversational text from the actual Python code block it generated.
4. **Integration with Sandbox:** Connect the output of the Cloud Brain directly to the Sandbox Executor built in Epic 2. 

## Exit Gates (Definition of Done)
- [ ] Sending a basic text prompt ("Write a function that adds two numbers") to the FastAPI endpoint successfully triggers a cloud API call.
- [ ] Dhi perfectly extracts the raw Python code from the LLM's Markdown response string.
- [ ] That extracted code is automatically fed into the Epic 2 sandbox.
- [ ] The user receives a single JSON manifest indicating whether the cloud-generated code passed or failed the local proof.
