"""Checks customer catalogue search against the real starter product CSV."""

import unittest

from src.marketplace import load_marketplace_catalogue, search_marketplace_products
from src.session1 import linear_search_in_stock_below_price


class MarketplaceSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.products = load_marketplace_catalogue()

    def ids(self, products):
        return [str(product["product_id"]) for product in products]

    def test_storefront_loads_original_validated_catalogue(self) -> None:
        self.assertEqual(len(self.products), 32)
        self.assertEqual(len(self.ids(self.products)), len(set(self.ids(self.products))))
        self.assertTrue(all("version" in product for product in self.products))

    def test_literal_search_checks_title_and_description_case_insensitively(self) -> None:
        title_matches, _ = search_marketplace_products(self.products, query="65w")
        description_matches, _ = search_marketplace_products(
            self.products, query="ADAPTIVE NOISE CANCELLATION"
        )
        self.assertEqual(self.ids(title_matches), ["P1003"])
        self.assertEqual(self.ids(description_matches), ["P1001"])

    def test_category_and_price_filters_are_applied_exactly(self) -> None:
        matches, _ = search_marketplace_products(
            self.products,
            category="Home & Kitchen",
            price_below=1900.0,
            min_price=1000.0,
        )
        self.assertEqual(self.ids(matches), ["P1010", "P1014"])
        self.assertNotIn("P1002", self.ids(matches))

    def test_in_stock_filter_reuses_session1_search(self) -> None:
        actual, counts = search_marketplace_products(
            self.products, in_stock_only=True, price_below=30.0
        )
        expected, _ = linear_search_in_stock_below_price(self.products, 30.0)
        self.assertEqual(self.ids(actual), self.ids(expected))
        self.assertIsNotNone(counts)
        self.assertNotIn("P1013", self.ids(actual))

    def test_empty_results_are_empty_and_price_ceiling_is_strict(self) -> None:
        absent, _ = search_marketplace_products(self.products, query="not-a-real-item")
        boundary, _ = search_marketplace_products(self.products, price_below=599.0)
        self.assertEqual(absent, [])
        self.assertNotIn("P1002", self.ids(boundary))  # Exactly at the exclusive ceiling.

    def test_multi_term_project_query_returns_complete_local_match_with_filters(self) -> None:
        matches, counts = search_marketplace_products(
            self.products,
            query="lightweight laptop for programming",
            price_below=60000,
            in_stock_only=True,
            sort="relevance",
        )
        self.assertEqual(self.ids(matches), ["P1016"])
        self.assertLess(float(matches[0]["price"]), 60000)
        self.assertGreater(int(matches[0]["stock"]), 0)
        self.assertTrue(all("relevance_score" in product for product in matches))
        self.assertTrue(all(product["product_id"] in self.ids(self.products) for product in matches))
        self.assertIsNotNone(counts)


if __name__ == "__main__":
    unittest.main()
