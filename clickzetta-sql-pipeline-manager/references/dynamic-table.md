# Dynamic Table（动态表）SQL 参考

> **⚠️ ClickZetta 特有语法**
> - 计算集群参数是 `VCLUSTER`，不是 `WAREHOUSE`（Snowflake 写法）
> - 修改 SQL 逻辑必须用 `CREATE OR REPLACE`，`ALTER` 不支持修改 AS 子句
> - `TARGET_LAG = DOWNSTREAM` 表示由上游动态表驱动刷新，不独立调度

动态表是 ClickZetta Lakehouse 的核心增量计算对象。通过 SQL 查询定义，自动增量刷新，无需手动调度。

## CREATE DYNAMIC TABLE

```sql
CREATE [ OR REPLACE ] DYNAMIC TABLE <name>
  TARGET_LAG = { '<num> { seconds | minutes | hours | days }' | DOWNSTREAM }
  VCLUSTER = <vcluster_name>
  [ COMMENT = '<comment>' ]
  [ PARTITION BY ( <col_name> [, <col_name>, ...] ) ]
  [ PROPERTIES ( '<key>' = '<value>' [, ...] ) ]
AS
  <query>;
```

**关键参数：**
- `TARGET_LAG`：目标延迟，如 `'1 minutes'`、`'30 seconds'`。`DOWNSTREAM` 表示由下游动态表驱动刷新
- `VCLUSTER`：运行刷新任务的计算集群名称
- `OR REPLACE`：若同名动态表已存在则替换（修改 SQL 逻辑必须用此方式）

**示例：**
```sql
-- 基础示例：每分钟刷新一次订单汇总
CREATE OR REPLACE DYNAMIC TABLE dw.order_summary
  TARGET_LAG = '1 minutes'
  VCLUSTER = default_ap
AS
SELECT
  date_trunc('hour', created_at) AS hour,
  region,
  COUNT(*) AS order_cnt,
  SUM(amount) AS total_amount
FROM ods.orders
GROUP BY 1, 2;

-- 多层动态表（下游跟随上游刷新）
CREATE OR REPLACE DYNAMIC TABLE dw.order_daily
  TARGET_LAG = DOWNSTREAM
  VCLUSTER = default_ap
AS
SELECT date(hour) AS day, region, SUM(total_amount) AS daily_amount
FROM dw.order_summary
GROUP BY 1, 2;
```

## ALTER DYNAMIC TABLE

```sql
-- 暂停刷新
ALTER DYNAMIC TABLE <name> SUSPEND;

-- 恢复刷新
ALTER DYNAMIC TABLE <name> RESUME;

-- 修改目标延迟
ALTER DYNAMIC TABLE <name> SET TARGET_LAG = '<num> { seconds | minutes | hours | days }';

-- 修改计算集群
ALTER DYNAMIC TABLE <name> SET VCLUSTER = <vcluster_name>;

-- 修改注释
ALTER DYNAMIC TABLE <name> SET COMMENT '<comment>';

-- 修改列名
ALTER DYNAMIC TABLE <name> RENAME COLUMN <old_col> TO <new_col>;
```

> 注意：修改 SQL 查询逻辑必须用 `CREATE OR REPLACE DYNAMIC TABLE`，ALTER 不支持修改 AS 子句。

## DROP DYNAMIC TABLE

```sql
DROP DYNAMIC TABLE [ IF EXISTS ] <name>;
```

## SHOW / DESC

```sql
-- 列出当前 schema 下所有动态表
SHOW TABLES WHERE is_dynamic = true;

-- 列出指定 schema 下的动态表
SHOW TABLES IN <schema_name> WHERE is_dynamic = true;

-- 查看动态表结构和调度配置
DESC DYNAMIC TABLE <name>;
DESCRIBE DYNAMIC TABLE <name> EXTENDED;

-- 查看完整建表语句
SHOW CREATE TABLE <name>;

-- 查看刷新历史（状态、耗时、触发方式、增量行数）
SHOW DYNAMIC TABLE REFRESH HISTORY <name>;
SHOW DYNAMIC TABLE REFRESH HISTORY <name> LIMIT 20;

-- 查看是否支持增量刷新
EXPLAIN SELECT * FROM <name>;
```

## 参数化动态表（SESSION_CONFIGS）

```sql
-- 定义参数化查询（用于分区增量刷新）
CREATE OR REPLACE DYNAMIC TABLE dw.sales_by_date
  TARGET_LAG = '1 hours'
  VCLUSTER = default_ap
AS
SELECT * FROM ods.sales
WHERE dt = SESSION_CONFIGS()['dt'];

-- 手动触发指定参数刷新
ALTER DYNAMIC TABLE dw.sales_by_date REFRESH CONFIGS ('dt'='2026-03-20');
```

## 注意事项

- 修改 SQL 逻辑 → 用 `CREATE OR REPLACE`，不能用 `ALTER`
- `TARGET_LAG = DOWNSTREAM` 只能用于有上游动态表的场景
- 动态表支持 Time Travel（`TIMESTAMP AS OF`）和 UNDROP
- 刷新失败不影响表的可查询性（返回上次成功版本的数据）

## 参考文档

- [CREATE DYNAMIC TABLE](https://www.yunqi.tech/documents/create-dynamic-table)
- [ALTER DYNAMIC TABLE](https://www.yunqi.tech/documents/alter-dynamic-table)
- [DROP DYNAMIC TABLE](https://www.yunqi.tech/documents/drop-dynamic-table)
- [SHOW DYNAMIC TABLES](https://www.yunqi.tech/documents/show-dynamic-table)
- [SHOW DYNAMIC TABLE REFRESH HISTORY](https://www.yunqi.tech/documents/refresh-history)
- [动态表简介](https://www.yunqi.tech/documents/dynamic_table_summary)
- [查看动态表刷新模式](https://www.yunqi.tech/documents/dynamic-table-incre)
- [动态表支持参数化定义](https://www.yunqi.tech/documents/dynamicTable-parmaters)
- [传统离线任务转增量实践](https://www.yunqi.tech/documents/transformt-dt)
