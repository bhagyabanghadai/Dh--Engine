# Epic 5: AST Extraction and Dependency Slicing (Eyes)
**Status**: Blocked (Requires Epics 1-4)
**Depends On**: Epics 1, 2, 3, 4

## Goal
Replace full-file prompt context with structural AST-based slices that include only target symbols and direct dependencies.

## In Scope
- Tree-sitter Python parser integration
- Symbol and call-edge extraction
- Context slicer API
- Interceptor integration

## Out of Scope
- Full multi-language support
- Advanced graph ranking heuristics

## Requirements
1. Integrate Tree-sitter Python bindings.
2. Extract symbol inventory from `.py` files:
   - Classes
   - Functions
3. Extract direct call edges (caller -> callee).
4. Implement slicer interface:
   - Input: function name or line number
   - Output: target symbol code + immediate dependencies
5. Integrate slicer output into interceptor context path (Epic 3), replacing raw full-file context by default.
6. Emit slice metadata for observability:
   - `symbol_count`
   - `edge_count`
   - `slice_size_bytes`

## Performance and Accuracy Gates (Locked)
- Parse performance: p95 <= 200ms for a 1000-line Python file on baseline dev machine.
- Slicer correctness: target symbol and direct dependencies included; unrelated symbols excluded.
- Interceptor uses sliced context by default once feature flag is enabled.

## Exit Gates (Definition of Done)
- [ ] AST parse and extraction tests pass on representative Python fixtures.
- [ ] Dependency slice output is deterministic for same input.
- [ ] Performance gate passes (`p95 <= 200ms`) with benchmark script.
- [ ] Cloud interceptor receives slicer output and not full raw file text in default path.

## Artifacts Produced
- AST parser and slicer modules
- Benchmark script and results
- Integration tests with interceptor
