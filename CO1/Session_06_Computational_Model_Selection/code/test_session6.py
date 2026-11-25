"""Correctness checks for category-indexed and batched search variants."""

import unittest

from src.hardware_analysis import (
    ContiguousCatalogue,
    batch_search_contiguous,
)
from src.search import (
    CategoryIndex,
    batch_category_search,
    batch_linear_search,
    linear_search,
)


class Session6SearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [
            {"product_id": "A", "category": "Books", "price": 10.0, "stock": 2},
            {"product_id": "B", "category": "Books", "price": 20.0, "stock": 0},
            {"product_id": "C", "category": "Games", "price": 30.0, "stock": 7},
        ]
        self.queries = [("Books", 10.0, 1), ("Games", 40.0, 1), ("Missing", 5.0, 1)]

    def ids(self, groups):
        return [[row["product_id"] for row in group] for group in groups]

    def test_category_index_matches_linear_queries(self) -> None:
        index = CategoryIndex(self.products)
        for query in self.queries:
            linear, _ = linear_search(self.products, *query)
            indexed, _ = index.search(*query)
            self.assertEqual(self.ids([linear]), self.ids([indexed]))

    def test_batched_searches_match_individual_searches(self) -> None:
        expected = [linear_search(self.products, *query)[0] for query in self.queries]
        linear_batch, _ = batch_linear_search(self.products, self.queries)
        indexed_batch, _ = batch_category_search(CategoryIndex(self.products), self.queries)
        contiguous_batch, _ = batch_search_contiguous(
            ContiguousCatalogue.from_products(self.products), self.queries
        )
        expected_ids = self.ids(expected)
        self.assertEqual(self.ids(linear_batch), expected_ids)
        self.assertEqual(self.ids(indexed_batch), expected_ids)
        self.assertEqual(contiguous_batch, expected_ids)


if __name__ == "__main__":
    unittest.main()
