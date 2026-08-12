# Introduction to Data Engineering on Google Cloud

A collection of self-contained, portfolio-ready data engineering projects on Google Cloud. Each project includes infrastructure as code, an automated runner, validation, documentation, and cleanup instructions.

## Batch Ingestion and Processing

| Project | Summary |
|---------|---------|
| [Loading Public Data into BigQuery](loading_data_into_bigquery/README.md) | Downloads a public dataset with pandas and loads it into a Terraform-provisioned BigQuery table. |
| [Dataflow Batch Analytics with Python](dataflow_batch_python/README.md) | Runs a bounded Apache Beam Python graph that aggregates site traffic by user and by minute on Dataflow. |
| [Serverless Spark to BigQuery](serverless_spark_to_bigquery/README.md) | Uses Serverless for Apache Spark to enrich a Cloud Storage CSV and load the result into BigQuery. |
| [Cloud Data Fusion Batch Pipeline](cloud_data_fusion_batch/README.md) | Deploys a visual GCS-to-Wrangler-to-BigQuery ETL pipeline through Cloud Data Fusion and the CDAP API. |

## Streaming and Change Data Capture

| Project | Summary |
|---------|---------|
| [Streaming Dataflow Dashboard](streaming_dataflow_dashboard/README.md) | Streams live Open-Meteo events through Pub/Sub and Dataflow into dashboard-ready BigQuery views. |
| [Dataflow Streaming with Python](dataflow_streaming_python/README.md) | Uses Python Apache Beam on Dataflow to window Pub/Sub traffic events and stream corridor aggregates into BigQuery. |
| [E-sports Streaming Analytics](esports_streaming_analytics/README.md) | Combines Pub/Sub, Apache Beam, Bigtable enrichment, BigQuery serving views, and Streamlit monitoring in one live platform. |
| [Datastream PostgreSQL to BigQuery](datastream_postgresql_to_bigquery/README.md) | Replicates PostgreSQL inserts into BigQuery in real time using Datastream change data capture. |

## Event-Driven and Serverless

| Project | Summary |
|---------|---------|
| [Cloud Run Function to BigQuery](cloud_run_function_to_bigquery/README.md) | Triggers a second-generation Cloud Run function from a storage event and performs an idempotent BigQuery load. |

## Analytics Engineering

| Project | Summary |
|---------|---------|
| [Dataform SQL Workflow](dataform_sql_workflow/README.md) | Publishes and executes SQLX transformations and data quality assertions over public BigQuery data. |
| [BigQuery Retail Data Warehouse](bigquery_retail_data_warehouse/README.md) | Combines nested JSON, ARRAY/STRUCT transformations, JOINs, UNION ALL, dimensional modeling, and date-partitioned reporting tables. |

## Data Quality

| Project | Summary |
|---------|---------|
| [Serverless Spark Data Quality](serverless_spark_data_quality/README.md) | Applies Spark validation rules and separates trusted records, quarantined failures, and quality metrics in BigQuery. |

## Lakehouse and External Data

| Project | Summary |
|---------|---------|
| [Lakehouse Qwik Start](lakehouse_qwik_start/README.md) | Queries governed Cloud Storage data through BigLake external tables and column-level policy tags. |
| [External Data and Iceberg Tables](querying_external_data_iceberg/README.md) | Writes an Apache Iceberg table to Cloud Storage and queries it from BigQuery without creating a managed data copy. |
| [Federated Query with AlloyDB](federated_query_alloydb/README.md) | Joins live AlloyDB data with native BigQuery data through `EXTERNAL_QUERY` without replicating the source table. |

## Machine Learning and Semantic Search

| Project | Summary |
|---------|---------|
| [BigQuery ML Transaction Prediction](bigquery_ml_transaction_prediction/README.md) | Trains, evaluates, and applies a BigQuery ML logistic regression model to predict ecommerce transactions. |
| [BigQuery Vector Search](bigquery_vector_search/README.md) | Generates Vertex AI embeddings and performs semantic retrieval with a BigQuery vector index. |

## Running a Project

Projects are independent. Open the linked README for prerequisites, architecture, permissions, execution commands, expected validation, and teardown behavior.

Most projects follow this interface:

```bash
cd <project-directory>
GCP_PROJECT_ID="your-project-id" ./run.sh
```

Review each project's cost and service requirements before running it. The runners normally destroy Terraform-managed resources automatically when execution finishes or fails.