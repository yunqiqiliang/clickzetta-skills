---
name: clickzetta-information-schema
description: |
  查询 ClickZetta Lakehouse INFORMATION_SCHEMA 元数据视图，获取表结构、字段信息、
  作业历史、用户权限、Volume 和 Connection 等元数据。支持空间级（当前工作空间）
  和实例级（所有工作空间，需 INSTANCE ADMIN）两个层级的查询。
  费用分析：JOB_HISTORY.CRU 字段统计计算消耗，TABLES.BYTES 统计存储用量，
  SYS.information_schema.WORKSPACES.WORKSPACE_STORAGE 汇总跨空间存储，
  可按用户/工作空间/时间段做成本归因和趋势分析。
  当用户说"查看表结构"、"查看字段信息"、"查看作业历史"、"查看 JOB 历史"、
  "查看慢查询"、"查看 CRU 消耗"、"费用分析"、"成本分析"、"计算费用"、
  "存储费用"、"用量统计"、"成本归因"、"哪个用户消耗最多"、"存储用量排行"、
  "查看用户列表"、"查看角色"、"查看权限"、
  "查看 Volume 列表"、"查看 Connection"、"查看物化视图刷新历史"、
  "元数据查询"、"information_schema"、"查看所有表"、"查看 Schema 列表"、
  "统计存储用量"、"查看删除的表"时触发。
---

# ClickZetta Lakehouse INFORMATION_SCHEMA 查询指南

## 概述

INFORMATION_SCHEMA 提供对 Lakehouse 元数据的只读查询能力，分为两个层级：

| 层级 | 访问路径 | 权限要求 | 覆盖范围 |
|---|---|---|---|
| 实例级 | `SYS.information_schema.<视图名>` | INSTANCE ADMIN | 所有工作空间的元数据 |
| 空间级 | `information_schema.<视图名>` | workspace_admin | 当前工作空间的元数据 |

**重要限制：**
- 所有视图只读，不可写入
- 数据有约 15 分钟延迟
- 建议使用 `SELECT 具体列名` 而非 `SELECT *`，避免视图结构变更导致任务失败
- 空间级视图只显示当前存在的对象（无 DELETE_TIME 字段）；实例级视图含已删除对象，用 `WHERE delete_time IS NULL` 过滤

---

## 快速参考：可用视图

### 空间级视图（`information_schema.*`）

| 视图名 | 说明 |
|---|---|
| SCHEMAS | 当前空间下的所有 Schema |
| TABLES | 当前空间下的所有表（含视图、物化视图） |
| COLUMNS | 所有表的字段信息 |
| VIEWS | 所有视图定义 |
| USERS | 空间内用户及角色 |
| ROLES | 空间内角色及成员 |
| JOB_HISTORY | 作业执行历史（保留 60 天，含 PT_DATE 分区列） |
| MATERIALIZED_VIEW_REFRESH_HISTORY | 物化视图刷新历史（含 PT_DATE 分区列） |
| AUTOMV_REFRESH_HISTORY | 自动物化视图刷新历史（含 PT_DATE 分区列） |
| VOLUMES | Volume 对象信息 |
| CONNECTIONS | 存储连接对象信息 |
| SORTKEY_CANDIDATES | 推荐排序列（由系统自动分析生成） |

### 实例级视图（`SYS.information_schema.*`）

| 视图名 | 说明 |
|---|---|
| WORKSPACES | 所有工作空间信息（含存储用量） |
| SCHEMAS | 所有空间的 Schema（含删除记录） |
| TABLES | 所有空间的表（含删除记录） |
| COLUMNS | 所有空间的字段（含删除记录） |
| VIEWS | 所有空间的视图 |
| USERS | 所有空间的用户 |
| ROLES | 所有空间的角色 |
| JOB_HISTORY | 所有空间的作业历史 |
| MATERIALIZED_VIEW_REFRESH_HISTORY | 所有空间的物化视图刷新历史 |
| AUTOMV_REFRESH_HISTORY | 所有空间的自动物化视图刷新历史 |
| VOLUMES | 所有空间的 Volume |
| CONNECTIONS | 所有空间的连接对象 |
| OBJECT_PRIVILEGES | 权限授予记录 |
| SORTKEY_CANDIDATES | 所有空间的排序列推荐 |
| **STORAGE_METERING** ⭐ | **存储费用明细（托管存储/多版本存储/网络传输），按天按空间** |
| **INSTANCE_USAGE** ⭐ | **计算费用明细（AP/GP集群/任务调度/数据集成），按天按空间** |

---

## 常用查询示例

### 查看表结构

```sql
-- 列出当前空间所有表
SELECT table_schema, table_name, table_type, row_count, bytes, create_time
FROM information_schema.tables
WHERE table_type = 'MANAGED_TABLE'
ORDER BY table_schema, table_name;

-- 查看某张表的字段
SELECT column_name, data_type, is_nullable, is_primary_key, is_clustering_column, comment
FROM information_schema.columns
WHERE table_schema = 'my_schema'
  AND table_name = 'my_table'
ORDER BY column_name;

-- 查找包含特定字段名的表
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE column_name ILIKE '%user_id%';
```

