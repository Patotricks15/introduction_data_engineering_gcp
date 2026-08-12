CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.fact_orders`
PARTITION BY order_date
CLUSTER BY customer_id, channel AS
SELECT
  orders.order_id,
  orders.order_date,
  orders.channel,
  customers.customer_id,
  SUM(item.quantity) AS total_units,
  ROUND(SUM(item.quantity * item.unit_price), 2) AS order_amount
FROM `{project_id}.{dataset_id}.stg_orders` AS orders
JOIN `{project_id}.{dataset_id}.dim_customers` AS customers
  ON orders.customer.customer_id = customers.customer_id
CROSS JOIN UNNEST(orders.items) AS item
GROUP BY orders.order_id, orders.order_date, orders.channel, customers.customer_id;

CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.fact_order_items`
PARTITION BY order_date
CLUSTER BY product_id, category AS
SELECT
  orders.order_id,
  orders.order_date,
  orders.customer.customer_id AS customer_id,
  products.product_id,
  products.category,
  item.quantity,
  item.unit_price,
  ROUND(item.quantity * item.unit_price, 2) AS line_amount
FROM `{project_id}.{dataset_id}.stg_orders` AS orders
CROSS JOIN UNNEST(orders.items) AS item
JOIN `{project_id}.{dataset_id}.dim_products` AS products
  ON item.product_id = products.product_id;