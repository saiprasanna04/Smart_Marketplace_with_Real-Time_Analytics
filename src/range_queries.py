"""Range-query structures used by Session 7.

All public ranges are zero-based and half-open: ``[left, right)``.  Both
structures expose small operation counters so the dashboard can show work
performed by the Python implementation rather than inferred timings.
"""

from __future__ import annotations

from collections.abc import Sequence


def _validate_range(length: int, left: int, right: int) -> None:
    if left < 0 or right < left or right > length:
        raise IndexError(f"expected 0 <= left <= right <= {length}")


class FenwickTree:
    """Fenwick tree with point-add, prefix-sum, and range-sum operations."""

    def __init__(self, values: Sequence[int | float]) -> None:
        self._values: list[int | float] = [0] * len(values)
        self._tree: list[int | float] = [0] * (len(values) + 1)
        self.operations = 0
        for index, value in enumerate(values):
            self.point_add(index, value)
        self.operations = 0

    def __len__(self) -> int:
        return len(self._values)

    @property
    def values(self) -> tuple[int | float, ...]:
        return tuple(self._values)

    def point_add(self, index: int, delta: int | float) -> None:
        if not 0 <= index < len(self):
            raise IndexError("Fenwick point index is out of range")
        self._values[index] += delta
        cursor = index + 1
        while cursor < len(self._tree):
            self._tree[cursor] += delta
            self.operations += 1
            cursor += cursor & -cursor

    def point_update(self, index: int, value: int | float) -> None:
        if not 0 <= index < len(self):
            raise IndexError("Fenwick point index is out of range")
        self.point_add(index, value - self._values[index])

    def prefix_sum(self, end_exclusive: int) -> int | float:
        """Sum positions ``[0, end_exclusive)``; zero is a valid endpoint."""
        if not 0 <= end_exclusive <= len(self):
            raise IndexError("Fenwick prefix endpoint is out of range")
        result: int | float = 0
        cursor = end_exclusive
        while cursor:
            result += self._tree[cursor]
            self.operations += 1
            cursor -= cursor & -cursor
        return result

    def range_sum(self, left: int, right: int) -> int | float:
        _validate_range(len(self), left, right)
        return self.prefix_sum(right) - self.prefix_sum(left)


class LazySegmentTree:
    """Lazy segment tree supporting range-add and range-sum in O(log n)."""

    def __init__(self, values: Sequence[int | float]) -> None:
        self._length = len(values)
        self._sum: list[int | float] = [0] * max(1, 4 * self._length)
        self._lazy: list[int | float] = [0] * max(1, 4 * self._length)
        self.operations = 0
        if self._length:
            self._build(1, 0, self._length, values)
        self.operations = 0

    def __len__(self) -> int:
        return self._length

    def _build(self, node: int, start: int, end: int, values: Sequence[int | float]) -> None:
        if end - start == 1:
            self._sum[node] = values[start]
            return
        middle = (start + end) // 2
        self._build(node * 2, start, middle, values)
        self._build(node * 2 + 1, middle, end, values)
        self._sum[node] = self._sum[node * 2] + self._sum[node * 2 + 1]

    def _apply(self, node: int, start: int, end: int, delta: int | float) -> None:
        self._sum[node] += (end - start) * delta
        self._lazy[node] += delta

    def _push(self, node: int, start: int, end: int) -> None:
        pending = self._lazy[node]
        if pending and end - start > 1:
            middle = (start + end) // 2
            self._apply(node * 2, start, middle, pending)
            self._apply(node * 2 + 1, middle, end, pending)
            self._lazy[node] = 0

    def range_add(self, left: int, right: int, delta: int | float) -> None:
        """Add ``delta`` to every element in ``[left, right)``."""
        _validate_range(self._length, left, right)
        if left == right or not self._length:
            return
        self._range_add(1, 0, self._length, left, right, delta)

    def _range_add(
        self, node: int, start: int, end: int, left: int, right: int,
        delta: int | float,
    ) -> None:
        self.operations += 1
        if left <= start and end <= right:
            self._apply(node, start, end, delta)
            return
        self._push(node, start, end)
        middle = (start + end) // 2
        if left < middle:
            self._range_add(node * 2, start, middle, left, right, delta)
        if middle < right:
            self._range_add(node * 2 + 1, middle, end, left, right, delta)
        self._sum[node] = self._sum[node * 2] + self._sum[node * 2 + 1]

    def range_sum(self, left: int, right: int) -> int | float:
        """Sum all elements in ``[left, right)``; an empty range sums to zero."""
        _validate_range(self._length, left, right)
        if left == right or not self._length:
            return 0
        return self._range_sum(1, 0, self._length, left, right)

    def _range_sum(self, node: int, start: int, end: int, left: int, right: int) -> int | float:
        self.operations += 1
        if left <= start and end <= right:
            return self._sum[node]
        self._push(node, start, end)
        middle = (start + end) // 2
        result: int | float = 0
        if left < middle:
            result += self._range_sum(node * 2, start, middle, left, right)
        if middle < right:
            result += self._range_sum(node * 2 + 1, middle, end, left, right)
        return result
