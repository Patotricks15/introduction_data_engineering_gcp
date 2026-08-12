import argparse
import json
from datetime import datetime
from typing import Any, Iterable

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions


def parse_event(line: str) -> dict[str, Any]:
    event = json.loads(line)
    required = {"event_id", "event_time", "user_id", "path", "bytes_sent"}
    missing = required - event.keys()
    if missing:
        raise ValueError(f"Missing traffic fields: {sorted(missing)}")
    event["bytes_sent"] = int(event["bytes_sent"])
    return event


def minute_key(event_time: str) -> str:
    timestamp = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
    return timestamp.replace(second=0, microsecond=0).isoformat()


def user_metrics(element: tuple[str, Iterable[dict[str, Any]]]) -> dict[str, Any]:
    user_id, events = element
    materialized = list(events)
    return {
        "user_id": user_id,
        "page_views": len(materialized),
        "bytes_sent": sum(event["bytes_sent"] for event in materialized),
        "unique_paths": len({event["path"] for event in materialized}),
    }


def minute_metrics(element: tuple[str, Iterable[dict[str, Any]]]) -> dict[str, Any]:
    minute, events = element
    materialized = list(events)
    return {
        "traffic_minute": minute,
        "page_views": len(materialized),
        "bytes_sent": sum(event["bytes_sent"] for event in materialized),
        "active_users": len({event["user_id"] for event in materialized}),
    }


def write_json(record: dict[str, Any]) -> str:
    return json.dumps(record, separators=(",", ":"), sort_keys=True)


def build_pipeline(
    pipeline: beam.Pipeline,
    input_pattern: str,
    user_output: str,
    minute_output: str,
) -> None:
    events = (
        pipeline
        | "Read Traffic" >> beam.io.ReadFromText(input_pattern)
        | "Parse Events" >> beam.Map(parse_event)
    )
    (
        events
        | "Key By User" >> beam.Map(lambda event: (event["user_id"], event))
        | "Group By User" >> beam.GroupByKey()
        | "Aggregate Users" >> beam.Map(user_metrics)
        | "Encode User Metrics" >> beam.Map(write_json)
        | "Write User Metrics" >> beam.io.WriteToText(user_output, file_name_suffix=".jsonl")
    )
    (
        events
        | "Key By Minute" >> beam.Map(lambda event: (minute_key(event["event_time"]), event))
        | "Group By Minute" >> beam.GroupByKey()
        | "Aggregate Minutes" >> beam.Map(minute_metrics)
        | "Encode Minute Metrics" >> beam.Map(write_json)
        | "Write Minute Metrics" >> beam.io.WriteToText(minute_output, file_name_suffix=".jsonl")
    )


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description="Aggregate site traffic with Apache Beam.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--user-output", required=True)
    parser.add_argument("--minute-output", required=True)
    return parser.parse_known_args(argv)


def run(argv: list[str] | None = None) -> None:
    known_args, pipeline_args = parse_args(argv)
    options = PipelineOptions(pipeline_args)
    options.view_as(SetupOptions).save_main_session = True
    with beam.Pipeline(options=options) as pipeline:
        build_pipeline(pipeline, known_args.input, known_args.user_output, known_args.minute_output)


if __name__ == "__main__":
    run()