"""Versioned local catalogue manager with optional durable JSON snapshots."""

from __future__ import annotations

import math
import json
import os
import tempfile
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from src.catalogue import load_catalogue
from src.fingerprint import description_fingerprint
from src.persistent_catalogue import PersistentCatalogue


class MarketplaceAdminState:
    """Manage one local catalogue session without rewriting the source CSV."""

    def __init__(
        self,
        products: list[dict[str, Any]] | None = None,
        *,
        persist_path: str | Path | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._persist_path = Path(persist_path) if persist_path is not None else None
        if products is None and self._persist_path and self._persist_path.is_file():
            saved = json.loads(self._persist_path.read_text(encoding="utf-8"))
            self._version_number = int(saved["version_number"])
            self._snapshots = {
                version_id: PersistentCatalogue.from_products(rows, version_id)
                for version_id, rows in saved["snapshots"].items()
            }
            self._current = self._snapshots[str(saved["current_version"])]
            return
        initial = products if products is not None else load_catalogue()
        self._current = PersistentCatalogue.from_products(initial, "V0")
        self._snapshots = {"V0": self._current}
        self._version_number = 0
        self._persist()

    def _persist(self) -> None:
        if self._persist_path is None:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version_number": self._version_number,
            "current_version": self._current.version_id,
            "snapshots": {
                version_id: [row.to_dict() for row in snapshot.products()]
                for version_id, snapshot in self._snapshots.items()
            },
        }
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{self._persist_path.name}.", suffix=".tmp", dir=self._persist_path.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self._persist_path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def _publish(self, snapshot: PersistentCatalogue) -> None:
        previous_current = self._current
        self._current = snapshot
        self._version_number = int(snapshot.version_id[1:])
        self._snapshots[snapshot.version_id] = snapshot
        try:
            self._persist()
        except Exception:
            del self._snapshots[snapshot.version_id]
            self._current = previous_current
            self._version_number = int(previous_current.version_id[1:])
            raise

    @property
    def version_id(self) -> str:
        with self._lock:
            return self._current.version_id

    def _next_version(self) -> str:
        self._version_number += 1
        return f"V{self._version_number}"

    def products(self, version_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            snapshot = self._snapshots.get(version_id or self._current.version_id)
            if snapshot is None:
                raise KeyError(f"catalogue version {version_id!r} does not exist")
            return [row.to_dict(snapshot.version_id) for row in snapshot.products()]

    def update_stock(self, product_id: str, stock: int) -> dict[str, Any]:
        if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
            raise ValueError("stock must be a non-negative integer")
        with self._lock:
            current = self._current.get(product_id)
            if current is None:
                raise KeyError(f"product {product_id!r} was not found")
            version_id = f"V{self._version_number + 1}"
            row = current.to_dict() | {"stock": stock}
            self._publish(self._current.with_product(row, version_id))
            return self._current.get(product_id).to_dict(version_id)  # type: ignore[union-attr]

    def update_stock_many(self, stock_by_id: Mapping[str, int]) -> list[dict[str, Any]]:
        """Apply a set of stock changes in one versioned snapshot."""
        normalized: dict[str, int] = {}
        for product_id, stock in stock_by_id.items():
            if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
                raise ValueError("stock values must be non-negative integers")
            normalized[str(product_id)] = stock
        with self._lock:
            rows = {row.product_id: row.to_dict() for row in self._current.products()}
            missing = sorted(set(normalized) - set(rows))
            if missing:
                raise KeyError(f"products were not found: {', '.join(missing)}")
            if not normalized:
                return []
            version_id = f"V{self._version_number + 1}"
            for product_id, stock in normalized.items():
                rows[product_id]["stock"] = stock
            next_snapshot = PersistentCatalogue.from_products(rows.values(), version_id)
            self._publish(next_snapshot)
            return [next_snapshot.get(product_id).to_dict(version_id) for product_id in normalized]  # type: ignore[union-attr]

    def add_product(self, row: Mapping[str, Any]) -> dict[str, Any]:
        required = {"product_id", "title", "description", "category", "price", "stock"}
        if not required.issubset(row):
            raise ValueError("product must include " + ", ".join(sorted(required)))
        product_id = str(row["product_id"]).strip()
        title = str(row["title"]).strip()
        description = str(row["description"]).strip()
        category = str(row["category"]).strip()
        try:
            price = float(row["price"])
            stock = int(row["stock"])
        except (TypeError, ValueError) as error:
            raise ValueError("product price and stock must be numeric") from error
        if not product_id or not title or not description or not category:
            raise ValueError("product text fields cannot be blank")
        if not math.isfinite(price) or price < 0 or stock < 0:
            raise ValueError("price and stock must be finite and non-negative")
        with self._lock:
            if self._current.get(product_id) is not None:
                raise ValueError(f"product ID {product_id!r} already exists")
            duplicates = self.check_duplicate_description(description)
            if duplicates["duplicate_product_ids"]:
                raise ValueError("exact description already exists; review duplicate listings first")
            optional = {
                str(key): value for key, value in row.items()
                if key not in required | {"version", "catalogue_version_id"}
            }
            version_id = f"V{self._version_number + 1}"
            record = {
                "product_id": product_id,
                "title": title,
                "description": description,
                "category": category,
                "price": price,
                "stock": stock,
                "version": str(row.get("version", "1.0")),
                **optional,
            }
            self._publish(self._current.with_product(record, version_id))
            return self._current.get(product_id).to_dict(version_id)  # type: ignore[union-attr]

    def update_product(self, product_id: str, changes: Mapping[str, Any]) -> dict[str, Any]:
        """Replace editable product fields while retaining unspecified metadata."""
        with self._lock:
            current = self._current.get(product_id)
            if current is None:
                raise KeyError(f"product {product_id!r} was not found")
            row = current.to_dict()
            row.update({key: value for key, value in changes.items() if key not in {"product_id", "version", "catalogue_version_id"}})
            row["product_id"] = product_id
            row["title"] = str(row["title"]).strip()
            row["description"] = str(row["description"]).strip()
            row["category"] = str(row["category"]).strip()
            row["brand"] = str(row.get("brand", "")).strip()
            try:
                row["price"] = float(row["price"])
                row["stock"] = int(row["stock"])
                if row.get("original_price") not in (None, ""):
                    row["original_price"] = float(row["original_price"])
                elif "original_price" in row:
                    row.pop("original_price")
            except (TypeError, ValueError) as error:
                raise ValueError("product price, original price, and stock must be numeric") from error
            if not all(row[key] for key in ("title", "description", "category")):
                raise ValueError("title, description, and category cannot be blank")
            if not math.isfinite(row["price"]) or row["price"] < 0 or row["stock"] < 0:
                raise ValueError("price and stock must be finite and non-negative")
            original = row.get("original_price")
            if original is not None and (not math.isfinite(original) or original < row["price"]):
                raise ValueError("original price must be finite and greater than or equal to price")
            if row.get("rating") is not None:
                row["rating"] = float(row["rating"])
                if not math.isfinite(row["rating"]) or not 0 <= row["rating"] <= 5:
                    raise ValueError("rating must be between 0 and 5")
            version_id = f"V{self._version_number + 1}"
            self._publish(self._current.with_product(row, version_id))
            return self._current.get(product_id).to_dict(version_id)  # type: ignore[union-attr]

    def delete_product(self, product_id: str) -> None:
        with self._lock:
            version_id = f"V{self._version_number + 1}"
            self._publish(self._current.without_product(product_id, version_id))

    def check_duplicate_description(self, description: str) -> dict[str, Any]:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description is required")
        with self._lock:
            fingerprint = description_fingerprint(description)
            candidates = [
                product
                for product in self._current.products()
                if description_fingerprint(product.description) == fingerprint
            ]
            exact = [product for product in candidates if product.description == description]
            return {
                "fingerprint": fingerprint,
                "candidate_product_ids": [product.product_id for product in candidates],
                "duplicate_product_ids": [product.product_id for product in exact],
                "is_duplicate": bool(exact),
                "exact_comparisons": len(candidates),
                "catalogue_version_id": self._current.version_id,
            }
