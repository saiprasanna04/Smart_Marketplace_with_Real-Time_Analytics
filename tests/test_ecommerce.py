"""Catalogue, persistence, checkout, and storefront API acceptance checks."""

from __future__ import annotations

import base64
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import dashboard
from src.catalogue import load_catalogue
from src.marketplace import search_marketplace_products, search_suggestions
from src.marketplace_admin import MarketplaceAdminState
from src.marketplace_store import OrderStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ECommerceCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.products = load_catalogue()

    def ids(self, rows):
        return [str(row["product_id"]) for row in rows]

    def test_catalogue_has_32_unique_products_and_distinct_local_webp_photos(self) -> None:
        self.assertEqual(len(self.products), 32)
        ids = self.ids(self.products)
        images = [str(row["image"]) for row in self.products]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(images), len(set(images)))
        for image in images:
            path = PROJECT_ROOT / "storefront" / image.removeprefix("/storefront/")
            self.assertTrue(path.is_file(), image)
            payload = path.read_bytes()
            self.assertTrue(payload.startswith(b"RIFF") and payload[8:12] == b"WEBP", image)

    def test_p1016_exact_programming_laptop_example_is_in_stock_below_60000(self) -> None:
        rows, _ = search_marketplace_products(
            self.products, query="lightweight laptop for programming", max_price=60000,
            in_stock_only=True, sort="relevance",
        )
        self.assertEqual(self.ids(rows), ["P1016"])
        self.assertEqual(rows[0]["price"], 54999)
        self.assertGreater(rows[0]["stock"], 0)

    def test_search_matches_actual_brands_categories_and_demo_rating_filter(self) -> None:
        brand_rows, _ = search_marketplace_products(self.products, query="Northstar Mobile")
        category_rows, _ = search_marketplace_products(self.products, category="Books")
        rated_rows, _ = search_marketplace_products(self.products, min_rating=4.7, in_stock_only=True)
        self.assertEqual(set(self.ids(brand_rows)), {"P1017", "P1019"})
        self.assertEqual(self.ids(category_rows), ["P1032"])
        self.assertTrue(rated_rows)
        self.assertTrue(all(float(row["rating"]) >= 4.7 and int(row["stock"]) > 0 for row in rated_rows))

    def test_suggestions_are_rows_from_the_current_catalogue(self) -> None:
        suggestions = search_suggestions(self.products, "programming laptop")
        self.assertEqual([row["product_id"] for row in suggestions], ["P1016"])

    def test_admin_catalogue_edits_and_snapshots_persist_across_restart(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json"
            sample = [self.products[0]]
            admin = MarketplaceAdminState(sample, persist_path=path)
            created = admin.add_product({
                "product_id": "P9000", "title": "Local Demo Item", "description": "A unique local test product.",
                "category": "Office Supplies", "brand": "Test Brand", "price": 500,
                "original_price": 650, "stock": 5, "rating": 4.2, "popularity": 8,
                "image": "/storefront/assets/product-images/electronics/p1001-wireless-headphones.webp",
                "specifications": {"Material": "Test"},
            })
            self.assertEqual(created["brand"], "Test Brand")
            edited = admin.update_product("P9000", {"title": "Updated Local Demo Item", "price": 450, "original_price": None, "stock": 4})
            self.assertEqual(edited["price"], 450)
            self.assertNotIn("original_price", edited)
            admin.update_stock_many({"P1001": 40, "P9000": 3})
            self.assertEqual(admin.version_id, "V3")
            admin.delete_product("P9000")
            restored = MarketplaceAdminState(persist_path=path)
            self.assertEqual(restored.version_id, "V4")
            self.assertEqual([row["product_id"] for row in restored.products()], ["P1001"])
            self.assertEqual(restored.products("V0")[0]["brand"], self.products[0]["brand"])

    def test_order_store_calculates_demo_discount_delivery_and_persists(self) -> None:
        customer = {"full_name": "Sample Customer", "phone": "0000000000", "address": "1 Demo Road", "city": "Test City", "postal_code": "000000", "payment_method": "demo"}
        product = next(row for row in self.products if row["product_id"] == "P1002")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "orders.json"
            store = OrderStore(path)
            order = store.place_order(customer, [{"product_id": "P1002", "quantity": 2}], [product])
            self.assertEqual(order["subtotal"], 1198.0)
            self.assertEqual(order["discount"], 400.0)
            self.assertEqual(order["delivery"], 99.0)
            self.assertEqual(order["total"], 1297.0)
            store.add(order)
            reloaded = OrderStore(path)
            self.assertEqual(reloaded.get_order(order["order_id"])["total"], 1297.0)
            with self.assertRaisesRegex(ValueError, "only 118 units"):
                reloaded.place_order(customer, [{"product_id": "P1002", "quantity": 119}], [product])


class StorefrontApiAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.old_admin = dashboard.ADMIN_STATE
        cls.old_orders = dashboard.ORDER_STORE
        data = Path(cls.temp.name)
        dashboard.ADMIN_STATE = MarketplaceAdminState(load_catalogue(), persist_path=data / "catalogue.json")
        dashboard.ORDER_STORE = OrderStore(data / "orders.json")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard.DashboardHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        dashboard.ADMIN_STATE = cls.old_admin
        dashboard.ORDER_STORE = cls.old_orders
        cls.temp.cleanup()

    def fetch(self, path: str, method: str = "GET", body: object | None = None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            response = urlopen(request, timeout=4)
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))
        return response.status, response.read()

    def test_search_suggestions_local_photo_checkout_admin_crud_and_analytics(self) -> None:
        status, admin_payload = self.fetch("/api/admin/data")
        self.assertEqual(status, 200, admin_payload)
        status, response = self.fetch("/api/marketplace/products?query=lightweight+laptop+for+programming&max_price=60000&in_stock=true&sort=relevance")
        self.assertEqual(status, 200)
        self.assertEqual([row["product_id"] for row in json.loads(response)["products"]], ["P1016"])
        status, response = self.fetch("/api/marketplace/suggestions?q=programming+laptop")
        self.assertEqual(json.loads(response)["suggestions"][0]["product_id"], "P1016")
        status, image = self.fetch("/storefront/assets/product-images/electronics/p1016-programming-laptop.webp")
        self.assertEqual(status, 200)
        self.assertTrue(image.startswith(b"RIFF") and image[8:12] == b"WEBP")

        upload = base64.b64encode(image).decode("ascii")
        product = {"product_id": "P9000", "title": "API Test Product", "brand": "Test Brand", "description": "Unique API acceptance product.", "category": "Books", "price": 399, "original_price": 499, "stock": 8, "rating": 4.1, "popularity": 3, "created_at": "2026-11-01", "specifications": {"Format": "Test"}, "image_data": f"data:image/webp;base64,{upload}"}
        status, response = self.fetch("/api/admin/products", "POST", product)
        self.assertEqual(status, 201, response)
        created = json.loads(response)["product"]
        self.assertEqual(created["brand"], "Test Brand")
        self.assertEqual(self.fetch(created["image"])[0], 200)

        status, response = self.fetch("/api/admin/products/P9000", "PUT", {"title": "Edited API Test Product", "price": 349, "stock": 6, "original_price": None, "category": "Office Supplies"})
        self.assertEqual(status, 200, response)
        self.assertEqual(json.loads(response)["product"]["price"], 349)
        status, response = self.fetch("/api/marketplace/products?query=Edited+API+Test+Product")
        self.assertEqual(json.loads(response)["products"][0]["product_id"], "P9000")

        customer = {"full_name": "Browser Test Customer", "phone": "0000000000", "address": "2 Test Lane", "city": "Test City", "postal_code": "123456", "payment_method": "cash_on_delivery"}
        status, response = self.fetch("/api/orders", "POST", {"customer": customer, "items": [{"product_id": "P1002", "quantity": 2}]})
        self.assertEqual(status, 201, response)
        order = json.loads(response)["order"]
        self.assertEqual(order["total"], 1297.0)
        self.assertEqual(self.fetch(f"/api/orders/{order['order_id']}")[0], 200)
        status, analytics = self.fetch("/api/admin/storefront")
        self.assertEqual(json.loads(analytics)["analytics"]["order_count"], 1)
        self.assertEqual(json.loads(analytics)["analytics"]["sales_inr"], 1297.0)

        status, response = self.fetch("/api/admin/products/P9000", "DELETE")
        self.assertEqual(status, 200)
        self.assertEqual(self.fetch("/api/marketplace/products/P9000")[0], 404)
        data = Path(self.temp.name)
        restored = MarketplaceAdminState(persist_path=data / "catalogue.json")
        self.assertNotIn("P9000", [row["product_id"] for row in restored.products()])
        self.assertEqual(OrderStore(data / "orders.json").list_orders()[0]["order_id"], order["order_id"])


if __name__ == "__main__":
    unittest.main()
