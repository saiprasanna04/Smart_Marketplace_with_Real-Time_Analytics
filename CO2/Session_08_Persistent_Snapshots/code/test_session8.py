"""Session 8 checks for immutable catalogue history and version identifiers."""

import unittest

from src.catalogue import load_catalogue
from src.persistent_catalogue import (
    FatNodeMap,
    PersistentCatalogue,
    build_snapshot_demo,
    versioned_cache_key,
)


class Session8PersistentCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.products = load_catalogue()

    def test_path_copy_versions_keep_older_product_rows(self) -> None:
        v0 = PersistentCatalogue.from_products(self.products, "V0")
        original = v0.get("P1001")
        assert original is not None
        changed = original.to_dict()
        changed["stock"] = original.stock + 1
        v1 = v0.with_product(changed, "V1")
        changed_twice = changed | {"stock": int(changed["stock"]) + 2}
        v2 = v1.with_product(changed_twice, "V2")

        self.assertEqual(v0.get("P1001").stock, original.stock)
        self.assertEqual(v1.get("P1001").stock, original.stock + 1)
        self.assertEqual(v2.get("P1001").stock, original.stock + 3)
        self.assertEqual([v.version_id for v in (v0, v1, v2)], ["V0", "V1", "V2"])
        self.assertEqual(len(v2.products()), len(self.products))
        self.assertGreater(v2.last_update_node_copies, 0)

    def test_snapshot_comparison_and_fat_node_trace(self) -> None:
        demo = build_snapshot_demo(self.products)
        self.assertTrue(demo["older_versions_unchanged"])
        self.assertEqual([item["version_id"] for item in demo["versions"]], ["V0", "V1", "V2"])
        self.assertGreater(demo["copy_on_write_records_stored"], len(self.products))
        self.assertGreater(demo["path_copy_nodes_created_for_updates"], 0)
        self.assertEqual(demo["fat_node_v0_stock"], self.products[0]["stock"])
        self.assertEqual(demo["fat_node_trace"]["selected_version"], "V0")
        self.assertTrue(all(value > 0 for value in demo["memory_estimate_bytes"].values()))

    def test_fat_nodes_return_latest_value_not_after_requested_version(self) -> None:
        values = FatNodeMap()
        values.write("P1", "V0", "before")
        values.write("P1", "V2", "later")
        old_value, _ = values.get("P1", "V1")
        latest_value, trace = values.get("P1", "V9")
        self.assertEqual(old_value, "before")
        self.assertEqual(latest_value, "later")
        self.assertEqual(trace["selected_version"], "V2")

    def test_cache_key_varies_with_snapshot_and_is_stable_for_query(self) -> None:
        first = versioned_cache_key("V1", "laptop", {"category": "Electronics"})
        same = versioned_cache_key("V1", "laptop", {"category": "Electronics"})
        later = versioned_cache_key("V2", "laptop", {"category": "Electronics"})
        self.assertEqual(first, same)
        self.assertNotEqual(first, later)


if __name__ == "__main__":
    unittest.main()
