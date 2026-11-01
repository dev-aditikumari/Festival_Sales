-- Each product category's amount and its rank inside every zone.
-- RANK() is partitioned by zone, so rank 1 is the best category of that zone.
-- Pandas equivalent: festival_sales.analysis.category_rank_within_zone(df)
WITH zone_category AS (
    SELECT zone,
           product_category,
           ROUND(SUM(amount), 2) AS amount
    FROM diwali_sales
    GROUP BY zone, product_category
)
SELECT zone,
       product_category,
       amount::float8 AS amount,
       RANK() OVER (PARTITION BY zone ORDER BY amount DESC)::int AS rank_in_zone
FROM zone_category
ORDER BY zone, amount DESC, product_category;