### 查看 Schema 信息

```sql
-- 列出所有 Schema
SELECT schema_name, type, schema_creator, create_time, comment
FROM information_schema.schemas
ORDER BY create_time DESC;

-- 查找外部 Schema
SELECT schema_name, schema_creator, create_time
FROM information_schema.schemas
WHERE type = 'EXTERNAL';
```

### 查看作业历史

```sql
-- 最近 24 小时的作业
SELECT job_id, job_creator, status, execution_time, cru,
       input_bytes, output_bytes, start_time
FROM information_schema.job_history
WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 1 DAY AS DATE)
ORDER BY start_time DESC;

-- 失败的作业
SELECT job_id, job_creator, job_text, error_message, start_time
FROM information_schema.job_history
WHERE status = 'FAILED'
  AND pt_date >= CAST(CURRENT_DATE - INTERVAL 7 DAY AS DATE)
ORDER BY start_time DESC;

-- 按用户统计 CRU 消耗（最近 30 天）
-- 注意：status 成功值为 'SUCCEED'（非 'SUCCEEDED'）
-- 推荐用 pt_date 分区列过滤，性能更好
SELECT job_creator,
       COUNT(*) AS job_count,
       SUM(cru) AS total_cru,
       AVG(execution_time) AS avg_exec_sec
FROM information_schema.job_history
WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 30 DAY AS DATE)
  AND status = 'SUCCEED'
GROUP BY job_creator
ORDER BY total_cru DESC;

-- 慢查询（超过 60 秒）
SELECT job_id, job_creator, execution_time, input_bytes, job_text
FROM information_schema.job_history
WHERE execution_time > 60
  AND pt_date >= CAST(CURRENT_DATE - INTERVAL 7 DAY AS DATE)
ORDER BY execution_time DESC
LIMIT 20;
```

### 查看 Volume 信息

```sql
-- 列出所有外部 Volume
SELECT volume_name, volume_type, volume_region, volume_creator,
       connection_name, create_time
FROM information_schema.volumes
WHERE volume_type = 'EXTERNAL';

-- 查找特定 Schema 下的 Volume
SELECT volume_name, volume_url, volume_type, volume_creator
FROM information_schema.volumes
WHERE volume_schema = 'my_schema';
```

### 查看用户和权限

```sql
-- 列出空间内所有用户及角色
SELECT user_name, role_names, email, create_time
FROM information_schema.users
ORDER BY create_time DESC;

-- 查看角色成员
SELECT role_name, user_names
FROM information_schema.roles
ORDER BY role_name;
```

### 物化视图刷新监控

```sql
-- 最近刷新失败的物化视图
SELECT schema_name, materialized_view_name, status,
       start_time, end_time, error_message
FROM information_schema.materialized_view_refresh_history
WHERE status = 'FAILED'
  AND pt_date >= CAST(CURRENT_DATE - INTERVAL 7 DAY AS DATE)
ORDER BY start_time DESC;

-- 物化视图刷新耗时统计
SELECT materialized_view_name,
       COUNT(*) AS refresh_count,
       AVG(DATEDIFF('second', start_time, end_time)) AS avg_seconds,
       SUM(cru) AS total_cru
FROM information_schema.materialized_view_refresh_history
WHERE status = 'SUCCEED'
GROUP BY materialized_view_name
ORDER BY avg_seconds DESC;
```

### 费用分析（需 INSTANCE ADMIN）

费用分析使用两个实例级专有视图，**这是 JOB_HISTORY.CRU 无法替代的**：
- `STORAGE_METERING`：存储费用（托管存储/多版本存储/网络传输），含实际金额
- `INSTANCE_USAGE`：计算费用（AP/GP集群/任务调度/数据集成/流式集成），含实际金额

```sql
-- 按工作空间汇总本月计算费用（AP/GP/调度/集成）
SELECT workspace_name,
       sku_name,
       ROUND(SUM(measurements_consumption), 2) AS total_cru,
       ROUND(SUM(amount), 2) AS total_amount_yuan
FROM SYS.information_schema.instance_usage
WHERE measurement_start >= DATE_TRUNC('month', CURRENT_DATE)
  AND sku_category = 'compute'
GROUP BY workspace_name, sku_name
ORDER BY total_amount_yuan DESC;

-- 按工作空间汇总本月存储费用
SELECT workspace_name,
       sku_name,
       ROUND(SUM(measurements_consumption), 4) AS consumption,
       measurements_unit,
       ROUND(SUM(amount), 4) AS total_amount_yuan
FROM SYS.information_schema.storage_metering
WHERE measurement_start >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY workspace_name, sku_name, measurements_unit
ORDER BY workspace_name, total_amount_yuan DESC;

-- 存储 + 计算综合费用汇总（本月）
SELECT cost_type, workspace_name,
       ROUND(SUM(total_amount), 2) AS total_yuan
FROM (
  SELECT 'compute' AS cost_type, workspace_name, amount AS total_amount
  FROM SYS.information_schema.instance_usage
  WHERE measurement_start >= DATE_TRUNC('month', CURRENT_DATE)
  UNION ALL
  SELECT 'storage' AS cost_type, workspace_name, amount AS total_amount
  FROM SYS.information_schema.storage_metering
  WHERE measurement_start >= DATE_TRUNC('month', CURRENT_DATE)
) t
GROUP BY cost_type, workspace_name
ORDER BY cost_type, total_yuan DESC;

-- 按天统计计算费用趋势（最近 30 天）
SELECT DATE(measurement_start) AS dt,
       sku_name,
       ROUND(SUM(amount), 2) AS daily_amount_yuan
FROM SYS.information_schema.instance_usage
WHERE measurement_start >= CURRENT_DATE - INTERVAL 30 DAY
  AND sku_category = 'compute'
GROUP BY DATE(measurement_start), sku_name
ORDER BY dt, daily_amount_yuan DESC;
```

