"""Session 12 Mo and square-root query checks against naive oracles."""

import random
import unittest

from src.offline_analytics import (
    SqrtRangeSum,
    event_distinct_demo,
    fixed_view_queries,
    mo_range_distinct,
    sorted_block_range_sums,
)


class Session12OfflineAnalyticsTests(unittest.TestCase):
    def test_fixed_event_ranges_match_naive_distinct_counts(self) -> None:
        product_ids = ["P1", "P2", "P1", "P3", "P3", "P4", "P2"]
        queries = [(0, 1), (0, 7), (2, 6), (7, 7), (1, 5)]
        result = mo_range_distinct(product_ids, queries)
        expected = [len(set(product_ids[left:right])) for left, right in queries]
        self.assertEqual(result["answers"], expected)
        self.assertEqual(result["pointer_moves"], result["add_operations"] + result["remove_operations"])

    def test_randomized_mo_results_match_naive(self) -> None:
        rng = random.Random(1212)
        for length in (0, 1, 13, 80):
            values = [rng.randrange(9) for _ in range(length)]
            queries = []
            for _ in range(70):
                left = rng.randrange(length + 1)
                right = rng.randrange(left, length + 1)
                queries.append((left, right))
            result = mo_range_distinct(values, queries)
            self.assertEqual(result["answers"], [len(set(values[left:right])) for left, right in queries])

    def test_sqrt_range_sum_and_sorted_block_processing(self) -> None:
        values = list(range(-30, 70))
        queries = [(0, 100), (4, 9), (23, 77), (100, 100), (5, 5)]
        structure = SqrtRangeSum(values, block_size=8)
        direct = [sum(values[left:right]) for left, right in queries]
        self.assertEqual([structure.range_sum(left, right) for left, right in queries], direct)
        offline = sorted_block_range_sums(values, queries, block_size=8)
        self.assertEqual(offline["answers"], direct)
        self.assertEqual(sorted(offline["sorted_query_indices"]), list(range(len(queries))))
        self.assertGreater(offline["block_or_element_reads"], 0)

    def test_invalid_query_ranges_and_block_sizes_rejected(self) -> None:
        with self.assertRaises(IndexError):
            mo_range_distinct([1, 2], [(0, 3)])
        with self.assertRaises(ValueError):
            mo_range_distinct([1], [(0, 1)], block_size=0)
        with self.assertRaises(ValueError):
            SqrtRangeSum([1], block_size=0)
        with self.assertRaises(IndexError):
            SqrtRangeSum([1]).range_sum(1, 0)

    def test_event_demo_checks_naive_oracle_and_boundaries(self) -> None:
        events = [f"P{index % 7}" for index in range(50)]
        demo = event_distinct_demo(events)
        self.assertTrue(demo["oracle_passed"])
        self.assertEqual(len(demo["queries"]), len(demo["distinct_product_counts"]))
        self.assertIn((50, 50), fixed_view_queries(events))


if __name__ == "__main__":
    unittest.main()
