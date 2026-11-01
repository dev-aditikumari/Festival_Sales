-- Top 10 products by total orders. Ties share a rank; product_id breaks ties in the listing.
-- Pandas equivalent: festival_sales.analysis.top_products(df, 10)
SELECT product_id,
       SUM(orders)::bigint AS orders,
       ROUND(SUM(amount), 2)::float8 AS amount,
       RANK() OVER (ORDER BY SUM(orders) DESC)::int AS orders_rank
FROM diwali_sales
GROUP BY product_id
ORDER BY orders DESC, product_id
LIMIT 10;
