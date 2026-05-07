# Dynamic Table DDL 完整语法参考

## CREATE DYNAMIC TABLE

```sql
CREATE [ OR REPLACE ] DYNAMIC TABLE [ IF NOT EXISTS ] <name>
  PROPERTIES ('<key>' = '<value>' [, '<key>' = '<value>' ...])
AS
  <select_statement>;
```

### PROPERTIES 参数

| 参数 | 说明 | 示例 |
|---|---|---|
| `target_lag` | 数据最大延迟容忍，与 `refresh_schedule` 二选一 | `'1 hour'`、`'30 minutes'` |
| `refresh_schedule` | 固定 cron 调度（5 字段），与 `target_lag` 二选一 | `'*/30 * * * *'` |
| `warehouse` | 执行刷新的 VCluster 名称 | `'default_ap'` |

### target_lag 合法值

| 格式 | 示例 |
|---|---|
| N minutes | `'5 minutes'`、`'30 minutes'` |
| N hours | `'1 hour'`、`'6 hours'` |
| N days | `'1 day'` |

### refresh_schedule cron 格式

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

-- 修改 target_lag
ALTER DYNAMIC TABLE <name> SET PROPERTIES ('target_lag' = '<new_lag>');

-- 修改 refresh_schedule
ALTER DYNAMIC TABLE <name> SET PROPERTIES ('refresh_schedule' = '<new_cron>');

-- 修改 warehouse
ALTER DYNAMIC TABLE <name> SET PROPERTIES ('warehouse' = '<new_vcluster>');
```

---

## DROP DYNAMIC TABLE

```sql
DROP DYNAMIC TABLE [ IF EXISTS ] <name>;
```

> ⚠️ 若有其他 Dynamic Table 依赖此表，需先删除下游。

---

## DESC / SHOW HISTORY

```sql
-- 查看表定义（含 SQL、刷新模式、调度配置）
DESC DYNAMIC TABLE <name>;

-- 查看刷新历史（最近 N 次）
SHOW DYNAMIC TABLE REFRESH HISTORY FOR <name>;
SHOW DYNAMIC TABLE REFRESH HISTORY FOR <name> LIMIT 20;
```

刷新历史返回列：`state`、`refresh_mode`（FULL/INCREMENTAL）、`duration`、`refresh_trigger`、`error_message`、`source_tables`、`job_id` 等。

---

## 查询 Dynamic Table 列表

`SHOW DYNAMIC TABLES` 语法不支持，用以下方式替代：

```sql
-- 列出指定 Schema 下所有 Dynamic Table（最常用）
SHOW TABLES IN <schema_name> WHERE is_dynamic;

-- 列出当前 Schema 下所有 Dynamic Table
SHOW TABLES WHERE is_dynamic;
-- 返回列：schema_name, table_name, is_view, is_materialized_view, is_external, is_dynamic
```

也可通过 `information_schema.tables` 查询：

```sql
SELECT table_name, table_type, last_modify_time
FROM information_schema.tables
WHERE table_schema = '<schema_name>';
```
