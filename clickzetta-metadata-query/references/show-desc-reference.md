# SHOW / DESC 命令完整语法参考

> 已通过实际 Lakehouse 连接验证（cn-shanghai-alicloud, f8866243, quick_start）

---

## SHOW 命令通用语法

```sql
SHOW <object_type_plural>
[ IN <scope> ]
[ LIKE '<pattern>' | WHERE <expression> ]
[ LIMIT <num> ]
```

### 作用域（IN）对应关系

| 对象类型 | IN 作用域 | 示例 |
|---|---|---|
| TABLE / VIEW / SYNONYM / TABLE STREAM / PIPE | `IN schema_name` | `SHOW TABLES IN sales` |
| SCHEMA / VCLUSTER / USERS / ROLES / PIPES | `IN workspace_name` | `SHOW SCHEMAS IN my_ws` |
| 作业 | `IN VCLUSTER vc_name`（可选） | `SHOW JOBS IN VCLUSTER prod` |
| 索引 / 列 | `IN table_name` 或 `FROM table_name` | `SHOW COLUMNS IN orders` |
| 分区 | 不支持 IN，直接跟表名 | `SHOW PARTITIONS my_table` |
| VOLUME | 不支持 IN，用 WHERE external/connection 过滤 | `SHOW VOLUMES WHERE external=true` |
| CONNECTION / SHARE / FUNCTION / CATALOG | 不支持作用域限定 | `SHOW CONNECTIONS` |

### WHERE 支持的对象和字段（实测验证）

| 对象 | LIKE | WHERE | 可过滤字段 |
|---|---|---|---|
| TABLE | ✅ | ✅ | `table_name`, `is_view`, `is_materialized_view`, `is_external`, `is_dynamic` |
| TABLE STREAM | ✅ | ✅ | `create_time`, `name`, `table_name`, `mode`, `comment` |
| CONNECTION | ✅ | ✅ | `name`, `category`, `type`, `enabled`, `created_time` |
| VCLUSTER | ✅ | ✅ | `name`, `vcluster_type`, `state`, `creator`, `create_time`, `running_jobs`, `queued_jobs` 等 |
| VOLUME | ✅ | ✅ | `external`（true/false）, `connection` — ⚠️ 不支持 `schema_name` 过滤 |
| JOB | ❌ | ✅ | `status`, `creator`, `priority`, `vcluster_name`, `job_id`, `start_time`, `end_time` |
| SHARE | ✅ | ✅ | `share_name`, `provider`, `provider_instance`, `scope`, `kind` |
| SYNONYM | ✅ | ✅ | `synonym_name`, `create_time`, `target_type`, `target_name` |
| PIPE | ✅ | ✅ | `pipe_name`, `pipe_kind`, `status`, `copy_statement` |
| SCHEMA | ✅ | ✅ | `schema_name` — ⚠️ `type` 字段不存在 |
| TABLE_HISTORY | ❌ | ✅ | `table_name` |
| CATALOG | ✅ | ✅ | `category` |
| ROLE | ✅ | ❌ | — |
| USER | ❌ | ❌ | — |
| FUNCTION | ❌ | ❌ | `SHOW FUNCTIONS` 不支持 LIKE/WHERE；用 `SHOW EXTERNAL FUNCTIONS LIKE '%xxx%'` 查用户自定义函数 |
| GRANT | ❌ | ❌ | 用 `SHOW GRANTS ON/TO` 语法代替；⚠️ 不支持 LIMIT |

---

## SHOW TABLES 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| schema_name | STRING | 所属 Schema |
| table_name | STRING | 对象名称 |
| is_view | BOOLEAN | 是否为视图 |
| is_materialized_view | BOOLEAN | 是否为物化视图 |
| is_external | BOOLEAN | 是否为外部表 |
| is_dynamic | BOOLEAN | 是否为动态表 |

常用过滤示例：

```sql
-- 列出指定 Schema 下所有 Dynamic Table（最常用）
SHOW TABLES IN my_schema WHERE is_dynamic;

-- 列出当前 Schema 下所有 Dynamic Table
SHOW TABLES WHERE is_dynamic;

-- 其他类型过滤
SHOW TABLES WHERE is_view = true;
SHOW TABLES WHERE is_materialized_view = true;
SHOW TABLES WHERE is_external = true;
SHOW TABLES WHERE is_view = false AND is_materialized_view = false;  -- 普通表
```

**注意**：`SHOW VIEWS IN schema` 语法不支持，需用 `SHOW TABLES WHERE is_view=true`

---

## SHOW CATALOGS 返回字段

| 字段 | 说明 |
|---|---|
| workspace_name | Catalog 名称 |
| created_time | 创建时间 |
| category | SHARED（共享 Catalog）/ EXTERNAL（外部 Catalog） |

---

## SHOW VOLUMES 返回字段

| 字段 | 说明 |
|---|---|
| schema_name | 所属 Schema |
| volume_name | Volume 名称 |
| create_time | 创建时间 |
| external | 是否为外部 Volume（BOOLEAN） |
| workspace_name | 所属工作空间 |
| url | 绑定的存储路径 |
| recursive_file_lookup | 是否递归扫描 |
| connection | 引用的 Connection 名称 |

