---
name: clickzetta-metadata-query
description: |
  通过 SHOW / DESC 命令族和 load_history() 函数查询 ClickZetta Lakehouse 对象元数据。
  覆盖：SHOW TABLES/SCHEMAS/COLUMNS/JOBS/VCLUSTERS/CONNECTIONS/USERS/ROLES/GRANTS/
  TABLE STREAMS/PARTITIONS/DYNAMIC TABLE REFRESH HISTORY/TABLES HISTORY，
  DESC TABLE/SCHEMA/HISTORY/VCLUSTER，SHOW CREATE TABLE，load_history() 导入历史。
  与 information_schema 的区别：SHOW/DESC 是实时命令，返回当前状态；
  information_schema 是元数据视图，有约 15 分钟延迟但支持复杂 SQL 分析。
  当用户说"查看表列表"、"查看字段"、"查看作业"、"SHOW TABLES"、"DESC TABLE"、
  "查看分区"、"查看历史版本"、"查看删除的表"、"查看导入历史"、"load_history"、
  "SHOW JOBS"、"查看集群状态"、"查看连接"、"查看权限"、"SHOW GRANTS"时触发。
---

# ClickZetta 元数据查询命令

阅读 [references/show-desc-reference.md](references/show-desc-reference.md) 了解完整语法。

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

## SHOW 命令速查

### 数据对象

```sql
-- 列出所有 Schema（EXTENDED 显示 type 字段）
SHOW SCHEMAS;
SHOW SCHEMAS EXTENDED;
SHOW SCHEMAS LIKE 'ods%';

-- 列出表（含视图、物化视图、动态表、外部表）
SHOW TABLES;
SHOW TABLES IN my_schema;
SHOW TABLES LIKE '%order%';

-- 按类型过滤（WHERE 支持字段：table_name/is_view/is_materialized_view/is_external/is_dynamic）
SHOW TABLES WHERE is_view = false AND is_materialized_view = false;  -- 普通表
SHOW TABLES WHERE is_view = true;                                    -- 视图
SHOW TABLES WHERE is_materialized_view = true;                       -- 物化视图
SHOW TABLES WHERE is_dynamic = true;                                 -- 动态表
SHOW TABLES WHERE is_external = true;                                -- 外部表

-- 查看字段列表
SHOW COLUMNS IN my_schema.my_table;
SHOW COLUMNS FROM my_table IN my_schema;  -- 等价写法

-- 查看完整建表语句（适用于表/视图/物化视图/动态表）
SHOW CREATE TABLE my_table;

-- 查看分区
SHOW PARTITIONS my_table;
SHOW PARTITIONS EXTENDED my_table;  -- 含 total_rows/bytes/total_files/时间戳
-- ⚠️ SHOW PARTITIONS WHERE 不支持按分区列名过滤，需用 PARTITION() 子句
SHOW PARTITIONS my_table PARTITION (dt = '2024-01');

-- 查看 Table Stream
SHOW TABLE STREAMS;
SHOW TABLE STREAMS IN my_schema;
SHOW TABLE STREAMS LIKE '%orders%';

-- 查看同义词
SHOW SYNONYMS IN my_schema;

-- 查看语义视图
SHOW SEMANTIC VIEWS;
SHOW SEMANTIC VIEWS IN my_schema;
```

### 计算与连接

```sql
-- 查看计算集群
SHOW VCLUSTERS;
SHOW VCLUSTERS WHERE state = 'RUNNING';
SHOW VCLUSTERS WHERE vcluster_type = 'ANALYTICS';

-- 查看作业（最近 7 天，最多 10000 条）
SHOW JOBS LIMIT 20;
SHOW JOBS IN VCLUSTER default_ap LIMIT 20;

-- 查看动态表刷新历史（最近 7 天）
SHOW DYNAMIC TABLE REFRESH HISTORY LIMIT 20;
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE state = 'FAILED';

-- 查看连接对象
SHOW CONNECTIONS;
SHOW CONNECTIONS LIKE '%oss%';
SHOW CONNECTIONS WHERE category = 'STORAGE';
```

### 用户与权限

