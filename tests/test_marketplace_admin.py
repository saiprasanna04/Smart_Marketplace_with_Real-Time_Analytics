"""Local catalogue manager tests for versioning, stock, and duplicates."""

import unittest

from src.catalogue import load_catalogue
from src.marketplace_admin import MarketplaceAdminState


class MarketplaceAdminTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = load_catalogue()
        self.admin = MarketplaceAdminState(self.products)

    def test_stock_update_creates_version_and_preserves_v0(self) -> None:
        old_stock = int(self.products[0]["stock"])
        updated = self.admin.update_stock("P1001", old_stock + 5)
        self.assertEqual(updated["catalogue_version_id"], "V1")
        self.assertEqual(self.admin.products("V0")[0]["stock"], old_stock)
        self.assertEqual(self.admin.products("V1")[0]["stock"], old_stock + 5)

    def test_stock_validation_and_missing_product(self) -> None:
        with self.assertRaises(ValueError):
            self.admin.update_stock("P1001", -1)
        with self.assertRaises(KeyError):
            self.admin.update_stock("missing", 0)

    def test_exact_duplicate_check_uses_fingerprint_then_text(self) -> None:
        original = str(self.products[0]["description"])
        duplicate = self.admin.check_duplicate_description(original)
        different = self.admin.check_duplicate_description(original + " updated")
        self.assertTrue(duplicate["is_duplicate"])
        self.assertIn("P1001", duplicate["duplicate_product_ids"])
        self.assertFalse(different["is_duplicate"])

    def test_product_creation_versions_catalogue_and_rejects_duplicate(self) -> None:
        created = self.admin.add_product({
            "product_id": "P9000", "title": "New Item", "description": "New description",
            "category": "Office Supplies", "price": "12.50", "stock": "6",
        })
        self.assertEqual(created["catalogue_version_id"], "V1")
        self.assertEqual(self.admin.products()[-1]["product_id"], "P9000")
        with self.assertRaises(ValueError):
            self.admin.add_product({
                "product_id": "P9001", "title": "Duplicate", "description": self.products[0]["description"],
                "category": "Electronics", "price": 1, "stock": 1,
            })


if __name__ == "__main__":
    unittest.main()
