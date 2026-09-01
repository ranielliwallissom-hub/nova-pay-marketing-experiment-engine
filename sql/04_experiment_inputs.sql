-- 04_experiment_inputs.sql
--
-- Prepares the exact input the Python synthetic-control script needs:
-- weekly new_customers by city, with a treatment-window flag attached.
-- The flag is computed dynamically (rank weeks descending, flag the most
-- recent 12) rather than hardcoding a date -- so this query still works
-- correctly if the underlying data window changes.

WITH ranked_weeks AS (
    SELECT DISTINCT
        week,
        DENSE_RANK() OVER (ORDER BY week DESC) AS week_rank_desc
    FROM city_metrics
),
treatment_flag AS (
    SELECT
        week,
        CASE WHEN week_rank_desc <= 12 THEN 1 ELSE 0 END AS is_treatment_window
    FROM ranked_weeks
)
SELECT
    cm.week,
    cm.city,
    cm.new_customers,
    cm.revenue,
    tf.is_treatment_window
FROM city_metrics cm
JOIN treatment_flag tf ON cm.week = tf.week
ORDER BY cm.week, cm.city;

-- Bonus: wide-format version (one column per city), useful for a quick
-- visual sanity check before handing off to Python for the actual
-- synthetic control fitting.
-- SELECT * FROM (
--     SELECT week, city, new_customers FROM city_metrics
-- ) PIVOT (SUM(new_customers) FOR city IN ('Berlin','Munich','Hamburg','Cologne','Frankfurt','Stuttgart'))
-- ORDER BY week;
