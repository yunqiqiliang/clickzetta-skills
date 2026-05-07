# Dynamic Table 增量刷新历史查询指南

查看 DT/MV 的增量刷新历史有三种方式，适用于不同场景。

---

## 方式一：SHOW DYNAMIC TABLE REFRESH HISTORY

查看 DT 的刷新作业级别信息，包括每次刷新的状态、耗时、触发方式、刷新模式等。

### 语法

```sql
-- 查看指定 DT 的刷新历史
SHOW DYNAMIC TABLE REFRESH HISTORY FOR my_dt;

-- 通过 WHERE 过滤（name 列匹配表名）
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE name = 'my_dt';

-- 限制返回行数
SHOW DYNAMIC TABLE REFRESH HISTORY FOR my_dt LIMIT 10;

-- 组合 WHERE + LIMIT
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE name = 'my_dt' AND state = 'SUCCEED' LIMIT 20;

-- MV 也支持同样的语法
SHOW MATERIALIZED VIEW REFRESH HISTORY FOR my_mv;
SHOW MATERIALIZED VIEW REFRESH HISTORY WHERE name = 'my_mv' LIMIT 10;
```

### 输出列

| 列名 | 类型 | 说明 |
|------|------|------|
| workspace_name | STRING | 所属 Workspace |
| schema_name | STRING | 所属 Schema |
| name | STRING | DT/MV 名称 |
| virtual_cluster | STRING | 执行刷新的虚拟集群 |
| start_time | TIMESTAMP | 刷新开始时间 |
| end_time | TIMESTAMP | 刷新结束时间（运行中为 NULL） |
| duration | INTERVAL | 刷新耗时（运行中显示已经过的时间） |
| state | STRING | 刷新状态（SUCCEED / FAILED / RUNNING 等） |
| refresh_trigger | STRING | 触发方式：`SYSTEM_SCHEDULED`（系统调度自动触发）或 `MANUAL`（用户手动 REFRESH） |
| refresh_mode | STRING | 刷新模式，见下方详细说明 |
| error_message | STRING | 失败时的错误信息（成功时为 NULL） |
| source_tables | ARRAY<MAP<STRING,STRING>> | 源表列表，每个元素是一个 MAP，包含 `workspace`、`schema`、`table_name` 三个 key |
| stats | MAP<STRING,STRING> | 刷新统计，包含 `rows_inserted`（插入行数）和 `rows_deleted`（删除行数） |
| job_id | STRING | 对应的 Job ID，可用于关联 `information_schema.job_history` 查更多详情 |

### refresh_mode 详解

`refresh_mode` 是判断增量计算是否生效的关键字段：

| 值 | 含义 | 说明 |
|----|------|------|
| `INCREMENTAL` | 增量刷新 | 增量引擎成功生成了增量计划，只处理了源表的变更数据 |
| `FULL` | 全量刷新 | 回退到全量重算。可能原因：首次刷新、维度表变更、增量计划生成失败、用户强制全量等 |
| `NO_DATA` | 无数据变更 | 源表在上次刷新后没有新的数据变更，本次刷新跳过计算 |

### source_tables 详解

`source_tables` 列返回该次刷新涉及的所有输入表信息，每个元素是一个 MAP：

```
[
  {"workspace": "my_ws", "schema": "public", "table_name": "orders"},
  {"workspace": "my_ws", "schema": "public", "table_name": "dim_product"}
]
```

### stats 详解

`stats` 列返回该次刷新对目标表的写入统计：

```
{"rows_inserted": "1000", "rows_deleted": "50"}
```

- `rows_inserted`：本次刷新向目标表插入的行数
- `rows_deleted`：本次刷新从目标表删除的行数（增量模式下，更新操作会产生 delete + insert）

### 典型用法

```sql
-- 查看最近 5 次刷新是否成功
SHOW DYNAMIC TABLE REFRESH HISTORY FOR my_dt LIMIT 5;

-- 查看失败的刷新记录
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE name = 'my_dt' AND state = 'FAILED';

-- 查看是否回退到了全量刷新（排查增量是否生效）
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE name = 'my_dt' AND refresh_mode = 'FULL';

-- 查看无数据变更的刷新（源表没有新数据时会出现）
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE name = 'my_dt' AND refresh_mode = 'NO_DATA';

-- 查看系统自动调度的刷新
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE name = 'my_dt' AND refresh_trigger = 'SYSTEM_SCHEDULED';
```

---

## 方式二：DESC HISTORY

查看表的版本级别历史，包括每个版本的行数、字节数、操作类型等。适用于了解数据变更粒度。

### 语法

```sql
-- 查看 DT 的版本历史
DESC HISTORY my_dt;

-- 查看源表的版本历史
DESC HISTORY source_table;

-- 支持 WHERE 过滤
DESC HISTORY my_dt WHERE version > 10;

-- 支持 LIMIT
DESC HISTORY my_dt LIMIT 20;
```

### 输出列

对于普通表（DESC_TABLE_HISTORY）：

| 列名 | 类型 | 说明 |
|------|------|------|
| sequence | BIGINT | 序列号 |
| version | BIGINT | 版本号 |
| time | TIMESTAMP | 版本创建时间 |
| total_rows | BIGINT | 该版本的总行数 |
| total_bytes | BIGINT | 该版本的总字节数 |
| user | STRING | 操作用户 |
| operation | STRING | 操作类型（INSERT / COMPACTION / REFRESH 等） |
| job_id | STRING | 对应的 Job ID |

对于 DT/MV（DESC_MV_HISTORY），额外包含：

