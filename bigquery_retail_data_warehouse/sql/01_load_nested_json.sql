CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.stg_orders` AS
SELECT
  order_id,
  DATE(order_date) AS order_date,
  channel,
  STRUCT(
    customer.customer_id AS customer_id,
    customer.name AS customer_name,
    customer.city AS city,
    customer.segment AS segment
  ) AS customer,
  ARRAY(
    SELECT AS STRUCT
      item.product_id,
      item.name AS product_name,
      item.category,
      item.quantity,
      item.unit_price
    FROM UNNEST(items) AS item
  ) AS items
FROM `{project_id}.{dataset_id}.raw_orders`
WHERE order_id IS NOT NULL
  AND ARRAY_LENGTH(items) > 0;