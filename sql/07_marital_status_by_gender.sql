-- Marital status (0 = unmarried, 1 = married) crossed with gender.
-- Same shape as the single-column summaries, with two grouping keys.
-- Pandas equivalent: festival_sales.analysis.marital_status_by_gender(df)
WITH totals AS (
    SELECT marital_status,
           gender,
           COUNT(*)::bigint AS transactions,
           SUM(orders)::bigint AS orders,
           SUM(amount)::bigint AS amount
    FROM diwali_sales
    GROUP BY marital_status, gender
)
SELECT marital_status::int AS marital_status,
       gender::text AS gender,
       transactions,
       orders,
       amount,
       ROUND(100.0 * amount / SUM(amount) OVER (), 2)::float8 AS amount_share_pct,
       ROUND(100.0 * SUM(amount) OVER (ORDER BY amount DESC, marital_status, gender)
             / SUM(amount) OVER (), 2)::float8 AS cumulative_amount_share_pct,
       RANK() OVER (ORDER BY amount DESC)::int AS amount_rank
FROM totals
ORDER BY amount DESC, marital_status, gender;
