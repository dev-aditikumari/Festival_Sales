-- Sales and orders by gender.
-- A CTE aggregates per gender; window functions then add the share of the total,
-- the running (cumulative) share when sorted by amount, and the RANK.
-- Pandas equivalent: festival_sales.analysis.summarize(df, "gender")
WITH totals AS (
    SELECT gender,
           COUNT(*)::bigint AS transactions,
           SUM(orders)::bigint AS orders,
           SUM(amount)::bigint AS amount
    FROM diwali_sales
    GROUP BY gender
)
SELECT gender,
       transactions,
       orders,
       amount,
       ROUND(100.0 * amount / SUM(amount) OVER (), 2)::float8 AS amount_share_pct,
       ROUND(100.0 * SUM(amount) OVER (ORDER BY amount DESC, gender) / SUM(amount) OVER (), 2)::float8
           AS cumulative_amount_share_pct,
       RANK() OVER (ORDER BY amount DESC)::int AS amount_rank
FROM totals
ORDER BY amount DESC, gender;
