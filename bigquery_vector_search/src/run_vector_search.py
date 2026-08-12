from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from google.cloud import bigquery


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def render_sql(
    template: str, project_id: str, dataset_id: str, connection_id: str
) -> str:
    """Render trusted resource identifiers into a SQL template."""
    for name, value in {
        "project_id": project_id,
        "dataset_id": dataset_id,
    }.items():
        if not IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError(f"Invalid {name}: {value}")
    if not re.fullmatch(r"projects/[^/]+/locations/[^/]+/connections/[^/]+", connection_id):
        raise ValueError(f"Invalid connection_id: {connection_id}")
    connection_sql_id = connection_id.removeprefix("projects/").replace(
        "/locations/", "."
    ).replace("/connections/", ".")
    return (
        template.replace("__PROJECT_ID__", project_id)
        .replace("__DATASET_ID__", dataset_id)
        .replace("__CONNECTION_ID__", connection_sql_id)
    )


def run_setup(client: bigquery.Client, sql: str) -> None:
    """Create source data, remote model, embeddings, and vector index."""
    client.query(sql).result()


def search(
    client: bigquery.Client, sql: str, query_text: str
) -> list[dict[str, Any]]:
    """Run a parameterized semantic search and return serializable rows."""
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("query_text", "STRING", query_text)
        ]
    )
    return [dict(row.items()) for row in client.query(sql, job_config=job_config).result()]


def validate_results(results: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Require ranked results with valid cosine distances."""
    rows = list(results)
    if not rows:
        raise RuntimeError("VECTOR_SEARCH returned no results")
    distances = [float(row["distance"]) for row in rows]
    if distances != sorted(distances):
        raise RuntimeError("VECTOR_SEARCH results are not ordered by distance")
    if any(distance < 0 or distance > 2 for distance in distances):
        raise RuntimeError("VECTOR_SEARCH returned an invalid cosine distance")
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and query BigQuery embeddings.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--connection-id", required=True)
    parser.add_argument("--sql-directory", type=Path, required=True)
    parser.add_argument(
        "--query",
        default="How can I build a scalable data pipeline on Google Cloud?",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_template = (args.sql_directory / "setup.sql.tmpl").read_text(
        encoding="utf-8"
    )
    search_template = (args.sql_directory / "search.sql.tmpl").read_text(
        encoding="utf-8"
    )
    setup_sql = render_sql(
        setup_template, args.project_id, args.dataset_id, args.connection_id
    )
    search_sql = render_sql(
        search_template, args.project_id, args.dataset_id, args.connection_id
    )

    client = bigquery.Client(project=args.project_id)
    print("Creating documents, remote model, embeddings, and vector index...")
    run_setup(client, setup_sql)
    rows = validate_results(search(client, search_sql, args.query))

    print(f"Semantic query: {args.query}")
    for position, row in enumerate(rows, start=1):
        print(f"{position}. {row['title']} (cosine distance: {row['distance']:.4f})")


if __name__ == "__main__":
    main()