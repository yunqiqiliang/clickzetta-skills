---
name: clickzetta-data-lifecycle
description: |
  管理 ClickZetta Lakehouse 表的数据生命周期（TTL）和 Time Travel 数据保留周期。
  数据生命周期：自动回收超过指定天数未更新的数据（表或分区），释放存储空间。
  Time Travel 保留周期：控制历史版本数据保留时长，支持时间点查询和数据恢复。
  当用户说"设置生命周期"、"数据自动清理"、"TTL"、"data_lifecycle"、
  "表数据过期"、"自动回收数据"、"设置数据保留"、"data_retention_days"、
  "Time Travel 保留周期"、"查看哪些表有生命周期"、"批量设置生命周期"、
  "生命周期到期"、"数据生命周期管理"时触发。
  Keywords: TTL, data retention, time travel, lifecycle, auto-purge, storage
---

# ClickZetta 数据生命周期管理

阅读 [references/lifecycle-reference.md](references/lifecycle-reference.md) 了解完整语法。

## 两个独立概念

| 概念 | 属性键 | 作用 | 默认值 |
|---|---|---|---|
| 数据生命周期（TTL） | `data_lifecycle` | 自动回收超期未更新的数据 | `-1`（永不回收） |
| Time Travel 保留周期 | `data_retention_days` | 历史版本保留时长，支持时间点查询和恢复 | `1`（1天） |

两者可同时设置，互不影响。

---

## 设置数据生命周期（TTL）

### 建表时设置

```sql
-- 数据 7 天未更新则自动清空（保留表结构）
CREATE TABLE orders_archive (
    order_id BIGINT,
    amount DECIMAL(10,2),
    created_at TIMESTAMP
) PROPERTIES('data_lifecycle'='7');

-- 数据 30 天未更新则自动删除表结构和数据
CREATE TABLE temp_staging (
    id INT,
    data STRING
) PROPERTIES('data_lifecycle'='30', 'data_lifecycle_delete_meta'='true');
```

### 修改现有表

```sql
-- 设置生命周期为 90 天
ALTER TABLE my_table SET PROPERTIES ('data_lifecycle'='90');

-- 同时设置生命周期和到期删除表结构
ALTER TABLE my_table SET PROPERTIES ('data_lifecycle'='90', 'data_lifecycle_delete_meta'='true');

-- 关闭生命周期（永久保留）
ALTER TABLE my_table SET PROPERTIES ('data_lifecycle'='-1');
```

---

## 设置 Time Travel 保留周期

```sql
-- 设置保留 7 天历史版本（范围 0-90 天）
ALTER TABLE my_table SET PROPERTIES ('data_retention_days'='7');

-- 建表时同时设置两个属性
CREATE TABLE important_data (
    id INT,
    val STRING
) PROPERTIES('data_lifecycle'='365', 'data_retention_days'='30');
```

---

## 查看生命周期配置

### 查看单张表

```sql
-- 查看表属性（含 data_lifecycle 和 data_retention_days）
SHOW CREATE TABLE my_table;

-- 查看详细信息（含 last_modified_time 和 properties）
DESC EXTENDED my_table;
```

### 批量查询（通过 information_schema）

```sql
-- 查看当前 Schema 下所有表的生命周期配置
-- data_lifecycle = -1 表示永久保留
SELECT table_name, data_lifecycle, last_modify_time
FROM information_schema.tables
WHERE table_schema = 'my_schema'
ORDER BY data_lifecycle DESC;

-- 找出已设置生命周期的表（data_lifecycle > 0）
SELECT table_schema, table_name, data_lifecycle, last_modify_time
FROM information_schema.tables
WHERE data_lifecycle > 0
ORDER BY data_lifecycle;

-- 找出未设置生命周期的表（潜在存储浪费）
SELECT table_schema, table_name, bytes / 1024 / 1024 AS size_mb, last_modify_time
FROM information_schema.tables
WHERE data_lifecycle = -1
  AND table_type = 'MANAGED_TABLE'
  AND bytes > 100 * 1024 * 1024  -- 大于 100MB
ORDER BY bytes DESC;
```

### 查看分区表的分区修改时间

```sql
-- 分区表生命周期按分区的 last_modified_time 计算
SHOW PARTITIONS EXTENDED my_partitioned_table;
-- 返回字段：partitions, total_rows, bytes, total_files,
--           created_time, last_modified_time, last_data_time, last_compaction_time
```

---

## Time Travel 查询历史数据

```sql
-- 查询指定时间点的历史数据
SELECT * FROM my_table
TIMESTAMP AS OF '2024-01-15 10:00:00';

-- 查询 N 小时前的数据
SELECT * FROM my_table
TIMESTAMP AS OF CURRENT_TIMESTAMP - INTERVAL 12 HOURS;

-- 查看表的版本历史
DESC HISTORY my_table;
-- 返回：version, time, total_rows, total_bytes, user, operation, job_id, stats
```

---

## 数据恢复

```sql
-- 恢复表到指定时间点（覆盖当前数据）
RESTORE TABLE my_table TO TIMESTAMP AS OF '2024-01-15 10:00:00';

-- 恢复被误删的表
UNDROP TABLE my_table;
```

---

## 典型场景

### 场景 1：日志表按月清理

```sql
CREATE TABLE app_logs (
    log_id BIGINT,
    level STRING,
    message STRING,
    log_time TIMESTAMP
) PROPERTIES('data_lifecycle'='30');
```

### 场景 2：临时中间表自动清理

```sql
CREATE TABLE etl_staging_temp (
    id INT,
    raw_data STRING
) PROPERTIES('data_lifecycle'='3', 'data_lifecycle_delete_meta'='true');
```

### 场景 3：重要业务表保留长历史

```sql
-- 数据永久保留，但保留 30 天历史版本用于审计回溯
ALTER TABLE orders SET PROPERTIES ('data_retention_days'='30');
```

### 场景 4：批量为未设置生命周期的大表设置 TTL

```sql
-- 先查出未设置生命周期的大表
SELECT table_name, bytes / 1024 / 1024 AS size_mb
FROM information_schema.tables
WHERE table_schema = 'my_schema'
  AND data_lifecycle = -1
  AND table_type = 'MANAGED_TABLE'
ORDER BY bytes DESC;

-- 逐一设置（需手动执行每条）
ALTER TABLE table_a SET PROPERTIES ('data_lifecycle'='180');
ALTER TABLE table_b SET PROPERTIES ('data_lifecycle'='90');
```

---

## 注意事项

1. **回收不立即执行**：生命周期到期后，后台进程每 12 小时轮询一次，通常 24 小时内完成回收
2. **默认保留表结构**：到期只清空数据，不删除表；加 `data_lifecycle_delete_meta='true'` 才删表
3. **分区表按分区计算**：每个分区独立计算 `last_modified_time`，分区到期独立回收
4. **`data_lifecycle=-1`**：表示永久保留，`information_schema.tables` 中显示为 `-1`
5. **Time Travel 默认 1 天**：默认只能查 1 天内历史；需要更长回溯窗口须提前设置 `data_retention_days`
6. **`data_retention_days` 范围 0-90**：最长 90 天，超出范围报错
7. **策略变更竞态**：修改生命周期天数时，极少数情况下回收任务可能按旧策略执行一次，属正常机制
