import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verify_replication import validate_identifier


class ValidateIdentifierTest(unittest.TestCase):
    def test_accepts_bigquery_identifier(self) -> None:
        self.assertEqual(validate_identifier("postgres_replica"), "postgres_replica")

    def test_rejects_unsafe_identifier(self) -> None:
        with self.assertRaises(ValueError):
            validate_identifier("dataset`; DROP TABLE orders")


if __name__ == "__main__":
    unittest.main()
