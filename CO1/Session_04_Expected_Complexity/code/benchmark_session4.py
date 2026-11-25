"""Compare pairwise duplicate checking with narrow fingerprint buckets."""

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
from src.fingerprint import (
    description_fingerprint,
    fingerprint_duplicates,
    naive_pairwise_duplicates,
)


REPORT_DIR = PROJECT_ROOT / "reports" / "M1" / "session4"
RESULTS_PATH = REPORT_DIR / "session4_comparison.csv"
COLLISIONS_PATH = REPORT_DIR / "session4_collision_examples.csv"
FINGERPRINT_BITS = 4


def build_experiment_products(base: list[dict[str, object]]) -> list[dict[str, object]]:
    """Keep source descriptions, add exact duplicates, and add deterministic text."""
    products = [
        {"product_id": str(row["product_id"]), "description": str(row["description"])}
        for row in base
    ]
    for number in range(2):
        source = products[number]
        products.append(
            {"product_id": f"DUP-{number + 1}", "description": source["description"]}
        )
    for number in range(40):
        products.append(
            {
                "product_id": f"SYN-{number + 1:03d}",
                "description": f"Synthetic marketplace description number {number + 1}",
            }
        )
    return products


def find_collision_examples(
    products: list[dict[str, object]], width_bits: int, limit: int = 10
) -> list[dict[str, str]]:
    """Return a few different-description pairs sharing a narrowed fingerprint."""
    buckets: dict[str, list[dict[str, object]]] = {}
    examples: list[dict[str, str]] = []
    for product in products:
        description = str(product["description"])
        key = description_fingerprint(description, width_bits)
        for prior in buckets.get(key, []):
            if prior["description"] != description:
                examples.append(
                    {
                        "fingerprint": key,
                        "product_id_a": str(prior["product_id"]),
                        "product_id_b": str(product["product_id"]),
                        "description_a": str(prior["description"]),
                        "description_b": description,
                    }
                )
                if len(examples) >= limit:
                    return examples
        buckets.setdefault(key, []).append(product)
    return examples


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(trials: int) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    if trials <= 0:
        raise ValueError("trials must be greater than 0")
    products = build_experiment_products(load_catalogue())
    expected_duplicates, _ = naive_pairwise_duplicates(products)
    methods = ("naive_pairwise", "fingerprint_candidates")
    results: list[dict[str, object]] = []

    for method in methods:
        timings: list[int] = []
        summary = None
        for _ in range(trials):
            started = time.perf_counter_ns()
            if method == "naive_pairwise":
                duplicate_ids, comparisons = naive_pairwise_duplicates(products)
                summary = {
                    "duplicate_product_ids": duplicate_ids,
                    "description_comparisons": comparisons,
                    "fingerprint_candidate_checks": 0,
                    "exact_comparisons": comparisons,
                    "collision_pairs": 0,
                }
            else:
                detected = fingerprint_duplicates(products, FINGERPRINT_BITS)
                summary = {
                    "duplicate_product_ids": detected.duplicate_product_ids,
                    "description_comparisons": detected.description_comparisons,
                    "fingerprint_candidate_checks": detected.fingerprint_candidate_checks,
                    "exact_comparisons": detected.exact_comparisons,
                    "collision_pairs": detected.collision_pairs,
                }
            timings.append(time.perf_counter_ns() - started)

        correct = tuple(summary["duplicate_product_ids"]) == expected_duplicates
        if not correct:
            raise AssertionError(f"{method} produced incorrect duplicate IDs")
        results.append(
            {
                "method": method,
                "product_count": len(products),
                "fingerprint_width_bits": FINGERPRINT_BITS if method != "naive_pairwise" else "",
                "description_comparisons": summary["description_comparisons"],
                "fingerprint_candidate_checks": summary["fingerprint_candidate_checks"],
                "exact_comparisons": summary["exact_comparisons"],
                "median_execution_time_ms": statistics.median(timings) / 1_000_000,
                "correctness": correct,
                "duplicate_products": len(expected_duplicates),
                "collision_pairs": summary["collision_pairs"],
                "trial_count": trials,
            }
        )

    examples = find_collision_examples(products, FINGERPRINT_BITS)
    write_csv(
        RESULTS_PATH,
        [
            "method",
            "product_count",
            "fingerprint_width_bits",
            "description_comparisons",
            "fingerprint_candidate_checks",
            "exact_comparisons",
            "median_execution_time_ms",
            "correctness",
            "duplicate_products",
            "collision_pairs",
            "trial_count",
        ],
        [
            {
                **row,
                "median_execution_time_ms": f"{row['median_execution_time_ms']:.6f}",
            }
            for row in results
        ],
    )
    write_csv(
        COLLISIONS_PATH,
        ["fingerprint", "product_id_a", "product_id_b", "description_a", "description_b"],
        examples,
    )
    return results, examples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=31)
    args = parser.parse_args()
    if args.trials <= 0:
        parser.error("--trials must be greater than 0")
    rows, examples = run(args.trials)
    print("method,products,description_comparisons,candidate_checks,exact_comparisons,median_ms,correct,collisions")
    for row in rows:
        print(
            f"{row['method']},{row['product_count']},{row['description_comparisons']},"
            f"{row['fingerprint_candidate_checks']},{row['exact_comparisons']},"
            f"{row['median_execution_time_ms']:.6f},{row['correctness']},{row['collision_pairs']}"
        )
    print(f"Tiny-space collision examples saved: {len(examples)}")
    print(f"Saved results: {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
