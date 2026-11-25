"""Final M1 comparison of scans, category buckets, layouts, and query batching."""

import argparse
import csv
import html
import math
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.catalogue import load_catalogue
from src.hardware_analysis import (
    ContiguousCatalogue,
    batch_search_contiguous,
    search_contiguous,
)
from src.measurements import deep_size_bytes
from src.search import (
    CategoryIndex,
    batch_category_search,
    batch_linear_search,
    linear_search,
    reference_search,
)
from src.workload import generate_scaled_catalogue


REPORT_DIR = PROJECT_ROOT / "reports" / "M1" / "session6"
CSV_PATH = REPORT_DIR / "session6_benchmark.csv"
SVG_PATH = REPORT_DIR / "session6_runtime.svg"
SIZES = (20, 100, 1000, 10000)
QUERIES = (
    ("Electronics", 100.0, 1),
    ("Home & Kitchen", 50.0, 1),
    ("Sports & Outdoors", 80.0, 5),
    ("Clothing", 30.0, 1),
    ("No Such Category", 500.0, 1),
)
METHODS = (
    "linear_individual",
    "linear_batched",
    "category_hash_individual",
    "category_hash_batched",
    "contiguous_individual",
    "contiguous_batched",
)
COLORS = {
    "linear_individual": "#1f77b4",
    "linear_batched": "#17becf",
    "category_hash_individual": "#2ca02c",
    "category_hash_batched": "#98df8a",
    "contiguous_individual": "#d62728",
    "contiguous_batched": "#ff9896",
}


def expected_for_all(products: list[dict[str, object]]) -> list[list[str]]:
    expected: list[list[str]] = []
    for category, max_price, min_stock in QUERIES:
        matches = reference_search(products, category, max_price, min_stock)
        expected.append([str(product["product_id"]) for product in matches])
    return expected


def run_method(
    method: str,
    products: list[dict[str, object]],
    index: CategoryIndex,
    columns: ContiguousCatalogue,
) -> tuple[list[list[str]], int, int]:
    """Return ordered IDs, predicate/candidate count, and collection passes."""
    result_ids: list[list[str]] = []
    operation_count = 0
    if method == "linear_individual":
        for query in QUERIES:
            matches, inspected = linear_search(products, *query)
            result_ids.append([str(product["product_id"]) for product in matches])
            operation_count += inspected
        return result_ids, operation_count, len(QUERIES)

    if method == "linear_batched":
        matches_by_query, operation_count = batch_linear_search(products, QUERIES)
        result_ids = [
            [str(product["product_id"]) for product in matches]
            for matches in matches_by_query
        ]
        return result_ids, operation_count, 1 if QUERIES else 0

    if method == "category_hash_individual":
        for query in QUERIES:
            matches, inspected = index.search(*query)
            result_ids.append([str(product["product_id"]) for product in matches])
            operation_count += inspected
        return result_ids, operation_count, len(QUERIES)

    if method == "category_hash_batched":
        matches_by_query, operation_count = batch_category_search(index, QUERIES)
        result_ids = [
            [str(product["product_id"]) for product in matches]
            for matches in matches_by_query
        ]
        return result_ids, operation_count, len(QUERIES)

    if method == "contiguous_individual":
        for query in QUERIES:
            matches, inspected = search_contiguous(columns, *query)
            result_ids.append(list(matches))
            operation_count += inspected
        return result_ids, operation_count, len(QUERIES)

    if method == "contiguous_batched":
        matches_by_query, operation_count = batch_search_contiguous(columns, QUERIES)
        return matches_by_query, operation_count, 1 if QUERIES else 0

    raise ValueError(f"Unknown benchmark method: {method}")


def benchmark(trials: int) -> list[dict[str, object]]:
    if trials <= 0:
        raise ValueError("trials must be greater than 0")
    base = load_catalogue()
    rows: list[dict[str, object]] = []

    for size in SIZES:
        products = generate_scaled_catalogue(base, size)
        expected = expected_for_all(products)

        index_build_started = time.perf_counter_ns()
        index = CategoryIndex(products)
        index_build_ms = (time.perf_counter_ns() - index_build_started) / 1_000_000
        columns_build_started = time.perf_counter_ns()
        columns = ContiguousCatalogue.from_products(products)
        columns_build_ms = (time.perf_counter_ns() - columns_build_started) / 1_000_000
        memory_by_representation = {
            "linear": deep_size_bytes(products),
            "category_hash": deep_size_bytes(index),
            "contiguous": deep_size_bytes(columns),
        }

        for method in METHODS:
            timings: list[int] = []
            operation_count = 0
            collection_passes = 0
            actual_ids: list[list[str]] = []
            for _ in range(trials):
                started = time.perf_counter_ns()
                actual_ids, operation_count, collection_passes = run_method(
                    method, products, index, columns
                )
                timings.append(time.perf_counter_ns() - started)

            correct = actual_ids == expected
            if not correct:
                raise AssertionError(f"{method} returned IDs that differ from the reference")
            representation = method.split("_")[0]
            memory_key = {
                "linear": "linear",
                "category": "category_hash",
                "contiguous": "contiguous",
            }[representation]
            preparation_ms = {
                "linear": 0.0,
                "category": index_build_ms,
                "contiguous": columns_build_ms,
            }[representation]
            rows.append(
                {
                    "dataset_size": size,
                    "workload": "five_fixed_category_price_stock_queries",
                    "algorithm_representation": method,
                    "median_execution_time_ms": statistics.median(timings) / 1_000_000,
                    "preparation_time_ms": preparation_ms,
                    "memory_estimate_bytes": memory_by_representation[memory_key],
                    "operation_count": operation_count,
                    "collection_passes": collection_passes,
                    "correctness": correct,
                    "trial_count": trials,
                    "matching_products_total": sum(map(len, actual_ids)),
                }
            )
    return rows


