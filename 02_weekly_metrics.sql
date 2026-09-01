-- 02_weekly_metrics.sql
--
-- Weekly new customers and revenue by city. This is the corrected version
-- of the original query -- the fix was moving `city` out of GROUP BY's
-- WHERE clause (WHERE filters rows before grouping; GROUP BY only takes
-- column names to group by, not conditions) and adding `city` to both
-- SELECT and GROUP BY so we get one row per week PER CITY, not one row
-- per week across all cities combined.

SELECT
    week,
    city,
    SUM(new_customers) AS total_customers,
    SUM(revenue) AS total_revenue,
    AVG(contribution_margin) AS avg_contribution_margin
FROM city_metrics
WHERE city IN ('Berlin', 'Munich', 'Hamburg', 'Cologne', 'Frankfurt', 'Stuttgart')
GROUP BY week, city
ORDER BY week, city;