```sql
-- 查看用户
SHOW USERS;

-- 查看角色
SHOW ROLES;

-- 查看权限
SHOW GRANTS TO USER alice;
SHOW GRANTS TO ROLE analyst_role;
```

### 历史记录

```sql
-- 查看表历史（含已删除表，delete_time 为 NULL 表示未删除）
SHOW TABLES HISTORY;
SHOW TABLES HISTORY IN my_schema;
SHOW TABLES HISTORY LIKE '%temp%';

-- 查看 Pipe 对象
SHOW PIPES;
SHOW PIPES IN my_schema;
```

---

## DESC 命令速查

```sql
-- 查看表/视图/动态表/物化视图字段
DESC my_table;
DESC EXTENDED my_table;  -- 含 last_modified_time/properties/statistics

-- 查看 Schema
DESC SCHEMA my_schema;
DESC SCHEMA EXTENDED my_schema;  -- 含 creator/created_time/type

-- 查看计算集群
DESC VCLUSTER default_ap;

-- 查看连接对象
DESC CONNECTION my_oss_conn;
DESC CONNECTION EXTENDED my_oss_conn;

-- 查看索引
DESC INDEX idx_name;

-- 查看 Table Stream
DESC TABLE STREAM my_stream;

-- 查看动态表
DESC DYNAMIC TABLE my_dt;

-- 查看 Catalog
DESC CATALOG my_catalog;
```

---

## DESC HISTORY — 查看版本历史

```sql
-- 查看表的版本历史（依赖 data_retention_days 设置）
DESC HISTORY my_table;
-- 返回：version, time, total_rows, total_bytes, user, operation, job_id, stats

-- 查看动态表刷新历史
DESC HISTORY my_dynamic_table;
-- 额外返回：source_tables（基表信息）

-- 查看物化视图历史
DESC HISTORY my_materialized_view;
```

**返回字段说明：**

| 字段 | 说明 |
|---|---|
| version | 版本号（递增） |
| time | 操作时间 |
| total_rows | 该版本行数 |
| total_bytes | 该版本大小 |
| user | 操作用户 |
| operation | 操作类型（INSERT_INTO/UPDATE/DELETE/ALTER/CREATE/REFRESH 等） |
| job_id | 对应作业 ID |
| stats | 增量刷新统计（动态表专有） |

---

## load_history() — 查看文件导入历史

用于查看通过 COPY INTO 导入到表的文件历史，**保留 7 天**，主要用于 Pipe 去重判断。

```sql
-- 正确语法：表名用字符串（含 schema 前缀）
SELECT * FROM load_history('my_schema.my_table');
SELECT * FROM load_history('my_schema.my_table') LIMIT 100;

-- 按状态过滤
SELECT * FROM load_history('my_schema.my_table')
WHERE status = 'LOADED';

-- 查看最近导入的文件
SELECT file_path, last_copy_time, file_size, status, first_error_message
FROM load_history('my_schema.my_table')
ORDER BY last_copy_time DESC
LIMIT 20;
```

**返回字段：**

| 字段 | 说明 |
|---|---|
| file_path | 导入文件路径 |
| last_copy_time | 最后导入时间 |
| file_size | 文件大小 |
| status | LOADED / LOAD_FAILED |
| first_error_message | 失败时的错误信息 |

---

## 注意事项

1. **`SHOW SCHEMAS WHERE`**：`SHOW SCHEMAS` 不支持 WHERE 过滤，需用 `SHOW SCHEMAS EXTENDED` 后在应用层过滤，或用 `information_schema.schemas`
2. **`SHOW VIEWS`**：不支持 `SHOW VIEWS IN schema` 语法，需用 `SHOW TABLES WHERE is_view=true`
3. **`SHOW PARTITIONS WHERE`**：不支持按分区列名过滤（如 `WHERE dt='2024-01'`），需用 `PARTITION(dt='2024-01')` 子句
4. **`load_history()` 语法**：参数必须是带引号的字符串（`'schema.table'`），不能是裸表名
5. **`SHOW JOBS`**：只显示最近 7 天，最多 10000 条；`IN VCLUSTER` 可按集群过滤
6. **`SHOW DYNAMIC TABLE REFRESH HISTORY`**：只显示最近 7 天，最多 10000 条
