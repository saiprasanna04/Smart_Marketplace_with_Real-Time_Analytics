"""Run the Session 1 catalogue search baseline from the command line."""

import argparse
import sys

from src.catalogue import CatalogueValidationError, load_catalogue
from src.search import linear_search, reference_search


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the sample product catalogue.")
    parser.add_argument("--category", default="Electronics", help="exact category name")
    parser.add_argument("--max-price", type=float, default=100.0)
    parser.add_argument("--min-stock", type=int, default=1)
    args = parser.parse_args()

    try:
        catalogue = load_catalogue()
    except CatalogueValidationError as error:
        print(f"Catalogue error: {error}", file=sys.stderr)
        return 1

    matches, records_inspected = linear_search(
        catalogue, args.category, args.max_price, args.min_stock
    )
    oracle_matches = reference_search(
        catalogue, args.category, args.max_price, args.min_stock
    )
    match_ids = [str(product["product_id"]) for product in matches]
    oracle_ids = [str(product["product_id"]) for product in oracle_matches]
    if match_ids != oracle_ids:
        print(
            "Correctness check failed: linear search disagrees with the reference.",
            file=sys.stderr,
        )
        return 2

    print(f"Loaded products: {len(catalogue)}")
    print(
        f"Query: category={args.category!r}, max_price={args.max_price:g}, "
        f"min_stock={args.min_stock}"
    )
    print(f"Records inspected: {records_inspected}")
    print(f"Matching products: {len(matches)}")
    for product in matches:
        print(
            f"- {product['product_id']}: {product['title']} "
            f"(price={product['price']:.2f}, stock={product['stock']})"
        )
    print("Correctness oracle: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
