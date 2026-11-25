"""Assemble live dashboard data from the catalogue and existing project code."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.catalogue import load_catalogue
from src.dashboard_content import build_roadmap
from src.dynamic_buffer import DynamicEventBuffer
from src.fingerprint import FingerprintIndex
from src.phase2_services import build_phase2_payload
from src.session1 import (
    DEMO_PRICE_LIMIT,
    RAM_EXTERNAL_MEMORY_ASSUMPTIONS,
    benchmark_session1_sizes,
    linear_search_in_stock_below_price,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HAND_TRACE_PATH = PROJECT_ROOT / "data" / "products_hand_trace.csv"
CATALOGUE_1000_PATH = PROJECT_ROOT / "data" / "products_1000.csv"
VERIFICATION_PATH = PROJECT_ROOT / "reports" / "M1" / "session1_dashboard_verification.json"
M2_VERIFICATION_PATH = PROJECT_ROOT / "reports" / "M2" / "verification.json"


def _dynamic_buffer_demo() -> dict[str, object]:
    buffer = DynamicEventBuffer(initial_capacity=1)
    for event_number in range(1, 17):
        buffer.append({"event_id": f"E{event_number:02d}"})
    return {
        "events_appended": len(buffer),
        "final_capacity": buffer.capacity,
        "cumulative_copies": buffer.cumulative_copies,
        "total_actual_writes": buffer.total_actual_writes,
        "operation_log": buffer.operation_log,
    }


def _fingerprint_demo(products: list[dict[str, object]]) -> dict[str, object]:
    index = FingerprintIndex(width_bits=4)
    seen: dict[str, dict[str, object]] = {}
    for product in products:
        product_id = str(product["product_id"])
        outcome = index.add(product)
        if outcome.collision_product_ids:
            prior_id = outcome.collision_product_ids[0]
            prior = seen[prior_id]
            return {
                "fingerprint_width_bits": index.width_bits,
                "fingerprint": outcome.fingerprint,
                "product_a": {
                    "product_id": prior_id,
                    "description": prior["description"],
                },
                "product_b": {
                    "product_id": product_id,
                    "description": product["description"],
                },
                "candidate_checks": outcome.candidate_checks,
                "exact_comparisons": outcome.exact_comparisons,
                "is_duplicate": outcome.is_duplicate,
                "collision_rejected_as_duplicate": not outcome.is_duplicate,
            }
        seen[product_id] = product

    return {
        "fingerprint_width_bits": index.width_bits,
        "available": False,
        "message": "No unequal-description collision found in the current source catalogue.",
    }


def _test_status() -> dict[str, object]:
    test_paths = sorted((PROJECT_ROOT / "tests").glob("test_*.py"))
    status: dict[str, object] = {
        "command": "python -B -m pytest -q -p no:cacheprovider",
        "status": "Available; run locally to refresh verification evidence.",
        "test_files": [path.name for path in test_paths],
        "verification": None,
    }
    verification_path = M2_VERIFICATION_PATH if M2_VERIFICATION_PATH.exists() else VERIFICATION_PATH
    if verification_path.exists():
        try:
            status["verification"] = json.loads(
                verification_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            status["status"] = "Verification record is unreadable; rerun the test command."
        else:
            status["status"] = "Verified by the recorded local test run."
    return status


def _report_files() -> list[dict[str, str]]:
    phase1 = [
        {
            "label": "Session 1 baseline report",
            "path": "reports/M1/session1.md",
            "kind": "Session evidence",
            "description": "Existing computational-model analysis and baseline experiment.",
        },
        {
            "label": "Dashboard verification record",
            "path": "reports/M1/session1_dashboard_verification.json",
            "kind": "Test results",
            "description": "Recorded result from the local full unit-test run.",
        },
        {
            "label": "Session 2 benchmark",
            "path": "reports/M1/session2/session2_benchmark.csv",
            "kind": "Session evidence",
            "description": "Existing dictionary and contiguous representation measurements.",
        },
        {
            "label": "Session 3 operation log",
            "path": "reports/M1/session3/operation_log.csv",
            "kind": "Session evidence",
            "description": "Existing dynamic-buffer capacity, copy, and write log.",
        },
        {
            "label": "Session 4 collision examples",
            "path": "reports/M1/session4/session4_collision_examples.csv",
            "kind": "Session evidence",
            "description": "Existing narrow-fingerprint collision examples.",
        },
        {
            "label": "Session 5 before/after benchmark",
            "path": "reports/M1/session5/before_after_benchmark.csv",
            "kind": "Before-and-after evidence",
            "description": "Existing linear scan and category-index comparison.",
        },
        {
            "label": "Session 6 benchmark",
            "path": "reports/M1/session6/session6_benchmark.csv",
            "kind": "Session evidence",
            "description": "Existing multi-method final comparison data.",
        },
        {
            "label": "M1 final report",
            "path": "reports/M1/M1_Final_Report.md",
            "kind": "Milestone report",
            "description": "Existing M1 summary, evidence references, and acceptance checklist.",
        },
        {
            "label": "M2 final report",
            "path": "reports/M2/M2_Final_Report.md",
            "kind": "Milestone report",
            "description": "Session 7–12 implementations, tests, benchmarks, and integration review.",
        },
        {
            "label": "M2 benchmark results",
            "path": "reports/M2/session_benchmarks.csv",
            "kind": "Benchmark evidence",
            "description": "Reproducible Phase 2 comparisons with real measurements and operation counts.",
        },
        {
            "label": "M2 verification record",
            "path": "reports/M2/verification.json",
            "kind": "Test results",
            "description": "Full Python and cart test totals, syntax checks, live acceptance checks, and benchmark validation.",
        },
    ]
    phase2_sessions = [
        {
            "label": f"Session {session} implementation report",
            "path": f"reports/M2/session{session}.md",
            "kind": "Session evidence",
            "description": f"Session {session} explanation, actual measurements, and limitations.",
        }
        for session in range(7, 13)
    ]
    return phase1 + phase2_sessions


def _phase2_benchmarks() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "reports" / "M2" / "session_benchmarks.csv"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except (OSError, csv.Error):
        return []


def build_dashboard_payload(benchmark_trials: int = 7) -> dict[str, Any]:
    """Build dashboard data from the current files and executed algorithms."""
    hand_trace = load_catalogue(HAND_TRACE_PATH)
    catalogue_1000 = load_catalogue(CATALOGUE_1000_PATH)
    benchmark_rows = benchmark_session1_sizes(
        hand_trace, catalogue_1000, trials=benchmark_trials
    )
    search_results, search_counts = linear_search_in_stock_below_price(
        hand_trace, DEMO_PRICE_LIMIT
    )
    phase2 = build_phase2_payload(products=load_catalogue())
    phase2["benchmarks"] = _phase2_benchmarks()
    completion_checks = {
        session_number: bool(phase2[f"session{session_number}"]["acceptance_passed"])
        for session_number in range(7, 13)
    }
    roadmap = build_roadmap(completion_checks)
    total_sessions = sum(len(phase["sessions"]) for phase in roadmap)
    completed_sessions = sum(
        session["status"] == "completed"
        for phase in roadmap
        for session in phase["sessions"]
    )
    return {
        "project": {
            "title": "Smart Marketplace Search and Real-Time Analytics System",
            "description": (
                "An Algorithm Engineering for Data Systems project that builds "
                "and measures a marketplace search and analytics foundation."
            ),
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_percent": round(completed_sessions / total_sessions * 100, 1),
            "current_phase": 2,
            "milestone": {
                "name": "M2 · Advanced Data Structures",
                "status": "Complete" if all(completion_checks.values()) else "Active",
                "note": "Sessions 1–12 are complete when their live acceptance checks pass; Phases 3–6 remain upcoming.",
            },
        },
        "roadmap": roadmap,
        "phase2": phase2,
        "catalogue": {
            "hand_trace_count": len(hand_trace),
            "large_catalogue_count": len(catalogue_1000),
            "hand_trace": hand_trace,
            "products": catalogue_1000,
            "categories": sorted(
                {str(product["category"]) for product in catalogue_1000}
            ),
            "source": "data/products_1000.csv",
        },
        "session1": {
            "price_limit": DEMO_PRICE_LIMIT,
            "price_comparison": "strictly less than",
            "stock_rule": "stock greater than zero",
            "default_search": {
                "matches": search_results,
                "counts": search_counts,
                "dataset_size": len(hand_trace),
            },
            "benchmarks": benchmark_rows,
            "assumptions": list(RAM_EXTERNAL_MEMORY_ASSUMPTIONS),
        },
        "playground": {
            "dynamic_buffer": _dynamic_buffer_demo(),
            "fingerprint_collision": _fingerprint_demo(load_catalogue(PROJECT_ROOT / "data" / "products.csv")),
        },
        "reports": _report_files(),
        "tests": _test_status(),
    }
