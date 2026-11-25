"""Session 7 range-structure checks against a plain Python list oracle."""

import random
import unittest

from src.range_queries import FenwickTree, LazySegmentTree


class Session7RangeQueryTests(unittest.TestCase):
    def test_fenwick_single_full_empty_and_point_updates(self) -> None:
        tree = FenwickTree([4, 7, 2, 9])
        self.assertEqual(tree.range_sum(2, 3), 2)
        self.assertEqual(tree.range_sum(0, 4), 22)
        self.assertEqual(tree.range_sum(3, 3), 0)
        tree.point_update(1, 10)
        self.assertEqual(tree.range_sum(1, 3), 12)
        tree.point_add(3, -4)
        self.assertEqual(tree.values, (4, 10, 2, 5))

    def test_segment_tree_overlapping_range_adds(self) -> None:
        tree = LazySegmentTree([1, 2, 3, 4, 5])
        tree.range_add(1, 4, 10)
        tree.range_add(2, 5, -2)
        self.assertEqual(tree.range_sum(0, 5), 39)
        self.assertEqual(tree.range_sum(1, 3), 23)
        self.assertEqual(tree.range_sum(5, 5), 0)

    def test_empty_structures_and_empty_boundary_ranges(self) -> None:
        fenwick = FenwickTree([])
        segment = LazySegmentTree([])
        self.assertEqual(fenwick.prefix_sum(0), 0)
        self.assertEqual(fenwick.range_sum(0, 0), 0)
        self.assertEqual(segment.range_sum(0, 0), 0)
        segment.range_add(0, 0, 11)
        self.assertEqual(segment.range_sum(0, 0), 0)

    def test_invalid_ranges_and_point_indices_are_rejected(self) -> None:
        fenwick = FenwickTree([1, 2])
        segment = LazySegmentTree([1, 2])
        with self.assertRaises(IndexError):
            fenwick.range_sum(-1, 1)
        with self.assertRaises(IndexError):
            segment.range_add(0, 3, 1)
        with self.assertRaises(IndexError):
            fenwick.point_add(2, 1)

    def test_random_updates_match_naive_array_oracle(self) -> None:
        rng = random.Random(712)
        values = [rng.randrange(-20, 30) for _ in range(31)]
        expected = values[:]
        fenwick = FenwickTree(values)
        segment = LazySegmentTree(values)
        for _ in range(250):
            left = rng.randrange(len(values) + 1)
            right = rng.randrange(left, len(values) + 1)
            if rng.random() < 0.48:
                delta = rng.randrange(-10, 11)
                for index in range(left, right):
                    expected[index] += delta
                segment.range_add(left, right, delta)
                if left < right:
                    # Apply the same change as individual Fenwick point updates.
                    for index in range(left, right):
                        fenwick.point_add(index, delta)
            else:
                answer = sum(expected[left:right])
                self.assertEqual(fenwick.range_sum(left, right), answer)
                self.assertEqual(segment.range_sum(left, right), answer)
        self.assertEqual(fenwick.values, tuple(expected))


if __name__ == "__main__":
    unittest.main()
