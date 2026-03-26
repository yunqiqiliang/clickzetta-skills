# Snowflake → ClickZetta 迁移指南

> 全面覆盖从 Snowflake 迁移到 ClickZetta Lakehouse 时遇到的 SQL 兼容性问题，所有结论均经过真实 Lakehouse 验证。

---

## 对象概念映射

| Snowflake | ClickZetta | 说明 |
|---|---|---|
| DATABASE | WORKSPACE | 顶层容器 |
| SCHEMA | SCHEMA | 相同 |
| WAREHOUSE | VCLUSTER | 计算集群 |
| STAGE | VOLUME | 文件存储区域 |
| STORAGE INTEGRATION | STORAGE CONNECTION | 对象存储认证 |
| SNOWPIPE | PIPE | 持续导入管道 |
| STREAM | TABLE STREAM | CDC 变更捕获 |
| DYNAMIC TABLE | DYNAMIC TABLE | 语法不同 |
| TASK | Studio 任务 | 调度任务 |
| SEQUENCE | IDENTITY 列 | 自增序列 |
| SHARE | SHARE | 跨实例数据共享（语法相同） |

---

## DDL 差异

### CREATE TABLE

```sql
-- Snowflake
CREATE OR REPLACE TABLE orders (
    id NUMBER AUTOINCREMENT,
    customer_id NUMBER(10,0),
    amount NUMBER(18,2),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    meta VARIANT,
    tags ARRAY
) CLUSTER BY (DATE_TRUNC('month', created_at));

-- ClickZetta 等价写法
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT IDENTITY(1),          -- AUTOINCREMENT → IDENTITY
    customer_id INT,                 -- NUMBER(10,0) → INT
    amount DECIMAL(18,2),            -- NUMBER(18,2) → DECIMAL(18,2)
    status STRING DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT current_timestamp(),
    meta JSON,                       -- VARIANT → JSON
    tags ARRAY<STRING>               -- ARRAY → ARRAY<T>（需指定元素类型）
)
CLUSTERED BY (customer_id) INTO 16 BUCKETS;  -- CLUSTER BY → CLUSTERED BY ... BUCKETS
```

### 不支持的 DDL

```sql
-- ❌ CREATE OR REPLACE TABLE（用 IF NOT EXISTS）
CREATE OR REPLACE TABLE t (...);
-- ✅ ClickZetta
CREATE TABLE IF NOT EXISTS t (...);

-- ❌ CREATE SEQUENCE（用 IDENTITY 列）
CREATE SEQUENCE my_seq START 1 INCREMENT 1;
-- ✅ ClickZetta
CREATE TABLE t (id BIGINT IDENTITY(1), ...);

-- ❌ CREATE TEMPORARY TABLE（用 CTE 替代）
CREATE TEMPORARY TABLE temp_t AS SELECT ...;
-- ✅ ClickZetta
WITH temp_t AS (SELECT ...) SELECT * FROM temp_t;

-- ❌ CREATE TRANSIENT TABLE（用 data_lifecycle 控制）
CREATE TRANSIENT TABLE t (...);
-- ✅ ClickZetta
CREATE TABLE t (...) PROPERTIES ('data_lifecycle' = '1');

-- ❌ CLUSTER BY（列级别）
CREATE TABLE t (...) CLUSTER BY (col1, col2);
-- ✅ ClickZetta（分桶）
CREATE TABLE t (...) CLUSTERED BY (col1) INTO 16 BUCKETS;
```

---

## 数据类型映射

