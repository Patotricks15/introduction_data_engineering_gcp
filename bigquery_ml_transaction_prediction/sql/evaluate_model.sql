SELECT
  precision,
  recall,
  accuracy,
  f1_score,
  log_loss,
  roc_auc
FROM ML.EVALUATE(
  MODEL `{project_id}.{dataset_id}.{model_id}`,
  (
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
    WHERE _TABLE_SUFFIX BETWEEN '20170501' AND '20170630'
  )
)