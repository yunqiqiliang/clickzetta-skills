---
name: clickzetta-metadata-query
description: |
  通过 SHOW / DESC 命令族和 load_history() 函数查询 ClickZetta Lakehouse 对象元数据。
  覆盖所有 SHOW 命令（TABLES/SCHEMAS/CATALOGS/COLUMNS/VOLUMES/CONNECTIONS/JOBS/VCLUSTERS/
  PIPES/SHARES/USERS/ROLES/GRANTS/FUNCTIONS/TABLE STREAMS/PARTITIONS/SYNONYMS/INDEX/
  DYNAMIC TABLE REFRESH HISTORY/TABLES HISTORY），所有 DESC 命令（TABLE/SCHEMA/HISTORY/
  VCLUSTER/VOLUME/CONNECTION/FUNCTION/VIEW/DYNAMIC TABLE/SHARE/INDEX/TABLE STREAM），
  SHOW CREATE TABLE，load_history()，FROM (SHOW ...) 子查询，上下文函数。
  与 information_schema 的区别：SHOW/DESC 是实时命令，返回当前状态；
  information_schema 是元数据视图，有约 15 分钟延迟但支持复杂 SQL 分析。
  当用户说"查看表列表"、"查看字段"、"查看作业"、"SHOW TABLES"、"DESC TABLE"、
  "查看分区"、"查看历史版本"、"查看删除的表"、"查看导入历史"、"load_history"、
  "SHOW JOBS"、"查看集群状态"、"查看连接"、"查看权限"、"SHOW GRANTS"、
  "查看函数"、"查看 Volume"、"查看 Share"、"查看 Catalog"时触发。
---

# ClickZetta 元数据查询命令

阅读 [references/show-desc-reference.md](references/show-desc-reference.md) 了解完整语法和返回字段。

---

## SHOW / DESC 与 information_schema 的选择

| 场景 | 推荐方式 | 原因 |
|---|---|---|
| 快速查看当前状态 | `SHOW` / `DESC` | 实时，无延迟 |
| 复杂 SQL 分析、聚合统计 | `information_schema` | 支持 JOIN/GROUP BY/WHERE |
| 查看已删除对象 | `SHOW TABLES HISTORY` | 专用命令 |
| 费用分析 | `SYS.information_schema.instance_usage` | 含金额字段 |
| 导入文件去重 | `load_history()` | 专用函数 |

---

## 当前上下文

```sql
-- 查看当前连接的工作空间、Schema、用户、集群
SELECT current_workspace(), current_schema(), current_user(), current_vcluster();
```

---

## SHOW 命令速查

### 数据对象

```sql
-- Schema
SHOW SCHEMAS;
SHOW SCHEMAS EXTENDED;          -- 含 type 字段（managed/external）
SHOW SCHEMAS LIKE 'ods%';
-- ⚠️ SHOW SCHEMAS 不支持 WHERE，需用 EXTENDED 后应用层过滤

-- 表（含视图/物化视图/动态表/外部表）
SHOW TABLES;
SHOW TABLES IN my_schema;
SHOW TABLES LIKE '%order%';
-- WHERE 支持字段：table_name / is_view / is_materialized_view / is_external / is_dynamic
SHOW TABLES WHERE is_view = false AND is_materialized_view = false;  -- 普通表
SHOW TABLES WHERE is_view = true;                                    -- 视图
SHOW TABLES WHERE is_materialized_view = true;                       -- 物化视图
SHOW TABLES WHERE is_dynamic = true;                                 -- 动态表
SHOW TABLES WHERE is_external = true;                                -- 外部表
-- ⚠️ SHOW VIEWS IN schema 语法不支持，用 SHOW TABLES WHERE is_view=true

-- 字段
SHOW COLUMNS IN my_schema.my_table;
SHOW COLUMNS FROM my_table IN my_schema;

-- 完整建表语句（表/视图/物化视图/动态表）
SHOW CREATE TABLE my_table;

-- 分区
SHOW PARTITIONS my_table;
SHOW PARTITIONS EXTENDED my_table;          -- 含 rows/bytes/files/时间戳
SHOW PARTITIONS my_table PARTITION (dt = '2024-01');  -- 按分区值过滤
-- ⚠️ SHOW PARTITIONS WHERE dt='x' 不支持，需用 PARTITION() 子句

-- Volume（不支持 IN schema，用 WHERE 过滤）
SHOW VOLUMES;
SHOW VOLUMES LIKE '%oss%';
SHOW VOLUMES WHERE schema_name = 'my_schema';

-- Table Stream
SHOW TABLE STREAMS;
SHOW TABLE STREAMS IN my_schema;
SHOW TABLE STREAMS LIKE '%orders%';

-- 同义词
SHOW SYNONYMS IN my_schema;

-- 索引
SHOW INDEX IN my_schema.my_table;

-- 语义视图
SHOW SEMANTIC VIEWS;
SHOW SEMANTIC VIEWS IN my_schema;

-- 函数
SHOW FUNCTIONS LIKE '%date%';           -- 内置函数（按名称过滤）
SHOW EXTERNAL FUNCTIONS;                -- 用户创建的外部函数
SHOW EXTERNAL FUNCTIONS IN my_schema;
```

### Catalog（联邦查询）

```sql
-- 查看所有 Catalog（含 SHARED 和 EXTERNAL 类型）
SHOW CATALOGS;
-- 返回：workspace_name, created_time, category(SHARED/EXTERNAL)

-- 查看 Catalog 下的 Schema
SHOW SCHEMAS IN catalog_name;

-- 查看 Catalog.Schema 下的表
SHOW TABLES IN catalog_name.schema_name;
```

