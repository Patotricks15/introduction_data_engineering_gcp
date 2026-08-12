CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.daily_sales`
PARTITION BY sales_date
CLUSTER BY channel AS
WITH web_sales AS (
  SELECT
    orders.order_date AS sales_date,
    orders.channel,
    COUNT(DISTINCT orders.order_id) AS order_count,
    SUM(items.quantity) AS units_sold,
    ROUND(SUM(items.line_amount), 2) AS gross_revenue
  FROM `{project_id}.{dataset_id}.fact_orders` AS orders
  JOIN `{project_id}.{dataset_id}.fact_order_items` AS items USING (order_id)
  WHERE orders.channel = 'web'
  GROUP BY sales_date, channel
),
marketplace_sales AS (
  SELECT
    orders.order_date AS sales_date,
    orders.channel,
    COUNT(DISTINCT orders.order_id) AS order_count,
    SUM(items.quantity) AS units_sold,
    ROUND(SUM(items.line_amount), 2) AS gross_revenue
  FROM `{project_id}.{dataset_id}.fact_orders` AS orders
  JOIN `{project_id}.{dataset_id}.fact_order_items` AS items USING (order_id)
  WHERE orders.channel = 'marketplace'
  GROUP BY sales_date, channel
)
SELECT * FROM web_sales
UNION ALL
SELECT * FROM marketplace_sales;

CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.customer_sales_summary` AS
SELECT
  customers.customer_id,
  customers.customer_name,
  customers.segment,
  COUNT(DISTINCT orders.order_id) AS lifetime_orders,
  ROUND(SUM(orders.order_amount), 2) AS lifetime_revenue
FROM `{project_id}.{dataset_id}.dim_customers` AS customers
LEFT JOIN `{project_id}.{dataset_id}.fact_orders` AS orders USING (customer_id)
GROUP BY customers.customer_id, customers.customer_name, customers.segment;