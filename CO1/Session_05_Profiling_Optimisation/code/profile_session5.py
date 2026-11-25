"""Profile catalogue ingestion and search, then compare linear and indexed scans."""

import argparse
import csv
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.catalogue import REQUIRED_FIELDS, load_catalogue
from src.profiler import profile_callable, write_profile_csv, write_profile_text
from src.search import CategoryIndex, linear_search, reference_search
from src.workload import DEFAULT_QUERY, generate_scaled_catalogue


REPORT_DIR = PROJECT_ROOT / "reports" / "M1" / "session5"
PROFILE_TEXT_PATH = REPORT_DIR / "session5_profile.txt"
PROFILE_CSV_PATH = REPORT_DIR / "session5_profile_stats.csv"
BENCHMARK_PATH = REPORT_DIR / "before_after_benchmark.csv"
ENVIRONMENT_PATH = REPORT_DIR / "environment.txt"
SIZES = (20, 100, 1000, 10000)


def write_catalogue_csv(path: Path, products: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=REQUIRED_FIELDS)
        writer.writeheader()
        writer.writerows(products)


def profile_ingestion_and_search() -> list[tuple[str, object]]:
    base = load_catalogue()
    large = generate_scaled_catalogue(base, 10000)
    profiles = []

    # Generate a large CSV so ingestion profiling has enough work to inspect.
    with tempfile.TemporaryDirectory(prefix="marketplace_profile_") as temporary_dir:
        csv_path = Path(temporary_dir) / "products_10000.csv"
        write_catalogue_csv(csv_path, large)
        loaded, ingestion_profile = profile_callable(load_catalogue, csv_path)
        profiles.append(("catalogue_ingestion_10000", ingestion_profile))

    category, max_price, min_stock = DEFAULT_QUERY
    expected, _ = reference_search(large, category, max_price, min_stock), len(large)
    found, search_profile = profile_callable(
        linear_search, large, category, max_price, min_stock
    )
    result, _inspected = found
    expected_ids = [str(row["product_id"]) for row in expected]
    if [str(row["product_id"]) for row in result] != expected_ids:
        raise AssertionError("Profiled baseline search failed its correctness check")
    profiles.append(("baseline_search_10000", search_profile))
    if len(loaded) != 10000:
        raise AssertionError("Profiled catalogue ingestion did not load 10,000 records")
    return profiles


def compare_searches(trials: int) -> list[dict[str, object]]:
    base = load_catalogue()
    category, max_price, min_stock = DEFAULT_QUERY
    rows: list[dict[str, object]] = []
    for size in SIZES:
        products = generate_scaled_catalogue(base, size)
        expected, _ = reference_search(products, category, max_price, min_stock), size
        expected_ids = [str(row["product_id"]) for row in expected]
        index_build_timings: list[int] = []
        for _ in range(trials):
            started = time.perf_counter_ns()
            index = CategoryIndex(products)
            index_build_timings.append(time.perf_counter_ns() - started)

        for method in ("baseline_linear_scan", "category_hash_index"):
            timings: list[int] = []
            actual_ids: list[str] = []
            for _ in range(trials):
                started = time.perf_counter_ns()
                if method == "baseline_linear_scan":
                    matches, inspected = linear_search(
                        products, category, max_price, min_stock
                    )
                    actual_ids = [str(row["product_id"]) for row in matches]
                else:
                    matches, inspected = index.search(category, max_price, min_stock)
                    actual_ids = [str(row["product_id"]) for row in matches]
                timings.append(time.perf_counter_ns() - started)
            correct = actual_ids == expected_ids
            if not correct:
                raise AssertionError(f"{method} search returned incorrect IDs")
            rows.append(
                {
                    "data_size": size,
                    "version": method,
                    "median_execution_time_ms": statistics.median(timings) / 1_000_000,
                    "index_build_median_ms": (
                        statistics.median(index_build_timings) / 1_000_000
                        if method == "category_hash_index"
                        else 0.0
                    ),
                    "correctness": correct,
                    "trial_count": trials,
                    "matching_products": len(actual_ids),
                    "records_inspected": inspected,
                }
            )
    return rows


def write_benchmarks(rows: list[dict[str, object]]) -> None:
    fields = [
        "data_size",
        "version",
        "median_execution_time_ms",
        "index_build_median_ms",
        "correctness",
        "trial_count",
        "matching_products",
        "records_inspected",
    ]
    with BENCHMARK_PATH.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            formatted["median_execution_time_ms"] = f"{row['median_execution_time_ms']:.6f}"
            formatted["index_build_median_ms"] = f"{row['index_build_median_ms']:.6f}"
            writer.writerow(formatted)


def write_environment() -> None:
    details = [
        f"Python: {sys.version.replace(chr(10), ' ')}",
        f"Implementation: {platform.python_implementation()}",
        f"Operating system: {platform.platform()}",
        f"Machine: {platform.machine()}",
        f"Processor: {platform.processor() or 'not reported by platform module'}",
        "Profiling: cProfile and pstats; benchmark timing: time.perf_counter_ns",
    ]
    ENVIRONMENT_PATH.write_text("\n".join(details) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=31)
    args = parser.parse_args()
    if args.trials <= 0:
        parser.error("--trials must be greater than 0")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    profiles = profile_ingestion_and_search()
    write_profile_text(profiles, PROFILE_TEXT_PATH)
    write_profile_csv(profiles, PROFILE_CSV_PATH)
    for profile_name, profiler in profiles:
        profiler.dump_stats(REPORT_DIR / f"{profile_name}.prof")
    benchmark_rows = compare_searches(args.trials)
    write_benchmarks(benchmark_rows)
    write_environment()

    print("profile,function,calls,total_seconds,cumulative_seconds")
    from src.profiler import profile_rows

    for profile_name, profiler in profiles:
        for row in profile_rows(profile_name, profiler)[:5]:
            print(
                f"{profile_name},{row['function_name']},{row['number_of_calls']},"
                f"{row['total_time_seconds']:.6f},{row['cumulative_time_seconds']:.6f}"
            )
    print("data_size,version,median_ms,index_build_median_ms,correct,trials,matches,records_inspected")
    for row in benchmark_rows:
        print(
            f"{row['data_size']},{row['version']},{row['median_execution_time_ms']:.6f},"
            f"{row['index_build_median_ms']:.6f},"
            f"{row['correctness']},{row['trial_count']},{row['matching_products']},"
            f"{row['records_inspected']}"
        )
    print(f"Saved profile and benchmarks under: {REPORT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
