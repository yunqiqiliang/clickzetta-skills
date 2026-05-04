---
name: clickzetta-dynamic-table
description: |
  在 ClickZetta Lakehouse 中创建和管理 Dynamic Table（动态表），实现自动增量刷新的
  物化计算层。覆盖 CREATE DYNAMIC TABLE 完整语法、TARGET_LAG 与 REFRESH SCHEDULE
  配置、FULL vs INCREMENTAL 刷新模式选择、多级依赖链设计、刷新历史监控、
  与 Table Stream 的组合用法，以及 Medallion 架构中的典型应用模式。
  当用户说"Dynamic Table"、"动态表"、"自动刷新"、"增量刷新"、"物化视图"、
  "TARGET_LAG"、"REFRESH SCHEDULE"、"CREATE DYNAMIC TABLE"、
  "数据管道自动化"、"增量计算"、"自动物化"、"定时刷新"、
  "依赖刷新"时触发。
---

# ClickZetta Dynamic Table

Dynamic Table 是 Lakehouse 的自动增量计算原语：定义一条 SELECT 查询，系统按调度自动刷新结果，支持增量计算（只处理变更数据），无需手动编写 ETL 调度逻辑。

阅读 [references/ddl.md](references/ddl.md) 了解完整语法，[references/patterns.md](references/patterns.md) 了解典型应用模式。

---

## 核心概念

| 概念 | 说明 |
|---|---|
| **TARGET_LAG** | 数据最大延迟容忍，如 `'1 hour'`、`'5 minutes'`，系统据此决定刷新频率 |
| **REFRESH SCHEDULE** | 固定 cron 调度，与 TARGET_LAG 二选一 |
| **FULL 刷新** | 每次重算全量结果，适合复杂聚合或源表无变更跟踪 |
| **INCREMENTAL 刷新** | 只处理变更数据，效率高，需要源表开启 `change_tracking` |
| **依赖链** | Dynamic Table 可以依赖另一个 Dynamic Table，形成多级管道 |

---

## 快速开始

### 1. 创建 Dynamic Table

```sql
-- 基础语法：用 PROPERTIES 传入配置参数
CREATE DYNAMIC TABLE IF NOT EXISTS silver.orders_daily
  PROPERTIES ('target_lag' = '1 hour', 'warehouse' = 'default_ap')
AS
SELECT
  DATE(created_at)   AS order_date,
  region,
  SUM(amount)        AS total_amount,
  COUNT(*)           AS order_count
FROM bronze.raw_orders
GROUP BY 1, 2;
```

### 2. 查看状态

```sql
-- 查看表定义（含 SQL、刷新模式、调度配置）
DESC DYNAMIC TABLE silver.orders_daily;

-- 查看刷新历史（含耗时、状态、错误信息）
SHOW DYNAMIC TABLE REFRESH HISTORY FOR silver.orders_daily;
SHOW DYNAMIC TABLE REFRESH HISTORY FOR silver.orders_daily LIMIT 20;

-- 通过 information_schema.tables 查看 Dynamic Table 列表
-- is_dynamic = true 的行即为 Dynamic Table
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'silver';
```

### 3. 手动触发刷新

```sql
-- 立即刷新（不等调度）
ALTER DYNAMIC TABLE silver.orders_daily REFRESH;
```

---

## TARGET_LAG vs REFRESH SCHEDULE

```sql
-- 方式 1：TARGET_LAG — 声明数据最大延迟，系统自动决定刷新时机（推荐）
CREATE DYNAMIC TABLE my_table
  PROPERTIES ('target_lag' = '30 minutes', 'warehouse' = 'default_ap')
AS SELECT ...;

-- 方式 2：REFRESH SCHEDULE — 固定 cron 调度
CREATE DYNAMIC TABLE my_table
  PROPERTIES ('refresh_schedule' = '*/30 * * * *', 'warehouse' = 'default_ap')
AS SELECT ...;
```

**选择建议**：
- 业务对延迟有明确 SLA → 用 `target_lag`
- 需要与外部系统对齐（如每天 2 点刷新报表）→ 用 `refresh_schedule`

---

## 刷新模式

系统自动判断是否可以增量刷新。以下情况**只能 FULL 刷新**：
- 查询包含 `DISTINCT`、`UNION`、窗口函数（`ROW_NUMBER` 等）
- 源表未开启 `change_tracking`
- 查询包含子查询中的聚合

以下情况**支持 INCREMENTAL 刷新**（效率高，推荐）：
- 简单 filter + select
- GROUP BY 聚合（无 DISTINCT）
- 简单 JOIN（源表均开启 change_tracking）