| Snowflake | ClickZetta | 注意事项 |
|---|---|---|
| `NUMBER(p,s)` / `NUMERIC(p,s)` | `DECIMAL(p,s)` | |
| `NUMBER(10,0)` / `INTEGER` | `INT` / `BIGINT` | |
| `FLOAT` / `FLOAT4` | `FLOAT` | |
| `FLOAT8` / `DOUBLE` | `DOUBLE` | |
| `VARCHAR(n)` / `TEXT` | `STRING` 或 `VARCHAR(n)` | |
| `CHAR(n)` | `CHAR(n)` | 相同 |
| `BOOLEAN` | `BOOLEAN` | 相同，但写入规则不同（见下） |
| `DATE` | `DATE` | 相同 |
| `TIMESTAMP_LTZ` | `TIMESTAMP` | 带本地时区 |
| `TIMESTAMP_NTZ` | `TIMESTAMP_NTZ` | 无时区 |
| `TIMESTAMP_TZ` | `TIMESTAMP` | ClickZetta 无独立 TZ 类型 |
| `VARIANT` | `JSON` | 访问语法不同（见下） |
| `ARRAY` | `ARRAY<T>` | 需指定元素类型 |
| `OBJECT` | `MAP<STRING,STRING>` 或 `STRUCT<...>` | |
| `GEOGRAPHY` | 不支持 | |
| `VECTOR(FLOAT, N)` | `VECTOR(FLOAT, N)` | 相同 |

---

## ⚠️ 写入时类型转换（重要差异）

Snowflake 允许字符串隐式转换为日期/布尔等类型，ClickZetta **不允许**：

```sql
-- ❌ Snowflake 可以，ClickZetta 报错
INSERT INTO t VALUES ('2024-01-15', 'true', '123');

-- ✅ ClickZetta 必须显式转换
INSERT INTO t VALUES (DATE '2024-01-15', TRUE, CAST('123' AS INT));
INSERT INTO t VALUES (CAST('2024-01-15' AS DATE), CAST('true' AS BOOLEAN), 123);
```

| 目标类型 | Snowflake | ClickZetta |
|---|---|---|
| `DATE` ← `'2024-01-15'` | ✅ 隐式 | ❌ 需 `DATE '...'` 或 `CAST` |
| `TIMESTAMP` ← `'2024-01-15 12:00'` | ✅ 隐式 | ❌ 需 `TIMESTAMP '...'` 或 `CAST` |
| `BOOLEAN` ← `'true'` | ✅ 隐式 | ❌ 需 `TRUE`/`FALSE` 或 `CAST` |
| `BOOLEAN` ← `1` | ✅ 隐式 | ❌ 需 `CAST(1 AS BOOLEAN)` |
| `INT` ← `'123'` | ✅ 隐式 | ❌ 需 `CAST('123' AS INT)` |
| `JSON` ← `'{"k":1}'` | ✅ 隐式 | ❌ 需 `PARSE_JSON(...)` 或 `CAST` |
| WHERE 中字符串比较 | ✅ | ✅ 允许 |

---

## DML 差异

### INSERT / UPDATE

```sql
-- Snowflake：字符串可隐式转换
INSERT INTO orders VALUES (1, '2024-01-15', 'true');

-- ClickZetta：必须显式转换
INSERT INTO orders VALUES (1, DATE '2024-01-15', TRUE);
UPDATE orders SET dt = CAST('2024-06-01' AS DATE) WHERE id = 1;
```

### MERGE INTO

```sql
-- Snowflake：支持多个 WHEN NOT MATCHED，支持 WHEN NOT MATCHED BY SOURCE
MERGE INTO t USING s ON t.id = s.id
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT ...
WHEN NOT MATCHED BY SOURCE THEN DELETE;  -- ❌ ClickZetta 不支持

-- ClickZetta：WHEN NOT MATCHED 只能有一个，UPDATE 必须在 DELETE 前
MERGE INTO t USING s ON t.id = s.id
WHEN MATCHED AND s.flag = 0 THEN UPDATE SET t.val = s.val  -- UPDATE 在前
WHEN MATCHED AND s.flag = 1 THEN DELETE                    -- DELETE 在后
WHEN NOT MATCHED THEN INSERT (id, val) VALUES (s.id, s.val);
```

### 事务

```sql
-- ❌ ClickZetta 不支持事务语法
BEGIN;
BEGIN TRANSACTION;
START TRANSACTION;
COMMIT;
ROLLBACK;

-- ✅ 用 MERGE 实现原子性 UPSERT
MERGE INTO target USING source ON ...
```

---

## DQL 差异

### QUALIFY（窗口函数过滤）

