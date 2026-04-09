---
name: clickzetta-data-recovery
description: |
  ClickZetta Lakehouse 数据恢复与历史查询助手。覆盖 Time Travel 查询、UNDROP 恢复误删表、
  RESTORE TABLE 回滚到历史版本、DESC HISTORY 查看变更记录、SHOW TABLES HISTORY 查看删除记录、
  数据保留周期（data_retention_days）配置等完整数据恢复工作流。

  当用户说"恢复误删的表"、"表被 DROP 了怎么办"、"回滚数据"、"查看历史版本"、
  "时间旅行查询"、"UNDROP"、"RESTORE TABLE"、"数据保留周期"、"查看表的变更历史"、
  "误操作 DELETE/UPDATE 怎么恢复"、"数据回滚"时触发。

  包含 ClickZetta 特有的语法（TIMESTAMP AS OF、RESTORE TABLE TO、UNDROP TABLE）
  以及数据保留周期默认值（默认 1 天，最长 90 天）等关键约束。
---

# ClickZetta Lakehouse 数据恢复 Skill

## 核心命令速查

### 1. 查看表变更历史
```sql
-- 查看表的所有历史版本（版本号、时间、操作类型、操作用户）
DESC HISTORY table_name;
-- 示例
DESC HISTORY orders;
```
返回字段：`version`、`time`、`total_rows`、`total_bytes`、`user`、`operation`、`job_id`

### 2. 查看已删除表的记录
```sql
-- 查看当前 schema 下所有表（含已删除）的历史记录
SHOW TABLES HISTORY;

-- 指定 schema
SHOW TABLES HISTORY IN schema_name;

-- 按名称过滤
SHOW TABLES HISTORY LIKE 'orders%';

-- 按条件过滤（与 LIKE 二选一）
SHOW TABLES HISTORY WHERE delete_time IS NOT NULL;
```
返回字段：`schema_name`、`table_name`、`create_time`、`creator`、`rows`、`bytes`、`comment`、`retention_time`、`delete_time`

### 3. Time Travel 查询历史数据
```sql
-- 查询指定时间点的历史数据（只读，不修改表）
SELECT * FROM table_name TIMESTAMP AS OF 'timestamp_expression';

-- 示例：查询昨天下午 3 点的数据
SELECT * FROM orders TIMESTAMP AS OF '2026-03-18 15:00:00';

-- 使用 CAST
SELECT * FROM orders TIMESTAMP AS OF CAST('2026-03-18 15:00:00' AS TIMESTAMP);

-- 使用相对时间（12小时前）
SELECT * FROM orders TIMESTAMP AS OF CURRENT_TIMESTAMP() - INTERVAL 12 HOURS;

-- 带条件过滤
SELECT * FROM sales.transactions
  TIMESTAMP AS OF '2025-03-15 09:00:00'
WHERE amount > 10000;
```

### 4. RESTORE TABLE 回滚到历史版本
```sql
-- 将表回滚到指定时间点（原地修改，会覆盖当前数据）
RESTORE TABLE table_name TO TIMESTAMP AS OF 'timestamp_expression';

-- 标准流程：先查历史，再恢复
DESC HISTORY orders;
RESTORE TABLE orders TO TIMESTAMP AS OF '2026-03-18 14:59:00';

-- 验证恢复结果
SELECT COUNT(*) FROM orders;
```
> 注意：RESTORE TABLE 支持普通表和动态表，**不支持物化视图**。若表已被 DROP，需先用 UNDROP。

### 5. UNDROP TABLE 恢复被删除的表
```sql
-- 恢复被 DROP 的表（需在数据保留周期内）
UNDROP TABLE table_name;

-- 带 schema 前缀
UNDROP TABLE schema_name.table_name;

-- 示例
UNDROP TABLE production.orders;

-- 验证恢复
SHOW TABLES IN production LIKE 'orders';
SELECT COUNT(*) FROM production.orders;
```
> 支持：普通表（TABLE）、动态表（DYNAMIC TABLE）、物化视图（MATERIALIZED VIEW）
> 限制：若已存在同名表，需先 DROP 新表再 UNDROP

### 6. 配置数据保留周期（Time Travel）
```sql
-- 查看当前保留周期
DESC EXTENDED table_name;

-- 修改保留周期（单位：天，范围 0-90）
ALTER TABLE table_name SET PROPERTIES ('data_retention_days'='7');

-- 创建表时指定保留周期
CREATE TABLE orders (id INT, amount DECIMAL(10,2))
PROPERTIES ('data_retention_days'='30');
```
> 默认保留周期：**1 天（24小时）**，最长 **90 天**

