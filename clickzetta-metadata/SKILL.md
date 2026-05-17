---
name: clickzetta-metadata
description: |
  查询 ClickZetta Lakehouse 元数据，覆盖两种方式：
  SHOW/DESC 命令族（实时，适合单个对象即时查询）和
  INFORMATION_SCHEMA 视图（支持复杂 SQL 分析、费用归因、跨对象统计）。
  当用户说"查看表列表"、"查看字段"、"查看作业历史"、"SHOW TABLES"、
  "DESC TABLE"、"查看分区"、"查看权限"、"SHOW GRANTS"、"查看 Volume"、
  "费用分析"、"成本归因"、"用量统计"、"元数据查询"、"information_schema"时触发。
  注意：本 skill 仅覆盖只读元数据查询；权限变更请使用 clickzetta-access-control。
  Keywords: SHOW, DESC, metadata, load_history, information_schema, job history, cost analysis, CRU
---

# ClickZetta 元数据查询指南

## 执行方式

所有 SQL 通过 `cz-cli sql` 执行，无需 MCP 工具。

**执行示例：**

```bash
# 执行 SHOW/DESC 查询
cz-cli sql "SHOW TABLES" --sync -o table

# 执行 information_schema 查询
cz-cli sql "SELECT * FROM information_schema.tables LIMIT 10" --sync -o table

# 执行 load_history 查询
cz-cli sql "SELECT * FROM load_history('my_schema.my_table') LIMIT 20" --sync -o table
```

注意：`--sync` 等待结果返回；`-o table` 输出为表格格式便于阅读。

---

## 选择查询方式

| 场景 | 推荐方式 | 原因 |
|---|---|---|
| 快速查看当前状态（表、字段、集群） | `SHOW` / `DESC` | 实时，无延迟 |
| 复杂 SQL 分析、聚合统计 | `information_schema` | 支持 JOIN/GROUP BY/WHERE |
| 查看已删除对象 | `SHOW TABLES HISTORY` | 专用命令，实时 |
| 费用分析（含金额） | `SYS.information_schema.INSTANCE_USAGE` / `STORAGE_METERING` | 含实际金额字段 |
| CRU 消耗统计（无金额） | `information_schema.JOB_HISTORY` | 支持按用户/时间聚合 |
| 导入文件去重 | `load_history()` | 专用函数 |
| 跨空间查询 | `SYS.information_schema.*` | 需 INSTANCE ADMIN |

**延迟说明**：SHOW/DESC 实时返回；information_schema 视图有约 15 分钟延迟。

---

## 支持的命令与视图全览

**SHOW 命令**：TABLES / SCHEMAS / CATALOGS / COLUMNS / VOLUMES / CONNECTIONS / JOBS / VCLUSTERS /
PIPES / SHARES / USERS / ROLES / GRANTS / FUNCTIONS / TABLE STREAMS / PARTITIONS / SYNONYMS / INDEX /
DYNAMIC TABLE REFRESH HISTORY / TABLES HISTORY

**DESC 命令**：TABLE / SCHEMA / HISTORY / VCLUSTER / VOLUME / CONNECTION / FUNCTION / VIEW /
DYNAMIC TABLE / SHARE / INDEX / TABLE STREAM

**其他**：SHOW CREATE TABLE、load_history()、FROM (SHOW ...) 子查询、上下文函数

**INFORMATION_SCHEMA 视图**（空间级）：TABLES / COLUMNS / JOB_HISTORY / USERS / ROLES /
VOLUMES / CONNECTIONS / MATERIALIZED_VIEW_REFRESH_HISTORY / AUTOMV_REFRESH_HISTORY / SORTKEY_CANDIDATES

**INFORMATION_SCHEMA 视图**（实例级，需 INSTANCE ADMIN）：WORKSPACES / SCHEMAS / TABLES / COLUMNS /
VIEWS / USERS / ROLES / JOB_HISTORY / VOLUMES / CONNECTIONS / OBJECT_PRIVILEGES /
STORAGE_METERING / INSTANCE_USAGE

---

## 参考文档

- [SHOW/DESC 完整语法](references/show-desc-reference.md)
- [空间级 INFORMATION_SCHEMA 视图](references/views-reference.md)
- [实例级视图（需 INSTANCE ADMIN）](references/instance-views-reference.md)
- [费用计量视图（STORAGE_METERING / INSTANCE_USAGE）](references/metering-views-reference.md)

---

## SHOW / DESC 快速参考

### 当前上下文

```sql
SELECT current_workspace(), current_schema(), current_user(), current_vcluster();
```

### 数据对象

