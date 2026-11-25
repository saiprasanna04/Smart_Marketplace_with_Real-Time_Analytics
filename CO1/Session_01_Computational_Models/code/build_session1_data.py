"""Build the fixed Session 1 hand-trace and 1,000-product CSV datasets."""

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.catalogue import REQUIRED_FIELDS, load_catalogue
from src.workload import generate_scaled_catalogue


HAND_TRACE_ADDITIONS = (
    {
        "product_id": "P1016",
        "title": "Budget Wireless Mouse",
        "description": "Compact wireless mouse with adjustable sensitivity and a USB receiver.",
        "category": "Electronics",
        "price": 899.0,
        "stock": 23,
        "version": "1.0",
    },
    {
        "product_id": "P1017",
        "title": "Foldable Monitor Stand",
        "description": "Portable stand that raises a monitor and folds flat for storage.",
        "category": "Office Supplies",
        "price": 2450.0,
        "stock": 0,
        "version": "1.0",
    },
    {
        "product_id": "P1018",
        "title": "Creator Laptop",
        "description": "Performance laptop with a high-resolution display and 32 GB memory.",
        "category": "Electronics",
        "price": 59999.99,
        "stock": 2,
        "version": "1.0",
    },
    {
        "product_id": "P1019",
        "title": "Workstation Desktop",
        "description": "Desktop workstation configured for professional creative software.",
        "category": "Electronics",
        "price": 60000.0,
        "stock": 5,
        "version": "1.0",
    },
    {
        "product_id": "P1020",
        "title": "USB-C Earbuds",
        "description": "Wired in-ear headphones with an inline microphone and USB-C plug.",
        "category": "Electronics",
        "price": 1999.0,
        "stock": 60,
        "version": "1.0",
    },
)


def write_products(path: Path, products: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=REQUIRED_FIELDS)
        writer.writeheader()
        writer.writerows(products)


def main() -> int:
    source = load_catalogue(PROJECT_ROOT / "data" / "products.csv")
    hand_trace = source + [dict(product) for product in HAND_TRACE_ADDITIONS]
    large_catalogue = generate_scaled_catalogue(source, 1000)
    write_products(PROJECT_ROOT / "data" / "products_hand_trace.csv", hand_trace)
    write_products(PROJECT_ROOT / "data" / "products_1000.csv", large_catalogue)
    print(f"Wrote hand-trace fixture: {len(hand_trace)} records")
    print(f"Wrote deterministic catalogue: {len(large_catalogue)} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
