import json
import unittest

from src.build_pipeline import build_pipeline


class BuildPipelineTest(unittest.TestCase):
    def test_builds_connected_studio_pipeline_with_runtime_macros(self) -> None:
        pipeline = build_pipeline()
        config = pipeline["config"]
        stages = config["stages"]

        self.assertEqual(pipeline["artifact"]["name"], "cdap-data-pipeline")
        self.assertEqual(
            config["connections"],
            [
                {"from": "Cloud Storage Source", "to": "Wrangler Transform"},
                {"from": "Wrangler Transform", "to": "BigQuery Sink"},
            ],
        )
        self.assertEqual(
            [stage["plugin"]["name"] for stage in stages],
            ["GCSFile", "Wrangler", "BigQueryTable"],
        )
        self.assertEqual(stages[0]["plugin"]["properties"]["path"], "${input_path}")
        self.assertEqual(stages[2]["plugin"]["properties"]["dataset"], "${dataset_id}")

    def test_wrangler_schema_matches_rename_directive(self) -> None:
        pipeline = build_pipeline()
        transform = pipeline["config"]["stages"][1]
        output_schema = json.loads(transform["plugin"]["properties"]["schema"])
        field_names = [field["name"] for field in output_schema["fields"]]

        self.assertEqual(transform["plugin"]["properties"]["directives"], "rename size party_size")
        self.assertIn("party_size", field_names)
        self.assertNotIn("size", field_names)


if __name__ == "__main__":
    unittest.main()