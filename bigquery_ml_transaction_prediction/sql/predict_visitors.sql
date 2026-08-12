CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.{prediction_table_id}` AS
SELECT
  fullVisitorId AS visitor_id,
  predicted_will_buy_on_return_visit AS predicted_transaction,
  (
    SELECT probability.prob
    FROM UNNEST(predicted_will_buy_on_return_visit_probs) AS probability
    WHERE probability.label = 1
  ) AS transaction_probability
FROM ML.PREDICT(
  MODEL `{project_id}.{dataset_id}.{model_id}`,
  (
    SELECT
      fullVisitorId,
      IFNULL(totals.bounces, 0) AS bounces,
      IFNULL(totals.timeOnSite, 0) AS time_on_site,
      IFNULL(totals.pageviews, 0) AS pageviews,
      trafficSource.source AS traffic_source,
      trafficSource.medium AS traffic_medium,
      device.deviceCategory AS device_category,
      geoNetwork.country AS country
    FROM `bigquery-public-data.google_analytics_sample.ga_sessions_*`
    WHERE _TABLE_SUFFIX BETWEEN '20170701' AND '20170731'
  )
)
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY fullVisitorId
  ORDER BY (
    SELECT probability.prob
    FROM UNNEST(predicted_will_buy_on_return_visit_probs) AS probability
    WHERE probability.label = 1
  ) DESC
) = 1