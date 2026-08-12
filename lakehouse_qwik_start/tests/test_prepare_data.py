import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.prepare_data import export_csv_files


class ExportCsvFilesTest(unittest.TestCase):
    def test_exports_customer_and_invoice_with_expected_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database_path = root / "chinook.sqlite"
            self._create_database(database_path)

            paths = export_csv_files(database_path, root / "exports")

            self.assertEqual(
                [path.name for path in paths], ["customer.csv", "invoice.csv"]
            )
            with paths[0].open(newline="", encoding="utf-8") as customer_file:
                customer_rows = list(csv.reader(customer_file))
            with paths[1].open(newline="", encoding="utf-8") as invoice_file:
                invoice_rows = list(csv.reader(invoice_file))

            self.assertEqual(customer_rows[0][0:3], ["customer_id", "first_name", "last_name"])
            self.assertEqual(customer_rows[1][0:3], ["1", "Ada", "Lovelace"])
            self.assertEqual(invoice_rows[0][0:3], ["invoice_id", "customer_id", "invoice_date"])
            self.assertEqual(invoice_rows[1][-1], "9.99")

    @staticmethod
    def _create_database(path: Path) -> None:
        with sqlite3.connect(path) as connection:
            connection.execute(
                "CREATE TABLE Customer (CustomerId, FirstName, LastName, Company, "
                "Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId)"
            )
            connection.execute(
                "INSERT INTO Customer VALUES (1, 'Ada', 'Lovelace', NULL, '1 Main St', "
                "'London', NULL, 'UK', '10001', '555-0100', NULL, "
                "'ada@example.com', 3)"
            )
            connection.execute(
                "CREATE TABLE Invoice (InvoiceId, CustomerId, InvoiceDate, BillingAddress, "
                "BillingCity, BillingState, BillingCountry, BillingPostalCode, Total)"
            )
            connection.execute(
                "INSERT INTO Invoice VALUES (10, 1, '2026-01-01 00:00:00', '1 Main St', "
                "'London', NULL, 'UK', '10001', 9.99)"
            )


if __name__ == "__main__":
    unittest.main()