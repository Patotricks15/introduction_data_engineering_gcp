import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.run_workflow import build_source_files, wait_for_invocation


class BuildSourceFilesTest(unittest.TestCase):
    def test_renders_settings_and_loads_definitions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_directory = Path(temporary_directory)
            definitions = source_directory / "definitions"
            definitions.mkdir()
            (source_directory / "workflow_settings.yaml.tmpl").write_text(
                "defaultProject: __PROJECT_ID__\ndefaultDataset: __DATASET_ID__\n",
                encoding="utf-8",
            )
            (definitions / "example.sqlx").write_text(
                'config { type: "view" }\nSELECT 1', encoding="utf-8"
            )

            files = build_source_files(source_directory, "sample-project", "analytics")

            self.assertEqual(
                files["workflow_settings.yaml"],
                b"defaultProject: sample-project\ndefaultDataset: analytics\n",
            )
            self.assertIn("definitions/example.sqlx", files)


class WaitForInvocationTest(unittest.TestCase):
    @patch("src.run_workflow.request_json")
    def test_returns_successful_invocation(self, request_json: Mock) -> None:
        request_json.side_effect = [
            {"state": "RUNNING"},
            {"state": "SUCCEEDED", "name": "workflow-invocation"},
        ]

        result = wait_for_invocation(Mock(), "workflow-invocation", poll_seconds=0)

        self.assertEqual(result["state"], "SUCCEEDED")
        self.assertEqual(request_json.call_count, 2)

    @patch("src.run_workflow.request_json")
    def test_raises_for_failed_invocation(self, request_json: Mock) -> None:
        request_json.return_value = {"state": "FAILED"}

        with self.assertRaisesRegex(RuntimeError, "FAILED"):
            wait_for_invocation(Mock(), "workflow-invocation", poll_seconds=0)


if __name__ == "__main__":
    unittest.main()