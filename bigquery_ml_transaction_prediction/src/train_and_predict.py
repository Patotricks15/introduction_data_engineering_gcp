from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class EvaluationMetrics:
    precision: float
    recall: float
    accuracy: float
    f1_score: float
    log_loss: float
    roc_auc: float


def validate_identifier(value: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Unsafe BigQuery identifier: {value}")
    return value


def render_sql(
    path: Path,
    project_id: str,
    dataset_id: str,
    model_id: str,
    prediction_table_id: str,
) -> str:
    values = {
        "project_id": validate_identifier(project_id),
        "dataset_id": validate_identifier(dataset_id),
        "model_id": validate_identifier(model_id),
        "prediction_table_id": validate_identifier(prediction_table_id),
    }
    return path.read_text(encoding="utf-8").format(**values)


def parse_metrics(row: object) -> EvaluationMetrics:
    return EvaluationMetrics(
        precision=float(row.precision),
        recall=float(row.recall),
        accuracy=float(row.accuracy),
        f1_score=float(row.f1_score),
        log_loss=float(row.log_loss),
        roc_auc=float(row.roc_auc),
    )


def verify_metrics(metrics: EvaluationMetrics) -> None:
    if not 0.0 <= metrics.precision <= 1.0:
        raise RuntimeError("Precision must be between 0 and 1.")
    if not 0.0 <= metrics.recall <= 1.0:
        raise RuntimeError("Recall must be between 0 and 1.")
    if metrics.roc_auc <= 0.5:
        raise RuntimeError(f"Expected ROC AUC above 0.5, found {metrics.roc_auc:.4f}.")


def run_pipeline(
    project_id: str,
    location: str,
    dataset_id: str,
    model_id: str,
    prediction_table_id: str,
    sql_dir: Path,
) -> tuple[EvaluationMetrics, int]:
    from google.cloud import bigquery

    client = bigquery.Client(project=project_id)
    common = (project_id, dataset_id, model_id, prediction_table_id)

    training_sql = render_sql(sql_dir / "train_model.sql", *common)
    client.query(training_sql, location=location).result()

    evaluation_sql = render_sql(sql_dir / "evaluate_model.sql", *common)
    evaluation_row = next(iter(client.query(evaluation_sql, location=location).result()))
    metrics = parse_metrics(evaluation_row)
    verify_metrics(metrics)

    prediction_sql = render_sql(sql_dir / "predict_visitors.sql", *common)
    client.query(prediction_sql, location=location).result()
    prediction_table = client.get_table(
        f"{project_id}.{dataset_id}.{prediction_table_id}"
    )
    if prediction_table.num_rows == 0:
        raise RuntimeError("The prediction table is empty.")
    return metrics, prediction_table.num_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and verify a BigQuery ML model.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--prediction-table-id", required=True)
    parser.add_argument("--sql-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics, prediction_count = run_pipeline(
        args.project_id,
        args.location,
        args.dataset_id,
        args.model_id,
        args.prediction_table_id,
        args.sql_dir,
    )
    print(
        f"Model verified: ROC AUC={metrics.roc_auc:.4f}, "
        f"precision={metrics.precision:.4f}, recall={metrics.recall:.4f}."
    )
    print(f"Scored {prediction_count} unique visitors.")


if __name__ == "__main__":
    main()