**INSTANCE_USAGE SKU 枚举值（sku_category = 'compute'）：**

| sku_name | 说明 |
|---|---|
| AP类型计算集群 | 分析型 VCluster 费用 |
| GP类型计算集群 | 通用型 VCluster 费用 |
| 任务调度 | Studio 任务调度费用 |
| 数据集成 | 离线/实时同步任务费用 |
| 流式集成 | 流式数据集成费用 |

**STORAGE_METERING SKU 枚举值：**

| sku_category | sku_name | 说明 |
|---|---|---|
| storage | 托管存储容量 | 内部表数据存储 |
| storage | 多版本未删除存储 | Time Travel 历史版本存储 |
| network | 数据查询Internet数据传输 | 公网数据传输费用 |

```sql
-- 按用户统计 CRU 消耗（从 JOB_HISTORY，不含金额）
SELECT job_creator,
       COUNT(*) AS job_count,
       ROUND(SUM(cru), 2) AS total_cru,
       ROUND(AVG(execution_time), 1) AS avg_exec_sec
FROM information_schema.job_history
WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 30 DAY AS DATE)
  AND status = 'SUCCEED'
GROUP BY job_creator
ORDER BY total_cru DESC;

-- 按天统计 CRU 趋势（从 JOB_HISTORY）
SELECT pt_date,
       COUNT(*) AS job_count,
       ROUND(SUM(cru), 2) AS daily_cru
FROM information_schema.job_history
WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 30 DAY AS DATE)
GROUP BY pt_date
ORDER BY pt_date;

-- 存储用量排行（当前空间，按表）
SELECT table_schema, table_name,
       ROUND(bytes / 1024.0 / 1024 / 1024, 3) AS size_gb,
       row_count
FROM information_schema.tables
WHERE table_type = 'MANAGED_TABLE'
ORDER BY bytes DESC
LIMIT 20;

-- 跨空间存储汇总（需 INSTANCE ADMIN）
SELECT workspace_name,
       ROUND(workspace_storage / 1024.0 / 1024 / 1024, 2) AS storage_gb
FROM SYS.information_schema.workspaces
WHERE delete_time IS NULL
ORDER BY workspace_storage DESC;
```

### 实例级查询（需 INSTANCE ADMIN）

```sql
-- 查看所有工作空间存储用量
SELECT workspace_name, workspace_creator,
       ROUND(workspace_storage / 1024.0 / 1024 / 1024, 2) AS storage_gb,
       create_time
FROM SYS.information_schema.workspaces
WHERE delete_time IS NULL
ORDER BY workspace_storage DESC;

-- 跨空间查找大表（大于 10GB）
SELECT table_catalog, table_schema, table_name,
       row_count,
       ROUND(bytes / 1024.0 / 1024 / 1024, 2) AS size_gb
FROM SYS.information_schema.tables
WHERE delete_time IS NULL
  AND bytes > 10 * 1024 * 1024 * 1024
ORDER BY bytes DESC;

-- 查看权限授予记录
SELECT grantor, grantee, granted_to, object_type,
       object_schema, object_name, privilege_type, authorization_time
FROM SYS.information_schema.object_privileges
WHERE grantee = 'some_user'
ORDER BY authorization_time DESC;
```

- [视图字段详细说明](references/views-reference.md)
- [实例级视图字段说明](references/instance-views-reference.md)

---

## 注意事项

1. **ROW_COUNT / BYTES 为估计值**：PRIMARY KEY 表、实时写入表、分区操作后可能不准确
2. **并发 DDL 无一致性保证**：长时间运行的查询可能看不到最新创建的对象
3. **JOB_HISTORY 保留 60 天**：超过 60 天的历史记录会被自动清理
4. **空间级视图无 DELETE_TIME**：空间级视图只显示当前存在的对象；实例级视图含已删除对象，用 `WHERE delete_time IS NULL` 过滤
5. **JOB_HISTORY 有 PT_DATE 分区列**：用 `pt_date >= CAST(CURRENT_DATE - INTERVAL N DAY AS DATE)` 过滤，比 `start_time` 过滤性能更好
6. **STATUS 值注意**：JOB_HISTORY 成功状态为 `'SUCCEED'`（非 `'SUCCEEDED'`）；MV 刷新成功为 `'SUCCEED'`（非 `'FINISHED'`）
