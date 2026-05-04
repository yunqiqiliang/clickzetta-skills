# Dynamic Table 应用模式参考

## 模式 1：Medallion 三层架构

```
Bronze（原始数据）
    ↓ Dynamic Table（清洗，INCREMENTAL）
Silver（清洗数据）
    ↓ Dynamic Table（聚合，FULL）
Gold（指标数据）
    ↓ BI 工具直接查询
```

**Bronze → Silver**（增量清洗，推荐 INCREMENTAL）：
```sql
ALTER TABLE bronze.raw_orders SET PROPERTIES ('change_tracking' = 'true');

CREATE DYNAMIC TABLE IF NOT EXISTS silver.orders_cleaned
  PROPERTIES ('target_lag' = '15 minutes', 'warehouse' = 'default_ap')
AS
SELECT
  order_id,
  customer_id,
  CAST(amount AS DECIMAL(18,2))          AS amount,
  CAST(created_at AS TIMESTAMP)          AS created_at,
  COALESCE(region, 'unknown')            AS region
FROM bronze.raw_orders
WHERE order_id IS NOT NULL AND amount > 0;
```

**Silver → Gold**（聚合指标，通常 FULL）：
```sql
CREATE DYNAMIC TABLE IF NOT EXISTS gold.orders_daily_summary
  PROPERTIES ('target_lag' = '1 hour', 'warehouse' = 'default_ap')
AS
SELECT
  DATE(created_at)        AS stat_date,
  region,
  COUNT(*)                AS order_count,
  SUM(amount)             AS total_revenue,
  COUNT(DISTINCT customer_id) AS unique_customers
FROM silver.orders_cleaned
GROUP BY 1, 2;
```

---

## 模式 2：实时看板物化

适合 BI 工具（Superset、Grafana）直接查询，避免每次请求都跑重查询：

```sql
CREATE DYNAMIC TABLE IF NOT EXISTS rpt.realtime_dashboard
  PROPERTIES ('target_lag' = '5 minutes', 'warehouse' = 'default_ap')
AS
SELECT
  DATE_TRUNC('hour', event_time)  AS hour_bucket,
  event_type,
  COUNT(*)                        AS event_count,
  COUNT(DISTINCT user_id)         AS unique_users
FROM silver.events_cleaned
WHERE event_time >= DATEADD('day', -7, CURRENT_TIMESTAMP)
GROUP BY 1, 2;
```

---

## 模式 3：多源 JOIN 物化

将多表 JOIN 结果物化，避免 BI 查询时重复 JOIN：

```sql
CREATE DYNAMIC TABLE IF NOT EXISTS gold.order_detail_enriched
  PROPERTIES ('target_lag' = '30 minutes', 'warehouse' = 'default_ap')
AS
SELECT
  o.order_id,
  o.amount,
  o.created_at,
  c.name        AS customer_name,
  c.tier        AS customer_tier,
  p.name        AS product_name,
  p.category    AS product_category
FROM silver.orders_cleaned o
LEFT JOIN dim.customers c ON o.customer_id = c.customer_id
LEFT JOIN dim.products  p ON o.product_id  = p.product_id;
```

---

## 模式 4：滑动窗口指标

```sql
-- 过去 24 小时滚动指标（每 15 分钟刷新）
CREATE DYNAMIC TABLE IF NOT EXISTS rpt.rolling_24h_metrics
  PROPERTIES ('target_lag' = '15 minutes', 'warehouse' = 'default_ap')
AS
SELECT
  COUNT(*)                AS orders_24h,
  SUM(amount)             AS revenue_24h,
  AVG(amount)             AS avg_order_value_24h,
  COUNT(DISTINCT customer_id) AS unique_buyers_24h
FROM silver.orders_cleaned
WHERE created_at >= DATEADD('hour', -24, CURRENT_TIMESTAMP);
```

---

## 刷新模式决策树

```
查询是否包含 DISTINCT / 窗口函数 / 复杂子查询？
├── 是 → FULL 刷新（系统自动选择）
└── 否 → 源表是否开启 change_tracking？
         ├── 是 → INCREMENTAL 刷新（高效）
         └── 否 → FULL 刷新
                  建议：ALTER TABLE ... SET PROPERTIES ('change_tracking' = 'true')
```

---

## target_lag 选择指南

| 业务场景 | 推荐 target_lag |
|---|---|
| 实时监控大屏 | `'5 minutes'` |
| 运营日报 | `'1 hour'` |
| 管理层周报 | `'1 day'` |
| 历史归档分析 | `'1 day'` 或 refresh_schedule |
| BI 报表（非实时） | `'30 minutes'` ~ `'2 hours'` |

> ⚠️ target_lag 越小，VCluster 计算资源消耗越大。生产环境建议先用 `'1 hour'`，按需调小。