**注意**：`SHOW VOLUMES IN schema` 语法不支持；`WHERE schema_name='x'` 也不支持 — 只能用 `WHERE external=true/false` 或 `WHERE connection='xxx'` 过滤

---

## SHOW SHARES 返回字段

| 字段 | 说明 |
|---|---|
| share_name | Share 名称 |
| provider | 提供方账户名 |
| provider_instance | 提供方实例 ID |
| provider_workspace | 提供方工作空间 |
| scope | PRIVATE / PUBLIC |
| to_instance | 消费方实例（逗号分隔） |
| kind | OUTBOUND（对外共享）/ INBOUND（接收共享） |

---

## SHOW TABLES HISTORY 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| schema_name | STRING | 所属 Schema |
| table_name | STRING | 表名 |
| create_time | TIMESTAMP | 创建时间 |
| creator | STRING | 创建者 |
| rows | BIGINT | 行数 |
| bytes | BIGINT | 大小 |
| comment | STRING | 注释 |
| retention_time | INT | 数据保留天数 |
| delete_time | TIMESTAMP | 删除时间（NULL 表示未删除） |

---

## SHOW PARTITIONS EXTENDED 返回字段

| 字段 | 说明 |
|---|---|
| partitions | 分区值（如 `dt=2024-01`） |
| total_rows | 分区行数 |
| bytes | 分区大小 |
| total_files | 文件数 |
| created_time | 分区创建时间 |
| last_modified_time | 最后修改时间（生命周期从此起算） |
| last_data_time | 最后数据写入时间 |
| last_compaction_time | 最后 compaction 时间 |

**注意**：`SHOW PARTITIONS WHERE dt='2024-01'` 不支持，需用 `SHOW PARTITIONS my_table PARTITION(dt='2024-01')`

---

## SHOW JOBS 返回字段

| 字段 | 说明 |
|---|---|
| job_id | 作业 ID |
| status | SETUP / SUCCEED / FAILED / CANCELLED |
| creator | 提交用户 |
| priority | 优先级 |
| start_time | 开始时间 |
| end_time | 结束时间 |
| execution_time | 执行时长（INTERVAL 类型） |
| vcluster_name | 使用的集群 |
| job_text | SQL 语句 |
| query_tag | 用户标签 |

---

## SHOW FUNCTIONS / SHOW EXTERNAL FUNCTIONS 返回字段

| 字段 | 说明 |
|---|---|
| name | 函数名称（注意：列名是 `name`，不是 `function_name`） |
| type | 函数类型 |

> `SHOW FUNCTIONS` 列出所有内置函数和用户自定义函数，不支持 LIKE/WHERE。
> `SHOW EXTERNAL FUNCTIONS` 只列用户创建的外部函数，支持 `LIKE '%pattern%'`。

---

## SHOW DYNAMIC TABLE REFRESH HISTORY 返回字段

```sql
-- 全局（所有动态表，最近 7 天）
SHOW DYNAMIC TABLE REFRESH HISTORY LIMIT 20;
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE state = 'FAILED';

-- 指定表
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE name = 'my_dt' LIMIT 10;
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE name = 'my_dt' AND state = 'SUCCEED' LIMIT 20;
```

| 字段 | 说明 |
|---|---|
| workspace_name | 工作空间 |
| schema_name | Schema |
| name | 动态表名 |
| virtual_cluster | 使用集群 |
| start_time / end_time | 刷新时间 |
| duration | 耗时（INTERVAL） |
| state | SUCCEED / FAILED / RUNNING |
| refresh_trigger | MANUAL / SYSTEM_SCHEDULED |
| refresh_mode | NO_DATA / FULL / INCREMENTAL |
| error_message | 失败信息 |
| source_tables | 基表信息 |
| stats | 增量刷新条数 |

---

## SHOW CONNECTIONS 返回字段

| 字段 | 说明 |
|---|---|
| name | 连接名称（注意：列名是 `name`，不是 `connection_name`） |
| category | STORAGE / API / CATALOG |
| type | OSS / COS / S3 / KAFKA / CLOUD_FUNCTION / DATABRICKS_UNITY_CATALOG 等 |
| enabled | ENABLED / DISABLED |
| created_time | 创建时间 |

---

## DESC 命令支持的对象类型

