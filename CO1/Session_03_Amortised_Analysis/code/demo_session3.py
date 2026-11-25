"""Append a reproducible sequence and save the dynamic-buffer operation log."""

import csv
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dynamic_buffer import DynamicEventBuffer


OUTPUT_PATH = PROJECT_ROOT / "reports" / "M1" / "session3" / "operation_log.csv"


def main() -> int:
    buffer = DynamicEventBuffer(initial_capacity=1)
    for event_number in range(1, 17):
        buffer.append({"event_id": f"E{event_number:02d}"})

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "appended_events",
        "capacity",
        "copies_this_append",
        "cumulative_copies",
        "writes_this_append",
        "total_actual_writes",
    ]
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(buffer.operation_log)

    print("append,capacity,copies_now,copies_total,writes_now,writes_total")
    for row in buffer.operation_log:
        print(
            f"{row['appended_events']},{row['capacity']},{row['copies_this_append']},"
            f"{row['cumulative_copies']},{row['writes_this_append']},"
            f"{row['total_actual_writes']}"
        )
    print(f"Stored events: {len(buffer.to_list())}; final capacity: {buffer.capacity}")
    print(f"Saved: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
