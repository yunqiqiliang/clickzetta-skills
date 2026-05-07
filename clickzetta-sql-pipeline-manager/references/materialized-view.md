# Materialized View（物化视图）SQL 参考

> **⚠️ ClickZetta 特有语法**
> - 定时刷新：`REFRESH INTERVAL 10 MINUTE vcluster default`（与动态表语法相同）
> - 手动刷新：`REFRESH MATERIALIZED VIEW <name>;`
> - 修改注释用 `ALTER TABLE`，不是 `ALTER MATERIALIZED VIEW`

物化视图将查询结果预计算并物理存储，适合固定维度的聚合加速场景。与动态表的区别：物化视图支持手动或定时刷新，不支持增量刷新。

## CREATE MATERIALIZED VIEW

```sql
CREATE [ OR REPLACE ] MATERIALIZED VIEW <name>
  [ COMMENT = '<comment>' ]
  [ BUILD DEFERRED ]
  [ REFRESH INTERVAL <N> { SECOND | MINUTE | HOUR | DAY } vcluster <vcluster_name> ]
  [ DISABLE QUERY REWRITE ]
AS
  <query>;
```

**关键参数：**
- `REFRESH INTERVAL 10 MINUTE vcluster default`：定时自动刷新（与动态表语法相同）
- 不写 REFRESH 子句：只能手动触发 `REFRESH MATERIALIZED VIEW <name>;`
- `BUILD DEFERRED`：延迟构建，创建时不立即计算结果
- `DISABLE QUERY REWRITE`：禁用查询改写（不自动用 MV 加速查询）

**示例：**
```sql
-- 定时自动刷新的物化视图（每 10 分钟）
CREATE MATERIALIZED VIEW mv_dept_stats
REFRESH INTERVAL 10 MINUTE vcluster default
AS
SELECT
  d.dept_id,
  d.dept_name,
  COUNT(e.emp_id) AS emp_count,
  AVG(e.salary) AS avg_salary
FROM departments d
JOIN employees e ON d.dept_id = e.dept_id
GROUP BY d.dept_id, d.dept_name;

-- 修改刷新周期（需要 CREATE OR REPLACE）
CREATE OR REPLACE MATERIALIZED VIEW mv_dept_stats
BUILD DEFERRED
REFRESH INTERVAL 20 MINUTE vcluster default
DISABLE QUERY REWRITE
AS
SELECT
  d.dept_id,
  d.dept_name,
  d.location,
  ANY_VALUE(d.col1) AS col1,
  COUNT(e.emp_id) AS emp_count,
  AVG(e.salary) AS avg_salary
FROM departments d
JOIN employees e ON d.dept_id = e.dept_id
GROUP BY d.dept_id, d.dept_name, d.location;

-- 手动刷新
REFRESH MATERIALIZED VIEW mv_dept_stats;
```

## ALTER MATERIALIZED VIEW

```sql
-- 暂停自动刷新
ALTER MATERIALIZED VIEW <name> SUSPEND;

-- 恢复自动刷新
ALTER MATERIALIZED VIEW <name> RESUME;

-- 修改注释
ALTER TABLE <mv_name> SET COMMENT '<comment>';

-- 修改列注释（物化视图用 ALTER TABLE 语法）
ALTER TABLE <mv_name> CHANGE COLUMN <col_name> COMMENT '<comment>';
```

> 注意：物化视图的注释修改使用 `ALTER TABLE`，不是 `ALTER MATERIALIZED VIEW`。

## REFRESH MATERIALIZED VIEW

```sql
-- 手动触发全量刷新
REFRESH MATERIALIZED VIEW <name>;
```

## DROP MATERIALIZED VIEW

```sql
DROP MATERIALIZED VIEW [ IF EXISTS ] <name>;
```

## SHOW / DESC

```sql
-- 列出当前 schema 下所有物化视图
SHOW TABLES WHERE is_materialized_view = true;

-- 按名称过滤
SHOW TABLES LIKE 'mv_%' WHERE is_materialized_view = true;

-- 查看物化视图结构
DESC MATERIALIZED VIEW <name>;
DESCRIBE MATERIALIZED VIEW <name> EXTENDED;

-- 查看完整建表语句
SHOW CREATE TABLE <name>;
```

## 动态表 vs 物化视图 选择指南

| 场景 | 推荐 |
|---|---|
| 需要秒/分钟级自动增量刷新 | Dynamic Table |
| 固定聚合，手动或低频刷新 | Materialized View |
| 需要 CDC 变更感知 | Dynamic Table + Table Stream |
| 加速 BI 查询，数据不要求实时 | Materialized View |

## 参考文档

- [CREATE MATERIALIZED VIEW](https://www.yunqi.tech/documents/CREATEMATERIALIZEDVIEW)
- [ALTER MATERIALIZED VIEW](https://www.yunqi.tech/documents/alter-materialzied-view)
- [REFRESH MATERIALIZED VIEW](https://www.yunqi.tech/documents/REFRESH)
- [DROP MATERIALIZED VIEW](https://www.yunqi.tech/documents/DROPMATERIALIZEDVIEW)
- [SHOW MATERIALIZED VIEWS](https://www.yunqi.tech/documents/show-materialized-view)
- [物化视图概念与场景](https://www.yunqi.tech/documents/MATERIALIZEDVIEW)
- [物化视图 DDL 汇总](https://www.yunqi.tech/documents/materialized_ddl)
