"""Correctness checks for indirect and contiguous catalogue searches."""

import unittest

from src.hardware_analysis import ContiguousCatalogue, search_contiguous
from src.search import linear_search


class Session2RepresentationTests(unittest.TestCase):
    def test_contiguous_and_indirect_return_same_product_ids(self) -> None:
        products = [
            {"product_id": "A", "category": "Books", "price": 10.0, "stock": 2},
            {"product_id": "B", "category": "Books", "price": 20.0, "stock": 0},
            {"product_id": "C", "category": "Games", "price": 30.0, "stock": 7},
        ]
        indirect, indirect_count = linear_search(products, "Books", 10.0, 1)
        contiguous, contiguous_count = search_contiguous(
            ContiguousCatalogue.from_products(products), "Books", 10.0, 1
        )
        self.assertEqual([row["product_id"] for row in indirect], contiguous)
        self.assertEqual(indirect_count, contiguous_count)

    def test_empty_contiguous_catalogue(self) -> None:
        result, inspected = search_contiguous(
            ContiguousCatalogue.from_products([]), "Books", 10.0, 1
        )
        self.assertEqual(result, [])
        self.assertEqual(inspected, 0)


if __name__ == "__main__":
    unittest.main()
