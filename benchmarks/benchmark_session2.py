"""Compare dictionary-based indirect scans with column-based scans."""

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.catalogue import load_catalogue
from src.hardware_analysis import ContiguousCatalogue, search_contiguous
from src.search import linear_search
from src.workload import DEFAULT_QUERY, generate_scaled_catalogue


OUTPUT_PATH = PROJECT_ROOT / "reports" / "M1" / "session2" / "session2_benchmark.csv"
SIZES = (20, 100, 1000)


def run(trials: int, output_path: Path) -> list[dict[str, object]]:
    if trials <= 0:
        raise ValueError("trials must be greater than 0")
    base = load_catalogue()
    category, max_price, min_stock = DEFAULT_QUERY
    rows: list[dict[str, object]] = []

    for size in SIZES:
        products = generate_scaled_catalogue(base, size)
        columns = ContiguousCatalogue.from_products(products)
        expected, _ = linear_search(products, category, max_price, min_stock)
        expected_ids = [str(product["product_id"]) for product in expected]

        approaches = (
            ("indirect_dict", lambda: linear_search(products, category, max_price, min_stock)),
            ("contiguous_columns", lambda: search_contiguous(columns, category, max_price, min_stock)),
        )
        for representation, search in approaches:
            elapsed: list[int] = []
            actual_ids: list[str] = []
            inspected = 0
            for _ in range(trials):
                started = time.perf_counter_ns()
                matches, inspected = search()
                elapsed.append(time.perf_counter_ns() - started)
                if representation == "indirect_dict":
                    actual_ids = [str(product["product_id"]) for product in matches]
                else:
                    actual_ids = list(matches)

            correct = actual_ids == expected_ids
            if not correct:
                raise AssertionError(f"{representation} returned incorrect product IDs")
            rows.append(
                {
                    "data_size": size,
                    "representation": representation,
                    "median_execution_time_ms": statistics.median(elapsed) / 1_000_000,
                    "correctness": correct,
                    "trial_count": trials,
                    "matching_products": len(actual_ids),
                    "records_inspected": inspected,
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "data_size",
        "representation",
        "median_execution_time_ms",
        "correctness",
        "trial_count",
        "matching_products",
        "records_inspected",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            formatted["median_execution_time_ms"] = f"{row['median_execution_time_ms']:.6f}"
            writer.writerow(formatted)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=31)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    if args.trials <= 0:
        parser.error("--trials must be greater than 0")
    rows = run(args.trials, args.output)
    print("size,representation,median_ms,correct,trials,matches,records_inspected")
    for row in rows:
        print(
            f"{row['data_size']},{row['representation']},"
            f"{row['median_execution_time_ms']:.6f},{row['correctness']},"
            f"{row['trial_count']},{row['matching_products']},{row['records_inspected']}"
        )
    print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
