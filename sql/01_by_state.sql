-- Sales and orders by state.
-- A CTE aggregates per state; window functions then add the share of the total,
-- the running (cumulative) share when sorted by amount, and the RANK.
-- Pandas equivalent: festival_sales.analysis.summarize(df, "state")
WITH totals AS (
    SELECT state,
           COUNT(*)::bigint AS transactions,
           SUM(orders)::bigint AS orders,
           ROUND(SUM(amount), 2) AS amount
    FROM diwali_sales
    GROUP BY state
)
SELECT state,
       transactions,
       orders,
       amount::float8 AS amount,
       ROUND(100.0 * amount / SUM(amount) OVER (), 2)::float8 AS amount_share_pct,
       ROUND(100.0 * SUM(amount) OVER (ORDER BY amount DESC, state) / SUM(amount) OVER (), 2)::float8
           AS cumulative_amount_share_pct,
       RANK() OVER (ORDER BY amount DESC)::int AS amount_rank
FROM totals
ORDER BY amount DESC, state;
