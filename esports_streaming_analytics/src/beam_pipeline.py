import argparse
import json
from datetime import datetime, timezone
from typing import Any

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions, StandardOptions


class ParseEvent(beam.DoFn):
    INVALID = "invalid"

    def process(self, payload: bytes):
        try:
            event = json.loads(payload.decode("utf-8"))
            required = {
                "event_id",
                "event_time",
                "match_id",
                "player_id",
                "event_type",
                "action",
                "score_delta",
            }
            missing = required - event.keys()
            if missing:
                raise ValueError(f"Missing fields: {sorted(missing)}")
            yield event
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            yield beam.pvalue.TaggedOutput(
                self.INVALID,
                {
                    "payload": payload.decode("utf-8", errors="replace"),
                    "error": str(error),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                },
            )


def profile_from_bigtable_row(row: Any) -> dict[str, str]:
    cells = row.cells.get("profile", {}) if row else {}

    def value(column: bytes) -> str:
        versions = cells.get(column, [])
        return versions[0].value.decode("utf-8") if versions else "unknown"

    return {
        "display_name": value(b"display_name"),
        "team": value(b"team"),
        "region": value(b"region"),
        "rank": value(b"rank"),
    }


class EnrichWithBigtable(beam.DoFn):
    def __init__(self, project_id: str, instance_id: str, table_id: str) -> None:
        self.project_id = project_id
        self.instance_id = instance_id
        self.table_id = table_id
        self.table = None

    def setup(self) -> None:
        from google.cloud import bigtable

        self.table = bigtable.Client(project=self.project_id).instance(self.instance_id).table(
            self.table_id
        )

    def process(self, event: dict[str, Any]):
        row = self.table.read_row(event["player_id"].encode("utf-8"))
        yield {**event, **profile_from_bigtable_row(row), "processed_at": datetime.now(timezone.utc).isoformat()}


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-topic", required=True)
    parser.add_argument("--output-table", required=True)
    parser.add_argument("--dead-letter-table", required=True)
    parser.add_argument("--bigtable-project", required=True)
    parser.add_argument("--bigtable-instance", required=True)
    parser.add_argument("--bigtable-table", required=True)
    known_args, pipeline_args = parser.parse_known_args(argv)

    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).streaming = True
    options.view_as(SetupOptions).save_main_session = True

    pipeline = beam.Pipeline(options=options)
    parsed = (
        pipeline
        | "Read PubSub" >> beam.io.ReadFromPubSub(topic=known_args.input_topic)
        | "Parse JSON" >> beam.ParDo(ParseEvent()).with_outputs(ParseEvent.INVALID, main="valid")
    )
    enriched = parsed.valid | "Enrich Player Profiles" >> beam.ParDo(
        EnrichWithBigtable(
            known_args.bigtable_project,
            known_args.bigtable_instance,
            known_args.bigtable_table,
        )
    )
    enriched | "Write Enriched Events" >> beam.io.WriteToBigQuery(
        known_args.output_table,
        method=beam.io.WriteToBigQuery.Method.STREAMING_INSERTS,
        create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
    )
    parsed.invalid | "Write Invalid Events" >> beam.io.WriteToBigQuery(
        known_args.dead_letter_table,
        method=beam.io.WriteToBigQuery.Method.STREAMING_INSERTS,
        create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
    )
    pipeline.run()


if __name__ == "__main__":
    run()