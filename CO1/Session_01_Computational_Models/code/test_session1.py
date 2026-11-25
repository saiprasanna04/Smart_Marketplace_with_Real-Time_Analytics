"""Acceptance checks for the Session 1 price-search foundation."""

import unittest

from src.catalogue import load_catalogue
from src.session1 import (
    DEMO_PRICE_LIMIT,
    benchmark_session1_sizes,
    linear_search_in_stock_below_price,
    reference_in_stock_below_price,
)


class Session1FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hand_trace = load_catalogue("data/products_hand_trace.csv")
        cls.catalogue_1000 = load_catalogue("data/products_1000.csv")

    def test_required_catalogue_sizes_are_present(self) -> None:
        self.assertEqual(len(self.hand_trace), 20)
        self.assertEqual(len(self.catalogue_1000), 1000)

    def test_search_obeys_stock_and_strict_price_limit(self) -> None:
        matches, _counts = linear_search_in_stock_below_price(
            self.hand_trace, DEMO_PRICE_LIMIT
        )
        matching_ids = {str(product["product_id"]) for product in matches}
        self.assertIn("P1018", matching_ids)  # ₹59,999.99 is below the limit.
        self.assertNotIn("P1017", matching_ids)  # Out of stock.
        self.assertNotIn("P1019", matching_ids)  # ₹60,000 is not below the limit.

    def test_operation_counts_match_actual_short_circuit_work(self) -> None:
        catalogue = [
            {"product_id": "A", "price": 10.0, "stock": 2},
            {"product_id": "B", "price": 5.0, "stock": 0},
            {"product_id": "C", "price": 10.0, "stock": 1},
        ]
        matches, counts = linear_search_in_stock_below_price(catalogue, 10.0)
        self.assertEqual([row["product_id"] for row in matches], [])
        self.assertEqual(counts["records_inspected"], 3)
        self.assertEqual(counts["stock_checks"], 3)
        self.assertEqual(counts["price_checks"], 2)
        self.assertEqual(counts["predicate_evaluations"], 5)
        self.assertEqual(counts["result_writes"], 0)
        self.assertEqual(counts["counted_operations"], 5)

    def test_matches_equal_independent_oracle_at_multiple_sizes(self) -> None:
        for catalogue in (
            self.hand_trace,
            self.catalogue_1000[:100],
            self.catalogue_1000,
        ):
            matches, _counts = linear_search_in_stock_below_price(catalogue)
            expected = reference_in_stock_below_price(catalogue)
            self.assertEqual(
                [row["product_id"] for row in matches],
                [row["product_id"] for row in expected],
            )

    def test_live_benchmark_reports_measured_rows_and_oracle_status(self) -> None:
        rows = benchmark_session1_sizes(
            self.hand_trace, self.catalogue_1000, trials=1
        )
        self.assertEqual([row["product_count"] for row in rows], [20, 100, 1000])
        for row in rows:
            self.assertTrue(row["oracle_passed"])
            self.assertEqual(row["records_inspected"], row["product_count"])
            self.assertGreater(row["memory_estimate_bytes"], 0)
            self.assertGreaterEqual(row["median_time_ms"], 0)


if __name__ == "__main__":
    unittest.main()
