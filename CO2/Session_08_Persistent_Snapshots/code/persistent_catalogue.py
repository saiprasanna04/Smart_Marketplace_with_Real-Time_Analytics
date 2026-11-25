"""Versioned catalogue snapshots using three persistence techniques."""

from __future__ import annotations

import hashlib
import json
from bisect import bisect_right
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from src.measurements import deep_size_bytes


@dataclass(frozen=True)
class ProductRecord:
    """Immutable product row; ``version`` is the product revision from CSV."""

    product_id: str
    title: str
    description: str
    category: str
    price: float
    stock: int
    version: str
    metadata_json: str = "{}"

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "ProductRecord":
        metadata = {
            str(key): value
            for key, value in row.items()
            if key not in {"product_id", "title", "description", "category", "price", "stock", "version", "catalogue_version_id"}
        }
        return cls(
            product_id=str(row["product_id"]),
            title=str(row["title"]),
            description=str(row["description"]),
            category=str(row["category"]),
            price=float(row["price"]),
            stock=int(row["stock"]),
            version=str(row["version"]),
            metadata_json=json.dumps(metadata, ensure_ascii=False, sort_keys=True),
        )

    def to_dict(self, catalogue_version_id: str | None = None) -> dict[str, Any]:
        record: dict[str, Any] = {
            "product_id": self.product_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "price": self.price,
            "stock": self.stock,
            "version": self.version,
        }
        record.update(json.loads(self.metadata_json))
        if catalogue_version_id is not None:
            record["catalogue_version_id"] = catalogue_version_id
        return record


@dataclass(frozen=True)
class _Node:
    key: str
    value: ProductRecord
    left: "_Node | None" = None
    right: "_Node | None" = None
    height: int = 1


def _height(node: _Node | None) -> int:
    return node.height if node else 0


def _make(key: str, value: ProductRecord, left: _Node | None, right: _Node | None) -> _Node:
    return _Node(key, value, left, right, 1 + max(_height(left), _height(right)))


def _balance(node: _Node, make_node=_make) -> _Node:
    factor = _height(node.left) - _height(node.right)
    if factor > 1:
        left = node.left
        assert left is not None
        if _height(left.left) < _height(left.right):
            pivot = left.right
            assert pivot is not None
            left = make_node(
                pivot.key,
                pivot.value,
                make_node(left.key, left.value, left.left, pivot.left),
                pivot.right,
            )
        pivot = left
        return make_node(
            pivot.key,
            pivot.value,
            pivot.left,
            make_node(node.key, node.value, pivot.right, node.right),
        )
    if factor < -1:
        right = node.right
        assert right is not None
        if _height(right.right) < _height(right.left):
            pivot = right.left
            assert pivot is not None
            right = make_node(
                pivot.key,
                pivot.value,
                pivot.left,
                make_node(right.key, right.value, pivot.right, right.right),
            )
        pivot = right
        return make_node(
            pivot.key,
            pivot.value,
            make_node(node.key, node.value, node.left, pivot.left),
            pivot.right,
        )
    return node


def _balanced_from_sorted(rows: list[ProductRecord], start: int, end: int) -> _Node | None:
    if start >= end:
        return None
    middle = (start + end) // 2
    row = rows[middle]
    left = _balanced_from_sorted(rows, start, middle)
    right = _balanced_from_sorted(rows, middle + 1, end)
    return _make(row.product_id, row, left, right)


def _insert_path_copy(
    node: _Node | None, product: ProductRecord
) -> tuple[_Node, int]:
    """Return a balanced updated root and count of newly allocated tree nodes."""
    copies = 0

    def make_node(key: str, value: ProductRecord, left: _Node | None, right: _Node | None) -> _Node:
        nonlocal copies
        copies += 1
        return _make(key, value, left, right)

    def insert(current: _Node | None) -> _Node:
        if current is None:
            return make_node(product.product_id, product, None, None)
        if product.product_id == current.key:
            return make_node(current.key, product, current.left, current.right)
        if product.product_id < current.key:
            child = insert(current.left)
            return _balance(make_node(current.key, current.value, child, current.right), make_node)
        child = insert(current.right)
        return _balance(make_node(current.key, current.value, current.left, child), make_node)

    return insert(node), copies


