# Epic 2: The Local Sandbox Verification
**Status**: Blocked (Requires Epic 1)

## Goal
Prove that we can take a string of Python code and execute it securely in a rootless Docker environment, enforcing strict CPU, RAM, and time limits, and successfully capture the `stdout`/`stderr`. 

## Requirements
1. **Docker Setup:** Create an ephemeral `Dockerfile` specifically for the `balanced` Dhi testing environment.
2. **The Execution Function:** Write the Python controller (`src/dhi/sandbox/executor.py`) that uses the Docker SDK to spin up the container, mount a temporary directory read-only, and execute `pytest`.
3. **Hard Limits Enforcement:** 
    - Enforce a absolute 45s wall clock timeout.
    - Disable container network access (`network_mode="none"`).
4. **The Response Manifest:** The sandbox function must return a structured JSON dictionary mapping exactly to our Verification Contract (Exit Code, Logs, Time Elapsed).

## Exit Gates (Definition of Done)
- [ ] Passing a perfectly valid `.py` file into the executor returns `success: true`.
- [ ] Passing a `.py` file with a syntax error returns `success: false` and the exact traceback string.
- [ ] Passing a malicious `.py` file that tries to run `while True:` is killed at exactly 45s and returns a `TimeoutViolation`.
- [ ] Passing a `.py` file that attempts to run `requests.get("google.com")` fails immediately with a `NetworkAccessViolation`.
