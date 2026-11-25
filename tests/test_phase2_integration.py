"""Integration checks joining advanced algorithms to catalogue and event data."""

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlencode
from http.server import ThreadingHTTPServer

import dashboard
from dashboard import DashboardHandler
from src.marketplace_admin import MarketplaceAdminState
from src.marketplace_store import OrderStore
from src.phase2_services import build_phase2_payload, load_event_rows


class QuietHandler(DashboardHandler):
    def log_message(self, format_string, *args):
        return


class Phase2DataIntegrationTests(unittest.TestCase):
    def test_simulated_events_use_anonymous_schema_and_valid_types(self) -> None:
        events = load_event_rows()
        self.assertEqual(len(events), 120)
        self.assertTrue({row["event_type"] for row in events} <= {"search", "view", "purchase"})
        self.assertTrue(all(row["anonymous_user_id"].startswith("anon-") for row in events))
        self.assertTrue(all(row["query"] for row in events if row["event_type"] == "search"))

    def test_phase2_services_integrate_products_and_event_analytics(self) -> None:
        payload = build_phase2_payload()
        self.assertEqual(payload["event_data"]["total_events"], 120)
        self.assertTrue(all(payload[f"session{number}"]["acceptance_passed"] for number in range(7, 13)))
        self.assertEqual(payload["session8"]["catalogue_version_id"], "V2")
        self.assertTrue(payload["session10"]["suffix_array_agrees"])
        self.assertTrue(payload["session11"]["link_cut_matches_hld"])
        self.assertTrue(payload["session12"]["oracle_passed"])


class DashboardAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.old_admin_state = dashboard.ADMIN_STATE
        cls.old_order_store = dashboard.ORDER_STORE
        cls.temp_data = tempfile.TemporaryDirectory()
        data_dir = Path(cls.temp_data.name)
        dashboard.ADMIN_STATE = MarketplaceAdminState(persist_path=data_dir / "catalogue.json")
        dashboard.ORDER_STORE = OrderStore(data_dir / "orders.json")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join(timeout=3)
        cls.server.server_close()
        dashboard.ADMIN_STATE = cls.old_admin_state
        dashboard.ORDER_STORE = cls.old_order_store
        cls.temp_data.cleanup()

    def request(self, method: str, path: str, body: object | None = None):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=10)
        encoded = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if encoded is not None else {}
        connection.request(method, path, body=encoded, headers=headers)
        response = connection.getresponse()
        content = response.read()
        result = json.loads(content) if response.getheader("Content-Type", "").startswith("application/json") else content.decode("utf-8")
        status = response.status
        connection.close()
        return status, result

    def test_customer_workspace_and_admin_routes_are_separate(self) -> None:
        status, home = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("smart<span>cart", home)
        self.assertNotIn("PROJECT WORKSPACE", home)
        status, workspace = self.request("GET", "/workspace")
        self.assertEqual(status, 200)
        self.assertIn("PROJECT WORKSPACE", workspace)
        status, admin = self.request("GET", "/admin")
        self.assertEqual(status, 200)
        self.assertIn("CATALOGUE &amp; ANALYTICS", admin)

    def test_analytics_and_substring_services_return_oracle_results(self) -> None:
        status, sales = self.request("GET", "/api/analytics/range?start=2&end=9")
        self.assertEqual(status, 200)
        self.assertTrue(sales["oracle_passed"])
        status, distinct = self.request("GET", "/api/analytics/distinct?start=0&end=20")
        self.assertEqual(status, 200)
        self.assertTrue(distinct["oracle_passed"])
        query = urlencode({"q": "noise cancellation", "algorithm": "suffix_automaton"})
        status, substring = self.request("GET", f"/api/search/substring?{query}")
        self.assertEqual(status, 200)
        self.assertTrue(substring["catalogue_version_id"].startswith("V"))
        self.assertTrue(substring["results"])

    def test_admin_stock_post_updates_live_storefront_and_version(self) -> None:
        before_status, before = self.request("GET", "/api/admin/catalogue?version=V0")
        self.assertEqual(before_status, 200)
        old_stock = before["products"][0]["stock"]
        status, result = self.request("POST", "/api/admin/stock", {"product_id": "P1001", "stock": old_stock + 1})
        self.assertEqual(status, 200)
        self.assertEqual(result["version_id"], "V1")
        current_status, current = self.request("GET", "/api/marketplace/products?query=wireless&sort=relevance")
        self.assertEqual(current_status, 200)
        product = next(row for row in current["products"] if row["product_id"] == "P1001")
        self.assertEqual(product["stock"], old_stock + 1)
        self.assertEqual(product["catalogue_version_id"], "V1")

    def test_project_search_returns_the_local_laptop_with_price_and_stock_filters(self) -> None:
        query = urlencode(
            {
                "query": "lightweight laptop for programming",
                "price_below": "60000",
                "in_stock": "true",
                "sort": "relevance",
            }
        )
        status, result = self.request("GET", f"/api/marketplace/products?{query}")
        self.assertEqual(status, 200)
        self.assertEqual([row["product_id"] for row in result["products"]], ["P1016"])
        self.assertLess(float(result["products"][0]["price"]), 60000)
        self.assertGreater(int(result["products"][0]["stock"]), 0)


if __name__ == "__main__":
    unittest.main()
