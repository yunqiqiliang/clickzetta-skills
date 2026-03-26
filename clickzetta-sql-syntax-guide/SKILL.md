---
name: clickzetta-sql-syntax-guide
description: |
  ClickZetta Lakehouse SQL 语法完整参考，以及与 Snowflake、Spark SQL 的差异对照。
  帮助从 Snowflake 或 Spark 迁移的用户快速找到正确语法，避免常见陷阱。
  覆盖数据类型、DDL（建表/分区/索引）、DML（INSERT/UPDATE/DELETE/MERGE）、
  查询语法（SELECT/CTE/窗口函数/JSON/LATERAL VIEW）、特有对象（VCLUSTER/DYNAMIC TABLE/
  TABLE STREAM/PIPE/VOLUME/SHARE/VECTOR）等全部语法领域。
  当用户说"Snowflake 迁移"、"Spark SQL 迁移"、"语法差异"、"ClickZetta 怎么写"、
  "Snowflake 语法在 ClickZetta 怎么用"、"TARGET_LAG"、"QUALIFY"、"VARIANT"、
  "METADATA$ACTION"、"CREATE OR REPLACE"、"LISTAGG"、"IFF"、"DATEADD"、
  "FLATTEN"、"PIVOT"、"SQL 语法参考"、"数据类型"时触发。
---

# ClickZetta Lakehouse SQL 语法指南

阅读详细差异对照：
- [references/vs-snowflake.md](references/vs-snowflake.md) — 与 Snowflake 的差异
- [references/vs-spark.md](references/vs-spark.md) — 与 Spark SQL 的差异

---

## 快速差异速查

### ⚠️ 最常见的迁移陷阱

| 场景 | Snowflake / Spark | ClickZetta 正确写法 |
|---|---|---|
| 替换建表 | `CREATE OR REPLACE TABLE t` | `CREATE TABLE IF NOT EXISTS t` + `ALTER TABLE` |
| 动态表刷新 | `TARGET_LAG = '1 minutes'` | `REFRESH INTERVAL 1 MINUTE VCLUSTER vc_name` |
| Stream 元数据 | `METADATA$ACTION` | `__change_type` |
| 对象存储导入 | `COPY INTO t FROM @stage` | `COPY INTO t FROM VOLUME v USING CSV` |
| 窗口过滤 | `QUALIFY ROW_NUMBER() = 1` | 子查询 `WHERE rn = 1` |
| 数组展开 | `FLATTEN(input => arr)` (SF) | `LATERAL VIEW EXPLODE(arr)` |
| 半结构化访问 | `data:key` (SF) | `data['key']` |
| 列表聚合 | `LISTAGG(col, ',')` (SF) | `GROUP_CONCAT(col SEPARATOR ',')` |
| 条件函数 | `IFF(cond, a, b)` (SF) | `IF(cond, a, b)` 或 `CASE WHEN` |
| 日期加减 | `DATEADD(day, 7, dt)` (SF) | `DATE_ADD(dt, 7)` 或 `dt + INTERVAL 7 DAY` |
| DATEDIFF 参数顺序 | `DATEDIFF(day, start, end)` (SF) | `DATEDIFF(end, start)` ← 顺序相反！ |
| 数值类型 | `NUMBER(p,s)` (SF) | `DECIMAL(p,s)` |
| 半结构化类型 | `VARIANT` (SF) | `JSON` |
| 行数限制 | `SELECT TOP 10` (SF) | `SELECT ... LIMIT 10` |

---

## 数据类型

```sql
-- 数值
TINYINT, SMALLINT, INT, BIGINT
FLOAT, DOUBLE
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
BOOLEAN
BINARY

-- 半结构化
JSON                   -- 替代 Snowflake VARIANT
ARRAY<T>               -- 需指定元素类型，如 ARRAY<INT>
MAP<K, V>              -- 如 MAP<STRING, INT>
STRUCT<f1:T1, f2:T2>   -- 结构体

-- AI 专用
VECTOR(FLOAT, 1024)    -- 向量类型（ClickZetta 特有）
```

---

## DDL

### 建表

