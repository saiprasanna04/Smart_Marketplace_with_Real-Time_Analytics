"""Unit tests for catalogue CSV validation and type conversion."""

import csv
import tempfile
import unittest
from pathlib import Path

from src.catalogue import CatalogueValidationError, load_catalogue


FIELDS = ["product_id", "title", "description", "category", "price", "stock", "version"]


class CatalogueLoaderTests(unittest.TestCase):
    def write_csv(self, path: Path, headers: list[str], row: list[str]) -> None:
        with path.open("w", encoding="utf-8", newline="") as file_handle:
            writer = csv.writer(file_handle)
            writer.writerow(headers)
            writer.writerow(row)

    def test_loads_product_and_converts_numeric_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "products.csv"
            self.write_csv(path, FIELDS, ["P1", "Lamp", "Desk lamp", "Home", "12.50", "4", "1.0"])
            product = load_catalogue(path)[0]
        self.assertEqual(product["product_id"], "P1")
        self.assertEqual(product["price"], 12.5)
        self.assertEqual(product["stock"], 4)

    def test_missing_required_column_has_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "products.csv"
            self.write_csv(path, FIELDS[:-1], ["P1", "Lamp", "Desk lamp", "Home", "12.50", "4"])
            with self.assertRaisesRegex(CatalogueValidationError, "missing required columns: version"):
                load_catalogue(path)

    def test_invalid_price_reports_row_and_field(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "products.csv"
            self.write_csv(path, FIELDS, ["P1", "Lamp", "Desk lamp", "Home", "free", "4", "1.0"])
            with self.assertRaisesRegex(CatalogueValidationError, "row 2.*price.*numeric"):
                load_catalogue(path)

    def test_blank_required_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "products.csv"
            self.write_csv(path, FIELDS, ["P1", "", "Desk lamp", "Home", "12.50", "4", "1.0"])
            with self.assertRaisesRegex(CatalogueValidationError, "'title' is required"):
                load_catalogue(path)


if __name__ == "__main__":
    unittest.main()