> ⚠️ **`data_retention_days` vs `data_lifecycle` 区别：**
> - `data_retention_days`：控制 **Time Travel 保留期**，即可以回溯查询/恢复的历史时长。增大此值会增加存储成本，但不会自动删除数据。
> - `data_lifecycle`：控制**数据 TTL（生命周期）**，到期后自动删除数据（可选同时删除表结构）。适用于日志、临时数据等有明确过期需求的场景。
> - 两者相互独立，可同时设置。

### 7. 数据生命周期（TTL）管理
```sql
-- 创建表时设置生命周期（7天后自动回收数据）
CREATE TABLE tname (col1 INT, col2 STRING)
PROPERTIES ('data_lifecycle'='7');

-- 创建表时设置生命周期并在到期时删除表结构
CREATE TABLE tname (col1 INT, col2 STRING)
PROPERTIES ('data_lifecycle'='7', 'data_lifecycle_delete_meta'='true');

-- 修改已有表的生命周期
ALTER TABLE tname SET PROPERTIES ('data_lifecycle'='30');

-- 关闭生命周期（永久保留）
ALTER TABLE tname SET PROPERTIES ('data_lifecycle'='-1');

-- 设置分区级别的生命周期（到期后自动回收该分区数据）
ALTER TABLE tname PARTITION (dt='2024-01-01') SET PROPERTIES ('data_lifecycle'='30');
```

> **分区级别支持**：`data_lifecycle` 和 `data_retention_days` 均支持在分区级别设置，可以对不同分区配置不同的保留策略。例如热数据分区保留 90 天 Time Travel，冷数据分区保留 1 天。

---

## 典型恢复场景

### 场景 A：表被误 DROP，立即恢复
```sql
-- Step 1: 确认表已被删除及删除时间
SHOW TABLES HISTORY LIKE 'orders';

-- Step 2: 直接 UNDROP（最快方式）
UNDROP TABLE orders;

-- Step 3: 验证
SELECT COUNT(*) FROM orders;
```

### 场景 B：误执行 DELETE/UPDATE，回滚数据
```sql
-- Step 1: 查看变更历史，找到误操作前的版本时间
DESC HISTORY analytics.events;

-- Step 2: 先用 Time Travel 验证历史数据
SELECT COUNT(*) FROM analytics.events
  TIMESTAMP AS OF '2026-03-18 14:55:00'
WHERE date < '2025-01-01';

-- Step 3a: 原地回滚（会覆盖当前所有数据）
RESTORE TABLE analytics.events TO TIMESTAMP AS OF '2026-03-18 14:55:00';

-- Step 3b: 仅补回被删除的数据（不影响其他数据）
INSERT INTO analytics.events
SELECT * FROM analytics.events TIMESTAMP AS OF '2026-03-18 14:55:00'
WHERE date < '2025-01-01';

-- Step 4: 验证
SELECT COUNT(*) FROM analytics.events WHERE date < '2025-01-01';
```

### 场景 C：Time Travel 查询历史数据（只读）
```sql
-- 查询指定时间点的数据，不修改表
SELECT *
FROM sales.transactions
  TIMESTAMP AS OF '2025-03-15 09:00:00'
WHERE amount > 10000
ORDER BY amount DESC;
```

---

## 关键约束与注意事项

| 项目 | 说明 |
|------|------|
| 默认保留周期 | 1 天（24小时） |
| 最长保留周期 | 90 天 |
| UNDROP 限制 | 同名表存在时无法 UNDROP，需先 DROP 新表 |
| RESTORE 限制 | 不支持物化视图；表已删除时需先 UNDROP |
| Time Travel 语法 | `TIMESTAMP AS OF`（不是 `AT`、`FOR SYSTEM_TIME AS OF`） |
| 时区 | 时间戳默认使用实例时区，建议明确指定或换算 UTC |
| 保留周期修改 | 会增加存储成本 |

---

## 决策树

```
数据丢失/损坏
├── 表被 DROP？
│   ├── 在保留周期内 → UNDROP TABLE
│   └── 超出保留周期 → 联系管理员 / 从备份恢复
└── 表存在，数据被 DELETE/UPDATE/TRUNCATE？
    ├── 在保留周期内
    │   ├── 需要全量回滚 → RESTORE TABLE TO TIMESTAMP AS OF
    │   └── 需要补回部分数据 → INSERT INTO ... SELECT ... TIMESTAMP AS OF
    └── 超出保留周期 → 联系管理员 / 从备份恢复
```
