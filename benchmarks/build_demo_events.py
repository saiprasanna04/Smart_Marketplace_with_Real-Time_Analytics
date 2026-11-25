"""Regenerate a fixed, anonymous marketplace event fixture for Sessions 7/12."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "events.csv"
EVENT_TYPES = (
    "search", "view", "view", "purchase", "view", "search",
    "view", "purchase", "view", "view", "search", "purchase",
)
SEARCHES = (
    "lightweight laptop for programming",
    "wireless headphones",
    "USB-C charger",
    "running shoes",
    "travel mug",
)


def generate_rows() -> list[dict[str, str]]:
    rows = []
    start = datetime(2026, 6, 1, 9, 0)
    event_number = 0
    for day in range(10):
        for slot, event_type in enumerate(EVENT_TYPES):
            event_number += 1
            timestamp = start + timedelta(days=day, minutes=slot * 37)
            product_id = f"P{1001 + ((day * 7 + slot * 3) % 15)}"
            rows.append(
                {
                    "event_id": f"E{event_number:04d}",
                    "timestamp": timestamp.isoformat(timespec="minutes"),
                    "anonymous_user_id": f"anon-{1 + (day * 2 + slot) % 8:02d}",
                    "event_type": event_type,
                    "product_id": product_id if event_type in {"view", "purchase"} else "",
                    "query": SEARCHES[(day + slot) % len(SEARCHES)] if event_type == "search" else "",
                }
            )
    return rows


def main() -> None:
    fields = ("event_id", "timestamp", "anonymous_user_id", "event_type", "product_id", "query")
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(generate_rows())
    print(f"Wrote {len(generate_rows())} simulated events to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
