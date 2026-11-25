"""Run the local Smart Marketplace browser acceptance flow with Playwright."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "QA" / "END_TO_END_TEST_RESULTS.json"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run() -> dict[str, object]:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    browser_errors: list[str] = []
    request_failures: list[str] = []
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="smart-marketplace-e2e-") as data_dir:
        env = os.environ.copy()
        env["SMART_MARKETPLACE_DATA_DIR"] = data_dir
        server = subprocess.Popen(
            [sys.executable, "dashboard.py", "--port", str(port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        base = f"http://127.0.0.1:{port}"
        try:
            import urllib.request

            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError(f"Dashboard exited early with status {server.returncode}.")
                try:
                    with urllib.request.urlopen(f"{base}/api/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except Exception:
                    time.sleep(.1)
            else:
                raise RuntimeError("Dashboard did not become ready within 10 seconds.")

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(viewport={"width": 1440, "height": 1000})
                page = context.new_page()
                page.on("pageerror", lambda error: browser_errors.append(str(error)))
                page.on("console", lambda message: browser_errors.append(message.text) if message.type == "error" else None)
                page.on("requestfailed", lambda request: request_failures.append(f"{request.method} {request.url}: {request.failure}") if request.failure != "net::ERR_ABORTED" else None)

                def check(name: str, detail: str) -> None:
                    checks.append({"name": name, "status": "passed", "detail": detail})

                page.goto(base, wait_until="networkidle")
                page.get_by_role("heading", name="Good choices, delivered simply.").wait_for()
                page.locator(".product-card").first.wait_for()
                page.locator("img[data-product-image]").evaluate_all("images => images.forEach(image => image.loading = 'eager')")
                page.wait_for_load_state("networkidle", timeout=15000)
                page.screenshot(path=str(ROOT / "reports" / "QA" / "storefront-home.png"), full_page=True)
                check("homepage_and_navigation", "Homepage, header, category cards, product sections and footer rendered in Chromium.")

                page.get_by_role("link", name="Categories", exact=True).first.click()
                page.get_by_role("heading", name="All categories").wait_for()
                page.locator(".category-card").first.click()
                expect(page.locator('#filters-form [name="category"]')).not_to_have_value("")
                page.locator("[data-reset-filters]").click()
                page.get_by_role("link", name="Products", exact=True).first.click()
                page.get_by_role("heading", name="Shop all products").wait_for()
                page.locator("img[data-product-image]").evaluate_all("images => images.forEach(image => image.loading = 'eager')")
                image_results = page.locator("img[data-product-image]").evaluate_all("images => Promise.all(images.map(async image => { try { await image.decode(); return {src:image.currentSrc,loaded:image.naturalWidth>0,width:image.naturalWidth}; } catch (_error) { return {src:image.currentSrc,loaded:false,width:image.naturalWidth}; } }))")
                if len(image_results) != 32 or not all(row["loaded"] for row in image_results):
                    details = page.locator("img[data-product-image]").evaluate_all("images => images.filter(image => !image.naturalWidth).map(image => ({attribute:image.getAttribute('src'),resolved:image.src,fallback:image.dataset.fallback,complete:image.complete}))")
                    raise AssertionError(f"Expected 32 loaded product photos; got {len(image_results)} rows, failed: {details}; request failures: {request_failures}")
                check("all_product_photos_load", f"All {len(image_results)} catalogue photographs loaded as browser-decoded local images.")
                page.screenshot(path=str(ROOT / "reports" / "QA" / "product-photo-grid.png"), full_page=True)

                page.locator('#filters-form [name="category"]').select_option(label="Electronics")
                page.get_by_role("button", name="Apply filters").click()
                expect(page.locator('[data-product-card="P1001"]')).to_be_visible()
                expect(page.locator('[data-product-card="P1002"]')).to_have_count(0)
                page.locator("#sort-filter").select_option("price_desc")
                expect(page.locator(".product-card").first).to_have_attribute("data-product-card", "P1016")
                page.locator("[data-reset-filters]").click()
                expect(page.locator(".product-card")).to_have_count(32)
                page.locator('[data-product-card="P1002"] .button-secondary').click()
                page.get_by_role("heading", name="Stainless Steel Travel Mug").wait_for()
                page.locator('[data-detail-quantity="1"]').click()
                expect(page.locator("#detail-quantity")).to_have_value("2")
                page.locator("[data-use-detail-quantity]").click()
                if page.locator("#cart-count").inner_text() != "2":
                    raise AssertionError("Product detail quantity was not applied to the cart.")
                page.locator(".cart-link").click()
                expect(page.locator(".quantity-stepper span")).to_have_text("2")
                page.locator('[data-cart-change="1"]').click()
                expect(page.locator(".quantity-stepper span")).to_have_text("3")
                page.locator('[data-cart-change="-1"]').click()
                expect(page.locator(".quantity-stepper span")).to_have_text("2")
                page.locator('[data-cart-remove="P1002"]').click()
                page.get_by_role("heading", name="Your cart is empty").wait_for()
                check("catalogue_filters_sort_details_and_quantities", "Category selection, reset, price sorting, product details, detail quantity, cart quantity controls and removal updated the rendered pages.")

                search = page.locator("#header-query")
                search.fill("lightweight laptop for programming")
                search.press("Enter")
                expect(page.locator(".product-card")).to_have_count(1, timeout=10000)
                expect(page.locator('[data-product-card="P1016"]')).to_be_visible()
                check("backend_search_and_price_example", "The live search API returned only P1016 for the programming laptop example under ₹60,000.")
                await_suggestions = page.request.get(f"{base}/api/marketplace/suggestions?q=programming+laptop")
                if await_suggestions.status != 200 or await_suggestions.json()["suggestions"][0]["product_id"] != "P1016":
                    raise AssertionError("Search suggestions did not come from the P1016 catalogue record.")
                check("catalogue_search_suggestions", "Suggestions reference an actual matching catalogue product.")

                page.locator('[data-wishlist-toggle="P1016"]').click()
                if page.locator("#wishlist-count").inner_text() != "1":
                    raise AssertionError("Wishlist count did not update.")
                page.reload(wait_until="networkidle")
                if page.locator("#wishlist-count").inner_text() != "1":
                    raise AssertionError("Wishlist did not persist through reload.")
                page.locator(".main-nav a[href='/products']").click()
                page.locator('[data-product-card="P1016"] [data-add-to-cart]').click()
                if page.locator("#cart-count").inner_text() != "1":
                    raise AssertionError("Cart add action did not update its count.")
                page.reload(wait_until="networkidle")
                if page.locator("#cart-count").inner_text() != "1":
                    raise AssertionError("Cart did not persist through reload.")
                page.locator(".wishlist-link").click()
                page.locator("[data-move-to-cart='P1016']").click()
                if page.locator("#wishlist-count").inner_text() != "0" or page.locator("#cart-count").inner_text() != "2":
                    raise AssertionError("Move-to-cart did not update both saved collections.")
                page.locator(".cart-link").click()
                page.locator("[data-cart-remove='P1016']").click()
                page.get_by_role("heading", name="Your cart is empty").wait_for()
                check("cart_wishlist_and_empty_state", "Cart and wishlist persist locally, quantity count updates, move-to-cart works, and remove shows the empty state.")

                page.locator(".main-nav a[href='/products']").click()
                page.locator('[data-product-card="P1002"] [data-add-to-cart]').click()
                page.locator('[data-product-card="P1002"] [data-add-to-cart]').click()
                page.locator(".cart-link").click()
                page.locator(".cart-summary").get_by_text("₹1,297.00").wait_for()
                page.get_by_role("link", name="Continue to checkout").click()
                page.get_by_role("heading", name="Delivery details").wait_for()
                details = {"full_name": "E2E Sample", "phone": "0000000000", "address": "3 Test Street", "city": "Test City", "postal_code": "123456"}
                for name, value in details.items():
                    page.locator(f'[name="{name}"]').fill(value)
                page.get_by_role("button", name="Place demo order · ₹1,297.00").click()
                page.get_by_role("heading", name="Thank you, E2E Sample").wait_for()
                order_id = page.locator(".order-head strong").inner_text()
                page.locator(".main-nav a[href='/orders']").click()
                page.get_by_text(order_id, exact=True).wait_for()
                check("checkout_and_persistent_orders", f"Simulated checkout created {order_id}; ₹99 delivery and order history were verified.")

                page.goto(f"{base}/admin", wait_until="networkidle")
                if not page.get_by_role("heading", name="Live demo storefront analytics").is_visible(timeout=5000):
                    raise AssertionError("Admin page did not render its storefront panel: " + page.locator("main").inner_text())
                expect(page.locator("#category-chart .category-bar-row")).not_to_have_count(0)
                expect(page.locator("#sales-chart .sales-bar")).not_to_have_count(0)
                expect(page.locator("#session-status .status")).to_have_count(6)
                page.locator('#duplicate-check [name="description"]').fill("Over-ear Bluetooth headphones with adaptive noise cancellation and 30-hour battery life.")
                page.get_by_role("button", name="Check description").click()
                page.get_by_text("Exact description already listed").wait_for()
                page.locator('#sales-range [name="start"]').fill("0")
                page.locator('#sales-range [name="end"]').fill("3")
                page.get_by_role("button", name="Query range").click()
                page.get_by_text("[0, 3):", exact=False).wait_for()
                page.locator('#distinct-range [name="start"]').fill("0")
                page.locator('#distinct-range [name="end"]').fill("5")
                page.get_by_role("button", name="Count distinct").click()
                page.get_by_text("distinct product IDs", exact=False).wait_for()
                page.locator('#substring-search [name="q"]').fill("wireless")
                page.get_by_role("button", name="Search descriptions").click()
                page.get_by_text("document matches", exact=False).wait_for()
                page.locator("#catalogue-filter").fill("P1001")
                stock_row = page.locator('tr[data-product="P1001"]')
                stock_row.locator('[name="stock"]').fill("43")
                stock_row.locator('[data-stock-form] button').click()
                expect(page.locator('tr[data-product="P1001"] [name="stock"]')).to_have_value("43")
                check("admin_stock_duplicate_and_analytics_controls", "Duplicate check, sales range, view-event range, phrase search, charts, six session statuses, and inline inventory save responded with live results.")
                page.locator("#catalogue-filter").fill("P9100")
                editor = page.locator("#product-editor")
                values = {"product_id":"P9100","title":"Browser Test Product","brand":"Test House","description":"A unique browser acceptance test item.","category":"Books","price":"299","original_price":"399","stock":"7","rating":"4.2","popularity":"4","created_at":"2026-11-01","specifications":'{"Format":"Paperback"}'}
                for name, value in values.items(): editor.locator(f'[name="{name}"]').fill(value)
                editor.locator('[name="image_file"]').set_input_files(str(ROOT / "storefront" / "assets" / "product-images" / "books" / "p1032-short-story-collection.webp"))
                editor.get_by_role("button", name="Add to catalogue").click()
                page.get_by_text("Product added in catalogue", exact=False).wait_for()
                page.locator("#catalogue-filter").fill("P9100")
                row = page.locator('tr[data-product="P9100"]')
                row.wait_for()
                image_path_response = page.request.get(f"{base}/api/marketplace/products/P9100")
                created_product = image_path_response.json()["product"]
                photo_response = page.request.get(f"{base}{created_product['image']}")
                if photo_response.status != 200 or not photo_response.body().startswith(b"RIFF"):
                    raise AssertionError("Admin image upload did not create a valid locally served WebP.")
                row.get_by_role("button", name="Edit").click()
                page.locator("#product-editor [name='title']").fill("Edited Browser Test Product")
                page.locator("#product-editor [name='price']").fill("249")
                page.get_by_role("button", name="Save product").click()
                page.get_by_text("Product updated in catalogue", exact=False).wait_for()
                page.locator("#catalogue-filter").fill("P9100")
                row = page.locator('tr[data-product="P9100"]')
                page.once("dialog", lambda dialog: dialog.accept())
                row.get_by_role("button", name="Delete").click()
                row.wait_for(state="detached")
                check("admin_create_upload_edit_delete_and_analytics", "Admin added a product, uploaded and served a local photo, edited price/title, and deleted it; storefront analytics rendered from local catalogue and order data.")

                page.goto(base, wait_until="networkidle")
                for width in (1440, 1024, 768, 390):
                    page.set_viewport_size({"width": width, "height": 920})
                    overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                    if overflow:
                        raise AssertionError(f"Storefront homepage has horizontal overflow at {width}px.")
                    page.locator(".main-nav").is_visible() if width > 820 else None
                page.set_viewport_size({"width": 390, "height": 844})
                page.locator("#mobile-nav-toggle").click()
                if not page.locator(".main-nav.open").is_visible():
                    raise AssertionError("Mobile navigation did not open.")
                page.locator(".main-nav a[href='/deals']").click()
                page.get_by_role("heading", name="Special offers").wait_for()
                check("responsive_layout_and_mobile_navigation", "Home has no horizontal overflow at 1440, 1024, 768 and 390 px; mobile navigation opens and navigates.")

                browser.close()

        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)

    if browser_errors:
        raise AssertionError("Browser console/page errors: " + " | ".join(browser_errors))
    if request_failures:
        raise AssertionError("Browser requests failed: " + " | ".join(request_failures))
    return {"status": "passed", "browser": "Playwright Chromium", "checks": checks,
            "browser_console_errors": browser_errors, "failed_requests": request_failures,
            "catalogue_photo_count": 32}


if __name__ == "__main__":
    result: dict[str, object]
    try:
        result = run()
    except Exception as error:
        result = {"status": "failed", "error": f"{type(error).__name__}: {error}", "checks": [],
                  "browser_console_errors": [], "failed_requests": [], "catalogue_photo_count": 32}
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        raise
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=True))
