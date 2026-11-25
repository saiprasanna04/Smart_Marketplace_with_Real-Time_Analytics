"""Square-root and Mo-style offline analytics for Session 12."""

from __future__ import annotations

import csv
import math
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.measurements import deep_size_bytes

@dataclass(frozen=True)
class ViewEvent:
    timestamp: datetime
    anonymous_user_id: str
    product_id: str
    event_id: str


def load_view_events(path: str | Path) -> list[ViewEvent]:
    """Load only valid view rows from the local simulated event CSV."""
    events: list[ViewEvent] = []
    try:
        handle = Path(path).open("r", encoding="utf-8-sig", newline="")
    except OSError as error:
        raise ValueError(f"cannot read event dataset {path!s}: {error}") from error
    with handle:
        reader = csv.DictReader(handle)
        required = {"event_id", "timestamp", "anonymous_user_id", "event_type", "product_id", "query"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("event CSV must include " + ", ".join(sorted(required)))
        for row_number, row in enumerate(reader, start=2):
            if row.get("event_type") != "view":
                continue
            try:
                timestamp = datetime.fromisoformat(row["timestamp"])
                anonymous_user_id = row["anonymous_user_id"].strip()
                product_id = row["product_id"].strip()
                event_id = row["event_id"].strip()
            except (ValueError, AttributeError, KeyError) as error:
                raise ValueError(f"invalid view event at CSV row {row_number}") from error
            if not anonymous_user_id or not product_id or not event_id:
                raise ValueError(f"view event at CSV row {row_number} is missing required values")
            events.append(ViewEvent(timestamp, anonymous_user_id, product_id, event_id))
    return events


def _validate_queries(length: int, queries: Sequence[tuple[int, int]]) -> None:
    for left, right in queries:
        if left < 0 or right < left or right > length:
            raise IndexError(f"query [{left}, {right}) is outside [0, {length})")


def mo_range_distinct(
    values: Sequence[Any], queries: Sequence[tuple[int, int]], block_size: int | None = None
) -> dict[str, Any]:
    """Answer half-open range-distinct queries with Mo's offline ordering."""
    _validate_queries(len(values), queries)
    if block_size is None:
        block_size = max(1, int(math.sqrt(max(1, len(values)))))
    if block_size <= 0:
        raise ValueError("block_size must be greater than zero")
    order = sorted(
        range(len(queries)),
        key=lambda index: (
            queries[index][0] // block_size,
            queries[index][1] if (queries[index][0] // block_size) % 2 == 0 else -queries[index][1],
        ),
    )
    frequencies: Counter[Any] = Counter()
    distinct = 0
    current_left = current_right = 0
    pointer_moves = additions = removals = 0
    answers = [0] * len(queries)

    def add(value: Any) -> None:
        nonlocal distinct, additions
        if frequencies[value] == 0:
            distinct += 1
        frequencies[value] += 1
        additions += 1

    def remove(value: Any) -> None:
        nonlocal distinct, removals
        frequencies[value] -= 1
        removals += 1
        if frequencies[value] == 0:
            distinct -= 1

    for query_index in order:
        left, right = queries[query_index]
        while current_left > left:
            current_left -= 1
            add(values[current_left])
            pointer_moves += 1
        while current_right < right:
            add(values[current_right])
            current_right += 1
            pointer_moves += 1
        while current_left < left:
            remove(values[current_left])
            current_left += 1
            pointer_moves += 1
        while current_right > right:
            current_right -= 1
            remove(values[current_right])
            pointer_moves += 1
        answers[query_index] = distinct
    return {
        "answers": answers,
        "pointer_moves": pointer_moves,
        "add_operations": additions,
        "remove_operations": removals,
        "block_size": block_size,
        "query_order": order,
        "complexity": "O((N + Q) sqrt(N)) pointer work in the standard Mo analysis.",
    }


class SqrtRangeSum:
    """Static range-sum decomposition with O(sqrt N) block storage/query work."""

    def __init__(self, values: Sequence[int | float], block_size: int | None = None) -> None:
        self.values = list(values)
        self.block_size = (
            block_size
            if block_size is not None
            else max(1, int(math.sqrt(max(1, len(values)))) + 1)
        )
        if self.block_size <= 0:
            raise ValueError("block_size must be greater than zero")
        self.block_sums = [0] * math.ceil(len(values) / self.block_size)
        for index, value in enumerate(values):
            self.block_sums[index // self.block_size] += value
        self.operations = 0

    def range_sum(self, left: int, right: int) -> int | float:
        """Sum values in the zero-based half-open range ``[left, right)``."""
        _validate_queries(len(self.values), [(left, right)])
        total: int | float = 0
        cursor = left
        while cursor < right and cursor % self.block_size:
            total += self.values[cursor]
            self.operations += 1
            cursor += 1
        while cursor + self.block_size <= right:
            total += self.block_sums[cursor // self.block_size]
            self.operations += 1
            cursor += self.block_size
        while cursor < right:
            total += self.values[cursor]
            self.operations += 1
            cursor += 1
        return total


def sorted_block_range_sums(
    values: Sequence[int | float],
    queries: Sequence[tuple[int, int]],
    block_size: int | None = None,
) -> dict[str, Any]:
    """Process ranges in sorted left-block order and report visits/comparisons."""
    _validate_queries(len(values), queries)
    block_size = (
        block_size
        if block_size is not None
        else max(1, int(math.sqrt(max(1, len(values)))) + 1)
    )
    if block_size <= 0:
        raise ValueError("block_size must be greater than zero")
    ordered = sorted(
        enumerate(queries),
        key=lambda pair: (pair[1][0] // block_size, pair[1][1]),
    )
    structure = SqrtRangeSum(values, block_size)
    answers: list[int | float] = [0] * len(queries)
    for index, (left, right) in ordered:
        answers[index] = structure.range_sum(left, right)
    return {
        "answers": answers,
        "sorted_query_indices": [index for index, _ in ordered],
        "block_size": block_size,
        "block_or_element_reads": structure.operations,
        "memory_estimate_bytes": deep_size_bytes(structure),
    }


def fixed_view_queries(view_product_ids: Sequence[str]) -> list[tuple[int, int]]:
    """Deterministic boundary and overlapping ranges for the sample event array."""
    length = len(view_product_ids)
    if not length:
        return [(0, 0)]
    first = min(10, length)
    middle = length // 2
    return [
        (0, first),
        (0, length),
        (middle, length),
        (max(0, middle - 5), min(length, middle + 8)),
        (length, length),
    ]


def event_distinct_demo(view_product_ids: Sequence[str]) -> dict[str, Any]:
    queries = fixed_view_queries(view_product_ids)
    result = mo_range_distinct(view_product_ids, queries)
    expected = [len(set(view_product_ids[left:right])) for left, right in queries]
    if result["answers"] != expected:
        raise AssertionError("Mo range-distinct result disagrees with the direct oracle")
    return {
        "view_events": len(view_product_ids),
        "product_id_array_prefix": list(view_product_ids[:24]),
        "queries": [{"left": left, "right_exclusive": right} for left, right in queries],
        "distinct_product_counts": result["answers"],
        "oracle_passed": result["answers"] == expected,
        "pointer_moves": result["pointer_moves"],
        "add_operations": result["add_operations"],
        "remove_operations": result["remove_operations"],
        "block_size": result["block_size"],
        "complexity": result["complexity"],
    }
