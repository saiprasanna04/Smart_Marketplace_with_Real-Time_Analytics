"""Unit tests for the exact Session 1 linear search."""

import unittest

from src.search import linear_search, reference_search


def make_product(product_id: str, category: str, price: float, stock: int) -> dict[str, object]:
    return {
        "product_id": product_id,
        "title": f"Product {product_id}",
        "description": "Test product",
        "category": category,
        "price": price,
        "stock": stock,
        "version": "1.0",
    }


class LinearSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalogue = [
            make_product("P1", "Electronics", 100.0, 3),
            make_product("P2", "Electronics", 100.01, 8),
            make_product("P3", "Home", 20.0, 9),
            make_product("P4", "Electronics", 50.0, 0),
        ]

    def test_returns_matching_products_and_inspection_count(self) -> None:
        matches, inspected = linear_search(self.catalogue, "Electronics", 100.0, 1)
        self.assertEqual([product["product_id"] for product in matches], ["P1"])
        self.assertEqual(inspected, 4)

    def test_no_matching_products(self) -> None:
        matches, inspected = linear_search(self.catalogue, "Books", 100.0, 1)
        self.assertEqual(matches, [])
        self.assertEqual(inspected, 4)

    def test_empty_catalogue(self) -> None:
        matches, inspected = linear_search([], "Electronics", 100.0, 1)
        self.assertEqual(matches, [])
        self.assertEqual(inspected, 0)

    def test_price_boundary_is_inclusive(self) -> None:
        matches, _ = linear_search(self.catalogue, "Electronics", 100.0, 1)
        self.assertIn("P1", [product["product_id"] for product in matches])

    def test_out_of_stock_product_is_excluded_when_stock_is_required(self) -> None:
        matches, _ = linear_search(self.catalogue, "Electronics", 100.0, 1)
        self.assertNotIn("P4", [product["product_id"] for product in matches])

    def test_reference_oracle_agrees_with_linear_search(self) -> None:
        matches, _ = linear_search(self.catalogue, "Electronics", 100.0, 1)
        reference = reference_search(self.catalogue, "Electronics", 100.0, 1)
        self.assertEqual(
            [product["product_id"] for product in matches],
            [product["product_id"] for product in reference],
        )


if __name__ == "__main__":
    unittest.main()
