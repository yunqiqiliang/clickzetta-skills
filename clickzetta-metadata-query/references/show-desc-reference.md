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
| TABLE / VIEW / SYNONYM / VOLUME / TABLE STREAM / PIPE | `IN schema_name` | `SHOW TABLES IN sales` |
| SCHEMA / VCLUSTER / USERS / ROLES / PIPES | `IN workspace_name` | `SHOW SCHEMAS IN my_ws` |
| 作业 | `IN VCLUSTER vc_name` | `SHOW JOBS IN VCLUSTER prod` |
| 索引 / 列 | `IN table_name` | `SHOW COLUMNS IN orders` |
| 分区 | 不支持 IN，直接跟表名 | `SHOW PARTITIONS my_table` |
| CONNECTION / SHARE / FUNCTION | 不支持作用域限定 | `SHOW CONNECTIONS` |

### WHERE 支持的对象和字段

| 对象 | 可过滤字段 |
|---|---|
| TABLE | `table_name`, `is_view`, `is_materialized_view`, `is_external`, `is_dynamic` |
| TABLE STREAM | `create_time`, `name`, `table_name`, `mode`, `comment` |
| CONNECTION | `name`, `category`, `type`, `enabled`, `created_time` |
| VCLUSTER | `name`, `vcluster_type`, `state`, `creator`, `create_time`, `running_jobs`, `queued_jobs` 等 |
| JOB | `status`, `creator`, `start_time`, `execution_time` 等 |
| SHARE | `name`, `provider`, `consumer` 等 |

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

**注意**：`SHOW VIEWS IN schema` 语法不支持，需用 `SHOW TABLES WHERE is_view=true`

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

## SHOW DYNAMIC TABLE REFRESH HISTORY 返回字段

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
| name | 连接名称 |
| category | STORAGE / API / CATALOG |
| type | OSS / COS / S3 / KAFKA / CLOUD_FUNCTION / DATABRICKS_UNITY_CATALOG 等 |
| enabled | ENABLED / DISABLED |
| created_time | 创建时间 |

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

## 常见陷阱

| 命令 | 陷阱 | 正确做法 |
|---|---|---|
| `SHOW SCHEMAS WHERE type=...` | 不支持 WHERE | 用 `SHOW SCHEMAS EXTENDED` 后应用层过滤 |
| `SHOW VIEWS IN schema` | 语法不支持 | `SHOW TABLES WHERE is_view=true` |
| `SHOW PARTITIONS t WHERE dt='x'` | 不支持按分区列 WHERE | `SHOW PARTITIONS t PARTITION(dt='x')` |
| `load_history(schema.table)` | 需要字符串 | `load_history('schema.table')` |
