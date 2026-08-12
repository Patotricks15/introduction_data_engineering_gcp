import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_SCHEMA = {
    "type": "record",
    "name": "tips_source",
    "fields": [
        {"name": "total_bill", "type": ["double", "null"]},
        {"name": "tip", "type": ["double", "null"]},
        {"name": "sex", "type": ["string", "null"]},
        {"name": "smoker", "type": ["string", "null"]},
        {"name": "day", "type": ["string", "null"]},
        {"name": "time", "type": ["string", "null"]},
        {"name": "size", "type": ["int", "null"]},
    ],
}
OUTPUT_SCHEMA = {
    "type": "record",
    "name": "tips_curated",
    "fields": [
        {"name": "total_bill", "type": ["double", "null"]},
        {"name": "tip", "type": ["double", "null"]},
        {"name": "sex", "type": ["string", "null"]},
        {"name": "smoker", "type": ["string", "null"]},
        {"name": "day", "type": ["string", "null"]},
        {"name": "time", "type": ["string", "null"]},
        {"name": "party_size", "type": ["int", "null"]},
    ],
}


def compact_schema(schema: dict[str, Any]) -> str:
    return json.dumps(schema, separators=(",", ":"))


def build_pipeline(name: str = "tips-batch-etl") -> dict[str, Any]:
    source_schema = compact_schema(SOURCE_SCHEMA)
    output_schema = compact_schema(OUTPUT_SCHEMA)
    return {
        "name": name,
        "description": "Batch ETL from Cloud Storage to BigQuery using Pipeline Studio.",
        "artifact": {
            "name": "cdap-data-pipeline",
            "version": "[6.0.0, 7.0.0)",
            "scope": "SYSTEM",
        },
        "config": {
            "resources": {"memoryMB": 2048, "virtualCores": 1},
            "driverResources": {"memoryMB": 2048, "virtualCores": 1},
            "connections": [
                {"from": "Cloud Storage Source", "to": "Wrangler Transform"},
                {"from": "Wrangler Transform", "to": "BigQuery Sink"},
            ],
            "postActions": [],
            "properties": {},
            "processTimingEnabled": True,
            "stageLoggingEnabled": True,
            "stages": [
                {
                    "name": "Cloud Storage Source",
                    "plugin": {
                        "name": "GCSFile",
                        "type": "batchsource",
                        "label": "Cloud Storage Source",
                        "artifact": {"name": "google-cloud"},
                        "properties": {
                            "useConnection": "false",
                            "project": "auto-detect",
                            "serviceAccountType": "filePath",
                            "serviceFilePath": "auto-detect",
                            "referenceName": "tips_source",
                            "path": "${input_path}",
                            "format": "csv",
                            "skipHeader": "true",
                            "enableQuotedValues": "true",
                            "fileEncoding": "UTF-8",
                            "recursive": "false",
                            "ignoreNonExistingFolders": "false",
                            "schema": source_schema,
                        },
                    },
                    "outputSchema": [{"name": "etlSchemaBody", "schema": source_schema}],
                    "id": "Cloud-Storage-Source",
                    "type": "batchsource",
                    "label": "Cloud Storage Source",
                    "_uiPosition": {"left": "120px", "top": "180px"},
                },
                {
                    "name": "Wrangler Transform",
                    "plugin": {
                        "name": "Wrangler",
                        "type": "transform",
                        "label": "Wrangler Transform",
                        "artifact": {"name": "wrangler-transform"},
                        "properties": {
                            "directives": "rename size party_size",
                            "field": "*",
                            "precondition": "false",
                            "on-error": "fail-pipeline",
                            "schema": output_schema,
                        },
                    },
                    "inputSchema": [
                        {"name": "Cloud Storage Source", "schema": source_schema}
                    ],
                    "outputSchema": [{"name": "etlSchemaBody", "schema": output_schema}],
                    "id": "Wrangler-Transform",
                    "type": "transform",
                    "label": "Wrangler Transform",
                    "_uiPosition": {"left": "420px", "top": "180px"},
                },
                {
                    "name": "BigQuery Sink",
                    "plugin": {
                        "name": "BigQueryTable",
                        "type": "batchsink",
                        "label": "BigQuery Sink",
                        "artifact": {"name": "google-cloud"},
                        "properties": {
                            "useConnection": "false",
                            "project": "auto-detect",
                            "serviceAccountType": "filePath",
                            "serviceFilePath": "auto-detect",
                            "referenceName": "tips_curated",
                            "dataset": "${dataset_id}",
                            "table": "${table_id}",
                            "bucket": "${temporary_bucket}",
                            "operation": "insert",
                            "truncateTable": "true",
                            "writeDisposition": "WRITE_TRUNCATE",
                            "allowSchemaRelaxation": "false",
                            "location": "${location}",
                            "createPartitionedTable": "false",
                            "partitioningType": "NONE",
                            "schema": output_schema,
                        },
                    },
                    "inputSchema": [{"name": "Wrangler Transform", "schema": output_schema}],
                    "outputSchema": [{"name": "etlSchemaBody", "schema": output_schema}],
                    "id": "BigQuery-Sink",
                    "type": "batchsink",
                    "label": "BigQuery Sink",
                    "_uiPosition": {"left": "720px", "top": "180px"},
                },
            ],
            "schedule": "0 1 * * *",
            "engine": "spark",
            "numOfRecordsPreview": 100,
            "maxConcurrentRuns": 1,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an importable Data Fusion pipeline.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name", default="tips-batch-etl")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build_pipeline(args.name), indent=2), encoding="utf-8")
    print(f"Wrote Pipeline Studio definition to {args.output}")


if __name__ == "__main__":
    main()