@dataclass(frozen=True)
class PersistentCatalogue:
    """AVL-backed immutable snapshot with path-copy updates."""

    version_id: str
    root: _Node | None
    product_count: int
    last_update_node_copies: int = 0

    @classmethod
    def from_products(
        cls, products: Iterable[Mapping[str, Any]], version_id: str = "V0"
    ) -> "PersistentCatalogue":
        records = sorted((ProductRecord.from_mapping(row) for row in products), key=lambda p: p.product_id)
        if len({record.product_id for record in records}) != len(records):
            raise ValueError("product IDs must be unique in a catalogue snapshot")
        return cls(version_id, _balanced_from_sorted(records, 0, len(records)), len(records))

    def get(self, product_id: str) -> ProductRecord | None:
        node = self.root
        while node is not None:
            if product_id == node.key:
                return node.value
            node = node.left if product_id < node.key else node.right
        return None

    def products(self) -> list[ProductRecord]:
        result: list[ProductRecord] = []
        stack: list[_Node] = []
        node = self.root
        while stack or node is not None:
            while node is not None:
                stack.append(node)
                node = node.left
            node = stack.pop()
            result.append(node.value)
            node = node.right
        return result

    def with_product(
        self, row: Mapping[str, Any], version_id: str
    ) -> "PersistentCatalogue":
        if not version_id or version_id == self.version_id:
            raise ValueError("a new, non-empty catalogue version ID is required")
        product = ProductRecord.from_mapping(row)
        root, copied = _insert_path_copy(self.root, product)
        old_exists = self.get(product.product_id) is not None
        return PersistentCatalogue(
            version_id,
            root,
            self.product_count if old_exists else self.product_count + 1,
            copied,
        )

    def without_product(self, product_id: str, version_id: str) -> "PersistentCatalogue":
        """Create a new immutable snapshot without one product."""
        if not version_id or version_id == self.version_id:
            raise ValueError("a new, non-empty catalogue version ID is required")
        if self.get(product_id) is None:
            raise KeyError(f"product {product_id!r} was not found")
        remaining = [row.to_dict() for row in self.products() if row.product_id != product_id]
        return PersistentCatalogue.from_products(remaining, version_id)