```sql
-- Schema
SHOW SCHEMAS;
SHOW SCHEMAS EXTENDED;
SHOW SCHEMAS LIKE 'ods%';

-- 表（含视图/物化视图/动态表/外部表）
SHOW TABLES;
SHOW TABLES IN my_schema;
SHOW TABLES LIKE '%order%';
SHOW TABLES WHERE is_view = false AND is_materialized_view = false;  -- 普通表
SHOW TABLES WHERE is_view = true;                                    -- 视图
SHOW TABLES WHERE is_materialized_view = true;                       -- 物化视图
SHOW TABLES WHERE is_dynamic = true;                                 -- 动态表
SHOW TABLES WHERE is_external = true;                                -- 外部表
-- ⚠️ SHOW VIEWS IN schema 语法不支持，用 SHOW TABLES WHERE is_view=true

-- 字段
SHOW COLUMNS IN my_schema.my_table;
SHOW COLUMNS FROM my_table IN my_schema;

-- 完整建表语句
SHOW CREATE TABLE my_table;

-- 分区
SHOW PARTITIONS my_table;
SHOW PARTITIONS EXTENDED my_table;
SHOW PARTITIONS my_table PARTITION (dt = '2024-01');
-- ⚠️ SHOW PARTITIONS WHERE col='x' 不支持，需用 PARTITION() 子句

-- Volume（不支持 IN schema，用 WHERE 过滤）
SHOW VOLUMES;
SHOW VOLUMES WHERE schema_name = 'my_schema';

-- Table Stream
SHOW TABLE STREAMS;
SHOW TABLE STREAMS IN my_schema;

-- 索引
SHOW INDEX IN my_schema.my_table;

-- 函数
SHOW FUNCTIONS LIKE '%date%';
SHOW EXTERNAL FUNCTIONS;
-- ⚠️ 不支持 IN schema 子句

-- 历史（含已删除表）
SHOW TABLES HISTORY;
SHOW TABLES HISTORY IN my_schema;
```

### Catalog（联邦查询）

```sql
SHOW CATALOGS;
SHOW SCHEMAS IN catalog_name;
SHOW TABLES IN catalog_name.schema_name;
```

### 计算与连接

```sql
-- 计算集群
SHOW VCLUSTERS;
SHOW VCLUSTERS WHERE state = 'RUNNING';

-- 作业（最近 7 天，最多 10000 条，不支持 ORDER BY）
SHOW JOBS LIMIT 20;
SHOW JOBS IN VCLUSTER default LIMIT 20;

-- 动态表刷新历史（最近 7 天）
SHOW DYNAMIC TABLE REFRESH HISTORY LIMIT 20;
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE state = 'FAILED';

-- 连接对象
SHOW CONNECTIONS;
SHOW CONNECTIONS WHERE category = 'STORAGE';

-- Pipe
SHOW PIPES;
SHOW PIPES IN my_schema;
```

### 用户、权限与共享

```sql
SHOW USERS;
SHOW ROLES;
SHOW GRANTS TO USER alice;
SHOW GRANTS TO ROLE analyst_role;
SHOW SHARES;
```

### DESC 命令

```sql
DESC my_table;
DESC EXTENDED my_table;          -- 含 last_modified_time/properties/statistics
DESC SCHEMA my_schema;
DESC VCLUSTER default;
DESC VOLUME my_volume;
DESC CONNECTION my_oss_conn;
DESC FUNCTION my_schema.my_function;  -- 仅支持外部函数
DESC SHARE my_share_name;
DESC CATALOG my_catalog;

-- 版本历史（依赖 data_retention_days）
DESC HISTORY my_table;
-- 返回：version, time, total_rows, total_bytes, user, operation, job_id
```

### load_history() — 文件导入历史

```sql
-- 参数必须是带引号的字符串
SELECT file_path, last_copy_time, file_size, status, first_error_message
FROM load_history('my_schema.my_table')
ORDER BY last_copy_time DESC
LIMIT 20;
-- ⚠️ load_history(schema.table) 不带引号会报错
```

### FROM (SHOW ...) 子查询

```sql
-- 过滤 SHOW 结果
SELECT schema_name, table_name
FROM (SHOW TABLES IN my_schema)
WHERE is_view = false;

-- 统计各类型表数量
SELECT
  CASE WHEN is_view THEN 'VIEW'
       WHEN is_materialized_view THEN 'MV'
       WHEN is_dynamic THEN 'DT'
       WHEN is_external THEN 'EXTERNAL'
       ELSE 'TABLE' END AS type,
  COUNT(*) AS cnt
FROM (SHOW TABLES IN my_schema)
GROUP BY 1;

-- 查看挂起的集群
SELECT name, state FROM (SHOW VCLUSTERS) WHERE state = 'SUSPENDED';
```

