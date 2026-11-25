"""Run the local, dependency-free Smart Marketplace project dashboard."""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import mimetypes
import os
import threading
import uuid
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from src.catalogue import load_catalogue
from src.dashboard_data import (
    CATALOGUE_1000_PATH,
    HAND_TRACE_PATH,
    PROJECT_ROOT,
    build_dashboard_payload,
)
from src.marketplace import (
    search_marketplace_products,
    search_suggestions,
)
from src.marketplace_admin import MarketplaceAdminState
from src.marketplace_store import OrderStore
from src.offline_analytics import load_view_events, mo_range_distinct
from src.phase2_services import build_phase2_payload
from src.persistent_catalogue import versioned_cache_key
from src.suffix_automaton import ProductDescriptionAutomata
from src.suffix_index import SuffixArrayIndex
from src.session1 import (
    DEMO_PRICE_LIMIT,
    benchmark_session1_sizes,
    linear_search_in_stock_below_price,
    reference_in_stock_below_price,
)


DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
STOREFRONT_DIR = PROJECT_ROOT / "storefront"
REPORTS_DIR = PROJECT_ROOT / "reports"
STORE_DIR = Path(os.environ.get("SMART_MARKETPLACE_DATA_DIR", PROJECT_ROOT / "data" / "storefront-state"))
ADMIN_STATE = MarketplaceAdminState(persist_path=STORE_DIR / "catalogue.json")
ORDER_STORE = OrderStore(STORE_DIR / "orders.json")
ORDER_LOCK = threading.RLock()


