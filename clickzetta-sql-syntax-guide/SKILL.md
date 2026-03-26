---
name: clickzetta-sql-syntax-guide
description: |
  ClickZetta Lakehouse SQL 语法完整参考，以及与 Snowflake、Spark SQL 的全面差异对照。
  覆盖 DDL（Schema/Table/View/Index/Time Travel）、DML（INSERT/UPDATE/DELETE/MERGE/COPY INTO）、
  DQL（SELECT/JOIN/窗口函数/CTE/JSON/ARRAY/STRUCT/LATERAL VIEW）、函数（日期/字符串/聚合/条件/向量）。
  帮助从 Snowflake 或 Spark 迁移的用户快速找到正确语法，避免常见陷阱。
  当用户说"Snowflake 迁移"、"Spark SQL 迁移"、"语法差异"、"ClickZetta 怎么写"、
  "Snowflake 语法在 ClickZetta 怎么用"、"TARGET_LAG"、"QUALIFY"、"VARIANT"、
  "METADATA$ACTION"、"CREATE OR REPLACE"、"LISTAGG"、"IFF"、"DATEADD"、
  "FLATTEN"、"PIVOT"、"SQL 语法参考"、"数据类型"、"DATEDIFF"、"CHARINDEX"、
  "ILIKE"、"ZEROIFNULL"、"OBJECT_CONSTRUCT"、"ARRAY_SIZE"时触发。
---

# ClickZetta Lakehouse SQL 语法指南

## 参考文档索引

| 文档 | 内容 |
|---|---|
| [DDL 参考](references/ddl-reference.md) | Schema/Table/View/Index/Time Travel 完整语法 |
| [DML 参考](references/dml-reference.md) | INSERT/UPDATE/DELETE/MERGE/COPY INTO 完整语法 |
| [DQL 参考](references/dql-reference.md) | SELECT/JOIN/窗口函数/CTE/JSON/ARRAY/LATERAL VIEW |
| [函数参考](references/functions-reference.md) | 数值/字符串/日期/条件/聚合/向量函数完整列表 |
| [vs Snowflake](references/vs-snowflake.md) | 对象概念映射 + 语法差异汇总 |
| [vs Spark SQL](references/vs-spark.md) | 数据类型映射 + 语法差异汇总 |

---

## ⚠️ 最常见迁移陷阱（速查）

| 场景 | Snowflake / Spark | ClickZetta 正确写法 |
|---|---|---|
| 替换建表 | `CREATE OR REPLACE TABLE t` | `CREATE TABLE IF NOT EXISTS t` |
| 动态表刷新 | `TARGET_LAG = '1 minutes'` | `REFRESH INTERVAL 1 MINUTE VCLUSTER vc` |
| Stream 元数据 | `METADATA$ACTION` | `__change_type` |
| 对象存储导入 | `COPY INTO t FROM @stage` | `COPY INTO t FROM VOLUME v USING CSV` |
| 窗口过滤 | `QUALIFY ROW_NUMBER() = 1` | 子查询 `WHERE rn = 1` |
| 数组展开 | `LATERAL FLATTEN(input => arr)` (SF) | `LATERAL VIEW EXPLODE(arr)` |
| 半结构化访问 | `data:key` (SF) | `data['key']` |
| 列表聚合 | `LISTAGG(col, ',')` (SF) | `GROUP_CONCAT(col SEPARATOR ',')` |
| 条件函数 | `IFF(cond, a, b)` (SF) | `IF(cond, a, b)` |
| 日期加减 | `DATEADD(day, 7, dt)` (SF) | `DATE_ADD(dt, 7)` |
| DATEDIFF 顺序 | `DATEDIFF(day, start, end)` (SF) | `DATEDIFF(end, start)` ← 顺序相反！ |
| 查找子串位置 | `CHARINDEX(sub, s)` (SF) | `INSTR(s, sub)` ← 参数顺序相反！ |
| 不区分大小写匹配 | `ILIKE` (SF) | `LOWER(s) LIKE LOWER(pattern)` |
| 数值类型 | `NUMBER(p,s)` (SF) | `DECIMAL(p,s)` |
| 半结构化类型 | `VARIANT` (SF) | `JSON` |
| 行数限制 | `SELECT TOP 10` (SF) | `SELECT ... LIMIT 10` |
| NULL转0 | `ZEROIFNULL(x)` (SF) | `COALESCE(x, 0)` |
| 0转NULL | `NULLIFZERO(x)` (SF) | `NULLIF(x, 0)` |
| 对象聚合 | `OBJECT_AGG(k, v)` (SF) | `MAP_AGG(k, v)` |
| 数组大小 | `ARRAY_SIZE(arr)` (SF) | `SIZE(arr)` |
| PIVOT | 原生 PIVOT 语法 (SF) | `CASE WHEN` 手动实现 |
| 临时表 | `CREATE TEMPORARY TABLE` (SF) | 不支持，用 CTE 替代 |
| 日期字符串写入 | `INSERT ... VALUES (..., '2024-01-15', ...)` | `CAST('2024-01-15' AS DATE)` 或 `DATE '2024-01-15'` 或 `TO_DATE(...)` |
| 时间字符串写入 | `INSERT ... VALUES (..., '2024-01-15 12:00:00', ...)` | `CAST(... AS TIMESTAMP)` 或 `TIMESTAMP '...'` 或 `TO_TIMESTAMP(...)` |
| BOOLEAN 写入 | `INSERT ... VALUES (..., 'true', ...)` 或 `..., 1, ...` | `TRUE` / `FALSE` 或 `CAST(1 AS BOOLEAN)` |
| JSON 写入 | `INSERT ... VALUES (..., '{"k":1}', ...)` | `PARSE_JSON('{"k":1}')` 或 `CAST(... AS JSON)` |
| 字符串写入数字列 | `INSERT ... VALUES (..., '123', ...)` | `CAST('123' AS INT)` |
| UPDATE 同样限制 | `UPDATE t SET dt = '2024-01-01'` | `UPDATE t SET dt = CAST('2024-01-01' AS DATE)` |
| WHERE 中可以 | 不适用 | `WHERE dt = '2024-01-01'` ✅ WHERE 中字符串可隐式比较 |
| 索引语法关键字 | `USING BLOOM_FILTER` | `BLOOMFILTER`（无 USING） |
| DROP INDEX | `DROP INDEX idx ON table` | `DROP INDEX idx`（无 ON table） |
| TRUNCATE IF EXISTS | `TRUNCATE TABLE IF EXISTS t` | `TRUNCATE TABLE t`（不支持 IF EXISTS） |
| MERGE 多 MATCHED 顺序 | DELETE 可在 UPDATE 前 | UPDATE 必须在 DELETE 之前 |

