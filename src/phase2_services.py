"""Live demonstrations that connect Sessions 7-12 to local project data."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict, deque
from datetime import date
from pathlib import Path
from typing import Any

from src.category_forest import HeavyLightDecomposition, LinkCutForest, marketplace_category_tree
from src.catalogue import load_catalogue
from src.offline_analytics import event_distinct_demo
from src.persistent_catalogue import build_snapshot_demo
from src.range_queries import FenwickTree, LazySegmentTree
from src.suffix_automaton import ProductDescriptionAutomata, automaton_demo
from src.suffix_index import SuffixArrayIndex, suffix_demo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = PROJECT_ROOT / "data" / "events.csv"


def load_event_rows(path: str | Path = EVENTS_PATH) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"event_id", "timestamp", "anonymous_user_id", "event_type", "product_id", "query"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("event CSV has an incomplete marketplace event schema")
        rows = list(reader)
    allowed = {"search", "view", "purchase"}
    for row in rows:
        if row.get("event_type") not in allowed:
            raise ValueError(f"unsupported event type {row.get('event_type')!r}")
        if not row.get("anonymous_user_id", "").startswith("anon-"):
            raise ValueError("the local demo event fixture must use anonymous user IDs")
        if row["event_type"] == "search" and not row.get("query"):
            raise ValueError("search events must have a query")
        if row["event_type"] in {"view", "purchase"} and not row.get("product_id"):
            raise ValueError("view and purchase events must have a product ID")
    return rows


def session7_demo(products: list[dict[str, Any]], event_rows: list[dict[str, str]]) -> dict[str, Any]:
    prices = {str(product["product_id"]): float(product["price"]) for product in products}
    sales_by_day: Counter[date] = Counter()
    purchases_by_day: Counter[date] = Counter()
    for event in event_rows:
        if event["event_type"] == "purchase":
            event_day = date.fromisoformat(event["timestamp"][:10])
            sales_by_day[event_day] += prices[event["product_id"]]
            purchases_by_day[event_day] += 1
    days = sorted(sales_by_day)
    daily_sales = [sales_by_day[day] for day in days]
    fenwick = FenwickTree(daily_sales)
    # Days 3 through 9, inclusive, become half-open indices [2, 9).
    left, right = min(2, len(days)), min(9, len(days))
    range_sales = fenwick.range_sum(left, right)
    expected_sales = sum(daily_sales[left:right])

    original_stock = [int(product["stock"]) for product in products[:12]]
    segment = LazySegmentTree(original_stock)
    stock_range = (2, min(7, len(original_stock)))
    before = segment.range_sum(*stock_range)
    segment.range_add(*stock_range, 4)
    after = segment.range_sum(*stock_range)
    expected_stock_after = before + 4 * (stock_range[1] - stock_range[0])
    return {
        "daily_sales": [
            {"day": day.isoformat(), "purchase_count": purchases_by_day[day], "sales_inr": sales_by_day[day]}
            for day in days
        ],
        "sales_query": {"label": "Days 3-9 inclusive", "left_index": left, "right_exclusive": right, "sales_inr": range_sales},
        "sales_oracle_passed": range_sales == expected_sales,
        "fenwick_operations": fenwick.operations,
        "stock_adjustment": {
            "catalogue_index_range": list(stock_range),
            "per_product_stock_adjustment": 4,
            "before_total": before,
            "after_total": after,
            "lazy_segment_tree_node_visits": segment.operations,
            "oracle_passed": after == expected_stock_after,
        },
        "structures": {
            "Fenwick tree": "O(log N) point update and prefix/range query; O(N) storage.",
            "Lazy segment tree": "O(log N) range add and range sum; O(N) storage.",
        },
    }


def _naive_tree_path_sum(values: dict[str, int], edges: list[tuple[str, str]], left: str, right: str) -> int:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for first, second in edges:
        adjacency[first].append(second)
        adjacency[second].append(first)
    parent: dict[str, str | None] = {left: None}
    pending = deque([left])
    while pending:
        node = pending.popleft()
        if node == right:
            break
        for neighbor in adjacency[node]:
            if neighbor not in parent:
                parent[neighbor] = node
                pending.append(neighbor)
    if right not in parent:
        raise ValueError("tree path does not exist")
    total = 0
    node: str | None = right
    while node is not None:
        total += values[node]
        node = parent[node]
    return total


def session11_demo(category_revenue: dict[str, int]) -> dict[str, Any]:
    values, edges = marketplace_category_tree(category_revenue)
    hld = HeavyLightDecomposition(values, edges)
    endpoints = ("Marketplace", "Electronics")
    hld_total = hld.path_sum(*endpoints)
    naive_total = _naive_tree_path_sum(values, edges, *endpoints)
    dynamic = LinkCutForest(values)
    dynamic_trace = []
    for left, right in edges:
        dynamic.link(left, right)
        dynamic_trace.append({"operation": "link", "parent": right, "category": left})
    dynamic_total = dynamic.path_sum(*endpoints)
    try:
        dynamic.link("Marketplace", "Electronics")
        cycle_rejected = False
    except ValueError:
        cycle_rejected = True
    dynamic_trace.append({"operation": "link", "parent": "Marketplace", "category": "Electronics", "status": "rejected cycle" if cycle_rejected else "unexpectedly applied"})
    leaf_parent = next((parent for child, parent in edges if child == "Electronics"), None)
    if leaf_parent:
        dynamic.cut("Electronics", leaf_parent)
        dynamic_trace.append({"operation": "cut", "parent": leaf_parent, "category": "Electronics", "status": "applied"})
    return {
        "category_revenue_inr": category_revenue,
        "category_nodes": len(values),
        "static_path": {"from": endpoints[0], "to": endpoints[1], "revenue_sum_inr": hld_total},
        "hld_oracle_passed": hld_total == naive_total,
        "hld_path_segments_visited": hld.path_segments_visited,
        "link_cut_path_sum_inr": dynamic_total,
        "link_cut_matches_hld": dynamic_total == hld_total,
        "dynamic_cycle_rejected": cycle_rejected,
        "dynamic_trace": dynamic_trace,
        "static_rebuild_note": "A topology change invalidates static HLD positions; rebuild HLD after legal category moves.",
    }


def build_phase2_payload(
    products: list[dict[str, Any]] | None = None,
    event_rows: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Run live, small correctness demonstrations over repository datasets."""
    products = products if products is not None else load_catalogue()
    event_rows = event_rows if event_rows is not None else load_event_rows()
    documents = {str(product["product_id"]): str(product["description"]) for product in products}
    views = [event["product_id"] for event in event_rows if event["event_type"] == "view"]

    category_revenue: Counter[str] = Counter()
    prices = {str(product["product_id"]): float(product["price"]) for product in products}
    categories = {str(product["product_id"]): str(product["category"]) for product in products}
    for event in event_rows:
        if event["event_type"] == "purchase":
            product_id = event["product_id"]
            category_revenue[categories[product_id]] += round(prices[product_id] * 100)

    suffix_index = SuffixArrayIndex(documents)
    automata = ProductDescriptionAutomata(documents)
    query = "noise"
    suffix_result = suffix_index.search(query)
    automata_result = automata.search(query)
    suffix_counts = Counter(row["document_id"] for row in suffix_result)
    automata_counts = {row["document_id"]: row["occurrences"] for row in automata_result}
    session7 = session7_demo(products, event_rows)
    session8 = build_snapshot_demo(products)
    session9 = suffix_demo(products)
    query9 = str(session9["query"])
    direct9 = sorted(
        (product_id, offset)
        for product_id, text in documents.items()
        for offset in range(len(text))
        if text.startswith(query9, offset)
    )
    actual9 = sorted((row["document_id"], row["offset"]) for row in session9["matches"])
    session9["acceptance_passed"] = (
        actual9 == direct9
        and not session9["absent_query_matches"]
        and session9["dc3_trace"]["algorithm_executed"] is False
    )
    session10 = automaton_demo(documents) | {
        "cross_check_query": query,
        "suffix_array_matches": dict(suffix_counts),
        "automaton_matches": automata_counts,
        "suffix_array_agrees": dict(suffix_counts) == automata_counts,
    }
    session10["acceptance_passed"] = bool(session10["suffix_array_agrees"])
    session11 = session11_demo(dict(category_revenue))
    session11["acceptance_passed"] = bool(
        session11["hld_oracle_passed"]
        and session11["link_cut_matches_hld"]
        and session11["dynamic_cycle_rejected"]
    )
    session12 = event_distinct_demo(views)
    session7["acceptance_passed"] = bool(
        session7["sales_oracle_passed"] and session7["stock_adjustment"]["oracle_passed"]
    )
    session8["acceptance_passed"] = bool(
        session8["older_versions_unchanged"]
        and session8["catalogue_version_id"] == "V2"
        and all(size > 0 for size in session8["memory_estimate_bytes"].values())
    )
    session12["acceptance_passed"] = bool(session12["oracle_passed"])
    return {
        "event_data": {
            "source": "data/events.csv",
            "total_events": len(event_rows),
            "event_type_counts": dict(Counter(row["event_type"] for row in event_rows)),
            "anonymous_user_count": len({row["anonymous_user_id"] for row in event_rows}),
            "view_event_count": len(views),
        },
        "session7": session7,
        "session8": session8,
        "session9": session9,
        "session10": session10,
        "session11": session11,
        "session12": session12,
    }