class DashboardHandler(BaseHTTPRequestHandler):
    """Serve the customer storefront and local project/admin APIs."""

    server_version = "SmartMarketplaceDashboard/1.0"

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        route = parsed.path
        try:
            if route in {"/", "/index.html", "/products", "/cart", "/wishlist", "/checkout", "/orders", "/deals", "/categories"} or route.startswith(("/products/", "/product/", "/order-confirmation/")):
                self._send_file(STOREFRONT_DIR / "index.html")
            elif route == "/workspace":
                self._send_file(DASHBOARD_DIR / "index.html")
            elif route == "/admin":
                self._send_file(DASHBOARD_DIR / "admin.html")
            elif route in {"/assets/app.css", "/assets/app.js"}:
                self._send_file(DASHBOARD_DIR / route.rsplit("/", 1)[1])
            elif route in {"/assets/admin.css", "/assets/admin.js"}:
                self._send_file(DASHBOARD_DIR / route.rsplit("/", 1)[1])
            elif route in {
                "/storefront/assets/app.css",
                "/storefront/assets/app.js",
                "/storefront/assets/cart-core.js",
            }:
                self._send_file(STOREFRONT_DIR / "assets" / route.rsplit("/", 1)[1])
            elif route.startswith("/storefront/assets/product-images/"):
                relative = Path(*unquote(route.removeprefix("/storefront/assets/product-images/")).replace("\\", "/").split("/"))
                image_root = (STOREFRONT_DIR / "assets" / "product-images").resolve()
                target = (image_root / relative).resolve()
                if not target.is_relative_to(image_root):
                    self._send_json({"error": "Invalid product image path"}, status=403)
                else:
                    self._send_file(target)
            elif route == "/api/health":
                self._send_json({"ok": True})
            elif route == "/api/marketplace/home":
                self._handle_marketplace_home()
            elif route == "/api/marketplace/suggestions":
                self._handle_marketplace_suggestions(parse_qs(parsed.query))
            elif route == "/api/marketplace/products":
                self._handle_marketplace_search(parse_qs(parsed.query))
            elif route.startswith("/api/marketplace/products/"):
                self._handle_marketplace_product(route.rsplit("/", 1)[-1])
            elif route == "/api/data":
                self._send_json(build_dashboard_payload())
            elif route == "/api/admin/data":
                self._handle_admin_data()
            elif route == "/api/admin/storefront":
                self._handle_storefront_admin_data()
            elif route == "/api/admin/catalogue":
                version_id = parse_qs(parsed.query).get("version", [None])[0]
                self._send_json({"version_id": version_id or ADMIN_STATE.version_id, "products": ADMIN_STATE.products(version_id)})
            elif route == "/api/orders":
                self._send_json({"orders": ORDER_STORE.list_orders()})
            elif route.startswith("/api/orders/"):
                order = ORDER_STORE.get_order(unquote(route.removeprefix("/api/orders/")))
                if order is None:
                    self._send_json({"error": "Order was not found"}, status=404)
                else:
                    self._send_json({"order": order})
            elif route == "/api/analytics/range":
                self._handle_range_analytics(parse_qs(parsed.query))
            elif route == "/api/analytics/distinct":
                self._handle_distinct_analytics(parse_qs(parsed.query))
            elif route == "/api/search/substring":
                self._handle_substring_search(parse_qs(parsed.query))
            elif route == "/api/search":
                self._handle_search(parse_qs(parsed.query))
            elif route == "/api/benchmarks.csv":
                self._handle_benchmark_export()
            elif route == "/api/benchmarks/m2.csv":
                self._handle_m2_benchmark_export()
            elif route.startswith("/files/"):
                self._handle_report_file(route.removeprefix("/files/"))
            elif route == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            else:
                self._send_json({"error": "Not found"}, status=404)
        except (ValueError, OSError) as error:
            self._send_json({"error": str(error)}, status=400)
        except Exception as error:  # Keep API failures visible to the local UI.
            self._send_json({"error": f"Dashboard request failed: {error}"}, status=500)

    def do_POST(self) -> None:
        route = urlsplit(self.path).path
        try:
            payload = self._read_json_body()
            if route == "/api/admin/stock":
                product = ADMIN_STATE.update_stock(str(payload.get("product_id", "")), payload.get("stock"))
                self._send_json({"product": product, "version_id": ADMIN_STATE.version_id})
            elif route == "/api/admin/products":
                payload = self._apply_uploaded_image(payload)
                product = ADMIN_STATE.add_product(payload)
                self._send_json({"product": product, "version_id": ADMIN_STATE.version_id}, status=201)
            elif route == "/api/orders":
                with ORDER_LOCK:
                    order = ORDER_STORE.place_order(payload.get("customer"), payload.get("items"), ADMIN_STATE.products())
                    ORDER_STORE.add(order)
                    try:
                        ORDER_STORE._read()  # ensure the durable append completed before touching inventory
                        stock_changes = {
                            line["product_id"]: int(next(row["stock"] for row in ADMIN_STATE.products() if row["product_id"] == line["product_id"])) - int(line["quantity"])
                            for line in order["items"]
                        }
                        ADMIN_STATE.update_stock_many(stock_changes)
                    except Exception:
                        ORDER_STORE.remove(str(order["order_id"]))
                        raise
                self._send_json({"order": order}, status=201)
            elif route == "/api/admin/duplicate-check":
                self._send_json(ADMIN_STATE.check_duplicate_description(str(payload.get("description", ""))))
            else:
                self._send_json({"error": "Not found"}, status=404)
        except (ValueError, KeyError) as error:
            self._send_json({"error": str(error)}, status=400)
        except Exception as error:
            self._send_json({"error": f"Dashboard request failed: {error}"}, status=500)

    def do_PUT(self) -> None:
        route = urlsplit(self.path).path
        try:
            if not route.startswith("/api/admin/products/"):
                self._send_json({"error": "Not found"}, status=404)
                return
            product_id = unquote(route.removeprefix("/api/admin/products/"))
            payload = self._apply_uploaded_image(self._read_json_body(), product_id)
            product = ADMIN_STATE.update_product(product_id, payload)
            self._send_json({"product": product, "version_id": ADMIN_STATE.version_id})
        except (ValueError, KeyError) as error:
            self._send_json({"error": str(error)}, status=400)
        except Exception as error:
            self._send_json({"error": f"Dashboard request failed: {error}"}, status=500)

    def do_DELETE(self) -> None:
        route = urlsplit(self.path).path
        try:
            if not route.startswith("/api/admin/products/"):
                self._send_json({"error": "Not found"}, status=404)
                return
            product_id = unquote(route.removeprefix("/api/admin/products/"))
            ADMIN_STATE.delete_product(product_id)
            self._send_json({"deleted": product_id, "version_id": ADMIN_STATE.version_id})
        except (ValueError, KeyError) as error:
            self._send_json({"error": str(error)}, status=400)
        except Exception as error:
            self._send_json({"error": f"Dashboard request failed: {error}"}, status=500)

    def _apply_uploaded_image(self, payload: dict[str, object], product_id: str | None = None) -> dict[str, object]:
        image_data = payload.pop("image_data", None)
        if image_data in (None, ""):
            return payload
        if not isinstance(image_data, str) or not image_data.startswith("data:") or ";base64," not in image_data:
            raise ValueError("image upload must be a base64 data URL")
        header, encoded = image_data.split(",", 1)
        mime = header[5:].split(";", 1)[0].lower()
        extensions = {"image/webp": ".webp", "image/jpeg": ".jpg", "image/png": ".png"}
        if mime not in extensions:
            raise ValueError("uploaded photo must be WebP, JPEG, or PNG")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as error:
            raise ValueError("uploaded photo data is invalid") from error
        if not data or len(data) > 900_000:
            raise ValueError("uploaded photo must be at most 900 KB")
        valid = (
            (mime == "image/webp" and data.startswith(b"RIFF") and data[8:12] == b"WEBP")
            or (mime == "image/jpeg" and data.startswith(b"\xff\xd8\xff"))
            or (mime == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
        )
        if not valid:
            raise ValueError("uploaded photo bytes do not match the declared image type")
        filename = f"upload-{uuid.uuid4().hex}{extensions[mime]}"
        target = STOREFRONT_DIR / "assets" / "product-images" / "uploads" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        payload["image"] = f"/storefront/assets/product-images/uploads/{filename}"
        return payload

    def _read_json_body(self) -> dict[str, object]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Content-Length must be an integer") from error
        if content_length < 0 or content_length > 1_300_000:
            raise ValueError("JSON request body must be at most 1.3 MB")
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("request body must be valid UTF-8 JSON") from error
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _handle_admin_data(self) -> None:
        products = ADMIN_STATE.products()
        phase2 = build_phase2_payload(products=products)
        self._send_json(
            {
                "catalogue": {"version_id": ADMIN_STATE.version_id, "products": products},
                "analytics": phase2,
                "storefront": self._storefront_analytics(products),
                "cache_key_example": versioned_cache_key(
                    ADMIN_STATE.version_id, "wireless", {"category": "Electronics"}
                ),
            }
        )

    def _storefront_analytics(self, products: list[dict[str, object]]) -> dict[str, object]:
        orders = ORDER_STORE.list_orders()
        sold = Counter()
        for order in orders:
            for line in order.get("items", []):
                sold[str(line["product_id"])] += int(line["quantity"])
        by_category = Counter(str(row["category"]) for row in products)
        by_id = {str(row["product_id"]): row for row in products}
        best_sellers = [
            {"product_id": product_id, "title": str(by_id[product_id]["title"]), "units_sold": count}
            for product_id, count in sold.most_common(8) if product_id in by_id
        ]
        return {
            "product_count": len(products),
            "category_count": len(by_category),
            "available_stock": sum(int(row["stock"]) for row in products),
            "out_of_stock_count": sum(int(row["stock"]) == 0 for row in products),
            "order_count": len(orders),
            "sales_inr": round(sum(float(order["total"]) for order in orders), 2),
            "best_sellers": best_sellers,
            "category_distribution": [{"category": name, "count": count} for name, count in sorted(by_category.items())],
            "recent_orders": orders[:8],
        }

    def _handle_storefront_admin_data(self) -> None:
        products = ADMIN_STATE.products()
        self._send_json({"catalogue": {"version_id": ADMIN_STATE.version_id, "products": products},
                         "orders": ORDER_STORE.list_orders(),
                         "analytics": self._storefront_analytics(products)})

    def _handle_marketplace_home(self) -> None:
        products = ADMIN_STATE.products()
        popular, _ = search_marketplace_products(products, sort="popular")
        recent, _ = search_marketplace_products(products, sort="newest")
        deals, _ = search_marketplace_products(products, sort="discount_desc")
        orders = ORDER_STORE.list_orders()
        sold = Counter(str(line["product_id"]) for order in orders for line in order.get("items", []))
        best_sellers = sorted(products, key=lambda row: (-sold[str(row["product_id"])], -int(row.get("popularity", 0))))
        self._send_json({"categories": sorted({str(row["category"]) for row in products}),
                         "trending": popular[:4], "best_sellers": best_sellers[:4],
                         "recent": recent[:4], "deals": [row for row in deals if float(row.get("original_price", row["price"])) > float(row["price"])][:4]})

    def _handle_marketplace_suggestions(self, query: dict[str, list[str]]) -> None:
        q = query.get("q", [""])[0]
        self._send_json({"query": q, "suggestions": search_suggestions(ADMIN_STATE.products(), q)})

    def _handle_range_analytics(self, query: dict[str, list[str]]) -> None:
        from src.range_queries import FenwickTree

        days = build_phase2_payload()["session7"]["daily_sales"]
        try:
            left = int(query.get("start", ["2"])[0])
            right = int(query.get("end", ["9"])[0])
        except ValueError as error:
            raise ValueError("start and end must be integer day indices") from error
        if left < 0 or right < left or right > len(days):
            raise ValueError(f"range must satisfy 0 <= start <= end <= {len(days)}")
        amounts = [float(day["sales_inr"]) for day in days]
        result = FenwickTree(amounts).range_sum(left, right)
        expected = sum(amounts[left:right])
        self._send_json(
            {
                "start": left,
                "end_exclusive": right,
                "sales_inr": result,
                "oracle_passed": result == expected,
                "days": days,
            }
        )

    def _handle_distinct_analytics(self, query: dict[str, list[str]]) -> None:
        views = load_view_events(PROJECT_ROOT / "data" / "events.csv")
        product_ids = [event.product_id for event in views]
        try:
            left = int(query.get("start", ["0"])[0])
            right = int(query.get("end", [str(len(product_ids))])[0])
        except ValueError as error:
            raise ValueError("start and end must be integer event indices") from error
        result = mo_range_distinct(product_ids, [(left, right)])
        actual = result["answers"][0]
        self._send_json(
            {
                "start": left,
                "end_exclusive": right,
                "distinct_products": actual,
                "pointer_moves": result["pointer_moves"],
                "oracle_passed": actual == len(set(product_ids[left:right])),
                "view_event_count": len(product_ids),
            }
        )

    def _handle_substring_search(self, query: dict[str, list[str]]) -> None:
        text_query = query.get("q", [""])[0]
        algorithm = query.get("algorithm", ["suffix_array"])[0]
        products = ADMIN_STATE.products()
        documents = {str(row["product_id"]): str(row["description"]) for row in products}
        if algorithm == "suffix_array":
            results = SuffixArrayIndex(documents).search(text_query)
        elif algorithm == "suffix_automaton":
            results = ProductDescriptionAutomata(documents).search(text_query)
        else:
            raise ValueError("algorithm must be suffix_array or suffix_automaton")
        self._send_json(
            {
                "query": text_query,
                "algorithm": algorithm,
                "catalogue_version_id": ADMIN_STATE.version_id,
                "cache_key": versioned_cache_key(ADMIN_STATE.version_id, text_query),
                "results": results,
            }
        )

    def _handle_marketplace_search(self, query: dict[str, list[str]]) -> None:
        catalogue = ADMIN_STATE.products()
        min_price = self._optional_price(query, "min_price")
        price_below = self._optional_price(query, "price_below")
        max_price = self._optional_price(query, "max_price")
        min_rating = self._optional_price(query, "min_rating")
        in_stock_only = query.get("in_stock", ["false"])[0].casefold() in {
            "1",
            "true",
            "yes",
        }
        products, session1_counts = search_marketplace_products(
            catalogue,
            query=query.get("query", [""])[0],
            category=query.get("category", [""])[0],
            brand=query.get("brand", [""])[0],
            min_price=min_price,
            price_below=price_below,
            max_price=max_price,
            min_rating=min_rating,
            in_stock_only=in_stock_only,
            sort=query.get("sort", ["relevance" if query.get("query", [""])[0].strip() else "featured"])[0],
        )
        self._send_json(
            {
                "products": products,
                "total": len(products),
                "categories": sorted({str(product["category"]) for product in catalogue}),
                "brands": sorted({str(product.get("brand", "")) for product in catalogue if product.get("brand")}),
                "ratings": sorted({float(product.get("rating", 0)) for product in catalogue}),
                "query": query.get("query", [""])[0],
                "session1_counts": session1_counts,
            }
        )

    def _handle_marketplace_product(self, encoded_product_id: str) -> None:
        product_id = unquote(encoded_product_id)
        product = next((row for row in ADMIN_STATE.products() if str(row["product_id"]) == product_id), None)
        if product is None:
            self._send_json({"error": f"Product {product_id!r} was not found."}, status=404)
            return
        self._send_json({"product": product})

    @staticmethod
    def _optional_price(query: dict[str, list[str]], name: str) -> float | None:
        values = query.get(name)
        if not values or not values[0].strip():
            return None
        try:
            return float(values[0])
        except ValueError as error:
            raise ValueError(f"{name} must be numeric") from error

    def _handle_search(self, query: dict[str, list[str]]) -> None:
        max_price_values = query.get("max_price", [str(DEMO_PRICE_LIMIT)])
        dataset = query.get("dataset", ["hand_trace"])[0]
        try:
            max_price = float(max_price_values[0])
        except (TypeError, ValueError) as error:
            raise ValueError("max_price must be a number") from error

        if dataset == "hand_trace":
            catalogue_path = HAND_TRACE_PATH
        elif dataset == "products_1000":
            catalogue_path = CATALOGUE_1000_PATH
        else:
            raise ValueError("dataset must be hand_trace or products_1000")

        catalogue = load_catalogue(catalogue_path)
        matches, counts = linear_search_in_stock_below_price(catalogue, max_price)
        expected = reference_in_stock_below_price(catalogue, max_price)
        actual_ids = [str(product["product_id"]) for product in matches]
        expected_ids = [str(product["product_id"]) for product in expected]
        self._send_json(
            {
                "dataset": dataset,
                "dataset_size": len(catalogue),
                "price_limit": max_price,
                "matches": matches,
                "counts": counts,
                "oracle_passed": actual_ids == expected_ids,
            }
        )

    def _handle_benchmark_export(self) -> None:
        hand_trace = load_catalogue(HAND_TRACE_PATH)
        catalogue_1000 = load_catalogue(CATALOGUE_1000_PATH)
        rows = benchmark_session1_sizes(hand_trace, catalogue_1000)
        output = io.StringIO(newline="")
        fields = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        content = output.getvalue().encode("utf-8")
        self._send_bytes(
            content,
            "text/csv; charset=utf-8",
            extra_headers={
                "Content-Disposition": 'attachment; filename="session1_benchmark.csv"'
            },
        )

    def _handle_m2_benchmark_export(self) -> None:
        path = REPORTS_DIR / "M2" / "session_benchmarks.csv"
        if not path.is_file():
            self._send_json({"error": "Run benchmarks/benchmark_m2.py first to generate M2 results."}, status=404)
            return
        self._send_bytes(
            path.read_bytes(),
            "text/csv; charset=utf-8",
            extra_headers={
                "Content-Disposition": 'attachment; filename="session_benchmarks.csv"'
            },
        )

    def _handle_report_file(self, relative_path: str) -> None:
        safe_relative_path = Path(*unquote(relative_path).replace("\\", "/").split("/"))
        target = (PROJECT_ROOT / safe_relative_path).resolve()
        report_root = REPORTS_DIR.resolve()
        if not target.is_relative_to(report_root) or target.suffix.lower() not in {
            ".md",
            ".csv",
            ".svg",
            ".txt",
            ".json",
        }:
            self._send_json({"error": "Only report documents and evidence files are available."}, status=403)
            return
        self._send_file(target)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_json({"error": "File not found"}, status=404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix.lower() in {".md", ".csv", ".txt"}:
            content_type = "text/plain; charset=utf-8"
        self._send_bytes(path.read_bytes(), content_type)

    def _send_json(self, payload: object, status: int = 200) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(content, "application/json; charset=utf-8", status=status)

    def _send_bytes(
        self,
        content: bytes,
        content_type: str,
        status: int = 200,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[dashboard] {self.address_string()} - {format_string % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8501, help="local dashboard port (default: 8501)")
    args = parser.parse_args()
    if not 0 < args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Smart Marketplace dashboard running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop the local server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard server stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
