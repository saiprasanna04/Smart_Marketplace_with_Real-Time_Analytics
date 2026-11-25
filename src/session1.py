"""Session 1 in-stock price search, correctness oracle, and live benchmark."""

from __future__ import annotations

import math
import statistics
import time
from collections.abc import Iterable, Mapping, Sequence

from src.hardware_analysis import simulate_block_reads
from src.measurements import deep_size_bytes


ProductRecord = Mapping[str, object]
DEMO_PRICE_LIMIT = 60_000.0
DEFAULT_BLOCK_SIZE = 64
BENCHMARK_TRIALS = 7


def linear_search_in_stock_below_price(
    catalogue: Iterable[ProductRecord], max_price: float = DEMO_PRICE_LIMIT
) -> tuple[list[ProductRecord], dict[str, int]]:
    """Return in-stock products strictly below ``max_price`` with visible counts.

    The operation counters describe the work performed by this Python loop:
    every record is visited and checked for stock; the price predicate is
    checked only when stock is positive; a result write is counted per match.
    """
    if not math.isfinite(max_price):
        raise ValueError("max_price must be a finite number")

    matches: list[ProductRecord] = []
    records_inspected = 0
    stock_checks = 0
    price_checks = 0

    for product in catalogue:
        records_inspected += 1
        stock_checks += 1
        if int(product["stock"]) > 0:
            price_checks += 1
            if float(product["price"]) < max_price:
                matches.append(product)

    predicate_evaluations = stock_checks + price_checks
    result_writes = len(matches)
    return matches, {
        "records_inspected": records_inspected,
        "stock_checks": stock_checks,
        "price_checks": price_checks,
        "predicate_evaluations": predicate_evaluations,
        "result_writes": result_writes,
        "counted_operations": predicate_evaluations + result_writes,
    }


def reference_in_stock_below_price(
    catalogue: Iterable[ProductRecord], max_price: float = DEMO_PRICE_LIMIT
) -> list[ProductRecord]:
    """Independent comprehension used as the Session 1 correctness oracle."""
    if not math.isfinite(max_price):
        raise ValueError("max_price must be a finite number")
    return [
        product
        for product in catalogue
        if int(product["stock"]) > 0 and float(product["price"]) < max_price
    ]


def benchmark_session1_sizes(
    hand_trace_catalogue: Sequence[ProductRecord],
    catalogue_1000: Sequence[ProductRecord],
    trials: int = BENCHMARK_TRIALS,
    max_price: float = DEMO_PRICE_LIMIT,
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> list[dict[str, object]]:
    """Measure the real Session 1 scan at 20, 100, and 1,000 products.

    Elapsed time covers only the in-memory linear search. Object memory uses
    the project's recursive ``sys.getsizeof`` estimate. Block reads are a
    record-per-block formula simulation, not physical I/O.
    """
    if trials <= 0:
        raise ValueError("trials must be greater than 0")
    if block_size <= 0:
        raise ValueError("block_size must be greater than 0")
    if len(hand_trace_catalogue) != 20:
        raise ValueError("hand-trace catalogue must contain exactly 20 records")
    if len(catalogue_1000) != 1000:
        raise ValueError("benchmark catalogue must contain exactly 1,000 records")

    workloads = (
        (20, hand_trace_catalogue),
        (100, catalogue_1000[:100]),
        (1000, catalogue_1000),
    )
    rows: list[dict[str, object]] = []

    for expected_size, catalogue in workloads:
        if len(catalogue) != expected_size:
            raise ValueError(f"{expected_size}-record workload has an unexpected size")

        expected_ids = [
            str(product["product_id"])
            for product in reference_in_stock_below_price(catalogue, max_price)
        ]
        elapsed_ns: list[int] = []
        final_counts: dict[str, int] = {}
        actual_ids: list[str] = []
        for _ in range(trials):
            started = time.perf_counter_ns()
            matches, final_counts = linear_search_in_stock_below_price(
                catalogue, max_price
            )
            elapsed_ns.append(time.perf_counter_ns() - started)
            actual_ids = [str(product["product_id"]) for product in matches]

        correct = actual_ids == expected_ids
        if not correct:
            raise AssertionError(
                f"Session 1 linear search disagreed with the oracle at size {expected_size}"
            )

        rows.append(
            {
                "product_count": expected_size,
                "records_inspected": final_counts["records_inspected"],
                "stock_checks": final_counts["stock_checks"],
                "price_checks": final_counts["price_checks"],
                "predicate_evaluations": final_counts["predicate_evaluations"],
                "result_writes": final_counts["result_writes"],
                "counted_operations": final_counts["counted_operations"],
                "median_time_ms": statistics.median(elapsed_ns) / 1_000_000,
                "matching_products": len(actual_ids),
                "memory_estimate_bytes": deep_size_bytes(catalogue),
                "block_size_records": block_size,
                "simulated_block_reads": simulate_block_reads(
                    expected_size, block_size
                ),
                "oracle_passed": correct,
                "trials": trials,
                "max_price_exclusive": max_price,
            }
        )

    return rows


RAM_EXTERNAL_MEMORY_ASSUMPTIONS = (
    {
        "model": "RAM model",
        "assumption": (
            "The catalogue is resident in memory; one stock or price predicate "
            "evaluation is counted as a basic operation."
        ),
        "reported_as": "Observed loop counters and machine-specific elapsed time.",
    },
    {
        "model": "External-memory model",
        "assumption": (
            "Records are scanned sequentially, and each assumed block holds "
            f"{DEFAULT_BLOCK_SIZE} records."
        ),
        "reported_as": "ceil(N / B) simulated block reads; no physical storage is measured.",
    },
    {
        "model": "Memory estimate",
        "assumption": (
            "Reachable Python objects are counted recursively with sys.getsizeof; "
            "shared objects are counted once."
        ),
        "reported_as": "Approximate Python object graph size, not process RSS.",
    },
)
