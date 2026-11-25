"""Reproducible size-scaling benchmark for the Session 1 linear scan."""

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

# Running this file directly sets sys.path to benchmarks/, so add the project
# root before importing the local src package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.catalogue import load_catalogue
from src.hardware_analysis import simulate_block_reads
from src.search import linear_search, reference_search
from src.workload import DEFAULT_QUERY, generate_scaled_catalogue


DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "reports" / "M1" / "session1_benchmark.csv"
BENCHMARK_SIZES = (20, 100, 1000)
CATEGORY, MAX_PRICE, MIN_STOCK = DEFAULT_QUERY


def benchmark_catalogue(
    catalogue: list[dict[str, object]], trials: int, block_size: int
) -> dict[str, object]:
    """Time repeated scans and return one summary row for a catalogue size."""
    if trials <= 0:
        raise ValueError("trials must be greater than 0")

    expected_ids = [
        str(product["product_id"])
        for product in reference_search(catalogue, CATEGORY, MAX_PRICE, MIN_STOCK)
    ]

    elapsed_ns: list[int] = []
    match_count = 0
    inspected_count = 0
    for _ in range(trials):
        start = time.perf_counter_ns()
        matches, inspected_count = linear_search(
            catalogue, CATEGORY, MAX_PRICE, MIN_STOCK
        )
        elapsed_ns.append(time.perf_counter_ns() - start)
        actual_ids = [str(product["product_id"]) for product in matches]
        if actual_ids != expected_ids:
            raise AssertionError("Linear search disagrees with the reference search")
        match_count = len(matches)

    if inspected_count != len(catalogue):
        raise AssertionError("Full linear scan did not inspect every product record")

    return {
        "product_count": len(catalogue),
        "records_inspected": inspected_count,
        "median_time_ms": statistics.median(elapsed_ns) / 1_000_000,
        "matching_products": match_count,
        "trials": trials,
        "block_size": block_size,
        "simulated_block_reads": simulate_block_reads(len(catalogue), block_size),
        "category": CATEGORY,
        "max_price": MAX_PRICE,
        "min_stock": MIN_STOCK,
    }


def run_benchmarks(
    base_catalogue: list[dict[str, object]],
    trials: int = 9,
    block_size: int = 64,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> list[dict[str, object]]:
    """Generate three dataset sizes, benchmark them, and save the summaries."""
    # The explicit sizes and deterministic expansion make runs comparable.
    rows = [
        benchmark_catalogue(generate_scaled_catalogue(base_catalogue, size), trials, block_size)
        for size in BENCHMARK_SIZES
    ]

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "product_count",
        "records_inspected",
        "median_time_ms",
        "matching_products",
        "trials",
        "block_size",
        "simulated_block_reads",
        "category",
        "max_price",
        "min_stock",
    ]
    with destination.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            formatted["median_time_ms"] = f"{row['median_time_ms']:.6f}"
            writer.writerow(formatted)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Session 1 search benchmark.")
    parser.add_argument("--trials", type=int, default=9, help="repetitions per size (default: 9)")
    parser.add_argument("--block-size", type=int, default=64, help="records per simulated block")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    if args.trials <= 0:
        parser.error("--trials must be greater than 0")
    if args.block_size <= 0:
        parser.error("--block-size must be greater than 0")

    base_catalogue = load_catalogue()
    rows = run_benchmarks(base_catalogue, args.trials, args.block_size, args.output)
    print(f"Benchmark query: category={CATEGORY!r}, max_price={MAX_PRICE:g}, min_stock={MIN_STOCK}")
    print(f"Trials per size: {args.trials}; simulated block size: {args.block_size} records")
    print("products,inspected,median_ms,matches,simulated_block_reads")
    for row in rows:
        print(
            f"{row['product_count']},{row['records_inspected']},"
            f"{row['median_time_ms']:.6f},{row['matching_products']},"
            f"{row['simulated_block_reads']}"
        )
    print(f"Saved CSV: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