def write_csv(rows: list[dict[str, object]]) -> None:
    fields = [
        "dataset_size",
        "workload",
        "algorithm_representation",
        "median_execution_time_ms",
        "preparation_time_ms",
        "memory_estimate_bytes",
        "operation_count",
        "collection_passes",
        "correctness",
        "trial_count",
        "matching_products_total",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            formatted["median_execution_time_ms"] = f"{row['median_execution_time_ms']:.6f}"
            formatted["preparation_time_ms"] = f"{row['preparation_time_ms']:.6f}"
            writer.writerow(formatted)


def write_svg(rows: list[dict[str, object]]) -> None:
    """Create a dependency-free SVG line chart with a logarithmic time axis."""
    sizes = list(SIZES)
    values = {method: {} for method in METHODS}
    for row in rows:
        values[str(row["algorithm_representation"])][int(row["dataset_size"])] = max(
            float(row["median_execution_time_ms"]), 1e-6
        )

    width, height = 960, 540
    left, right, top, bottom = 90, 250, 55, 80
    plot_width = width - left - right
    plot_height = height - top - bottom
    all_values = [time_ms for series in values.values() for time_ms in series.values()]
    log_min = min(math.log10(item) for item in all_values)
    log_max = max(math.log10(item) for item in all_values)
    if log_min == log_max:
        log_max += 1.0

    def x_position(size: int) -> float:
        return left + (sizes.index(size) / max(1, len(sizes) - 1)) * plot_width

    def y_position(time_ms: float) -> float:
        fraction = (math.log10(time_ms) - log_min) / (log_max - log_min)
        return top + (1.0 - fraction) * plot_height

    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="480" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">Session 6 median query time (log scale)</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#333"/>',
        f'<text x="25" y="{top + plot_height / 2}" transform="rotate(-90 25 {top + plot_height / 2})" text-anchor="middle" font-family="sans-serif" font-size="13">Median milliseconds (log scale)</text>',
    ]
    for size in sizes:
        x = x_position(size)
        pieces.append(f'<text x="{x}" y="{top + plot_height + 25}" text-anchor="middle" font-family="sans-serif" font-size="12">{size}</text>')
        pieces.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top + plot_height}" stroke="#ddd"/>')
    for method in METHODS:
        points = [
            (x_position(size), y_position(values[method][size]))
            for size in sizes
        ]
        point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        color = COLORS[method]
        pieces.append(f'<polyline points="{point_text}" fill="none" stroke="{color}" stroke-width="2"/>')
        for x, y in points:
            pieces.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"/>')
        legend_index = METHODS.index(method)
        legend_y = top + 18 + legend_index * 22
        pieces.append(f'<line x1="{left + plot_width + 20}" y1="{legend_y - 4}" x2="{left + plot_width + 42}" y2="{legend_y - 4}" stroke="{color}" stroke-width="3"/>')
        pieces.append(f'<text x="{left + plot_width + 50}" y="{legend_y}" font-family="sans-serif" font-size="11">{html.escape(method)}</text>')
    pieces.append('</svg>')
    SVG_PATH.write_text("\n".join(pieces), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=15)
    args = parser.parse_args()
    if args.trials <= 0:
        parser.error("--trials must be greater than 0")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = benchmark(args.trials)
    write_csv(rows)
    write_svg(rows)
    print("size,approach,median_ms,prep_ms,memory_bytes,operations,passes,correct")
    for row in rows:
        print(
            f"{row['dataset_size']},{row['algorithm_representation']},"
            f"{row['median_execution_time_ms']:.6f},{row['preparation_time_ms']:.6f},"
            f"{row['memory_estimate_bytes']},{row['operation_count']},"
            f"{row['collection_passes']},{row['correctness']}"
        )
    print(f"Saved CSV and SVG under {REPORT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