开启源表变更跟踪（增量刷新前提）：
```sql
ALTER TABLE bronze.raw_orders SET PROPERTIES ('change_tracking' = 'true');
```

---

## 管理操作

```sql
-- 暂停刷新（不删除数据）
ALTER DYNAMIC TABLE silver.orders_daily SUSPEND;

-- 恢复刷新
ALTER DYNAMIC TABLE silver.orders_daily RESUME;

-- 修改 TARGET_LAG
ALTER DYNAMIC TABLE silver.orders_daily SET PROPERTIES ('target_lag' = '2 hours');

-- 修改 REFRESH SCHEDULE
ALTER DYNAMIC TABLE silver.orders_daily SET PROPERTIES ('refresh_schedule' = '0 2 * * *');

-- 删除
DROP DYNAMIC TABLE IF EXISTS silver.orders_daily;
```

---

## 典型场景

### 场景 1：Medallion 架构三层管道

```sql
-- Bronze → Silver：清洗去重（INCREMENTAL）
ALTER TABLE bronze.raw_events SET PROPERTIES ('change_tracking' = 'true');

CREATE DYNAMIC TABLE IF NOT EXISTS silver.events_cleaned
  PROPERTIES ('target_lag' = '15 minutes', 'warehouse' = 'default_ap')
AS
SELECT
  event_id,
  user_id,
  event_type,
  CAST(event_time AS TIMESTAMP) AS event_time,
  JSON_EXTRACT_SCALAR(payload, '$.page') AS page
FROM bronze.raw_events
WHERE event_id IS NOT NULL;

-- Silver → Gold：聚合指标（FULL，因含 COUNT DISTINCT）
CREATE DYNAMIC TABLE IF NOT EXISTS gold.daily_active_users
  PROPERTIES ('target_lag' = '1 hour', 'warehouse' = 'default_ap')
AS
SELECT
  DATE(event_time)        AS stat_date,
  COUNT(DISTINCT user_id) AS dau,
  COUNT(*)                AS total_events
FROM silver.events_cleaned
GROUP BY 1;
```

### 场景 2：实时报表物化

```sql
-- 每小时刷新销售汇总，供 BI 工具直接查询
CREATE DYNAMIC TABLE IF NOT EXISTS rpt.sales_hourly
  PROPERTIES ('target_lag' = '1 hour', 'warehouse' = 'default_ap')
AS
SELECT
  DATE_TRUNC('hour', order_time) AS hour_bucket,
  product_category,
  SUM(amount)                    AS revenue,
  COUNT(*)                       AS order_cnt,
  AVG(amount)                    AS avg_order_value
FROM silver.orders_cleaned
WHERE order_time >= DATEADD('day', -30, CURRENT_DATE)
GROUP BY 1, 2;
```

### 场景 3：与 Table Stream 组合（事件驱动）

```sql
-- 用 Table Stream 捕获变更，Dynamic Table 消费 Stream 做聚合
-- 注意：Stream 作为 Dynamic Table 源时，每次刷新会消费 offset
CREATE TABLE STREAM bronze.orders_stream
  ON TABLE bronze.raw_orders
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD');

CREATE DYNAMIC TABLE IF NOT EXISTS silver.orders_incremental
  PROPERTIES ('target_lag' = '5 minutes', 'warehouse' = 'default_ap')
AS
SELECT order_id, customer_id, amount, status
FROM bronze.orders_stream
WHERE __change_type IN ('INSERT', 'UPDATE_AFTER');
```

---

## 监控与排障

```sql
-- 查看刷新历史（含耗时、状态、错误信息）
-- 返回列：state, refresh_mode, duration, error_message, source_tables 等
SHOW DYNAMIC TABLE REFRESH HISTORY FOR silver.orders_daily;

-- 通过 information_schema.tables 查看当前 Schema 下的 Dynamic Table
SELECT table_name, table_type, last_modify_time
FROM information_schema.tables
WHERE table_schema = 'silver';
```

常见问题：

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 刷新一直是 FULL 模式 | 源表未开启 change_tracking，或查询含 DISTINCT/窗口函数 | 开启 change_tracking；简化查询 |
| 刷新延迟超过 target_lag | VCluster 资源不足，或查询复杂度高 | 升级 VCluster 规格；拆分查询 |
| `SUSPEND` 后数据不更新 | 已暂停 | 执行 `ALTER DYNAMIC TABLE ... RESUME` |
| 依赖链中下游不刷新 | 上游 Dynamic Table 刷新失败 | 先修复上游，再手动 `REFRESH` 下游 |
| 删除报错 | 有下游 Dynamic Table 依赖 | 先删除下游，再删除上游 |
