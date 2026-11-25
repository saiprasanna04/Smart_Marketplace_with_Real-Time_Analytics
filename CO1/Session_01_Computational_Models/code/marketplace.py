"""Customer-facing catalogue search backed by the validated product CSV."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path

from src.catalogue import load_catalogue
from src.session1 import linear_search_in_stock_below_price


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_CATALOGUE_PATH = PROJECT_ROOT / "data" / "products.csv"
ProductRecord = Mapping[str, object]
STOP_WORDS = {"a", "an", "and", "for", "of", "or", "the", "to", "in", "on", "with", "by", "from"}


def load_marketplace_catalogue() -> list[dict[str, object]]:
    """Load the original catalogue for the storefront, not benchmark expansions."""
    return load_catalogue(MARKETPLACE_CATALOGUE_PATH)


def search_marketplace_products(
    catalogue: Iterable[ProductRecord],
    *,
    query: str = "",
    category: str = "",
    brand: str = "",
    min_price: float | None = None,
    price_below: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    in_stock_only: bool = False,
    sort: str = "featured",
) -> tuple[list[ProductRecord], dict[str, int] | None]:
    """Filter exact catalogue rows by literal text and marketplace facets.

    The exclusive ``price_below`` option is retained for Session 1 semantics;
    ``max_price`` is an inclusive customer-facing range filter. Search terms
    are matched against real title, brand, category, and description text.
    """
    for name, value in (("min_price", min_price), ("price_below", price_below), ("max_price", max_price)):
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError(f"{name} must be a finite number greater than or equal to 0")
    if min_rating is not None and (not math.isfinite(min_rating) or not 0 <= min_rating <= 5):
        raise ValueError("min_rating must be a number between 0 and 5")

    all_products = list(catalogue)
    session1_counts: dict[str, int] | None = None
    if in_stock_only:
        session1_limit = price_below
        if session1_limit is None:
            session1_limit = max((float(product["price"]) for product in all_products), default=0.0) + 1.0
        candidates, session1_counts = linear_search_in_stock_below_price(all_products, session1_limit)
    else:
        candidates = all_products

    query_key = query.strip().casefold()
    category_key = category.strip().casefold()
    brand_key = brand.strip().casefold()
    query_tokens = tuple(
        token for token in dict.fromkeys(re.findall(r"[\w]+", query_key, flags=re.UNICODE))
        if token not in STOP_WORDS
    )
    matches: list[ProductRecord] = []
    relevance_rows: list[tuple[int, ProductRecord]] = []
    complete_match_ids: set[str] = set()
    for product in candidates:
        title = str(product["title"])
        description = str(product["description"])
        category_value = str(product["category"])
        brand_value = str(product.get("brand", ""))
        searchable_fields = [title, brand_value, category_value, description]
        searchable = " ".join(searchable_fields).casefold()
        tokenized_fields = [set(re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE)) for value in searchable_fields]
        searchable_tokens = set().union(*tokenized_fields)
        title_tokens, brand_tokens = tokenized_fields[0], tokenized_fields[1]
        title_key = title.casefold()
        brand_value_key = brand_value.casefold()
        if query_key:
            matched_terms = [
                token for token in query_tokens
                if token in searchable_tokens
                or (token.endswith("s") and token[:-1] in searchable_tokens)
                or (f"{token}s" in searchable_tokens)
            ]
            if not matched_terms:
                continue
            score = sum(
                3 if token in title_tokens or f"{token}s" in title_tokens or (token.endswith("s") and token[:-1] in title_tokens)
                else 2 if token in brand_tokens or f"{token}s" in brand_tokens or (token.endswith("s") and token[:-1] in brand_tokens)
                else 1
                for token in matched_terms
            )
            if query_key in searchable:
                score += len(query_tokens) + 2
        else:
            matched_terms = []
            score = 0
        if category_key and category_key != category_value.casefold():
            continue
        if brand_key and brand_key != brand_value_key:
            continue
        price = float(product["price"])
        if min_price is not None and price < min_price:
            continue
        if price_below is not None and price >= price_below:
            continue
        if max_price is not None and price > max_price:
            continue
        if min_rating is not None and float(product.get("rating", 0)) < min_rating:
            continue
        if query_key:
            if len(matched_terms) == len(query_tokens):
                complete_match_ids.add(str(product["product_id"]))
            relevance_rows.append((score, product))
        else:
            matches.append(product)

    sort_key = sort.casefold()
    if query_key:
        if complete_match_ids:
            relevance_rows = [row for row in relevance_rows if str(row[1]["product_id"]) in complete_match_ids]
        if sort_key in {"relevance", "featured"}:
            relevance_rows.sort(key=lambda item: item[0], reverse=True)
        matches = [dict(product) | {"relevance_score": score} for score, product in relevance_rows]

    if sort_key == "price_asc":
        matches.sort(key=lambda product: float(product["price"]))
    elif sort_key == "price_desc":
        matches.sort(key=lambda product: float(product["price"]), reverse=True)
    elif sort_key == "name":
        matches.sort(key=lambda product: str(product["title"]).casefold())
    elif sort_key in {"popular", "popularity"}:
        matches.sort(key=lambda product: (-int(product.get("popularity", 0)), str(product["product_id"])))
    elif sort_key == "newest":
        matches.sort(key=lambda product: (str(product.get("created_at", "")), str(product["product_id"])), reverse=True)
    elif sort_key == "discount_desc":
        matches.sort(key=lambda product: _discount_rate(product), reverse=True)
    elif sort_key not in {"featured", "relevance"}:
        raise ValueError("sort must be featured, relevance, price_asc, price_desc, name, popular, newest, or discount_desc")
    return matches, session1_counts


def _discount_rate(product: ProductRecord) -> float:
    original = float(product.get("original_price", product["price"]))
    price = float(product["price"])
    return (original - price) / original if original > price and original else 0.0


def search_suggestions(catalogue: Iterable[ProductRecord], query: str, limit: int = 6) -> list[dict[str, str]]:
    """Return suggestions derived from matching rows in the current catalogue."""
    query_key = query.strip().casefold()
    if len(query_key) < 2:
        return []
    products, _ = search_marketplace_products(catalogue, query=query_key, sort="relevance")
    return [
        {"product_id": str(row["product_id"]), "title": str(row["title"]),
         "brand": str(row.get("brand", "")), "category": str(row["category"])}
        for row in products[:max(1, min(int(limit), 10))]
    ]


def find_marketplace_product(product_id: str) -> dict[str, object] | None:
    """Return one validated product by exact product ID, if present."""
    for product in load_marketplace_catalogue():
        if str(product["product_id"]) == product_id:
            return product
    return None
