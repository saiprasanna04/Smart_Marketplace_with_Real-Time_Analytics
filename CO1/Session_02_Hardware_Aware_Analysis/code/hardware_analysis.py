"""Small data-layout tools and simulations for hardware cost models."""

from array import array
from collections.abc import Mapping, Sequence

from src.search import ProductQuery


class ContiguousCatalogue:
    """Column-based catalogue with packed numeric arrays and parallel ID/category columns.

    Prices and stock counts are stored in compact C arrays. IDs and categories
    remain Python strings held in tuples, but do not sit inside per-product
    dictionaries.
    """

    def __init__(
        self,
        product_ids: tuple[str, ...],
        categories: tuple[str, ...],
        prices: array,
        stocks: array,
    ) -> None:
        lengths = {len(product_ids), len(categories), len(prices), len(stocks)}
        if len(lengths) != 1:
            raise ValueError("All contiguous catalogue columns must have the same length")
        self.product_ids = product_ids
        self.categories = categories
        self.prices = prices
        self.stocks = stocks

    @classmethod
    def from_products(cls, products: Sequence[Mapping[str, object]]) -> "ContiguousCatalogue":
        """Copy the filter and result fields from product dictionaries into columns."""
        return cls(
            tuple(str(product["product_id"]) for product in products),
            tuple(str(product["category"]) for product in products),
            array("d", (float(product["price"]) for product in products)),
            array("q", (int(product["stock"]) for product in products)),
        )

    def __len__(self) -> int:
        return len(self.product_ids)


def search_contiguous(
    catalogue: ContiguousCatalogue,
    category: str,
    max_price: float,
    min_stock: int,
) -> tuple[list[str], int]:
    """Apply Session 1's exact filter to column-based data and count rows inspected."""
    matching_ids: list[str] = []
    records_inspected = 0
    for index in range(len(catalogue)):
        records_inspected += 1
        if (
            catalogue.categories[index] == category
            and catalogue.prices[index] <= max_price
            and catalogue.stocks[index] >= min_stock
        ):
            matching_ids.append(catalogue.product_ids[index])
    return matching_ids, records_inspected


def batch_search_contiguous(
    catalogue: ContiguousCatalogue, queries: Sequence[ProductQuery]
) -> tuple[list[list[str]], int]:
    """Answer a query batch in one outer pass over the contiguous columns."""
    results: list[list[str]] = [[] for _ in queries]
    predicate_evaluations = 0
    for product_index in range(len(catalogue)):
        for query_index, (category, max_price, min_stock) in enumerate(queries):
            predicate_evaluations += 1
            if (
                catalogue.categories[product_index] == category
                and catalogue.prices[product_index] <= max_price
                and catalogue.stocks[product_index] >= min_stock
            ):
                results[query_index].append(catalogue.product_ids[product_index])
    return results, predicate_evaluations


def simulate_block_reads(record_count: int, block_size: int) -> int:
    """Estimate sequential block transfers when a block holds ``block_size`` rows.

    This is a record-based model simulation. It does not access or measure a
    physical disk, filesystem, or operating-system cache.
    """
    if record_count < 0:
        raise ValueError("record_count must be greater than or equal to 0")
    if block_size <= 0:
        raise ValueError("block_size must be greater than 0")
    return (record_count + block_size - 1) // block_size
