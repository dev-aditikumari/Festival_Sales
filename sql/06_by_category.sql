-- Sales and orders by product category.
-- A CTE aggregates per product_category; window functions then add the share of the total,
-- the running (cumulative) share when sorted by amount, and the RANK.
-- Pandas equivalent: festival_sales.analysis.summarize(df, "product_category")
WITH totals AS (
    SELECT product_category,
           COUNT(*)::bigint AS transactions,
           SUM(orders)::bigint AS orders,
           SUM(amount)::bigint AS amount
    FROM diwali_sales
    GROUP BY product_category
)
SELECT product_category,
       transactions,
       orders,
       amount,
       ROUND(100.0 * amount / SUM(amount) OVER (), 2)::float8 AS amount_share_pct,
       ROUND(100.0 * SUM(amount) OVER (ORDER BY amount DESC, product_category) / SUM(amount) OVER (), 2)::float8
           AS cumulative_amount_share_pct,
       RANK() OVER (ORDER BY amount DESC)::int AS amount_rank
FROM totals
ORDER BY amount DESC, product_category;
