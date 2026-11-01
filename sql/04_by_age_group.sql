-- Sales and orders by age group.
-- A CTE aggregates per age_group; window functions then add the share of the total,
-- the running (cumulative) share when sorted by amount, and the RANK.
-- Pandas equivalent: festival_sales.analysis.summarize(df, "age_group")
WITH totals AS (
    SELECT age_group,
           COUNT(*)::bigint AS transactions,
           SUM(orders)::bigint AS orders,
           ROUND(SUM(amount), 2) AS amount
    FROM diwali_sales
    GROUP BY age_group
)
SELECT age_group,
       transactions,
       orders,
       amount::float8 AS amount,
       ROUND(100.0 * amount / SUM(amount) OVER (), 2)::float8 AS amount_share_pct,
       ROUND(100.0 * SUM(amount) OVER (ORDER BY amount DESC, age_group) / SUM(amount) OVER (), 2)::float8
           AS cumulative_amount_share_pct,
       RANK() OVER (ORDER BY amount DESC)::int AS amount_rank
FROM totals
ORDER BY amount DESC, age_group;
