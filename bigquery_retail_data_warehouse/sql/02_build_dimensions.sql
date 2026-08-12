CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.dim_customers`
CLUSTER BY segment, city AS
SELECT
  customer.customer_id,
  ANY_VALUE(customer.customer_name) AS customer_name,
  ANY_VALUE(customer.city) AS city,
  ANY_VALUE(customer.segment) AS segment,
  MIN(order_date) AS first_order_date
FROM `{project_id}.{dataset_id}.stg_orders`
GROUP BY customer.customer_id;

CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.dim_products`
CLUSTER BY category AS
WITH web_products AS (
  SELECT item.*
  FROM `{project_id}.{dataset_id}.stg_orders`, UNNEST(items) AS item
  WHERE channel = 'web'
),
marketplace_products AS (
  SELECT item.*
  FROM `{project_id}.{dataset_id}.stg_orders`, UNNEST(items) AS item
  WHERE channel = 'marketplace'
),
unified_products AS (
  SELECT * FROM web_products
  UNION ALL
  SELECT * FROM marketplace_products
)
SELECT
  product_id,
  ANY_VALUE(product_name) AS product_name,
  ANY_VALUE(category) AS category,
  ANY_VALUE(unit_price) AS current_unit_price
FROM unified_products
GROUP BY product_id;