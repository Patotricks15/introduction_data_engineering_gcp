import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


FUNCTION_PATH = Path(__file__).parents[1] / "function" / "main.py"
SPEC = importlib.util.spec_from_file_location("function_main", FUNCTION_PATH)
assert SPEC and SPEC.loader
FUNCTION_MAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FUNCTION_MAIN)


class LoadObjectTest(unittest.TestCase):
    def test_loads_csv_with_truncate_disposition(self) -> None:
        client = Mock(project="sample-project")
        client.get_table.return_value.num_rows = 244

        row_count = FUNCTION_MAIN.load_object(
            {"bucket": "landing-bucket", "name": "tips.csv"},
            "analytics",
            "tips",
            client,
        )

        self.assertEqual(row_count, 244)
        client.load_table_from_uri.assert_called_once()
        uri, destination = client.load_table_from_uri.call_args.args
        job_config = client.load_table_from_uri.call_args.kwargs["job_config"]
        self.assertEqual(uri, "gs://landing-bucket/tips.csv")
        self.assertEqual(destination, "sample-project.analytics.tips")
        self.assertEqual(job_config.skip_leading_rows, 1)
        self.assertEqual(job_config.write_disposition, "WRITE_TRUNCATE")

    def test_skips_non_csv_objects(self) -> None:
        client = Mock(project="sample-project")

        row_count = FUNCTION_MAIN.load_object(
            {"bucket": "landing-bucket", "name": "notes.txt"},
            "analytics",
            "tips",
            client,
        )

        self.assertEqual(row_count, 0)
        client.load_table_from_uri.assert_not_called()


if __name__ == "__main__":
    unittest.main()