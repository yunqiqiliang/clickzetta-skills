# 数据生命周期管理参考

> 来源：https://www.yunqi.tech/documents/data-lifecycle
> 已通过实际 Lakehouse 连接验证（cn-shanghai-alicloud, f8866243, quick_start）

---

## 核心属性

| 属性键 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `data_lifecycle` | 正整数 / -1 | `-1` | 数据自动回收周期（天）。-1 表示永不回收 |
| `data_lifecycle_delete_meta` | boolean string | `'false'` | 到期时是否同时删除表结构。默认只清空数据 |
| `data_retention_days` | 整数 0-90 | `1` | Time Travel 历史版本保留天数 |

---

## CREATE TABLE 语法

```sql
CREATE TABLE tname (
    col1 datatype1,
    col2 datatype2
) PROPERTIES(
    'data_lifecycle'='<天数>',
    'data_lifecycle_delete_meta'='true',   -- 可选，到期删表结构
    'data_retention_days'='<天数>'          -- 可选，Time Travel 保留周期
);
```

**验证结果**：`SHOW CREATE TABLE` 输出中属性显示在 `TBLPROPERTIES` 块内：
```sql
CREATE TABLE quick_start.mcp_demo.lifecycle_test_table(
  `id` int,
  `name` string,
  `created_at` timestamp)
USING PARQUET
TBLPROPERTIES(
  'data_lifecycle'='7',
  'data_retention_days'='7');
```

---

## ALTER TABLE 语法

```sql
-- 设置/修改生命周期
ALTER TABLE tname SET PROPERTIES ('data_lifecycle'='<天数>');

-- 关闭生命周期
ALTER TABLE tname SET PROPERTIES ('data_lifecycle'='-1');

-- 设置到期删除表结构
ALTER TABLE tname SET PROPERTIES ('data_lifecycle_delete_meta'='true');

-- 设置 Time Travel 保留周期
ALTER TABLE tname SET PROPERTIES ('data_retention_days'='<天数>');

-- 同时设置多个属性
ALTER TABLE tname SET PROPERTIES (
    'data_lifecycle'='90',
    'data_lifecycle_delete_meta'='true',
    'data_retention_days'='30'
);
```

---

## 查看配置

### DESC EXTENDED

```sql
DESC EXTENDED tname;
```

**实际输出结构**（验证结果）：

| column_name | data_type | comment |
|---|---|---|
| id | int | |
| name | string | |
| ... | ... | |
| # detailed table information | | |
| workspace | quick_start | |
| schema | mcp_demo | |
| name | lifecycle_test_table | |
| creator | qiliang | |
| created_time | 2026-05-01 11:05:08.904 | |
| last_modified_time | 2026-05-01 11:05:26.442 | |
| comment | | |
| properties | (("data_lifecycle","7"),("data_retention_days","7")) | |
| version | 3377453148768716241 | |
| type | TABLE | |
| format | PARQUET | |
| statistics | 1 rows 2445 bytes | |

关键字段：
- `last_modified_time`：生命周期从此时间起算
- `properties`：显示所有 TBLPROPERTIES

### SHOW CREATE TABLE

```sql
SHOW CREATE TABLE tname;
-- 返回完整 DDL，TBLPROPERTIES 中包含 data_lifecycle 等属性
```

### information_schema.tables

```sql
SELECT table_name, data_lifecycle, last_modify_time
FROM information_schema.tables
WHERE table_schema = 'my_schema';
-- data_lifecycle = -1 表示永久保留（未设置生命周期）
-- data_lifecycle > 0 表示已设置生命周期（单位：天）
```

---

## 分区表

分区表的生命周期按**分区**计算，每个分区独立判断 `last_modified_time`。

```sql
-- 查看分区的修改时间
SHOW PARTITIONS EXTENDED tname;
```

**实际输出字段**（验证结果）：

| 字段 | 说明 |
|---|---|
| partitions | 分区值（如 dt=2024-01-01） |
| total_rows | 分区行数 |
| bytes | 分区大小 |
| total_files | 文件数 |
| created_time | 分区创建时间 |
| last_modified_time | 分区最后修改时间（生命周期从此起算） |
| last_data_time | 最后数据写入时间 |
| last_compaction_time | 最后 compaction 时间 |

---

## Time Travel 语法

```sql
-- 查询历史时间点数据
SELECT * FROM tname TIMESTAMP AS OF '<timestamp>';
SELECT * FROM tname TIMESTAMP AS OF CURRENT_TIMESTAMP - INTERVAL 12 HOURS;

-- 查看版本历史
DESC HISTORY tname;
-- 返回：version, time, total_rows, total_bytes, user, operation, job_id, stats

-- 恢复到历史版本（注意：目标时间点必须晚于表创建时间）
RESTORE TABLE tname TO TIMESTAMP AS OF '<timestamp>';

-- 恢复被删除的表
UNDROP TABLE tname;
```

**注意**：`RESTORE TABLE` 的目标时间点不能早于表创建时间，否则报错：
`InvalidArgument: toTimestamp is smaller than timestamp of fromTimestamp`

---

## 工作原理

1. 生命周期回收依赖 `last_modified_time`（DDL/DML 操作会更新此时间）
2. 后台进程每 **12 小时**轮询一次，到期数据通常在 **24 小时内**被回收
3. 到期数据不立即删除，仍可查询，直到后台进程执行
4. 被回收的数据仍遵守 `data_retention_days`，可用 Time Travel 查询
5. 默认行为：只清空数据，**保留表结构**；设置 `data_lifecycle_delete_meta='true'` 才删表
