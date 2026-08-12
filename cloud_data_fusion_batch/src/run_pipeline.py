import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


TERMINAL_STATES = {"COMPLETED", "FAILED", "KILLED", "REJECTED"}


def cdap_request(
    method: str,
    url: str,
    access_token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"CDAP request failed ({error.code}): {details}") from error
    return json.loads(body) if body else None


def wait_for_run(
    endpoint: str,
    pipeline_name: str,
    access_token: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    runs_url = (
        f"{endpoint}/v3/namespaces/default/apps/{pipeline_name}"
        "/workflows/DataPipelineWorkflow/runs"
    )
    deadline = time.monotonic() + timeout_seconds
    run_id = ""
    while time.monotonic() < deadline:
        runs = cdap_request("GET", runs_url, access_token) or []
        if runs:
            run_id = runs[0]["runid"]
            status = runs[0]["status"]
            print(f"Pipeline run {run_id}: {status}")
            if status in TERMINAL_STATES:
                if status != "COMPLETED":
                    raise RuntimeError(f"Pipeline finished with status {status}.")
                return runs[0]
        time.sleep(20)
    raise TimeoutError(
        f"Pipeline run {run_id or '<pending>'} did not complete within {timeout_seconds} seconds."
    )


def active_access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy and execute a Data Fusion pipeline.")
    parser.add_argument("--api-endpoint", required=True)
    parser.add_argument("--pipeline", type=Path, required=True)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--table-id", required=True)
    parser.add_argument("--temporary-bucket", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--timeout", type=int, default=3600)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoint = args.api_endpoint.rstrip("/")
    pipeline = json.loads(args.pipeline.read_text(encoding="utf-8"))
    pipeline_name = pipeline["name"]
    token = active_access_token()
    app_url = f"{endpoint}/v3/namespaces/default/apps/{pipeline_name}"
    start_url = f"{app_url}/workflows/DataPipelineWorkflow/start"

    cdap_request("PUT", app_url, token, pipeline)
    print(f"Deployed pipeline {pipeline_name}.")
    cdap_request(
        "POST",
        start_url,
        token,
        {
            "input_path": args.input_path,
            "dataset_id": args.dataset_id,
            "table_id": args.table_id,
            "temporary_bucket": args.temporary_bucket,
            "location": args.location,
        },
    )
    print(f"Started pipeline {pipeline_name}.")
    wait_for_run(endpoint, pipeline_name, token, args.timeout)


if __name__ == "__main__":
    main()