CREATE OR REPLACE MODEL `{project_id}.{dataset_id}.{model_id}`
OPTIONS(
  model_type = 'LOGISTIC_REG',
  input_label_cols = ['will_buy_on_return_visit'],
  auto_class_weights = TRUE
) AS
SELECT
  IFNULL(totals.bounces, 0) AS bounces,
  IFNULL(totals.timeOnSite, 0) AS time_on_site,
  IFNULL(totals.pageviews, 0) AS pageviews,
  trafficSource.source AS traffic_source,
  trafficSource.medium AS traffic_medium,
  device.deviceCategory AS device_category,
  geoNetwork.country AS country,
  IF(totals.transactions > 0, 1, 0) AS will_buy_on_return_visit
FROM `bigquery-public-data.google_analytics_sample.ga_sessions_*`
WHERE _TABLE_SUFFIX BETWEEN '20160801' AND '20170430'