def versioned_cache_key(
    version_id: str, query: str, filters: Mapping[str, Any] | None = None
) -> str:
    """Stable cache key contract that includes the catalogue snapshot version."""
    if not version_id:
        raise ValueError("version_id is required for version-aware cache keys")
    canonical = json.dumps(
        {"query": query, "filters": dict(filters or {})},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    return f"catalogue:{version_id}:{digest}"


class FatNodeMap:
    """Persistence by keeping a versioned modification history at each key."""

    def __init__(self) -> None:
        self._history: dict[str, list[tuple[int, Any]]] = {}

    @staticmethod
    def _ordinal(version_id: str) -> int:
        if not version_id.startswith("V") or not version_id[1:].isdigit():
            raise ValueError("version IDs must have the form V0, V1, ...")
        return int(version_id[1:])

    def write(self, key: str, version_id: str, value: Any) -> None:
        ordinal = self._ordinal(version_id)
        history = self._history.setdefault(key, [])
        if history and ordinal <= history[-1][0]:
            raise ValueError("fat-node writes must use increasing version IDs per key")
        history.append((ordinal, value))

    def get(self, key: str, version_id: str) -> tuple[Any | None, dict[str, Any]]:
        ordinal = self._ordinal(version_id)
        history = self._history.get(key, [])
        positions = [entry[0] for entry in history]
        index = bisect_right(positions, ordinal) - 1
        trace = {
            "requested_version": version_id,
            "history_versions": [f"V{item}" for item in positions],
            "selected_history_index": index,
            "history_entries_examined_by_binary_search": max(1, len(positions).bit_length()),
        }
        if index < 0:
            return None, trace
        trace["selected_version"] = f"V{history[index][0]}"
        return history[index][1], trace


def build_snapshot_demo(products: list[dict[str, Any]]) -> dict[str, Any]:
    """Build V0/V1/V2 with copy-on-write, fat-node, and path-copy variants."""
    base = {str(row["product_id"]): dict(row) for row in products}
    changed_a = dict(base["P1001"])
    changed_a["stock"] = int(changed_a["stock"]) + 3
    changed_a["version"] = "2.0"
    changed_b = dict(base["P1002"])
    changed_b["stock"] = int(changed_b["stock"]) - 2
    changed_b["version"] = "2.0"

    cow_v0 = base
    cow_v1 = dict(cow_v0)
    cow_v1["P1001"] = changed_a
    cow_v2 = dict(cow_v1)
    cow_v2["P1002"] = changed_b

    fat = FatNodeMap()
    for key, row in base.items():
        fat.write(key, "V0", row)
    fat.write("P1001", "V1", changed_a)
    fat.write("P1002", "V2", changed_b)

    path_v0 = PersistentCatalogue.from_products(products, "V0")
    path_v1 = path_v0.with_product(changed_a, "V1")
    path_v2 = path_v1.with_product(changed_b, "V2")
    versions = {"V0": path_v0, "V1": path_v1, "V2": path_v2}
    old_a = path_v0.get("P1001")
    v1_a = path_v1.get("P1001")
    v2_a = path_v2.get("P1001")
    fat_v0, fat_trace = fat.get("P1001", "V0")
    fat_v2, _ = fat.get("P1001", "V2")
    cow_snapshots = [cow_v0, cow_v1, cow_v2]
    path_snapshots = [path_v0, path_v1, path_v2]
    fat_snapshot = fat
    memory_growth = [
        {
            "version_id": version_id,
            "copy_on_write_snapshot_entries": sum(len(snapshot) for snapshot in cow_snapshots[:index + 1]),
            "copy_on_write_estimate_bytes": deep_size_bytes(cow_snapshots[:index + 1]),
            "path_copy_shared_estimate_bytes": deep_size_bytes(path_snapshots[:index + 1]),
        }
        for index, version_id in enumerate(versions)
    ]
    return {
        "versions": [
            {
                "version_id": version_id,
                "products": snapshot.product_count,
                "P1001_stock": snapshot.get("P1001").stock if snapshot.get("P1001") else None,
                "P1002_stock": snapshot.get("P1002").stock if snapshot.get("P1002") else None,
            }
            for version_id, snapshot in versions.items()
        ],
        "older_versions_unchanged": (
            old_a is not None
            and v1_a is not None
            and v2_a is not None
            and old_a.stock == int(base["P1001"]["stock"])
            and v1_a.stock == old_a.stock + 3
            and v2_a.stock == v1_a.stock
        ),
        "copy_on_write_records_stored": sum(len(snapshot) for snapshot in (cow_v0, cow_v1, cow_v2)),
        "path_copy_nodes_created_for_updates": path_v1.last_update_node_copies + path_v2.last_update_node_copies,
        "memory_growth": memory_growth,
        "memory_estimate_bytes": {
            "copy_on_write_full_snapshot_roots": deep_size_bytes(cow_snapshots),
            "path_copy_shared_roots": deep_size_bytes(path_snapshots),
            "fat_node_histories": deep_size_bytes(fat_snapshot),
        },
        "fat_node_trace": fat_trace,
        "fat_node_v0_stock": fat_v0["stock"] if fat_v0 else None,
        "fat_node_v2_stock": fat_v2["stock"] if fat_v2 else None,
        "catalogue_version_id": path_v2.version_id,
        "example_cache_key": versioned_cache_key("V2", "laptop", {"category": "Electronics"}),
    }
