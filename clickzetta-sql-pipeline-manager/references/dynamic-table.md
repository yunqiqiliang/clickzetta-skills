# Dynamic Table（动态表）SQL 参考

> **⚠️ ClickZetta 特有语法**
> - 刷新调度写法：`REFRESH interval 5 MINUTE VCLUSTER default_ap`（不是 `TARGET_LAG`）
> - 修改调度周期或计算集群必须用 `CREATE OR REPLACE`，`ALTER` 不支持
> - `ALTER DYNAMIC TABLE` 只支持：SUSPEND / RESUME / SET COMMENT / RENAME COLUMN

动态表是 ClickZetta Lakehouse 的核心增量计算对象。通过 SQL 查询定义，自动增量刷新，无需手动调度。

## CREATE DYNAMIC TABLE

```sql
CREATE [ OR REPLACE ] DYNAMIC TABLE <name>
  [ (<column_list>) ]
  [ PARTITIONED BY (<col_name>) ]
  [ CLUSTERED BY (<col_name>) ]
  [ COMMENT <comment> ]
  [ PROPERTIES ( data_lifecycle = <day_num> ) ]
  REFRESH [ START WITH <timestamp_expr> ] interval <n> { SECOND | MINUTE | HOUR | DAY }
  VCLUSTER <vcluster_name>
AS
  <query>;
```

**关键参数：**
- `REFRESH interval <n> MINUTE`：刷新间隔，最小 1 分钟
- `VCLUSTER`：运行刷新任务的计算集群名称（直接跟名称，不带等号和引号）
- `OR REPLACE`：若同名动态表已存在则替换（修改 SQL 逻辑或调度配置必须用此方式）

**示例：**
```sql
-- 基础示例：每 5 分钟刷新一次订单汇总
CREATE OR REPLACE DYNAMIC TABLE dw.order_summary
  REFRESH interval 5 MINUTE
  VCLUSTER default_ap
AS
SELECT
  date_trunc('hour', created_at) AS hour,
  region,
  COUNT(*) AS order_cnt,
  SUM(amount) AS total_amount
FROM ods.orders
GROUP BY 1, 2;

-- 修改调度周期（必须用 CREATE OR REPLACE）
CREATE OR REPLACE DYNAMIC TABLE dw.order_summary
  REFRESH interval 10 MINUTE
  VCLUSTER default_ap
AS
SELECT
  date_trunc('hour', created_at) AS hour,
  region,
  COUNT(*) AS order_cnt,
  SUM(amount) AS total_amount
FROM ods.orders
GROUP BY 1, 2;
```

## ALTER DYNAMIC TABLE

```sql
-- 暂停刷新
ALTER DYNAMIC TABLE <name> SUSPEND;

-- 恢复刷新
ALTER DYNAMIC TABLE <name> RESUME;

-- 修改注释
ALTER DYNAMIC TABLE <name> SET COMMENT <comment>;

-- 修改列名
ALTER DYNAMIC TABLE <name> RENAME COLUMN <old_col> TO <new_col>;

-- 修改列注释
ALTER DYNAMIC TABLE <name> CHANGE COLUMN <col_name> COMMENT <comment>;

-- 修改属性
ALTER DYNAMIC TABLE <name> SET PROPERTIES ( key = value );
ALTER DYNAMIC TABLE <name> UNSET PROPERTIES ( key );
```

> 注意：修改调度周期、计算集群、SQL 查询逻辑，必须用 `CREATE OR REPLACE DYNAMIC TABLE`，ALTER 不支持这些操作。

## REFRESH DYNAMIC TABLE（手动触发）

```sql
-- 手动触发一次刷新
REFRESH DYNAMIC TABLE <name>;
```

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
```

## 注意事项

- 修改 SQL 逻辑、调度周期、计算集群 → 用 `CREATE OR REPLACE`，不能用 `ALTER`
- 刷新间隔最小 1 分钟
- 动态表支持 Time Travel（`TIMESTAMP AS OF`）和 UNDROP
- 刷新失败不影响表的可查询性（返回上次成功版本的数据）
- 非简单加列/减列的 `CREATE OR REPLACE` 会触发一次全量刷新

## 参数化动态表（SESSION_CONFIGS）

通过 `SESSION_CONFIGS()` 函数定义参数化查询，在刷新时传入分区值控制刷新范围：

```sql
-- 创建参数化动态表
CREATE OR REPLACE DYNAMIC TABLE dwd.orders_partitioned
  REFRESH interval 30 MINUTE
  VCLUSTER default_ap
AS
SELECT order_id, user_id, amount, dt
FROM ods.orders
WHERE dt = SESSION_CONFIGS('target_date', CAST(CURRENT_DATE() AS STRING));

-- 手动触发刷新并传入参数
REFRESH DYNAMIC TABLE dwd.orders_partitioned
  WITH PROPERTIES ('target_date' = '2024-06-15');
```

适用场景：传统按天全量 ETL 改造为增量任务，用 SESSION_CONFIGS 替换调度变量。

## 动态表 DML 操作

动态表默认不支持 DML，需先开启参数：

```sql
-- 开启 DML 支持
ALTER DYNAMIC TABLE <name> SET PROPERTIES ('cz.dynamic.table.enable.dml' = 'true');

-- 支持的 DML 操作
INSERT INTO <name> VALUES (...);
DELETE FROM <name> WHERE ...;
```

> ⚠️ 执行 DML 后，下一次自动刷新会触发**全量刷新**（而非增量），仅在数据修正等特殊场景使用。

## 参考文档

- [CREATE DYNAMIC TABLE](https://www.yunqi.tech/documents/create-dynamic-table)
- [ALTER DYNAMIC TABLE](https://www.yunqi.tech/documents/alter-dynamic-table)
- [DROP DYNAMIC TABLE](https://www.yunqi.tech/documents/drop-dynamic-table)
- [SHOW DYNAMIC TABLES](https://www.yunqi.tech/documents/show-dynamic-table)
- [SHOW DYNAMIC TABLE REFRESH HISTORY](https://www.yunqi.tech/documents/refresh-history)
- [动态表简介](https://www.yunqi.tech/documents/dynamic_table_summary)
- [查看动态表刷新模式](https://www.yunqi.tech/documents/dynamic-table-incre)
- [传统离线任务转增量实践](https://www.yunqi.tech/documents/transformt-dt)
- [动态表支持参数化定义](https://www.yunqi.tech/documents/dynamicTable-parmaters)
- [动态表支持DML语句修改](https://www.yunqi.tech/documents/dynamicTable-dml)
