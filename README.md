# Smart Marketplace Search and Real-Time Analytics System

An academic Algorithm Engineering for Data Systems project with a local Smart Cart storefront, an AEDS project workspace, and a product and order administration dashboard. The interfaces share a Python standard-library server and local product data. Checkout creates a simulated order; no payment is processed.

The storefront contains 32 sample products. Product photos are stored locally as WebP files, with Unsplash source and license links in `storefront/assets/product-images/SOURCES.json`. Prices, stock, brands, ratings, and catalogue history are demo data.

## Requirements

- Python 3.10 or newer to run the application
- Pytest for the Python test suite
- Node.js for cart-core tests and JavaScript syntax checks
- Playwright Chromium for the real-browser acceptance run

The application has no third-party runtime dependencies. Install development dependencies for tests and browser verification:

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

## Run the application on Windows PowerShell

From this directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python dashboard.py
```

Open the customer site at `http://127.0.0.1:8501`. Stop the server with `Ctrl+C`. To use another port, run `python dashboard.py --port 8513`.

## Interfaces

- `/` — Smart Cart storefront
- `/categories` — category explorer
- `/products` — catalogue search, category/brand/price/rating/stock filters, and sorting
- `/product/<id>` — product details
- `/deals` — discounted catalogue items
- `/cart` and `/wishlist` — browser-local saved items, quantity controls, and removal
- `/checkout`, `/orders`, and `/order-confirmation/<id>` — simulated checkout and local demo order history
- `/workspace` — AEDS overview, roadmap, session workspaces, algorithm playground, benchmarks, reports, and architecture
- `/admin` — persistent product management, photo upload, stock updates, order analytics, duplicate-description checks, and AEDS analytics tools

Product records load from `data/products.csv`. Admin changes are saved as versioned snapshots in `data/storefront-state/catalogue.json`; simulated orders are saved in `data/storefront-state/orders.json`. The source CSV is not overwritten. Set `SMART_MARKETPLACE_DATA_DIR` to use a different writable folder. Demo checkout details are stored locally with the order.

## Project status

- Sessions 1–6 are preserved with their existing implementations, tests, and M1 evidence.
- Sessions 7–12 have local implementations and focused oracle tests. Workspace status is based on live acceptance checks.
- Sessions 13–36 remain upcoming. Their curriculum details have not been added.
- Session 7–12 requirements in the supplied project brief were used. The separately referenced official PDF was not available in the attachment files in this workspace.

### Session 7–12 implementations

| Session | Implementation |
|---:|---|
| 7 | Fenwick point updates/prefix/range sums and lazy segment-tree range add/sum |
| 8 | Copy-on-write comparison, fat-node histories, immutable AVL path-copy snapshots, versioned cache keys |
| 9 | Prefix-doubling suffix array, Kasai LCP, document sentinels; DC3 is a labelled guided trace |
| 10 | Per-description suffix automata with suffix links, clone traces, membership, and occurrence counts |
| 11 | Heavy-light decomposition and link-cut forest path sums, links, cuts, and cycle rejection |
| 12 | Mo range-distinct processing, pointer-movement counts, and sorted-block square-root range sums |

`data/events.csv` is a deterministic 120-row simulated event stream with anonymous IDs and `search`, `view`, and `purchase` event types. Regenerate it with:

```powershell
python benchmarks\build_demo_events.py
```

## Verification

Run the full Python suite, including Sessions 1–12 and dashboard/API integration checks:

```powershell
python -B -m pytest -q -p no:cacheprovider
```

Run cart tests and JavaScript syntax checks:

```powershell
node --test tests\cart-core.test.cjs
node --check dashboard\app.js
node --check dashboard\admin.js
node --check storefront\assets\app.js
node --check storefront\assets\cart-core.js
```

Run the real Chromium storefront and admin acceptance flow:

```powershell
python scripts\run_e2e.py
```

The browser flow checks catalogue search and suggestions, all 32 local product photos, cart and wishlist persistence, simulated checkout and order history, admin product create/edit/delete and photo upload, analytics rendering, and responsive navigation. Results and screenshots are written under `reports/QA/`.

## Reproduce benchmarks and reports

Generate reproducible Sessions 7–12 benchmark rows and reports:

```powershell
python benchmarks\benchmark_m2.py --trials 5
```

This writes `reports/M2/session_benchmarks.csv`, reports for Sessions 7–12, and `reports/M2/M2_Final_Report.md`. The benchmark centre reads recorded rows and exposes CSV export.

Reproduce existing Phase 1 experiments:

```powershell
python benchmarks\benchmark_m1.py --trials 9 --block-size 64
python benchmarks\benchmark_session2.py --trials 31
python benchmarks\demo_session3.py
python benchmarks\benchmark_session4.py --trials 31
python benchmarks\profile_session5.py --trials 31
python benchmarks\benchmark_session6.py --trials 15
```

Run the Session 1 baseline directly:

```powershell
python main.py --category Electronics --max-price 100 --min-stock 1
```

## Data and measurement notes

- `data/products.csv` has 32 storefront demo products. P1016 is an in-stock programming laptop listed at ₹54,999 for the ₹60,000 search example.
- `data/products_hand_trace.csv` is the 20-record Session 1 fixture.
- `data/products_1000.csv` is the deterministic 1,000-product Session 1 benchmark catalogue.
- `data/events.csv` contains simulated, anonymous marketplace events; it is not real customer activity.
- `reports/M1/` preserves existing Sessions 1–6 evidence. `reports/M2/` contains Session 7–12 reports and benchmarks. `reports/QA/` contains e-commerce functional, photo, control, and browser verification evidence.
- Benchmark times are machine-specific medians. `sys.getsizeof` values are recursive Python object-size estimates, not process RSS.
- External-memory block counts and hardware/cache explanations are simulations or theory unless a report explicitly identifies an actual measured device counter.
- The suffix-array implementation is prefix doubling. The DC3 content is a guided trace, not a locally implemented DC3 constructor.
- The storefront does not connect to a payment processor or shipping service. Orders and checkout addresses are demo records stored locally.

## Main folders

- `src/` — catalogue, marketplace, Session 1–12 algorithms, and integrated data services
- `tests/` — Python correctness and integration tests plus Node cart tests
- `benchmarks/` — reproducible Phase 1/2 experiment scripts and deterministic fixture generation
- `data/` — local products, simulated events, Session 1 fixtures, and runtime demo state
- `reports/M1/`, `reports/M2/`, `reports/QA/` — session, milestone, and e-commerce evidence
- `dashboard/` — AEDS workspace and admin frontend
- `storefront/` — Smart Cart frontend and locally stored product photos
- `scripts/` — photo downloader and Playwright browser acceptance runner
