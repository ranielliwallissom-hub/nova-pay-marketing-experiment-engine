-- 01_data_quality.sql
--
-- Data quality audit. This should run FIRST, before anything else touches
-- the data. Checks: row counts, null counts, duplicate grain, and join
-- integrity between city_metrics and channel_performance.

-- Row counts
SELECT 'city_metrics' AS table_name, COUNT(*) AS row_count FROM city_metrics
UNION ALL
SELECT 'channel_performance', COUNT(*) FROM channel_performance
UNION ALL
SELECT 'cohort_retention', COUNT(*) FROM cohort_retention;

-- Null checks (city_metrics)
SELECT
    SUM(CASE WHEN week IS NULL THEN 1 ELSE 0 END) AS null_week,
    SUM(CASE WHEN city IS NULL THEN 1 ELSE 0 END) AS null_city,
    SUM(CASE WHEN new_customers IS NULL THEN 1 ELSE 0 END) AS null_new_customers,
    SUM(CASE WHEN revenue IS NULL THEN 1 ELSE 0 END) AS null_revenue
FROM city_metrics;

-- Duplicate grain check: (week, city) should be unique in city_metrics
SELECT week, city, COUNT(*) AS n
FROM city_metrics
GROUP BY week, city
HAVING COUNT(*) > 1;

-- Duplicate grain check: (week, city, channel) should be unique in channel_performance
SELECT week, city, channel, COUNT(*) AS n
FROM channel_performance
GROUP BY week, city, channel
HAVING COUNT(*) > 1;

-- Join integrity: every (week, city) in city_metrics should exist in channel_performance, and vice versa
SELECT cm.week, cm.city
FROM city_metrics cm
LEFT JOIN (SELECT DISTINCT week, city FROM channel_performance) cp
    ON cm.week = cp.week AND cm.city = cp.city
WHERE cp.week IS NULL;