```sql
-- Snowflake：支持 QUALIFY
SELECT * FROM orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) = 1;

-- ClickZetta：不支持 QUALIFY，用子查询
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS rn
    FROM orders
) t WHERE rn = 1;
```

### PIVOT / UNPIVOT

```sql
-- Snowflake：原生支持
SELECT * FROM sales
PIVOT (SUM(amount) FOR month IN ('Jan', 'Feb', 'Mar'));

-- ClickZetta：用 CASE WHEN
SELECT product,
    SUM(CASE WHEN month = 'Jan' THEN amount END) AS Jan,
    SUM(CASE WHEN month = 'Feb' THEN amount END) AS Feb
FROM sales GROUP BY product;
```

### LATERAL FLATTEN → LATERAL VIEW EXPLODE

```sql
-- Snowflake：LATERAL FLATTEN
SELECT f.value::STRING AS skill
FROM employees, LATERAL FLATTEN(input => skills) f;

-- ClickZetta：LATERAL VIEW EXPLODE
SELECT skill
FROM employees
LATERAL VIEW EXPLODE(skills) lv AS skill;

-- 带位置索引
SELECT pos, skill
FROM employees
LATERAL VIEW POSEXPLODE(skills) lv AS pos, skill;
```

### JSON 访问语法

```sql
-- Snowflake：冒号语法
SELECT data:address:city AS city FROM users;
SELECT data[0]:name AS name FROM users;
SELECT data:scores[2] AS score FROM users;

-- ClickZetta：方括号语法
SELECT data['address']['city'] AS city FROM users;
SELECT data['phoneNumbers'][0]['name'] AS name FROM users;
SELECT data['scores'][2] AS score FROM users;

-- 类型转换
-- Snowflake: data:age::INT
-- ClickZetta: CAST(data['age'] AS INT)
```

### OBJECT_CONSTRUCT / ARRAY_CONSTRUCT

```sql
-- Snowflake
SELECT OBJECT_CONSTRUCT('name', 'Alice', 'age', 30) AS obj;
SELECT ARRAY_CONSTRUCT(1, 2, 3) AS arr;

-- ClickZetta
SELECT MAP('name', 'Alice') AS obj;          -- 简单 MAP
SELECT STRUCT(1 AS id, 'Alice' AS name);     -- ⚠️ 命名字段语法不支持
SELECT STRUCT(1, 'Alice') AS person;         -- ✅ 位置参数
SELECT ARRAY(1, 2, 3) AS arr;               -- ARRAY_CONSTRUCT → ARRAY()
```

### ASOF JOIN / MATCH_RECOGNIZE

```sql
-- ❌ ClickZetta 不支持
SELECT * FROM t1 ASOF JOIN t2 ON t1.id = t2.id;
SELECT * FROM t MATCH_RECOGNIZE (...);
```

---

## 函数差异

### 日期函数

```sql
-- Snowflake → ClickZetta
DATEADD(day, 7, dt)          → DATE_ADD(dt, 7) 或 dt + INTERVAL 7 DAY
DATEDIFF(day, start, end)    → DATEDIFF(end, start)  ⚠️ 参数顺序相反！
DATE_TRUNC('month', dt)      → DATE_TRUNC('month', dt)  相同
TO_DATE('2024-01-01')        → TO_DATE('2024-01-01')  相同
CONVERT_TIMEZONE(tz, dt)     → CONVERT_TZ(dt, from_tz, to_tz)
SYSDATE() / GETDATE()        → CURRENT_TIMESTAMP() / NOW()
LAST_DAY(dt)                 → LAST_DAY(dt)  相同
YEAR(dt) / MONTH(dt)         → YEAR(dt) / MONTH(dt)  相同
```

### 字符串函数

```sql
-- Snowflake → ClickZetta
CHARINDEX(sub, s)            → INSTR(s, sub)  ⚠️ 参数顺序相反！
EDITDISTANCE(s1, s2)         → LEVENSHTEIN(s1, s2)
STRTOK(s, delim, n)          → SPLIT_PART(s, delim, n)
ILIKE(s, pattern)            → ILIKE(s, pattern)  ✅ ClickZetta 也支持！
CONTAINS(s, sub)             → INSTR(s, sub) > 0
STARTSWITH(s, prefix)        → s LIKE 'prefix%'
ENDSWITH(s, suffix)          → s LIKE '%suffix'
INITCAP(s)                   → INITCAP(s)  相同
REGEXP_LIKE(s, p)            → RLIKE(s, p) 或 s RLIKE p
```

