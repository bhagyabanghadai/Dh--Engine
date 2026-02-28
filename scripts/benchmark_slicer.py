"""Slicer performance benchmark script.

Measures p95 parse+slicer latency over a generated ~1000-line Python fixture.
Validates Epic 5 gate: p95 <= 200ms.
"""

from __future__ import annotations

import statistics
import sys
import textwrap
import time

_FUNC_TEMPLATE = textwrap.dedent(
    """\
    def func_{i}(x: int) -> int:
        # Perform computation {i}
        y = x + {i}
        return helper_{i}(y)

    def helper_{i}(value: int) -> int:
        return value * 2 + {i}
    """
)


def _generate_fixture(target_lines: int = 1000) -> tuple[str, str]:
    """Return (source_code, target_name) fixture with about *target_lines* lines."""
    blocks: list[str] = []
    while sum(block.count("\n") for block in blocks) < target_lines:
        index = len(blocks)
        blocks.append(_FUNC_TEMPLATE.format(i=index))
    source = "\n".join(blocks)
    return source, "func_0"


N_WARMUP = 3
N_SAMPLES = 50
P95_LIMIT_MS = 200.0


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    index = int(0.95 * (len(values_sorted) - 1))
    return values_sorted[index]


def main() -> int:
    from dhi.ast_ext.slicer import ContextSlicer

    slicer = ContextSlicer()
    source, target = _generate_fixture()
    actual_lines = source.count("\n") + 1

    print(f"Fixture: {actual_lines} lines  |  target symbol: '{target}'")
    print(f"Warmup runs: {N_WARMUP}  |  Sample runs: {N_SAMPLES}")

    for _ in range(N_WARMUP):
        slicer.slice_source(source, target)

    latencies_ms: list[float] = []
    result = None
    for _ in range(N_SAMPLES):
        start = time.perf_counter()
        result = slicer.slice_source(source, target)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        latencies_ms.append(elapsed_ms)

    p50 = statistics.median(latencies_ms)
    p95 = _p95(latencies_ms)
    p_max = max(latencies_ms)

    assert result is not None
    print(
        "\nLast slice: "
        f"found={result.found} "
        f"symbols={result.symbol_count} "
        f"edges={result.edge_count} "
        f"bytes={result.slice_size_bytes}"
    )
    print(f"\nLatency (ms) over {N_SAMPLES} samples:")
    print(f"  p50  : {p50:7.2f} ms")
    print(f"  p95  : {p95:7.2f} ms   (limit: {P95_LIMIT_MS:.0f} ms)")
    print(f"  max  : {p_max:7.2f} ms")

    if p95 <= P95_LIMIT_MS:
        print(f"\nGATE PASSED - p95 {p95:.2f}ms <= {P95_LIMIT_MS:.0f}ms")
        return 0

    print(f"\nGATE FAILED - p95 {p95:.2f}ms > {P95_LIMIT_MS:.0f}ms")
    return 1


if __name__ == "__main__":
    sys.exit(main())
