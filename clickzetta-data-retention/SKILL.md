---
name: clickzetta-data-retention
description: |
  管理 ClickZetta Lakehouse 数据生命周期（TTL 自动回收）和数据恢复（Time Travel / UNDROP / RESTORE）。
  覆盖数据生命周期设置（data_lifecycle）、Time Travel 保留周期（data_retention_days）、
  历史数据查询（TIMESTAMP AS OF）、误删表恢复（UNDROP TABLE）、数据回滚（RESTORE TABLE）、
  变更历史查看（DESC HISTORY）等完整数据管理工作流。
  当用户说"设置生命周期"、"数据自动清理"、"TTL"、"data_lifecycle"、"表数据过期"、
  "自动回收数据"、"设置数据保留"、"data_retention_days"、"Time Travel"、
  "恢复误删的表"、"表被 DROP 了怎么办"、"回滚数据"、"查看历史版本"、
  "UNDROP"、"RESTORE TABLE"、"误操作恢复"、"数据回滚"、"时间旅行"时触发。
  Keywords: TTL, data retention, time travel, lifecycle, UNDROP, RESTORE, recovery, rollback
---

# ClickZetta 数据生命周期与恢复

## 两个核心概念

| 概念 | 属性键 | 作用 | 默认值 | 范围 |
|---|---|---|---|---|
| 数据生命周期（TTL） | `data_lifecycle` | 自动回收超期未更新的数据 | `-1`（永不回收） | 任意正整数天 |
| Time Travel 保留周期 | `data_retention_days` | 历史版本保留时长，支持时间点查询和恢复 | `1`（1天） | 0-90 天 |

两者独立，可同时设置。

---

## 数据生命周期（TTL）

### 设置

```sql
-- 建表时设置（7天未更新自动清空数据）
CREATE TABLE orders_archive (id BIGINT, amount DECIMAL(10,2))
PROPERTIES('data_lifecycle'='7');

-- 到期同时删除表结构
CREATE TABLE temp_staging (id INT, data STRING)
PROPERTIES('data_lifecycle'='30', 'data_lifecycle_delete_meta'='true');

-- 修改现有表
ALTER TABLE my_table SET PROPERTIES ('data_lifecycle'='90');

-- 关闭生命周期
ALTER TABLE my_table SET PROPERTIES ('data_lifecycle'='-1');
```

### 查看

```sql
-- 查看单表
SHOW CREATE TABLE my_table;

-- 批量查看已设置生命周期的表
SELECT table_schema, table_name, data_lifecycle, last_modify_time
FROM information_schema.tables
WHERE data_lifecycle > 0
ORDER BY data_lifecycle;
```

### 注意事项
- 回收不立即执行，后台每 12 小时轮询，通常 24 小时内完成
- 默认只清空数据不删表；加 `data_lifecycle_delete_meta='true'` 才删表
- 分区表按分区独立计算 `last_modified_time`

---

## Time Travel 与数据恢复

### 配置保留周期

```sql
-- 修改保留周期（默认 1 天，最长 90 天）
ALTER TABLE my_table SET PROPERTIES ('data_retention_days'='7');

-- 建表时指定
CREATE TABLE orders (id INT, amount DECIMAL(10,2))
PROPERTIES ('data_retention_days'='30');
```

### 查看变更历史

```sql
DESC HISTORY my_table;
-- 返回：version, time, total_rows, total_bytes, user, operation, job_id

-- 查看已删除表的记录
SHOW TABLES HISTORY;
SHOW TABLES HISTORY LIKE 'orders%';
```

### Time Travel 查询历史数据

```sql
-- 查询指定时间点（只读）
SELECT * FROM orders TIMESTAMP AS OF '2026-03-18 15:00:00';

-- 相对时间
SELECT * FROM orders TIMESTAMP AS OF CURRENT_TIMESTAMP() - INTERVAL 12 HOURS;
```

### RESTORE TABLE 回滚

```sql
-- 将表回滚到指定时间点（覆盖当前数据）
RESTORE TABLE orders TO TIMESTAMP AS OF '2026-03-18 14:59:00';
```
> 支持普通表和动态表，不支持物化视图。

### UNDROP TABLE 恢复误删表

```sql
-- 恢复被 DROP 的表（需在保留周期内）
UNDROP TABLE orders;
```
> 同名表存在时无法 UNDROP，需先 DROP 新表再 UNDROP。

---

## 典型场景

### 误删表恢复
```sql
SHOW TABLES HISTORY LIKE 'orders';
UNDROP TABLE orders;
SELECT COUNT(*) FROM orders;
```

### 误执行 DELETE/UPDATE 回滚
```sql
DESC HISTORY analytics.events;
-- 全量回滚
RESTORE TABLE analytics.events TO TIMESTAMP AS OF '2026-03-18 14:55:00';
-- 或仅补回部分数据
INSERT INTO analytics.events
SELECT * FROM analytics.events TIMESTAMP AS OF '2026-03-18 14:55:00'
WHERE date < '2025-01-01';
```

### 日志表自动清理
```sql
CREATE TABLE app_logs (log_id BIGINT, message STRING, log_time TIMESTAMP)
PROPERTIES('data_lifecycle'='30');
```

---

## 决策树

```
数据丢失/损坏
├── 表被 DROP？
│   ├── 在保留周期内 → UNDROP TABLE
│   └── 超出保留周期 → 联系管理员
└── 数据被 DELETE/UPDATE/TRUNCATE？
    ├── 在保留周期内
    │   ├── 全量回滚 → RESTORE TABLE TO TIMESTAMP AS OF
    │   └── 补回部分 → INSERT INTO ... SELECT ... TIMESTAMP AS OF
    └── 超出保留周期 → 联系管理员
```