| 列名 | 类型 | 说明 |
|------|------|------|
| source_tables | ARRAY<MAP<STRING,STRING>> | 源表及其对应的版本信息 |

DESC HISTORY 对 DT/MV 的 `source_tables` 比 SHOW REFRESH HISTORY 更详细，包含每个源表在该版本对应的快照信息：

```
[
  {"table_name": "orders", "workspace": "my_ws", "schema": "public", "version": "123", "sequence": "5", "commit_time": "2025-01-15 10:30:00"},
  {"table_name": "dim_product", "workspace": "my_ws", "schema": "public", "version": "456", "sequence": "2", "commit_time": "2025-01-15 08:00:00"}
]
```

- `version`：源表的 snapshot_id
- `sequence`：源表的 sequence 号
- `commit_time`：源表该版本的提交时间

这些信息可以用来追溯某次刷新读取了源表的哪个版本数据。

### 典型用法

```sql
-- 查看 DT 最近的版本变化，确认 compaction 是否正常执行
DESC HISTORY my_dt LIMIT 10;

-- 查看源表的版本历史，判断数据写入频率
DESC HISTORY source_table LIMIT 20;

-- 查看 DT 的 compaction 记录
DESC HISTORY my_dt WHERE operation = 'COMPACTION';
```

---

## 方式三：information_schema.materialized_view_refresh_history

从 information_schema 查询刷新历史，适合跨表批量分析、与其他系统集成、或做长期趋势监控。数据按天分区（pt_date），保留天数由系统配置决定。

### 语法

```sql
-- 查看指定 DT 的刷新历史
SELECT *
FROM information_schema.materialized_view_refresh_history
WHERE materialized_view_name = 'my_dt'
ORDER BY start_time DESC
LIMIT 10;

-- 查看某天所有 DT 的刷新情况
SELECT materialized_view_name, status, start_time, end_time, error_message
FROM information_schema.materialized_view_refresh_history
WHERE pt_date = '2025-01-15'
ORDER BY start_time DESC;

-- 查看失败的刷新
SELECT materialized_view_name, error_code, error_message, start_time
FROM information_schema.materialized_view_refresh_history
WHERE status = 'FAILED' AND pt_date >= '2025-01-01'
ORDER BY start_time DESC;
```

### 输出列

| 列名 | 类型 | 说明 |
|------|------|------|
| workspace_name | STRING | 所属 Workspace |
| schema_name | STRING | 所属 Schema |
| materialized_view_name | STRING | DT/MV 名称 |
| cru | DOUBLE | 消耗的计算资源单位 |
| virtual_cluster_name | STRING | 执行刷新的虚拟集群 |
| status | STRING | 刷新状态 |
| scheduled_start_time | TIMESTAMP | 计划开始时间 |
| start_time | TIMESTAMP | 实际开始时间 |
| end_time | TIMESTAMP | 结束时间 |
| error_code | STRING | 错误码 |
| error_message | STRING | 错误信息 |
| pt_date | STRING | 分区日期 |

### 典型用法

```sql
-- 统计某个 DT 最近 7 天的刷新成功率
SELECT
    pt_date,
    COUNT(*) AS total,
    SUM(CASE WHEN status = 'SUCCEED' THEN 1 ELSE 0 END) AS success,
    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed
FROM information_schema.materialized_view_refresh_history
WHERE materialized_view_name = 'my_dt'
  AND pt_date >= DATE_FORMAT(DATEADD(DAY, -7, CURRENT_DATE()), '%Y-%m-%d')
GROUP BY pt_date
ORDER BY pt_date;

-- 查看消耗 CRU 最多的刷新
SELECT materialized_view_name, cru, start_time, end_time
FROM information_schema.materialized_view_refresh_history
WHERE pt_date >= '2025-01-01'
ORDER BY cru DESC
LIMIT 10;
```

### 与 information_schema.job_history 的区别

`information_schema.job_history` 记录所有类型的 Job（SQL 查询、DML、DDL 等），而 `materialized_view_refresh_history` 专门记录 DT/MV 的刷新历史，字段更有针对性。

如果需要查看刷新 Job 的完整信息（如 job_text、input_bytes 等），可以通过 job_id 关联：

```sql
-- 通过 SHOW DYNAMIC TABLE REFRESH HISTORY 获取 job_id，再到 job_history 查详情
SELECT *
FROM information_schema.job_history
WHERE job_id = '<从 SHOW REFRESH HISTORY 获取的 job_id>'
  AND pt_date = '2025-01-15';
```

---

## 三种方式对比

| 特性 | SHOW REFRESH HISTORY | DESC HISTORY | information_schema |
|------|---------------------|--------------|-------------------|
| 粒度 | 刷新作业级别 | 表版本级别 | 刷新作业级别 |
| 刷新模式（增量/全量/无数据） | ✅ refresh_mode | ❌ | ❌ |
| 触发方式（调度/手动） | ✅ refresh_trigger | ❌ | ❌ |
| 写入统计（inserted/deleted） | ✅ stats | ❌ | ❌ |
| 源表列表 | ✅ 表名级别 | ✅ 含版本/sequence/commit_time | ❌ |
| 版本号/总行数/总字节数 | ❌ | ✅ version/total_rows/total_bytes | ❌ |
| CRU 消耗 | ❌ | ❌ | ✅ cru |
| 跨表批量查询 | ❌（单表） | ❌（单表） | ✅（可批量） |
| compaction 记录 | ❌ | ✅ | ❌ |
| 适用场景 | 排查增量是否生效、刷新状态 | 查看数据版本变化、追溯源表版本 | 批量分析/监控/CRU 统计 |
