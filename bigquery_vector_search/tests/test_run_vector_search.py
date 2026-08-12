import unittest
from unittest.mock import Mock

from src.run_vector_search import render_sql, search, validate_results


class RenderSqlTest(unittest.TestCase):
    def test_renders_bigquery_resource_names(self) -> None:
        rendered = render_sql(
            "SELECT '__PROJECT_ID__', '__DATASET_ID__', '__CONNECTION_ID__'",
            "sample-project",
            "vector_demo",
            "projects/sample-project/locations/US/connections/vertex-ai",
        )

        self.assertEqual(
            rendered,
            "SELECT 'sample-project', 'vector_demo', 'sample-project.US.vertex-ai'",
        )

    def test_rejects_invalid_dataset_identifier(self) -> None:
        with self.assertRaisesRegex(ValueError, "dataset_id"):
            render_sql(
                "SELECT 1",
                "sample-project",
                "invalid.dataset",
                "projects/sample-project/locations/US/connections/vertex-ai",
            )


class SearchTest(unittest.TestCase):
    def test_passes_query_as_parameter(self) -> None:
        client = Mock()
        client.query.return_value.result.return_value = [
            Mock(items=lambda: [("title", "Result"), ("distance", 0.2)])
        ]

        rows = search(client, "SELECT @query_text", "data pipelines")

        self.assertEqual(rows[0]["title"], "Result")
        job_config = client.query.call_args.kwargs["job_config"]
        self.assertEqual(job_config.query_parameters[0].value, "data pipelines")

    def test_validates_distance_order(self) -> None:
        rows = validate_results(
            [
                {"title": "First", "distance": 0.1},
                {"title": "Second", "distance": 0.3},
            ]
        )

        self.assertEqual(len(rows), 2)

    def test_rejects_unordered_distances(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not ordered"):
            validate_results(
                [
                    {"title": "First", "distance": 0.4},
                    {"title": "Second", "distance": 0.2},
                ]
            )


if __name__ == "__main__":
    unittest.main()