---

## 数据类型速查

```sql
-- 数值
TINYINT / SMALLINT / INT / BIGINT
FLOAT / DOUBLE
DECIMAL(p, s)          -- 精确数值（Snowflake 用 NUMBER）

-- 字符串
STRING                 -- 推荐，无长度限制
VARCHAR(n)             -- 最大 65533 字符
CHAR(n)                -- 定长，1-255

-- 时间
DATE                   -- YYYY-MM-DD
TIMESTAMP              -- 带本地时区（≈ Snowflake TIMESTAMP_LTZ）
TIMESTAMP_NTZ          -- 无时区（同 Snowflake TIMESTAMP_NTZ）

-- 布尔 / 二进制
BOOLEAN / BINARY

-- 半结构化
JSON                   -- 替代 Snowflake VARIANT
ARRAY<T>               -- 需指定元素类型，如 ARRAY<INT>
MAP<K, V>              -- 如 MAP<STRING, INT>
STRUCT<f1:T1, f2:T2>   -- 结构体

-- AI 专用
VECTOR(FLOAT, 1024)    -- 向量类型（ClickZetta 特有）
```

---

## ClickZetta 特有对象（Snowflake/Spark 无对应）

```sql
-- 计算集群
CREATE VCLUSTER my_vc VCLUSTER_TYPE = ANALYTICS VCLUSTER_SIZE = 4;
USE VCLUSTER my_vc;

-- 动态表（增量计算）
CREATE DYNAMIC TABLE sales_daily
    REFRESH INTERVAL 5 MINUTE VCLUSTER default_ap
AS SELECT DATE(created_at) AS dt, SUM(amount) AS total FROM orders GROUP BY 1;

-- Table Stream（CDC）
CREATE TABLE STREAM orders_stream ON TABLE orders
    WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD');
-- 元数据字段：__change_type（INSERT/UPDATE_BEFORE/UPDATE_AFTER/DELETE）

-- Pipe（持续导入）
CREATE PIPE oss_pipe
    AS COPY INTO orders FROM VOLUME my_volume USING CSV OPTIONS('header'='true');

-- Volume（对象存储）
CREATE EXTERNAL VOLUME my_vol
    LOCATION 'oss://bucket/path'
    USING CONNECTION my_oss_conn;

-- Share（跨实例数据共享）
CREATE SHARE my_share;
GRANT SELECT, READ METADATA ON TABLE public.orders TO SHARE my_share;

-- Time Travel
SELECT * FROM orders TIMESTAMP AS OF '2024-01-01 00:00:00';
RESTORE TABLE orders TO TIMESTAMP AS OF '2024-01-01 00:00:00';
UNDROP TABLE orders;

-- 向量检索
CREATE TABLE docs (id INT, vec VECTOR(FLOAT, 1024),
    INDEX vec_idx (vec) USING VECTOR PROPERTIES ("distance.function"="cosine_distance"));
SELECT id, cosine_distance(vec, CAST('[0.1,0.2,...]' AS VECTOR(1024))) AS dist
FROM docs ORDER BY dist LIMIT 10;
```
