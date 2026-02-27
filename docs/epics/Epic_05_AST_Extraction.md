# Epic 5: AST Extraction (The Eyes)
**Status**: Blocked (Requires Epics 1-4)

## Goal
Stop sending massive, full files to the Cloud LLM. Introduce Tree-sitter so Dhi can parse Python files into Abstract Syntax Trees and identify dependencies.

## Requirements
1. **Tree-sitter Integration:** Install and configure the official Python bindings for Tree-sitter.
2. **Node Extraction:** Write the logic to parse a `.py` file and extract a list of all defined `Classes` and `Functions`.
3. **Edge Detection:** Extract a list of all function *calls*—knowing which functions depend on other functions.
4. **The Dependency Slicer:** Given a line number or function name, output *only* the text of that target function and its immediate connected dependencies, stripping out the rest of the file.

## Exit Gates (Definition of Done)
- [ ] Pointing Dhi at a 1,000-line Python file with 20 functions successfully parses the AST in milliseconds.
- [ ] Requesting structural context for `Function A` correctly returns the text of `Function A` and `Function B` (which it calls), while ignoring completely unrelated functions.
- [ ] The Cloud Interceptor from Epic 3 now uses this sliced AST block instead of raw file text in its context prompt.
