# Medallion 架构与 Table Stream 组合模式

## Medallion 三层管道

```
Bronze（原始数据）
    ↓ Dynamic Table（清洗，INCREMENTAL）
Silver（清洗数据）
    ↓ Dynamic Table（聚合，FULL）
Gold（指标数据）
    ↓ BI 工具直接查询
```

### Bronze → Silver（增量清洗）

```sql
-- 前提：源表开启变更跟踪
ALTER TABLE bronze.raw_orders SET PROPERTIES ('change_tracking' = 'true');

CREATE DYNAMIC TABLE IF NOT EXISTS silver.orders_cleaned
REFRESH INTERVAL 15 MINUTE vcluster default
AS
SELECT
  order_id,
  customer_id,
  CAST(amount AS DECIMAL(18,2))  AS amount,
  CAST(created_at AS TIMESTAMP)  AS created_at,
  COALESCE(region, 'unknown')    AS region
FROM bronze.raw_orders
WHERE order_id IS NOT NULL AND amount > 0;
```

### Silver → Gold（聚合指标，通常 FULL）

```sql
CREATE DYNAMIC TABLE IF NOT EXISTS gold.orders_daily_summary
REFRESH INTERVAL 60 MINUTE vcluster default
AS
SELECT
  DATE(created_at)              AS stat_date,
  region,
  COUNT(*)                      AS order_count,
  SUM(amount)                   AS total_revenue,
  COUNT(DISTINCT customer_id)   AS unique_customers
FROM silver.orders_cleaned
GROUP BY 1, 2;
```

---

## 与 Table Stream 组合（事件驱动）

Table Stream 捕获源表变更，Dynamic Table 消费 Stream 做增量处理。

### 基本模式

```sql
-- 1. 源表开启变更跟踪
ALTER TABLE bronze.raw_orders SET PROPERTIES ('change_tracking' = 'true');

-- 2. 创建 Table Stream
CREATE TABLE STREAM bronze.orders_stream
  ON TABLE bronze.raw_orders
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD');

-- 3. Dynamic Table 消费 Stream
-- 注意：Stream 作为 DT 源时，每次刷新会消费 offset
CREATE DYNAMIC TABLE IF NOT EXISTS silver.orders_incremental
REFRESH INTERVAL 5 MINUTE vcluster default
AS
SELECT order_id, customer_id, amount, status
FROM bronze.orders_stream
WHERE __change_type IN ('INSERT', 'UPDATE_AFTER');
```

### MERGE INTO + Table Stream（替代非分区 DT 的去重场景）

当需要按主键去重且源表持续写入时，推荐用 MERGE INTO 替代 Dynamic Table：

```sql
-- 1. 创建 Table Stream
CREATE TABLE STREAM source_stream ON TABLE source_table
WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD', 'SHOW_INITIAL_ROWS' = 'TRUE');

-- 2. 创建目标表
CREATE TABLE target_table (
    id BIGINT,
    col1 STRING,
    col2 INT,
    event_time TIMESTAMP
);

-- 3. 定时调度 MERGE INTO 消费 Stream
MERGE INTO target_table t
USING (
    SELECT id, col1, col2, event_time,
        CASE WHEN `value` IS NULL OR `value` = '' THEN 'DELETE' ELSE 'UPSERT' END AS op
    FROM source_stream
) s ON t.id = s.id
WHEN MATCHED AND s.op = 'UPSERT' THEN UPDATE SET
    t.col1 = s.col1, t.col2 = s.col2, t.event_time = s.event_time
WHEN NOT MATCHED AND s.op = 'UPSERT' THEN INSERT
    (id, col1, col2, event_time) VALUES (s.id, s.col1, s.col2, s.event_time);
```

---

## 实时报表物化

```sql
-- 每小时刷新销售汇总，供 BI 工具直接查询
CREATE DYNAMIC TABLE IF NOT EXISTS rpt.sales_hourly
REFRESH INTERVAL 60 MINUTE vcluster default
AS
SELECT
  DATE_TRUNC('hour', order_time) AS hour_bucket,
  product_category,
  SUM(amount)                    AS revenue,
  COUNT(*)                       AS order_cnt,
  AVG(amount)                    AS avg_order_value
FROM silver.orders_cleaned
WHERE order_time >= DATEADD(day, -30, CURRENT_DATE)
GROUP BY 1, 2;
```
