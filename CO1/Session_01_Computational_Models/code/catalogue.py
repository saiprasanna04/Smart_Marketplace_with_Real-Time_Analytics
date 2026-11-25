"""Load and validate product records from the marketplace CSV file."""

import csv
import json
import math
from pathlib import Path


REQUIRED_FIELDS = (
    "product_id",
    "title",
    "description",
    "category",
    "price",
    "stock",
    "version",
)

DEFAULT_CATALOGUE_PATH = Path(__file__).resolve().parents[1] / "data" / "products.csv"


class CatalogueValidationError(ValueError):
    """Raised when a product CSV cannot be read or contains invalid records."""


def load_catalogue(path: str | Path = DEFAULT_CATALOGUE_PATH) -> list[dict[str, object]]:
    """Read a CSV catalogue and return normalized product dictionaries.

    Text fields are stripped, prices become floats, and stock values become
    integers. Errors include the file and CSV row so invalid input is easy to
    locate and correct.
    """
    catalogue_path = Path(path)
    try:
        file_handle = catalogue_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as error:
        raise CatalogueValidationError(
            f"Cannot read catalogue '{catalogue_path}': {error}"
        ) from error

    products: list[dict[str, object]] = []
    seen_product_ids: set[str] = set()

    try:
        with file_handle:
            reader = csv.DictReader(file_handle)
            if reader.fieldnames is None:
                raise CatalogueValidationError(
                    f"Catalogue '{catalogue_path}' is empty or has no header row."
                )

            reader.fieldnames = [
                name.strip() if name is not None else "" for name in reader.fieldnames
            ]
            duplicate_headers = sorted(
                name for name in set(reader.fieldnames) if reader.fieldnames.count(name) > 1
            )
            if duplicate_headers:
                raise CatalogueValidationError(
                    f"Catalogue '{catalogue_path}' has duplicate column names: "
                    f"{', '.join(duplicate_headers)}."
                )

            missing_headers = [
                field for field in REQUIRED_FIELDS if field not in reader.fieldnames
            ]
            if missing_headers:
                raise CatalogueValidationError(
                    f"Catalogue '{catalogue_path}' is missing required columns: "
                    f"{', '.join(missing_headers)}."
                )

            for row_number, row in enumerate(reader, start=2):
                # Ignore truly blank lines; report partially filled rows below.
                if not row or all(
                    value is None
                    or (isinstance(value, str) and not value.strip())
                    or (isinstance(value, list) and not value)
                    for value in row.values()
                ):
                    continue

                issues: list[str] = []
                if row.get(None):
                    issues.append("contains extra values beyond the header columns")

                values: dict[str, str] = {}
                for field in REQUIRED_FIELDS:
                    raw_value = row.get(field)
                    value = raw_value.strip() if isinstance(raw_value, str) else ""
                    if not value:
                        issues.append(f"'{field}' is required and cannot be blank")
                    values[field] = value

                price: float | None = None
                if values["price"]:
                    try:
                        price = float(values["price"])
                        if not math.isfinite(price) or price < 0:
                            issues.append(
                                "'price' must be a finite number greater than or equal to 0"
                            )
                    except ValueError:
                        issues.append(f"'price' must be numeric; got {values['price']!r}")

                stock: int | None = None
                if values["stock"]:
                    try:
                        stock = int(values["stock"])
                        if stock < 0:
                            issues.append(
                                "'stock' must be an integer greater than or equal to 0"
                            )
                    except ValueError:
                        issues.append(f"'stock' must be an integer; got {values['stock']!r}")

                product_id = values["product_id"]
                if product_id and product_id in seen_product_ids:
                    issues.append(f"duplicate product_id {product_id!r}")

                if issues:
                    raise CatalogueValidationError(
                        f"Invalid catalogue data in '{catalogue_path}' at row "
                        f"{row_number}: " + "; ".join(issues) + "."
                    )

                # Numeric fields are known to be populated and valid here.
                product = {field: values[field] for field in REQUIRED_FIELDS}
                product["price"] = price
                product["stock"] = stock
                for field in reader.fieldnames:
                    if field in REQUIRED_FIELDS or field == "":
                        continue
                    raw_value = row.get(field)
                    value = raw_value.strip() if isinstance(raw_value, str) else ""
                    if not value:
                        continue
                    try:
                        if field in {"original_price", "rating"}:
                            number = float(value)
                            if not math.isfinite(number) or number < 0:
                                raise ValueError
                            product[field] = number
                        elif field in {"popularity"}:
                            number = int(value)
                            if number < 0:
                                raise ValueError
                            product[field] = number
                        elif field == "specifications":
                            parsed = json.loads(value)
                            if not isinstance(parsed, dict):
                                raise ValueError
                            product[field] = parsed
                        else:
                            product[field] = value
                    except (ValueError, json.JSONDecodeError):
                        raise CatalogueValidationError(
                            f"Invalid catalogue data in '{catalogue_path}' at row "
                            f"{row_number}: '{field}' has an invalid value {value!r}."
                        ) from None
                products.append(product)
                seen_product_ids.add(product_id)
    except csv.Error as error:
        raise CatalogueValidationError(
            f"Invalid CSV formatting in '{catalogue_path}': {error}"
        ) from error

    return products
