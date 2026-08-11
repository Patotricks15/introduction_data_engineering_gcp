import argparse
from pathlib import Path

import pandas as pd
from google.cloud import bigquery


DATA_URL = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv"
EXPECTED_COLUMNS = ["total_bill", "tip", "sex", "smoker", "day", "time", "size"]


def load_public_data() -> pd.DataFrame:
    dataframe = pd.read_csv(DATA_URL)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    if dataframe.columns.tolist() != EXPECTED_COLUMNS:
        raise ValueError(f"Unexpected source columns: {dataframe.columns.tolist()}")
    return dataframe


def load_into_bigquery(
    dataframe: pd.DataFrame,
    project_id: str,
    dataset_id: str,
    table_id: str,
    csv_path: Path,
) -> None:
    dataframe.to_csv(csv_path, index=False)

    client = bigquery.Client(project=project_id)
    destination = f"{project_id}.{dataset_id}.{table_id}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    with csv_path.open("rb") as csv_file:
        load_job = client.load_table_from_file(
            csv_file,
            destination,
            job_config=job_config,
        )

    load_job.result()
    table = client.get_table(destination)
    print(f"Loaded {table.num_rows} rows into {destination}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load a public dataset into BigQuery.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--table-id", required=True)
    parser.add_argument("--csv-path", type=Path, default=Path("data/tips.csv"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.csv_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe = load_public_data()
    load_into_bigquery(
        dataframe=dataframe,
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        table_id=args.table_id,
        csv_path=args.csv_path,
    )


if __name__ == "__main__":
    main()