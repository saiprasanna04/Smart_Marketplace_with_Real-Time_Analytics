"""Baseline exact linear search and a small independent correctness oracle."""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence


ProductRecord = Mapping[str, object]
ProductQuery = tuple[str, float, int]


def linear_search(
    catalogue: Iterable[ProductRecord],
    category: str,
    max_price: float,
    min_stock: int,
) -> tuple[list[ProductRecord], int]:
    """Return every exact category/price/stock match and inspected row count.

    The category comparison is exact and both numeric boundaries are
    inclusive. Since every matching product must be returned, this baseline
    inspects every record in the catalogue.
    """
    matches: list[ProductRecord] = []
    records_inspected = 0

    for product in catalogue:
        records_inspected += 1
        if (
            product["category"] == category
            and float(product["price"]) <= max_price
            and int(product["stock"]) >= min_stock
        ):
            matches.append(product)

    return matches, records_inspected


def reference_search(
    catalogue: Iterable[ProductRecord],
    category: str,
    max_price: float,
    min_stock: int,
) -> list[ProductRecord]:
    """Simple independent reference implementation used as a correctness oracle."""
    return [
        record
        for record in catalogue
        if record.get("category") == category
        and float(record.get("price", float("inf"))) <= max_price
        and int(record.get("stock", -1)) >= min_stock
    ]


class CategoryIndex:
    """Reusable hash-based category buckets for repeated marketplace queries."""

    def __init__(self, catalogue: Iterable[ProductRecord]) -> None:
        self._by_category: dict[object, list[ProductRecord]] = defaultdict(list)
        self.product_count = 0
        for product in catalogue:
            self._by_category[product["category"]].append(product)
            self.product_count += 1

    def search(
        self, category: str, max_price: float, min_stock: int
    ) -> tuple[list[ProductRecord], int]:
        """Inspect only records in one category bucket and apply the same filter."""
        matches: list[ProductRecord] = []
        candidates = self._by_category.get(category, ())
        records_inspected = 0
        for product in candidates:
            records_inspected += 1
            if (
                product["category"] == category
                and float(product["price"]) <= max_price
                and int(product["stock"]) >= min_stock
            ):
                matches.append(product)
        return matches, records_inspected


def batch_linear_search(
    catalogue: Sequence[ProductRecord], queries: Sequence[ProductQuery]
) -> tuple[list[list[ProductRecord]], int]:
    """Answer several queries during one outer pass over the catalogue.

    The operation count is product-query predicate evaluations. This still
    evaluates each query against each product, but traverses the outer
    catalogue sequence only once.
    """
    results: list[list[ProductRecord]] = [[] for _ in queries]
    predicate_evaluations = 0
    for product in catalogue:
        for query_number, (category, max_price, min_stock) in enumerate(queries):
            predicate_evaluations += 1
            if (
                product["category"] == category
                and float(product["price"]) <= max_price
                and int(product["stock"]) >= min_stock
            ):
                results[query_number].append(product)
    return results, predicate_evaluations


def batch_category_search(
    index: CategoryIndex, queries: Sequence[ProductQuery]
) -> tuple[list[list[ProductRecord]], int]:
    """Answer multiple requests using the reusable category buckets."""
    results: list[list[ProductRecord]] = []
    candidates_inspected = 0
    for category, max_price, min_stock in queries:
        matches, inspected = index.search(category, max_price, min_stock)
        results.append(matches)
        candidates_inspected += inspected
    return results, candidates_inspected