```sql
CREATE TABLE IF NOT EXISTS orders (
    id          BIGINT,
    customer_id INT,
    amount      DECIMAL(18, 2),
    status      STRING,
    created_at  TIMESTAMP,
    tags        ARRAY<STRING>,
    meta        JSON
)
PARTITIONED BY (DATE(created_at))
COMMENT '订单表';

-- ⚠️ 含 ARRAY/JSON 列的表，索引需单独创建
ALTER TABLE orders ADD INDEX id_bf (id) USING BLOOM_FILTER;
ALTER TABLE orders ADD INDEX status_inv (status) USING INVERTED;
```

### 修改表

```sql
ALTER TABLE orders ADD COLUMN region STRING AFTER status;
ALTER TABLE orders RENAME COLUMN old_name TO new_name;
ALTER TABLE orders DROP COLUMN unnecessary_col;
ALTER TABLE orders SET COMMENT '新注释';
```

---

## DML

### INSERT

```sql
-- 追加
INSERT INTO orders (id, amount) VALUES (1, 100.0);
INSERT INTO orders SELECT * FROM staging_orders;

-- 覆盖（整表或分区）
INSERT OVERWRITE TABLE orders SELECT * FROM new_orders;
INSERT OVERWRITE TABLE orders PARTITION (dt='2024-01-01')
SELECT * FROM new_orders WHERE dt = '2024-01-01';
```

### UPDATE / DELETE

```sql
UPDATE orders SET status = 'cancelled' WHERE id = 123;
DELETE FROM orders WHERE created_at < '2020-01-01';
```

### MERGE INTO（UPSERT）

```sql
MERGE INTO target t
USING source s ON t.id = s.id
WHEN MATCHED AND s.deleted = 1 THEN DELETE
WHEN MATCHED THEN UPDATE SET t.amount = s.amount, t.status = s.status
WHEN NOT MATCHED THEN INSERT (id, amount, status) VALUES (s.id, s.amount, s.status);
-- ⚠️ WHEN NOT MATCHED 只能有一个
```

---

## 查询语法

### SELECT 扩展

```sql
-- 排除列（ClickZetta 特有）
SELECT * EXCEPT(password, secret_key) FROM users;

-- GROUP BY ALL（自动推断分组列）
SELECT year, month, region, SUM(amount) FROM orders GROUP BY ALL;

-- GROUPING SETS / ROLLUP / CUBE
SELECT region, product, SUM(sales)
FROM orders
GROUP BY ROLLUP (region, product);
```

### CTE

```sql
WITH
    monthly AS (
        SELECT DATE_TRUNC('month', created_at) AS month, SUM(amount) AS total
        FROM orders GROUP BY 1
    ),
    ranked AS (
        SELECT *, RANK() OVER (ORDER BY total DESC) AS rnk FROM monthly
    )
SELECT * FROM ranked WHERE rnk <= 5;
```

### 窗口函数

```sql
SELECT
    id,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS rn,
    SUM(amount) OVER (PARTITION BY customer_id
                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total,
    LAG(amount, 1) OVER (ORDER BY created_at) AS prev_amount
FROM orders;

-- 替代 Snowflake QUALIFY
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS rn
    FROM orders
) t WHERE rn = 1;
```

### JSON 查询

```sql
-- 访问 JSON 字段（用 [] 而非 Snowflake 的 :）
SELECT data['address']['city'] AS city FROM users;
SELECT data['phoneNumbers'][0]['number'] AS phone FROM users;

-- 构建 JSON
SELECT PARSE_JSON('{"name":"Alice","age":30}') AS info;

-- 类型转换
SELECT CAST(data['age'] AS INT) AS age FROM users;
```

### LATERAL VIEW（展开数组）

```sql
-- 展开数组
SELECT e.id, s.skill
FROM employees e
LATERAL VIEW EXPLODE(e.skills) s AS skill;

-- 带位置索引
SELECT e.id, ps.pos, ps.skill
FROM employees e
LATERAL VIEW POSEXPLODE(e.skills) ps AS pos, skill;

-- OUTER（空数组也保留行）
SELECT e.id, s.skill
FROM employees e
LATERAL VIEW OUTER EXPLODE(e.skills) s AS skill;
```

### STRUCT / ARRAY 操作

```sql
-- 构建 STRUCT
SELECT STRUCT(name, age, email) AS user_info FROM users;

-- 访问 STRUCT 字段
SELECT address.city, address.zip FROM users;

-- 数组操作
SELECT ARRAY_AGG(order_id) AS order_ids FROM orders GROUP BY customer_id;
SELECT TRANSFORM(skills, x -> UPPER(x)) AS upper_skills FROM employees;
SELECT FILTER(scores, x -> x > 90) AS high_scores FROM students;
SELECT ARRAY_CONTAINS(tags, 'vip') FROM users;
SELECT SIZE(skills) AS skill_count FROM employees;
```