**注意**：不支持创建包含 SHOW 命令的视图。

### SHOW/DESC 注意事项

1. `SHOW SCHEMAS WHERE`：不支持，需用 `SHOW SCHEMAS EXTENDED` 后应用层过滤
2. `SHOW VIEWS IN schema`：语法报错，用 `SHOW TABLES WHERE is_view=true`
3. `SHOW VOLUMES IN schema`：语法报错，用 `SHOW VOLUMES WHERE schema_name='x'`
4. `SHOW PARTITIONS WHERE col='x'`：不支持，用 `PARTITION(col='x')` 子句
5. `SHOW JOBS`：只显示最近 7 天，最多 10000 条；不支持 ORDER BY
6. `LIKE` 和 `WHERE` 不能同时用：用 `FROM (SHOW TABLES) WHERE table_name LIKE 'x%'` 替代

---

## INFORMATION_SCHEMA 快速参考

### 层级说明

| 层级 | 访问路径 | 权限要求 | 覆盖范围 |
|---|---|---|---|
| 空间级 | `information_schema.<视图名>` | workspace_admin | 当前工作空间 |
| 实例级 | `SYS.information_schema.<视图名>` | INSTANCE ADMIN | 所有工作空间 |

**重要限制**：所有视图只读，数据有约 15 分钟延迟。空间级视图只显示当前存在的对象；实例级视图含已删除对象，用 `WHERE delete_time IS NULL` 过滤。

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
| AUTOMV_REFRESH_HISTORY | 自动物化视图刷新历史 |
| VOLUMES | Volume 对象信息 |
| CONNECTIONS | 存储连接对象信息 |
| SORTKEY_CANDIDATES | 推荐排序列 |

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

### 物化视图刷新监控

```sql
-- 最近刷新失败的物化视图
SELECT schema_name, materialized_view_name, status,
       start_time, end_time, error_message
FROM information_schema.materialized_view_refresh_history
WHERE status = 'FAILED'
  AND pt_date >= CAST(CURRENT_DATE - INTERVAL 7 DAY AS DATE)
ORDER BY start_time DESC;
```

### 费用分析（需 INSTANCE ADMIN）

费用分析使用两个实例级专有视图，**这是 JOB_HISTORY.CRU 无法替代的**：
- `STORAGE_METERING`：存储费用（托管存储/多版本存储/网络传输），含实际金额
- `INSTANCE_USAGE`：计算费用（AP/GP集群/任务调度/数据集成/流式集成），含实际金额

```sql
-- 按工作空间汇总本月计算费用
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

### 存储用量分析

```sql
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

-- 跨空间查找大表（大于 10GB）
SELECT table_catalog, table_schema, table_name,
       row_count,
       ROUND(bytes / 1024.0 / 1024 / 1024, 2) AS size_gb
FROM SYS.information_schema.tables
WHERE delete_time IS NULL
  AND bytes > 10 * 1024 * 1024 * 1024
ORDER BY bytes DESC;
```

### 用户和权限

```sql
-- 列出空间内所有用户及角色
SELECT user_name, role_names, email, create_time
FROM information_schema.users
ORDER BY create_time DESC;

-- 查看权限授予记录（需 INSTANCE ADMIN）
SELECT grantor, grantee, granted_to, object_type,
       object_schema, object_name, privilege_type, authorization_time
FROM SYS.information_schema.object_privileges
WHERE grantee = 'some_user'
ORDER BY authorization_time DESC;
```

---

## INFORMATION_SCHEMA 注意事项

1. **ROW_COUNT / BYTES 为估计值**：PRIMARY KEY 表、实时写入表、分区操作后可能不准确
2. **JOB_HISTORY 保留 60 天**：超过 60 天的历史记录会被自动清理
3. **空间级视图无 DELETE_TIME**：实例级视图含已删除对象，用 `WHERE delete_time IS NULL` 过滤
4. **JOB_HISTORY 有 PT_DATE 分区列**：用 `pt_date >= CAST(CURRENT_DATE - INTERVAL N DAY AS DATE)` 过滤，比 `start_time` 过滤性能更好
5. **STATUS 值注意**：JOB_HISTORY 成功状态为 `'SUCCEED'`（非 `'SUCCEEDED'`）；MV 刷新成功为 `'SUCCEED'`（非 `'FINISHED'`）
6. **SYS.information_schema 包含所有 workspace 数据**：不加 `table_catalog` 过滤会返回所有 workspace 的结果。字段名是 `create_time`（不是 `created_time`）
7. **STORAGE_METERING / INSTANCE_USAGE 仅实例级**：需 INSTANCE ADMIN 权限，通过 `SYS.information_schema.*` 访问；含实际金额字段，是费用分析的权威来源
