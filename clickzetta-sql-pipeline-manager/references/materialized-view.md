# Materialized View（物化视图）SQL 参考

物化视图将查询结果预计算并物理存储，适合固定维度的聚合加速场景。与动态表的区别：物化视图支持手动或定时刷新，不支持增量刷新。

## CREATE MATERIALIZED VIEW

```sql
CREATE [ OR REPLACE ] MATERIALIZED VIEW <name>
  [ COMMENT = '<comment>' ]
  [ REFRESH
      { MANUAL
      | AUTO EVERY '<num> { seconds | minutes | hours | days }'
      }
  ]
  [ VCLUSTER = <vcluster_name> ]
AS
  <query>;
```

**关键参数：**
- `REFRESH MANUAL`：只能手动触发刷新（默认）
- `REFRESH AUTO EVERY '1 hours'`：定时自动刷新
- `VCLUSTER`：执行刷新的计算集群

**示例：**
```sql
-- 手动刷新的物化视图
CREATE OR REPLACE MATERIALIZED VIEW dw.mv_product_stats
  COMMENT '商品销售统计'
  REFRESH MANUAL
  VCLUSTER = default_ap
AS
SELECT
  product_id,
  COUNT(*) AS order_cnt,
  SUM(amount) AS total_revenue
FROM ods.orders
GROUP BY product_id;

-- 每小时自动刷新
CREATE OR REPLACE MATERIALIZED VIEW dw.mv_hourly_summary
  REFRESH AUTO EVERY '1 hours'
  VCLUSTER = default_ap
AS
SELECT date_trunc('hour', created_at) AS hour, SUM(amount) AS revenue
FROM ods.orders
GROUP BY 1;
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
