from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions, StandardOptions
from apache_beam.transforms import trigger
from apache_beam.transforms.window import FixedWindows

from src.events import parse_event


class ParseEvent(beam.DoFn):
    INVALID = "invalid"

    def process(self, payload: bytes):
        try:
            event = parse_event(payload)
            event_timestamp = datetime.fromisoformat(
                event["event_time"].replace("Z", "+00:00")
            ).timestamp()
            yield beam.window.TimestampedValue(event, event_timestamp)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            yield beam.pvalue.TaggedOutput(
                self.INVALID,
                {
                    "payload": payload.decode("utf-8", errors="replace"),
                    "error": str(error),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                },
            )


class BuildAggregate(beam.DoFn):
    def process(self, item: tuple[str, list[int]], window=beam.DoFn.WindowParam):
        corridor, speeds = item
        yield {
            "window_start": window.start.to_utc_datetime().isoformat(),
            "window_end": window.end.to_utc_datetime().isoformat(),
            "corridor": corridor,
            "vehicle_count": len(speeds),
            "average_speed_kph": round(sum(speeds) / len(speeds), 2),
            "max_speed_kph": max(speeds),
        }


def build_pipeline(
    pipeline: beam.Pipeline,
    input_topic: str,
    output_table: str,
    dead_letter_table: str,
) -> None:
    parsed = (
        pipeline
        | "Read PubSub" >> beam.io.ReadFromPubSub(topic=input_topic)
        | "Parse Events" >> beam.ParDo(ParseEvent()).with_outputs(ParseEvent.INVALID, main="valid")
    )

    aggregates = (
        parsed.valid
        | "Fixed Event Time Windows" >> beam.WindowInto(
            FixedWindows(60),
            trigger=trigger.AfterWatermark(
                early=trigger.AfterProcessingTime(20),
                late=trigger.AfterCount(1),
            ),
            accumulation_mode=trigger.AccumulationMode.ACCUMULATING,
            allowed_lateness=120,
        )
        | "Key By Corridor" >> beam.Map(lambda event: (event["corridor"], event["speed_kph"]))
        | "Collect Speeds" >> beam.GroupByKey()
        | "Build Window Metrics" >> beam.ParDo(BuildAggregate())
    )

    aggregates | "Write Metrics" >> beam.io.WriteToBigQuery(
        output_table,
        method=beam.io.WriteToBigQuery.Method.STREAMING_INSERTS,
        create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
    )
    parsed.invalid | "Write Invalid Events" >> beam.io.WriteToBigQuery(
        dead_letter_table,
        method=beam.io.WriteToBigQuery.Method.STREAMING_INSERTS,
        create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
    )


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-topic", required=True)
    parser.add_argument("--output-table", required=True)
    parser.add_argument("--dead-letter-table", required=True)
    known_args, pipeline_args = parser.parse_known_args(argv)

    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).streaming = True
    options.view_as(SetupOptions).save_main_session = True

    pipeline = beam.Pipeline(options=options)
    build_pipeline(
        pipeline,
        known_args.input_topic,
        known_args.output_table,
        known_args.dead_letter_table,
    )
    pipeline.run()


if __name__ == "__main__":
    run()