# ClickZetta Lakehouse vs Spark SQL 差异

> 来源：产品文档 + Spark Connector 文档

## 数据类型映射

| ClickZetta | Spark SQL | 说明 |
|---|---|---|
| `BOOLEAN` | `BooleanType` | 相同 |
| `TINYINT` | `ByteType` | 1字节 |
| `SMALLINT` | `ShortType` | 2字节 |
| `INT` | `IntegerType` | 4字节 |
| `BIGINT` | `LongType` | 8字节 |
| `FLOAT` | `FloatType` | 4字节浮点 |
| `DOUBLE` | `DoubleType` | 8字节浮点 |
| `DECIMAL(p,s)` | `DecimalType(p,s)` | 精确数值 |
| `STRING` / `VARCHAR` | `StringType` | 字符串 |
| `BINARY` | `BinaryType` | 二进制 |
| `DATE` | `DateType` | 日期 |
| `TIMESTAMP` | `TimestampType` | 带时区时间戳 |
| `TIMESTAMP_NTZ` | `TimestampNTZType` | 无时区时间戳 |
| `ARRAY<T>` | `ArrayType` | 数组 |
| `MAP<K,V>` | `MapType` | 键值对 |
| `STRUCT<f:T>` | `StructType` | 结构体 |

---

## 建表语法差异

### 分区

```sql
-- Spark SQL：PARTITIONED BY
CREATE TABLE orders (id INT, amount DECIMAL, dt STRING)
USING PARQUET
PARTITIONED BY (dt);

-- ClickZetta：相同语法，但不需要 USING 子句
CREATE TABLE orders (id INT, amount DECIMAL, dt STRING)
PARTITIONED BY (dt);
```

### Bucket（分桶）

```sql
-- Spark SQL
CREATE TABLE orders (id INT, amount DECIMAL)
CLUSTERED BY (id) INTO 8 BUCKETS;

-- ClickZetta：相同语法
CREATE TABLE orders (id INT, amount DECIMAL)
CLUSTERED BY (id) INTO 8 BUCKETS;
```

### 表属性

```sql
-- Spark SQL：TBLPROPERTIES
CREATE TABLE orders (id INT)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- ClickZetta：PROPERTIES
CREATE TABLE orders (id INT)
PROPERTIES ('data_lifecycle' = '30');  -- 数据保留天数
```

---

## 查询语法差异

### LATERAL VIEW（展开数组）

```sql
-- 两者语法相同（ClickZetta 兼容 Hive/Spark 风格）
SELECT id, skill
FROM employees
LATERAL VIEW EXPLODE(skills) t AS skill;

-- POSEXPLODE（带位置索引）
SELECT id, pos, skill
FROM employees
LATERAL VIEW POSEXPLODE(skills) t AS pos, skill;
```

### 窗口函数

```sql
-- 两者基本相同
SELECT id, amount,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS rn,
    SUM(amount) OVER (PARTITION BY customer_id
                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM orders;
```

### CTE（公用表表达式）

```sql
-- 两者语法相同
WITH
    monthly_sales AS (
        SELECT DATE_TRUNC('month', order_date) AS month, SUM(amount) AS total
        FROM orders GROUP BY 1
    ),
    ranked AS (
        SELECT *, RANK() OVER (ORDER BY total DESC) AS rnk FROM monthly_sales
    )
SELECT * FROM ranked WHERE rnk <= 3;
```

### STRUCT / ARRAY 操作

```sql
-- Spark SQL
SELECT address.city FROM users;                    -- STRUCT 字段访问
SELECT skills[0] FROM employees;                   -- ARRAY 索引
SELECT EXPLODE(skills) FROM employees;             -- 展开数组
SELECT TRANSFORM(skills, x -> UPPER(x)) FROM emp; -- 数组变换

-- ClickZetta（相同语法）
SELECT address.city FROM users;
SELECT skills[0] FROM employees;
SELECT EXPLODE(skills) FROM employees;
SELECT TRANSFORM(skills, x -> UPPER(x)) FROM emp;
```

---

## 函数差异

### 日期函数

```sql
-- 两者基本兼容
DATE_ADD(date, days)
DATE_SUB(date, days)
DATEDIFF(end_date, start_date)   -- 注意：ClickZetta 参数顺序与 Snowflake 相反
DATE_TRUNC('month', date)
DATE_FORMAT(date, 'yyyy-MM-dd')
FROM_UNIXTIME(unix_ts)
UNIX_TIMESTAMP(date_str)
```

### 字符串函数

```sql
-- 两者基本兼容
CONCAT(s1, s2, ...)
CONCAT_WS(',', s1, s2, ...)
SPLIT(str, ',')
REGEXP_EXTRACT(str, pattern, group)
REGEXP_REPLACE(str, pattern, replacement)
INSTR(str, substr)
SUBSTR(str, pos, len)
TRIM(str) / LTRIM(str) / RTRIM(str)
```

### 聚合函数

```sql
-- 两者基本兼容
COUNT(*) / COUNT(DISTINCT col)
SUM / AVG / MAX / MIN
COLLECT_LIST(col)    -- Spark：返回数组（含重复）
COLLECT_SET(col)     -- Spark：返回去重数组
ARRAY_AGG(col)       -- ClickZetta：等价于 COLLECT_LIST
```

---

## ClickZetta 特有功能（Spark 无对应）

```sql
-- 1. VCLUSTER（计算集群管理）
CREATE VCLUSTER my_vc VCLUSTER_TYPE = ANALYTICS VCLUSTER_SIZE = 4;
USE VCLUSTER my_vc;

-- 2. DYNAMIC TABLE（增量计算）
CREATE DYNAMIC TABLE sales_summary
    REFRESH INTERVAL 5 MINUTE VCLUSTER default_ap
AS SELECT customer_id, SUM(amount) FROM orders GROUP BY 1;

-- 3. TABLE STREAM（CDC 变更捕获）
CREATE TABLE STREAM orders_stream ON TABLE orders
    WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD');

-- 4. PIPE（持续导入）
CREATE PIPE my_pipe
    AS COPY INTO orders FROM VOLUME my_volume USING CSV;

-- 5. VECTOR 类型（向量检索）
CREATE TABLE embeddings (id INT, vec VECTOR(FLOAT, 1024));
SELECT id, cosine_distance(vec, vector(0.1, 0.2, ...)) AS dist
FROM embeddings ORDER BY dist LIMIT 10;

-- 6. Time Travel
SELECT * FROM orders TIMESTAMP AS OF '2024-01-01 00:00:00';
RESTORE TABLE orders TO TIMESTAMP AS OF '2024-01-01 00:00:00';
UNDROP TABLE orders;

-- 7. SHARE（跨实例数据共享）
CREATE SHARE my_share;
GRANT SELECT, READ METADATA ON TABLE public.orders TO SHARE my_share;
```

---

## Spark SQL 特有功能（ClickZetta 无对应）

```sql
-- 1. Delta Lake 特有语法
OPTIMIZE table_name ZORDER BY (col);
VACUUM table_name RETAIN 168 HOURS;

-- 2. SHOW TABLES EXTENDED
SHOW TABLES EXTENDED IN schema LIKE 'orders*';

-- 3. DESCRIBE HISTORY（Delta）
DESCRIBE HISTORY orders;

-- 4. GENERATE（生成列）
CREATE TABLE orders (
    id INT,
    year INT GENERATED ALWAYS AS (YEAR(order_date))
);
```