### 聚合函数

```sql
-- Snowflake → ClickZetta
LISTAGG(col, ',') WITHIN GROUP (ORDER BY col)  → GROUP_CONCAT(col ORDER BY col SEPARATOR ',')
ARRAY_AGG(col) WITHIN GROUP (ORDER BY col)     → ARRAY_AGG(col)  ⚠️ 不支持 WITHIN GROUP
OBJECT_AGG(key, value)                         → MAP_AGG(key, value)
APPROX_COUNT_DISTINCT(col)                     → APPROX_COUNT_DISTINCT(col)  相同
MEDIAN(col)                                    → MEDIAN(col)  相同
```

### 条件函数

```sql
-- Snowflake → ClickZetta
IFF(cond, a, b)              → IF(cond, a, b)
ZEROIFNULL(x)                → COALESCE(x, 0) 或 NVL(x, 0)
NULLIFZERO(x)                → NULLIF(x, 0)
DECODE(expr, v1, r1, ...)    → DECODE(expr, v1, r1, ...)  相同
BOOLAND(a, b)                → a AND b
BOOLOR(a, b)                 → a OR b
```

---

## Stream 元数据字段

```sql
-- Snowflake Stream
METADATA$ACTION        -- 'INSERT' / 'DELETE'
METADATA$ISUPDATE      -- TRUE/FALSE（UPDATE 会产生一对 DELETE+INSERT）
METADATA$ROW_ID        -- 行唯一标识

-- ClickZetta Table Stream
__change_type          -- 'INSERT' / 'UPDATE_BEFORE' / 'UPDATE_AFTER' / 'DELETE'
__commit_version       -- 提交版本号
__commit_timestamp     -- 提交时间戳

-- 消费 Stream 的 MERGE 写法
-- Snowflake
MERGE INTO target t USING stream s ON t.id = s.id
WHEN MATCHED AND s.METADATA$ACTION = 'DELETE' THEN DELETE
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED AND s.METADATA$ACTION = 'INSERT' THEN INSERT ...;

-- ClickZetta
MERGE INTO target t USING stream s ON t.id = s.id
WHEN MATCHED AND s.__change_type = 'UPDATE_AFTER' THEN UPDATE SET ...
WHEN MATCHED AND s.__change_type = 'DELETE' THEN DELETE
WHEN NOT MATCHED AND s.__change_type = 'INSERT' THEN INSERT ...;
```

---

## Dynamic Table 差异

```sql
-- Snowflake
CREATE DYNAMIC TABLE product_sales
    TARGET_LAG = '1 minutes'
    WAREHOUSE = my_warehouse
AS SELECT ...;

-- ClickZetta（不支持 TARGET_LAG）
CREATE DYNAMIC TABLE product_sales
    REFRESH INTERVAL 1 MINUTE VCLUSTER default_ap
AS SELECT ...;
```

---

## 已验证的兼容性（Snowflake 有，ClickZetta 也有）

- `SEMI JOIN` / `ANTI JOIN` ✅
- `ILIKE` ✅（ClickZetta 也支持）
- `MINUS`（等价于 EXCEPT）✅
- `DECODE` ✅
- `INITCAP` ✅
- `MEDIAN` ✅
- `APPROX_COUNT_DISTINCT` ✅
- `TRY_CAST` ✅
- `NULLIF` / `COALESCE` / `NVL` ✅
- `GROUPING SETS` / `ROLLUP` / `CUBE` ✅
- `WITH CTE` ✅
- `REGEXP_LIKE` / `RLIKE` ✅
- `SPLIT_PART` ✅
- `LAST_DAY` ✅
- `IDENTITY` 列（替代 AUTOINCREMENT/SEQUENCE）✅
