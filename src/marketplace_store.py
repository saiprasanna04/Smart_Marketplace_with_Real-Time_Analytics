"""Durable, local demo-order storage and exact checkout calculations."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


DELIVERY_THRESHOLD_MINOR = 199_900  # ₹1,999.00
DELIVERY_FEE_MINOR = 9_900  # ₹99.00


def to_minor_units(value: object) -> int:
    try:
        amount = Decimal(str(value))
    except Exception as error:
        raise ValueError("price must be numeric") from error
    if not amount.is_finite() or amount < 0:
        raise ValueError("price must be finite and non-negative")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_minor_units(value: int) -> float:
    return float(Decimal(value) / 100)


class OrderStore:
    """Store simulated orders in an atomically replaced local JSON file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])
        # Fail early on a corrupt local store so the caller can report it.
        self._read()

    def _read(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not read order store {self.path}: {error}") from error
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise ValueError("order store must contain a JSON array of order objects")
        return data

    def _write(self, orders: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(orders, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def list_orders(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(reversed(self._read()))

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        with self._lock:
            return next((row for row in reversed(self._read()) if row["order_id"] == order_id), None)

    def place_order(self, customer: object, items: object, catalogue: list[dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(customer, dict):
            raise ValueError("customer information is required")
        if not isinstance(items, list) or not items:
            raise ValueError("at least one product is required to place an order")
        customer_fields = {name: str(customer.get(name, "")).strip() for name in ("full_name", "phone", "address", "city", "postal_code")}
        if any(not customer_fields[name] for name in customer_fields):
            raise ValueError("name, phone, address, city, and postal code are required")
        payment_method = str(customer.get("payment_method", "cash_on_delivery"))
        if payment_method not in {"cash_on_delivery", "demo"}:
            raise ValueError("payment method must be cash_on_delivery or demo")

        by_id = {str(product["product_id"]): product for product in catalogue}
        normalized: dict[str, int] = {}
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("each order item must be an object")
            product_id = str(item.get("product_id", ""))
            quantity = item.get("quantity")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                raise ValueError("product quantities must be positive whole numbers")
            normalized[product_id] = normalized.get(product_id, 0) + quantity
        if any(product_id not in by_id for product_id in normalized):
            missing = next(product_id for product_id in normalized if product_id not in by_id)
            raise ValueError(f"product {missing!r} is no longer available")
        for product_id, quantity in normalized.items():
            if int(by_id[product_id]["stock"]) < quantity:
                raise ValueError(f"only {int(by_id[product_id]['stock'])} units of {product_id} are available")

        lines: list[dict[str, Any]] = []
        subtotal_minor = 0
        discount_minor = 0
        for product_id, quantity in normalized.items():
            product = by_id[product_id]
            price_minor = to_minor_units(product["price"])
            original_minor = to_minor_units(product.get("original_price", product["price"]))
            line_subtotal = price_minor * quantity
            subtotal_minor += line_subtotal
            discount_minor += max(0, original_minor - price_minor) * quantity
            lines.append({
                "product_id": product_id,
                "title": str(product["title"]),
                "brand": str(product.get("brand", "")),
                "category": str(product["category"]),
                "image": str(product.get("image", "")),
                "quantity": quantity,
                "unit_price": from_minor_units(price_minor),
                "line_total": from_minor_units(line_subtotal),
            })
        delivery_minor = 0 if subtotal_minor >= DELIVERY_THRESHOLD_MINOR else DELIVERY_FEE_MINOR
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return {
            "order_id": f"ORD-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
            "created_at": now,
            "status": "Confirmed (demo)",
            "payment_method": "Cash on delivery (demo)" if payment_method == "cash_on_delivery" else "Demo checkout",
            "customer": customer_fields,
            "items": lines,
            "item_count": sum(normalized.values()),
            "subtotal": from_minor_units(subtotal_minor),
            "discount": from_minor_units(discount_minor),
            "delivery": from_minor_units(delivery_minor),
            "total": from_minor_units(subtotal_minor + delivery_minor),
            "currency": "INR",
        }

    def add(self, order: dict[str, Any]) -> None:
        with self._lock:
            orders = self._read()
            if any(row.get("order_id") == order["order_id"] for row in orders):
                raise ValueError("order ID collision; retry checkout")
            self._write([*orders, order])

    def remove(self, order_id: str) -> None:
        with self._lock:
            orders = self._read()
            self._write([row for row in orders if row.get("order_id") != order_id])

