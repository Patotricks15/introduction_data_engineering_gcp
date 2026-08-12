from __future__ import annotations

import argparse
import base64
import time
from pathlib import Path
from typing import Any, Mapping

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.cloud import bigquery


API_ROOT = "https://dataform.googleapis.com/v1beta1"
TERMINAL_STATES = {"SUCCEEDED", "FAILED", "CANCELLED"}


def build_source_files(
    source_directory: Path, project_id: str, dataset_id: str
) -> dict[str, bytes]:
    """Load local Dataform files and render project-specific settings."""
    settings = (source_directory / "workflow_settings.yaml.tmpl").read_text(
        encoding="utf-8"
    )
    settings = settings.replace("__PROJECT_ID__", project_id).replace(
        "__DATASET_ID__", dataset_id
    )
    files = {"workflow_settings.yaml": settings.encode("utf-8")}
    for path in sorted((source_directory / "definitions").glob("*.sqlx")):
        files[f"definitions/{path.name}"] = path.read_bytes()
    return files


def request_json(
    session: AuthorizedSession,
    method: str,
    url: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Send an authenticated Dataform request and return its JSON response."""
    response = session.request(method, url, json=payload, timeout=60)
    response.raise_for_status()
    return response.json() if response.content else {}


def create_workspace(
    session: AuthorizedSession, repository_name: str, workspace_id: str
) -> str:
    workspace_name = f"{repository_name}/workspaces/{workspace_id}"
    request_json(
        session,
        "POST",
        f"{API_ROOT}/{repository_name}/workspaces?workspaceId={workspace_id}",
        {},
    )
    return workspace_name


def write_files(
    session: AuthorizedSession, workspace_name: str, files: Mapping[str, bytes]
) -> None:
    for path, contents in files.items():
        request_json(
            session,
            "POST",
            f"{API_ROOT}/{workspace_name}:writeFile",
            {
                "path": path,
                "contents": base64.b64encode(contents).decode("ascii"),
            },
        )


def compile_workspace(session: AuthorizedSession, workspace_name: str) -> str:
    repository_name = workspace_name.rsplit("/workspaces/", maxsplit=1)[0]
    result = request_json(
        session,
        "POST",
        f"{API_ROOT}/{repository_name}/compilationResults",
        {"workspace": workspace_name},
    )
    errors = result.get("compilationErrors", [])
    if errors:
        messages = "; ".join(error.get("message", str(error)) for error in errors)
        raise RuntimeError(f"Dataform compilation failed: {messages}")
    return str(result["name"])


def invoke_workflow(
    session: AuthorizedSession, compilation_result: str, service_account: str
) -> str:
    repository_name = compilation_result.rsplit("/compilationResults/", maxsplit=1)[0]
    result = request_json(
        session,
        "POST",
        f"{API_ROOT}/{repository_name}/workflowInvocations",
        {
            "compilationResult": compilation_result,
            "invocationConfig": {
                "includedTags": ["daily"],
                "transitiveDependenciesIncluded": True,
                "serviceAccount": service_account,
            },
        },
    )
    return str(result["name"])


def wait_for_invocation(
    session: AuthorizedSession, invocation_name: str, poll_seconds: float = 5
) -> dict[str, Any]:
    while True:
        invocation = request_json(
            session, "GET", f"{API_ROOT}/{invocation_name}"
        )
        state = invocation.get("state", "RUNNING")
        if state in TERMINAL_STATES:
            if state != "SUCCEEDED":
                raise RuntimeError(f"Dataform workflow finished with state {state}")
            return invocation
        time.sleep(poll_seconds)


def verify_output(project_id: str, dataset_id: str) -> int:
    client = bigquery.Client(project=project_id)
    query = (
        f"SELECT COUNT(*) AS row_count "
        f"FROM `{project_id}.{dataset_id}.corpus_summary`"
    )
    row_count = int(next(iter(client.query(query).result())).row_count)
    if row_count <= 0:
        raise RuntimeError("Dataform output table is empty")
    return row_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish and execute a Dataform workflow.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--service-account", required=True)
    parser.add_argument("--source-directory", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    repository_name = (
        f"projects/{args.project_id}/locations/{args.region}"
        f"/repositories/{args.repository_id}"
    )

    files = build_source_files(
        args.source_directory, args.project_id, args.dataset_id
    )
    workspace_name = create_workspace(session, repository_name, "portfolio-workspace")
    write_files(session, workspace_name, files)
    compilation_result = compile_workspace(session, workspace_name)
    invocation_name = invoke_workflow(
        session, compilation_result, args.service_account
    )
    wait_for_invocation(session, invocation_name)
    row_count = verify_output(args.project_id, args.dataset_id)
    print(f"Workflow succeeded and produced {row_count} corpus summary rows.")


if __name__ == "__main__":
    main()