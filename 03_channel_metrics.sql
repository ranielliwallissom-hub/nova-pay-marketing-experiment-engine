-- 03_channel_metrics.sql
--
-- Channel-level performance: spend, clicks, attributed conversions, and
-- two derived metrics -- CPC and attributed CAC. NOTE: "attributed CAC"
-- here is built from ATTRIBUTED conversions, not incremental ones -- this
-- is deliberately labeled to avoid the attribution-vs-incrementality
-- confusion the whole project is built around. Never call this "iCAC".

SELECT
    DATE_TRUNC('month', week) AS month,
    city,
    channel,
    SUM(spend) AS total_spend,
    SUM(clicks) AS total_clicks,
    SUM(attributed_conversions) AS total_attributed_conversions,
    ROUND(SUM(spend) / NULLIF(SUM(clicks), 0), 2) AS cpc,
    ROUND(SUM(spend) / NULLIF(SUM(attributed_conversions), 0), 2) AS attributed_cac
FROM channel_performance
GROUP BY DATE_TRUNC('month', week), city, channel
ORDER BY month, city, channel;