### 计算与连接

```sql
-- 计算集群
SHOW VCLUSTERS;
SHOW VCLUSTERS WHERE state = 'RUNNING';
SHOW VCLUSTERS WHERE vcluster_type = 'ANALYTICS';

-- 作业（最近 7 天，最多 10000 条）
SHOW JOBS LIMIT 20;
SHOW JOBS IN VCLUSTER default_ap LIMIT 20;

-- 动态表刷新历史（最近 7 天）
SHOW DYNAMIC TABLE REFRESH HISTORY LIMIT 20;
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE state = 'FAILED';

-- 连接对象
SHOW CONNECTIONS;
SHOW CONNECTIONS LIKE '%oss%';
SHOW CONNECTIONS WHERE category = 'STORAGE';

-- Pipe
SHOW PIPES;
SHOW PIPES IN my_schema;
```

### 用户、权限与共享

```sql
-- 用户
SHOW USERS;

-- 角色
SHOW ROLES;

-- 权限
SHOW GRANTS TO USER alice;
SHOW GRANTS TO ROLE analyst_role;

-- 数据共享
SHOW SHARES;
-- 返回：share_name, provider, provider_instance, provider_workspace, scope, to_instance, kind(OUTBOUND/INBOUND)
```

### 历史记录

```sql
-- 表历史（含已删除表，delete_time 为 NULL 表示未删除）
SHOW TABLES HISTORY;
SHOW TABLES HISTORY IN my_schema;
SHOW TABLES HISTORY LIKE '%temp%';
```

---

## DESC 命令速查

```sql
-- 表/视图/动态表/物化视图字段
DESC my_table;
DESC EXTENDED my_table;          -- 含 last_modified_time/properties/statistics

-- Schema
DESC SCHEMA my_schema;
DESC SCHEMA EXTENDED my_schema;  -- 含 creator/created_time/type

-- 计算集群
DESC VCLUSTER default_ap;
DESC VCLUSTER EXTENDED default_ap;

-- Volume
DESC VOLUME my_volume;
DESC VOLUME EXTENDED my_volume;

-- 连接对象
DESC CONNECTION my_oss_conn;
DESC CONNECTION EXTENDED my_oss_conn;

-- 外部函数（仅支持用户创建的外部函数，不支持内置函数）
DESC FUNCTION my_schema.my_function;

-- 视图（返回字段列表）
DESC VIEW my_view;

-- 动态表（返回字段 + 调度配置）
DESC DYNAMIC TABLE my_dt;

-- 索引
DESC INDEX idx_name;

-- Table Stream
DESC TABLE STREAM my_stream;

-- Share（返回共享的对象列表）
DESC SHARE my_share_name;
-- 返回：kind(WORKSPACE/SCHEMA/TABLE), name, shared_on

-- Catalog
DESC CATALOG my_catalog;
```

---

## DESC HISTORY — 查看版本历史

```sql
-- 表/动态表/物化视图的版本历史（依赖 data_retention_days）
DESC HISTORY my_table;
-- 返回：version, time, total_rows, total_bytes, user, operation, job_id, stats
-- operation 值：INSERT_INTO / UPDATE / DELETE / ALTER / CREATE / REFRESH 等
```

---

## load_history() — 查看文件导入历史

```sql
-- 参数必须是带引号的字符串（含 schema 前缀）
SELECT * FROM load_history('my_schema.my_table');
SELECT file_path, last_copy_time, file_size, status, first_error_message
FROM load_history('my_schema.my_table')
ORDER BY last_copy_time DESC
LIMIT 20;
-- ⚠️ load_history(schema.table) 不带引号会报错
```

---

## FROM (SHOW ...) 子查询 — 重要特性

SHOW 命令结果可以直接作为子查询使用，支持 WHERE/GROUP BY/JOIN 等操作：

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

-- 结合 information_schema 深度分析
SELECT t.table_name, t.is_dynamic, i.create_time, i.row_count
FROM (SHOW TABLES WHERE is_dynamic = true) t
LEFT JOIN information_schema.tables i
  ON t.table_name = i.table_name AND t.schema_name = i.table_schema;
```

**注意**：不支持创建包含 SHOW 命令的视图（`CREATE VIEW AS SELECT * FROM (SHOW TABLES)` 会失败）。

---

## 注意事项

1. **`SHOW SCHEMAS WHERE`**：不支持，需用 `SHOW SCHEMAS EXTENDED` 后应用层过滤
2. **`SHOW VIEWS IN schema`**：语法报错，用 `SHOW TABLES WHERE is_view=true`
3. **`SHOW VOLUMES IN schema`**：语法报错，用 `SHOW VOLUMES WHERE schema_name='x'`
4. **`SHOW PARTITIONS WHERE col='x'`**：不支持按分区列名过滤，用 `PARTITION(col='x')` 子句
5. **`load_history()` 语法**：参数必须是带引号的字符串 `'schema.table'`
6. **`DESC FUNCTION`**：仅支持用户创建的外部函数，不支持内置函数
7. **`SHOW JOBS`**：只显示最近 7 天，最多 10000 条
8. **`SHOW DYNAMIC TABLE REFRESH HISTORY`**：只显示最近 7 天，最多 10000 条
9. **`LIKE` 和 `WHERE` 不能同时用**：用 `FROM (SHOW TABLES) WHERE table_name LIKE 'x%'` 替代