| 对象类型 | 语法 | EXTENDED 支持 | 说明 |
|---|---|---|---|
| table/view/dynamic_table/materialized_view/external_table | `DESC TABLE [EXTENDED] name` | ✅ | 所有表类型统一用 DESC TABLE |
| semantic_view | `DESC EXTENDED name` | — | 返回维度/指标/逻辑表定义 |
| schema | `DESC SCHEMA [EXTENDED] name` | ✅ | EXTENDED 返回创建者、时间、权限等 |
| vcluster | `DESC VCLUSTER name` | ❌ | — |
| connection | `DESC CONNECTION [EXTENDED] name` | ✅ | EXTENDED 返回完整属性 |
| catalog | `DESC CATALOG name` | ❌ | — |
| stream/table_stream | `DESC TABLE STREAM name` | ❌ | — |
| job | `DESC JOB job_id` | ❌ | object_name 为 job_id |
| share | `DESC SHARE name` | ❌ | 返回 share 中包含的对象 |
| index | `DESC INDEX [EXTENDED] name` | ✅ | — |
| function/external_function | `DESC FUNCTION [EXTENDED] name` | ✅ | 仅支持用户创建的函数 |
| volume | `DESC VOLUME name` | ❌ | — |
| pipe | `DESC PIPE name` | ❌ | — |

> ⚠️ `DESC FUNCTION` 不支持内置函数（如 `year`、`count`），只支持用户创建的外部函数。

---

## DESC HISTORY 返回字段

| 字段 | 说明 |
|---|---|
| version | 版本号 |
| time | 操作时间 |
| total_rows | 该版本行数 |
| total_bytes | 该版本大小 |
| user | 操作用户 |
| operation | INSERT_INTO / UPDATE / DELETE / ALTER / CREATE / REFRESH 等 |
| job_id | 对应作业 ID |
| stats | 增量刷新统计（动态表专有） |
| source_tables | 基表信息（动态表专有） |

---

## load_history() 语法

```sql
-- 正确：参数为带引号的字符串
SELECT * FROM load_history('schema_name.table_name');
SELECT * FROM load_history('schema_name.table_name') LIMIT 100;

-- 错误：不能用裸表名
-- SELECT * FROM load_history(schema.table);  ❌
-- SELECT * FROM load_history(TABLE schema.table);  ❌
```

返回字段：`file_path`, `last_copy_time`, `file_size`, `status`, `first_error_message`

保留时间：7 天

---

## FROM (SHOW ...) 子查询

大多数 SHOW 命令支持作为子查询使用，可实现排序、过滤、JOIN 等操作：

```sql
-- ✅ 支持子查询的 SHOW 命令
SELECT * FROM (SHOW TABLES) WHERE is_view = false ORDER BY table_name;
SELECT * FROM (SHOW SCHEMAS) WHERE schema_name LIKE 'mcp%';
SELECT * FROM (SHOW VCLUSTERS) WHERE state = 'RUNNING' ORDER BY name;
SELECT * FROM (SHOW USERS);
SELECT * FROM (SHOW ROLES);
SELECT * FROM (SHOW SHARES);
SELECT * FROM (SHOW CONNECTIONS);
SELECT * FROM (SHOW JOBS) WHERE status = 'FAILED';
SELECT * FROM (SHOW GRANTS);
SELECT * FROM (SHOW FUNCTIONS) WHERE name LIKE '%count%';
SELECT * FROM (SHOW DYNAMIC TABLE REFRESH HISTORY) WHERE state = 'FAILED';
SELECT * FROM (SHOW COLUMNS FROM my_table);

-- ❌ 不支持子查询
-- SELECT * FROM (SHOW CREATE TABLE my_table);  -- parser return null
```

> 💡 **SHOW 结果排序的唯一方法**：`SHOW ... ORDER BY` 不支持，但可用子查询：
> ```sql
> SELECT * FROM (SHOW TABLES) ORDER BY table_name;
> SELECT * FROM (SHOW VCLUSTERS) ORDER BY create_time DESC;
> ```

---

## 常见陷阱

| 命令 | 陷阱 | 正确做法 |
|---|---|---|
| `SHOW SCHEMAS WHERE type=...` | `type` 字段不存在 | `SHOW SCHEMAS WHERE schema_name LIKE '%xxx%'` |
| `SHOW VIEWS IN schema` | 语法不支持 | `SHOW TABLES WHERE is_view=true` |
| `SHOW VOLUMES IN schema` | 语法不支持 | `SHOW VOLUMES WHERE external=true/false` 或 `WHERE connection='xxx'` |
| `SHOW VOLUMES WHERE schema_name='x'` | `schema_name` 字段不可过滤 | `SHOW VOLUMES LIKE '%name%'` |
| `SHOW PARTITIONS t WHERE dt='x'` | 不支持按分区列 WHERE | `SHOW PARTITIONS t PARTITION(dt='x')` |
| `load_history(schema.table)` | 需要字符串 | `load_history('schema.table')` |
| `DESC FUNCTION year` | 不支持内置函数 | 仅支持用户创建的外部函数 |
| `LIKE` + `WHERE` 同时用 | 不支持 | 用 `WHERE table_name LIKE 'x%'` 代替，或用子查询 `SELECT * FROM (SHOW TABLES) WHERE table_name LIKE 'x%'` |
| `SHOW GRANTS ... LIMIT n` | 不支持 LIMIT | 直接 `SHOW GRANTS TO USER name` |
| `SHOW FUNCTIONS LIKE '%xxx%'` | 不支持 LIKE | 用 `SHOW EXTERNAL FUNCTIONS LIKE '%xxx%'` |