---

## ClickZetta 特有对象速查

```sql
-- 计算集群
CREATE VCLUSTER my_vc VCLUSTER_TYPE = ANALYTICS VCLUSTER_SIZE = 4
    MIN_REPLICAS = 1 MAX_REPLICAS = 5 AUTO_SUSPEND_IN_SECOND = 1800;
USE VCLUSTER my_vc;

-- 动态表（增量计算，替代 Snowflake Dynamic Table）
CREATE DYNAMIC TABLE sales_daily
    REFRESH INTERVAL 5 MINUTE VCLUSTER default_ap
AS SELECT DATE(created_at) AS dt, SUM(amount) AS total FROM orders GROUP BY 1;

-- Table Stream（CDC，替代 Snowflake Stream）
CREATE TABLE STREAM orders_stream ON TABLE orders
    WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD');
-- 消费：__change_type = 'INSERT'/'UPDATE_BEFORE'/'UPDATE_AFTER'/'DELETE'

-- Pipe（持续导入，替代 Snowpipe）
CREATE PIPE oss_pipe
    AS COPY INTO orders FROM VOLUME my_volume USING CSV OPTIONS('header'='true');

-- Volume（对象存储，替代 Stage）
CREATE EXTERNAL VOLUME my_vol
    LOCATION 'oss://bucket/path'
    USING CONNECTION my_oss_conn;

-- Share（跨实例数据共享）
CREATE SHARE my_share;
GRANT SELECT, READ METADATA ON TABLE public.orders TO SHARE my_share;
ALTER SHARE my_share ADD INSTANCE consumer_instance;

-- Time Travel
SELECT * FROM orders TIMESTAMP AS OF '2024-01-01 00:00:00';
RESTORE TABLE orders TO TIMESTAMP '2024-01-01 00:00:00';
UNDROP TABLE orders;

-- 向量检索
CREATE TABLE docs (id INT, vec VECTOR(FLOAT, 1024),
    INDEX vec_idx (vec) USING VECTOR PROPERTIES ("distance.function"="cosine_distance"));
SELECT id, cosine_distance(vec, CAST('[0.1,0.2,...]' AS VECTOR(1024))) AS dist
FROM docs ORDER BY dist LIMIT 10;
```

---

## 常用函数速查

```sql
-- 日期
DATE_ADD(dt, 7)                    -- 加天数
DATE_SUB(dt, 7)                    -- 减天数
DATEDIFF(end_dt, start_dt)         -- 天数差（注意：end 在前！）
DATE_TRUNC('month', dt)            -- 截断到月
DATE_FORMAT(dt, 'yyyy-MM-dd')      -- 格式化
YEAR(dt) / MONTH(dt) / DAY(dt)
CURRENT_DATE() / CURRENT_TIMESTAMP() / NOW()

-- 字符串
CONCAT(s1, s2) / CONCAT_WS(',', s1, s2)
SPLIT(str, ',')                    -- 返回 ARRAY
REGEXP_EXTRACT(str, pattern, 1)
REGEXP_REPLACE(str, pattern, repl)
INSTR(str, substr)                 -- 查找位置（替代 Snowflake CHARINDEX）
UPPER(s) / LOWER(s) / TRIM(s)
SUBSTR(s, pos, len) / LEFT(s, n) / RIGHT(s, n)
LENGTH(s) / CHAR_LENGTH(s)

-- 条件
IF(cond, a, b)                     -- 替代 Snowflake IFF
CASE WHEN ... THEN ... ELSE ... END
COALESCE(a, b, c)                  -- 第一个非 NULL
NULLIF(a, b)                       -- a=b 时返回 NULL
NVL(a, b)                          -- a 为 NULL 时返回 b

-- 聚合
COUNT(*) / COUNT(DISTINCT col)
SUM / AVG / MAX / MIN
GROUP_CONCAT(col ORDER BY col SEPARATOR ',')  -- 替代 Snowflake LISTAGG
ARRAY_AGG(col)                     -- 收集为数组
APPROX_COUNT_DISTINCT(col)         -- 近似去重计数
BOOL_OR(cond) / BOOL_AND(cond)     -- 布尔聚合
```
