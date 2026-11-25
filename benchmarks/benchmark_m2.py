"""Reproducible benchmark and report generator for Sessions 7-12."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
import time
from collections import Counter, deque
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.catalogue import load_catalogue
from src.category_forest import HeavyLightDecomposition, LinkCutForest
from src.measurements import deep_size_bytes
from src.offline_analytics import SqrtRangeSum, mo_range_distinct, sorted_block_range_sums
from src.offline_analytics import load_view_events
from src.phase2_services import EVENTS_PATH
from src.persistent_catalogue import PersistentCatalogue
from src.range_queries import FenwickTree, LazySegmentTree
from src.suffix_automaton import ProductDescriptionAutomata
from src.suffix_index import SuffixArrayIndex


OUTPUT_DIR = ROOT / "reports" / "M2"
FIELDS = (
    "session", "algorithm", "baseline", "input_size", "query_count", "trials",
    "median_time_ms", "operations", "memory_estimate_bytes", "correctness", "notes",
)


def _median_run(action: Callable[[], tuple[bool, int, int]], trials: int) -> tuple[float, int, int, bool]:
    timings: list[int] = []
    operations = memory = 0
    correct = True
    for _ in range(trials):
        started = time.perf_counter_ns()
        trial_correct, trial_operations, trial_memory = action()
        timings.append(time.perf_counter_ns() - started)
        operations, memory = trial_operations, trial_memory
        correct = correct and trial_correct
    return statistics.median(timings) / 1_000_000, operations, memory, correct


def _row(session: int, algorithm: str, baseline: str, size: int, queries: int, trials: int,
         action: Callable[[], tuple[bool, int, int]], notes: str) -> dict[str, Any]:
    median_ms, operations, memory, correct = _median_run(action, trials)
    return {
        "session": session,
        "algorithm": algorithm,
        "baseline": baseline,
        "input_size": size,
        "query_count": queries,
        "trials": trials,
        "median_time_ms": f"{median_ms:.6f}",
        "operations": operations,
        "memory_estimate_bytes": memory,
        "correctness": str(correct).lower(),
        "notes": notes,
    }


def _products(size: int) -> list[dict[str, Any]]:
    source = load_catalogue()
    return [source[index % len(source)] | {"product_id": f"PX{index:06d}"} for index in range(size)]


def _session7(trials: int) -> list[dict[str, Any]]:
    size = 2048
    initial = [((index * 17) % 101) - 20 for index in range(size)]
    rng = random.Random(7007)
    point_updates = [(rng.randrange(size), rng.randrange(-7, 8)) for _ in range(180)]
    queries = [(rng.randrange(size), rng.randrange(size + 1)) for _ in range(160)]
    queries = [(min(a, b), max(a, b)) for a, b in queries]
    rows = []

    def fenwick_action():
        tree = FenwickTree(initial)
        oracle = initial[:]
        for index, delta in point_updates:
            tree.point_add(index, delta)
            oracle[index] += delta
        actual = [tree.range_sum(left, right) for left, right in queries]
        expected = [sum(oracle[left:right]) for left, right in queries]
        return actual == expected, tree.operations, deep_size_bytes(tree)

    def naive_point_action():
        oracle = initial[:]
        operations = 0
        for index, delta in point_updates:
            oracle[index] += delta
            operations += 1
        actual = []
        for left, right in queries:
            total = 0
            for value in oracle[left:right]:
                total += value
                operations += 1
            actual.append(total)
        return actual == [sum(oracle[left:right]) for left, right in queries], operations, deep_size_bytes(oracle)

    rows.append(_row(7, "FenwickTree", "naive point-update/range-sum array", size, len(queries), trials, fenwick_action,
                     "Python counter counts Fenwick internal-node reads/writes; range convention is half-open."))
    rows.append(_row(7, "Naive array", "direct baseline", size, len(queries), trials, naive_point_action,
                     "Counts each updated element and each array element read by range sums."))

    range_updates = [(rng.randrange(size + 1), rng.randrange(size + 1), rng.randrange(-5, 6)) for _ in range(100)]
    range_updates = [(min(left, right), max(left, right), delta) for left, right, delta in range_updates]

    def segment_action():
        tree = LazySegmentTree(initial)
        oracle = initial[:]
        for left, right, delta in range_updates:
            tree.range_add(left, right, delta)
            for index in range(left, right):
                oracle[index] += delta
        actual = [tree.range_sum(left, right) for left, right in queries]
        expected = [sum(oracle[left:right]) for left, right in queries]
        return actual == expected, tree.operations, deep_size_bytes(tree)

    def naive_range_action():
        oracle = initial[:]
        operations = 0
        for left, right, delta in range_updates:
            for index in range(left, right):
                oracle[index] += delta
                operations += 1
        actual = []
        for left, right in queries:
            total = 0
            for value in oracle[left:right]:
                total += value
                operations += 1
            actual.append(total)
        expected = [sum(oracle[left:right]) for left, right in queries]
        return actual == expected, operations, deep_size_bytes(oracle)

    rows.append(_row(7, "LazySegmentTree", "naive range-add/range-sum array", size, len(queries), trials, segment_action,
                     "Counts recursive segment-tree node visits; update/query workload is deterministic."))
    rows.append(_row(7, "Naive range array", "direct baseline", size, len(queries), trials, naive_range_action,
                     "Counts each item changed by an update and each item read by a sum."))
    return rows


def _session8(trials: int) -> list[dict[str, Any]]:
    size, update_count = 500, 24
    products = _products(size)
    updates = [index * 17 % size for index in range(update_count)]
    rows = []

    def persistent_action():
        version = PersistentCatalogue.from_products(products, "V0")
        versions = [version]
        copies = 0
        for number, index in enumerate(updates, start=1):
            current = version.get(f"PX{index:06d}")
            assert current is not None
            changed = current.to_dict() | {"stock": current.stock + number}
            version = version.with_product(changed, f"V{number}")
            versions.append(version)
            copies += version.last_update_node_copies
        correct = all(version.get("PX000000") is not None for version in versions)
        correct = correct and versions[0].get("PX000000").stock == products[0]["stock"]
        correct = correct and versions[-1].product_count == size
        return correct, copies, deep_size_bytes(versions)

    def cow_action():
        current = {str(row["product_id"]): dict(row) for row in products}
        versions = [current]
        copies = 0
        for number, index in enumerate(updates, start=1):
            product_id = f"PX{index:06d}"
            current = dict(current)
            copies += size
            current[product_id] = current[product_id] | {"stock": int(current[product_id]["stock"]) + number}
            versions.append(current)
        correct = versions[0]["PX000000"]["stock"] == products[0]["stock"] and len(versions[-1]) == size
        return correct, copies, deep_size_bytes(versions)

    rows.append(_row(8, "AVL path-copy snapshots", "copy-on-write full dictionary snapshots", size, update_count, trials, persistent_action,
                     "Operation count is the implementation's new immutable tree nodes across updates."))
    rows.append(_row(8, "Copy-on-write snapshots", "full snapshot baseline", size, update_count, trials, cow_action,
                     "Operation count is dictionary entries copied for each version; Python object sizes share unchanged row objects."))
    return rows


def _direct_substrings(documents: dict[str, str], queries: list[str]):
    matches = []
    comparisons = 0
    for query in queries:
        query_matches = []
        for document_id, text in documents.items():
            for start in range(len(text)):
                offset = 0
                while offset < len(query) and start + offset < len(text):
                    comparisons += 1
                    if text[start + offset] != query[offset]:
                        break
                    offset += 1
                if offset == len(query):
                    query_matches.append((document_id, start))
        matches.append(query_matches)
    return matches, comparisons


def _session9_10(trials: int) -> list[dict[str, Any]]:
    source = load_catalogue()
    documents = {
        f"P{number:05d}": str(source[number % len(source)]["description"])
        for number in range(48)
    }
    queries = ["USB-C", "battery", "wireless", "water", "not-present"]
    expected, baseline_ops = _direct_substrings(documents, queries)
    rows = []

    def suffix_action():
        index = SuffixArrayIndex(documents)
        actual = [[(row["document_id"], row["offset"]) for row in index.search(query)] for query in queries]
        operations = sum(index.construction_operations.values()) + sum(index.lcp_operations.values()) + index.query_character_comparisons
        return actual == expected, operations, deep_size_bytes(index)

    def direct_action():
        actual, operations = _direct_substrings(documents, queries)
        return actual == expected, operations, deep_size_bytes(documents)

    rows.append(_row(9, "Suffix array + Kasai LCP", "direct substring scans", sum(map(len, documents.values())), len(queries), trials, suffix_action,
                     "Measured build and exact queries; operation count includes rank-key evaluations, rank comparisons, LCP character comparisons, and query comparisons."))
    rows.append(_row(9, "Direct substring scan", "simple baseline", sum(map(len, documents.values())), len(queries), trials, direct_action,
                     f"Counts character comparisons over all description positions; baseline comparison count {baseline_ops}."))

    def automaton_action():
        index = ProductDescriptionAutomata(documents)
        actual_rows = [index.search(query) for query in queries]
        actual = []
        for query_index, results in enumerate(actual_rows):
            row_map = {row["document_id"]: row["occurrences"] for row in results}
            actual.append(sorted(row_map.items()))
        expected_counts = [
            sorted(Counter(document_id for document_id, _ in query_matches).items())
            for query_matches in expected
        ]
        operations = sum(machine.construction_operations + machine.query_operations for machine in index.automata.values())
        correct = actual == expected_counts
        return correct, operations, deep_size_bytes(index)

    rows.append(_row(10, "Per-document suffix automata", "direct substring scans", sum(map(len, documents.values())), len(queries), trials, automaton_action,
                     "Counts transition-existence checks during construction and transition checks during queries; direct scans are the oracle."))
    rows.append(_row(10, "Direct substring scan", "simple baseline", sum(map(len, documents.values())), len(queries), trials, direct_action,
                     f"Counts character comparisons over all description positions; baseline comparison count {baseline_ops}."))
    return rows


def _path(adjacency: dict[str, set[str]], values: dict[str, int], start: str, end: str):
    parent = {start: None}
    queue = deque([start])
    visits = 0
    while queue:
        node = queue.popleft()
        visits += 1
        if node == end:
            break
        for neighbor in adjacency[node]:
            if neighbor not in parent:
                parent[neighbor] = node
                queue.append(neighbor)
    total, node = 0, end
    while node is not None:
        total += values[node]
        node = parent[node]
    return total, visits


def _session11(trials: int) -> list[dict[str, Any]]:
    size = 240
    rng = random.Random(1111)
    values = {f"C{i:04d}": rng.randrange(1, 100) for i in range(size)}
    edges = [(f"C{i:04d}", f"C{(i - 1) // 2:04d}") for i in range(1, size)]
    adjacency = {node: set() for node in values}
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    pairs = [(f"C{rng.randrange(size):04d}", f"C{rng.randrange(size):04d}") for _ in range(180)]
    expected = [_path(adjacency, values, left, right)[0] for left, right in pairs]
    rows = []

    def hld_action():
        tree = HeavyLightDecomposition(values, edges)
        actual = [tree.path_sum(left, right) for left, right in pairs]
        return actual == expected, tree.path_segments_visited + tree._tree.operations, deep_size_bytes(tree)

    def lct_action():
        tree = LinkCutForest(values)
        for left, right in edges:
            tree.link(left, right)
        actual = [tree.path_sum(left, right) for left, right in pairs]
        return actual == expected, tree.rotations + tree.accesses, deep_size_bytes(tree)

    def naive_action():
        actual = []
        operations = 0
        for left, right in pairs:
            result, visits = _path(adjacency, values, left, right)
            actual.append(result)
            operations += visits
        return actual == expected, operations, deep_size_bytes(adjacency)

    rows.append(_row(11, "Heavy-light decomposition", "naive BFS path traversal", size, len(pairs), trials, hld_action,
                     "Timer includes static decomposition and queries; operations count chain ranges and Fenwick internal accesses."))
    rows.append(_row(11, "Link-cut forest", "naive BFS path traversal", size, len(pairs), trials, lct_action,
                     "Timer includes linking the initial forest and queries; counts splay rotations and access calls."))
    rows.append(_row(11, "Naive BFS path traversal", "simple baseline", size, len(pairs), trials, naive_action,
                     "Counts queue nodes visited across each path search; adjacency and values are the same inputs."))
    return rows


def _session12(trials: int) -> list[dict[str, Any]]:
    fixed_view_ids = [event.product_id for event in load_view_events(EVENTS_PATH)]
    values = [fixed_view_ids[index % len(fixed_view_ids)] for index in range(2200)]
    rng = random.Random(1212)
    queries = []
    for _ in range(220):
        left = rng.randrange(len(values) + 1)
        right = rng.randrange(left, len(values) + 1)
        queries.append((left, right))
    expected_distinct = [len(set(values[left:right])) for left, right in queries]
    sums = [index % 101 for index in range(len(values))]
    expected_sums = [sum(sums[left:right]) for left, right in queries]
    rows = []

    def mo_action():
        result = mo_range_distinct(values, queries)
        return result["answers"] == expected_distinct, result["pointer_moves"], deep_size_bytes(result)

    def naive_distinct_action():
        answers = []
        operations = 0
        for left, right in queries:
            answers.append(len(set(values[left:right])))
            operations += right - left
        return answers == expected_distinct, operations, deep_size_bytes(values)

    def sqrt_action():
        result = sorted_block_range_sums(sums, queries)
        return result["answers"] == expected_sums, result["block_or_element_reads"], result["memory_estimate_bytes"]

    def naive_sum_action():
        answers = []
        operations = 0
        for left, right in queries:
            subtotal = 0
            for value in sums[left:right]:
                subtotal += value
                operations += 1
            answers.append(subtotal)
        return answers == expected_sums, operations, deep_size_bytes(sums)

    rows.append(_row(12, "Mo range-distinct", "naive per-range set", len(values), len(queries), trials, mo_action,
                     "Counts left/right window movements over the fixed local product-view ID array."))
    rows.append(_row(12, "Naive range-distinct", "simple baseline", len(values), len(queries), trials, naive_distinct_action,
                     "Counts every view ID visited in each direct slice."))
    rows.append(_row(12, "Sorted-block square-root sums", "naive per-range sum", len(sums), len(queries), trials, sqrt_action,
                     "Counts complete block totals and edge elements read while processing ranges in sorted left-block order."))
    rows.append(_row(12, "Naive range sum", "simple baseline", len(sums), len(queries), trials, naive_sum_action,
                     "Counts every numeric value read from each direct interval."))
    return rows


def _write_reports(rows: list[dict[str, Any]], trials: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "session_benchmarks.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    for session in range(7, 13):
        session_rows = [row for row in rows if int(row["session"]) == session]
        title = {
            7: "Range queries and lazy updates",
            8: "Persistent catalogue snapshots",
            9: "Suffix arrays and longest common prefixes",
            10: "Suffix automata for description text",
            11: "Category tree queries and dynamic forests",
            12: "Offline query processing and exact service review",
        }[session]
        lines = [
            f"# Session {session}: {title}",
            "",
            "## Implementation and verification",
            "",
            f"The implementation is in `src/` and correctness checks are in `tests/test_session{session}.py`. The benchmark below was generated locally with the standard-library script `benchmarks/benchmark_m2.py`.",
            "",
            "## Measured results",
            "",
            f"Trials per row: {trials}. Timings are local medians. Memory is a recursive `sys.getsizeof` object-graph estimate, not process RSS.",
            "",
            "| Algorithm | Baseline | Input size | Queries | Median ms | Operations | Memory bytes | Correct |",
            "|---|---|---:|---:|---:|---:|---:|:---:|",
        ]
        for row in session_rows:
            lines.append(
                f"| {row['algorithm']} | {row['baseline']} | {row['input_size']} | {row['query_count']} | {row['median_time_ms']} | {row['operations']} | {row['memory_estimate_bytes']} | {row['correctness']} |"
            )
        lines += ["", "## Measurement notes", ""]
        lines.extend(f"- {row['notes']}" for row in session_rows)
        lines += ["", "Results are from this run and depend on machine load. Complexity claims are theoretical; operation counts follow the named counters or explicitly described loop visits.", ""]
        (OUTPUT_DIR / f"session{session}.md").write_text("\n".join(lines), encoding="utf-8")

    summary = [
        "# M2 Final Report: Sessions 7–12",
        "",
        "## Scope and implementation status",
        "",
        "Sessions 7–12 implement range structures, persistent catalogue history, exact substring indexes, category path services, and offline event analytics. Session 9's DC3 component is a guided trace; the measured suffix-array builder is prefix doubling. Session 11 includes an implemented HLD and link-cut forest.",
        "",
        "The implementation follows the detailed requirements in the user-provided project brief. The separately referenced official PDF was not present in the available attachment files, so PDF-only acceptance details could not be checked.",
        "",
        "## Benchmark comparison",
        "",
        f"Generated by `python benchmarks/benchmark_m2.py --trials {trials}`. The CSV contains all per-algorithm rows.",
        "",
        "| Session | Algorithm | Baseline | Size | Median ms | Operations | Memory bytes | Correct |",
        "|---:|---|---|---:|---:|---:|---:|:---:|",
    ]
    for row in rows:
        summary.append(
            f"| {row['session']} | {row['algorithm']} | {row['baseline']} | {row['input_size']} | {row['median_time_ms']} | {row['operations']} | {row['memory_estimate_bytes']} | {row['correctness']} |"
        )
    summary += [
        "",
        "## Integration review",
        "",
        "- Session 7 aggregates purchase-event revenue into daily bins and reports Fenwick range sums; range stock changes use the lazy segment tree.",
        "- Session 8 supplies catalogue version IDs V0/V1/V2 and version-aware cache-key construction. Admin inventory changes create a new in-memory persistent snapshot.",
        "- Sessions 9–10 index the actual product descriptions and expose exact substring APIs.",
        "- Session 11 builds a category hierarchy from catalogue categories and purchase revenue, then verifies HLD against a naive traversal and LinkCutForest.",
        "- Session 12 loads the fixed anonymous view-event array and exposes Mo range-distinct analytics.",
        "- `/workspace` presents session pages and `/admin` manages the local catalogue and analytics; `/` remains the customer storefront.",
        "",
        "## Test record",
        "",
        "The recorded Python and cart test totals, syntax checks, live Session 7–12 acceptance checks, and benchmark correctness summary are in [`verification.json`](verification.json), dated with the run that produced it.",
        "",
        "## Limitations",
        "",
        "Admin catalogue edits live in memory and reset when the local server process restarts. The event dataset is deterministic synthetic activity, not customer data. Memory values are Python object-size estimates. Timing results are machine-specific. The DC3 construction is a labelled guided trace rather than an implementation. Sessions 13–36 remain upcoming.",
        "",
    ]
    (OUTPUT_DIR / "M2_Final_Report.md").write_text("\n".join(summary), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=5)
    args = parser.parse_args()
    if args.trials <= 0:
        parser.error("--trials must be positive")
    rows = _session7(args.trials) + _session8(args.trials) + _session9_10(args.trials) + _session11(args.trials) + _session12(args.trials)
    _write_reports(rows, args.trials)
    failed = [row for row in rows if row["correctness"] != "true"]
    print(f"Wrote {len(rows)} benchmark rows to reports/M2/session_benchmarks.csv")
    print(f"Correct rows: {len(rows) - len(failed)}; failed rows: {len(failed)}")
    if failed:
        for row in failed:
            print(f"FAILED S{row['session']} {row['algorithm']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
