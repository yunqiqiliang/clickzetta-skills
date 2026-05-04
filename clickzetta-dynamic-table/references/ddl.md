# Dynamic Table DDL 完整语法参考

## CREATE DYNAMIC TABLE

```sql
CREATE [ OR REPLACE ] DYNAMIC TABLE [ IF NOT EXISTS ] <name>
  { TARGET_LAG = '<lag_value>' | REFRESH SCHEDULE = '<cron_expr>' }
  WAREHOUSE = '<vcluster_name>'
  [ COMMENT = '<comment>' ]
AS
  <select_statement>;
```

### TARGET_LAG 合法值

| 格式 | 示例 |
|---|---|
| N minutes | `'5 minutes'`、`'30 minutes'` |
| N hours | `'1 hour'`、`'6 hours'` |
| N days | `'1 day'` |

### REFRESH SCHEDULE cron 格式

标准 5 字段 cron（分 时 日 月 周）：

```
'*/5 * * * *'     -- 每 5 分钟
'0 * * * *'       -- 每小时整点
'0 2 * * *'       -- 每天凌晨 2 点
'0 2 * * 1'       -- 每周一凌晨 2 点
'0 2 1 * *'       -- 每月 1 日凌晨 2 点
```

---

## ALTER DYNAMIC TABLE

```sql
-- 立即触发一次刷新
ALTER DYNAMIC TABLE <name> REFRESH;

-- 暂停自动刷新（数据保留，不再更新）
ALTER DYNAMIC TABLE <name> SUSPEND;

-- 恢复自动刷新
ALTER DYNAMIC TABLE <name> RESUME;

-- 修改 TARGET_LAG
ALTER DYNAMIC TABLE <name> SET TARGET_LAG = '<new_lag>';

-- 修改 REFRESH SCHEDULE
ALTER DYNAMIC TABLE <name> SET REFRESH SCHEDULE = '<new_cron>';

-- 修改 WAREHOUSE
ALTER DYNAMIC TABLE <name> SET WAREHOUSE = '<new_vcluster>';

-- 修改注释
ALTER DYNAMIC TABLE <name> SET COMMENT = '<new_comment>';
```

---

## DROP DYNAMIC TABLE

```sql
DROP DYNAMIC TABLE [ IF EXISTS ] <name>;
```

> ⚠️ 若有其他 Dynamic Table 依赖此表，需先删除下游。

---

## SHOW / DESC

```sql
-- 列出当前 Schema 下所有 Dynamic Table
SHOW DYNAMIC TABLES;

-- 列出指定 Schema 下的
SHOW DYNAMIC TABLES IN SCHEMA <schema_name>;

-- 查看表定义（含 SQL、刷新模式、调度配置）
DESC DYNAMIC TABLE <name>;

-- 查看刷新历史（最近 N 次）
SHOW DYNAMIC TABLE REFRESH HISTORY FOR <name>;
SHOW DYNAMIC TABLE REFRESH HISTORY FOR <name> LIMIT 20;
```

---

## information_schema 查询

```sql
-- 查看所有 Dynamic Table 状态
SELECT
  table_name,
  refresh_mode,          -- FULL 或 INCREMENTAL
  scheduling_state,      -- ACTIVE / SUSPENDED / FAILED
  last_refresh_time,
  last_refresh_duration_seconds,
  target_lag_seconds
FROM information_schema.dynamic_tables
WHERE schema_name = '<schema_name>'
ORDER BY last_refresh_time DESC;
```
