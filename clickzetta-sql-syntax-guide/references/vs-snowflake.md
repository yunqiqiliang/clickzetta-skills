# ClickZetta Lakehouse vs Snowflake SQL 差异

> 来源：产品文档 + 迁移实践

## 对象概念映射

| ClickZetta Lakehouse | Snowflake | 说明 |
|---|---|---|
| WORKSPACE | DATABASE | 工作空间 ≈ 数据库 |
| SCHEMA | SCHEMA | 相同 |
| VCLUSTER | WAREHOUSE | 计算集群 |
| STORAGE CONNECTION | STORAGE INTEGRATION | 对象存储认证 |
| VOLUME | STAGE | 文件存储区域 |
| TABLE | TABLE | 相同 |
| PIPE | SNOWPIPE | 持续导入管道 |
| TABLE STREAM | STREAM | 变更数据捕获 |
| DYNAMIC TABLE | DYNAMIC TABLE | 增量计算表（语法不同） |
| Studio 任务 | TASK | 调度任务 |

---

## DDL 差异

### CREATE OR REPLACE vs IF NOT EXISTS

```sql
-- Snowflake：支持 CREATE OR REPLACE
CREATE OR REPLACE TABLE orders (id INT, amount DECIMAL);

-- ClickZetta：不支持 CREATE OR REPLACE，用 IF NOT EXISTS
CREATE TABLE IF NOT EXISTS orders (id INT, amount DECIMAL);
-- 修改已有表用 ALTER TABLE
```

### 注释语法

```sql
-- Snowflake：支持 // 和 ///
// 这是注释
/// 这也是注释

-- ClickZetta：只支持 -- 和 /* */
-- 这是注释
/* 这也是注释 */
```

### 数据类型差异

| ClickZetta | Snowflake | 说明 |
|---|---|---|
| `STRING` | `VARCHAR` / `TEXT` | ClickZetta 推荐用 STRING |
| `TIMESTAMP` | `TIMESTAMP_LTZ` | 本地时区时间戳 |
| `TIMESTAMP_NTZ` | `TIMESTAMP_NTZ` | 无时区时间戳 |
| `JSON` | `VARIANT` | 半结构化数据 |
| `ARRAY<T>` | `ARRAY` | ClickZetta 需指定元素类型 |
| `MAP<K,V>` | `OBJECT` | 键值对 |
| `STRUCT<f:T,...>` | `OBJECT` | 结构体 |
| `VECTOR(FLOAT, N)` | 无原生支持 | 向量类型（ClickZetta 特有） |
| `TINYINT` | `NUMBER(3,0)` | 1字节整数 |
| `SMALLINT` | `NUMBER(5,0)` | 2字节整数 |
| 无 `NUMBER` | `NUMBER(p,s)` | ClickZetta 用 `DECIMAL(p,s)` |

### ⚠️ 写入时隐式类型转换（重要差异）

Snowflake 允许写入时字符串隐式转换为日期/布尔等类型，ClickZetta **不允许**：

| 操作 | Snowflake | ClickZetta |
|---|---|---|
| INSERT 字符串→DATE | ✅ 允许 | ❌ 报错，需 `CAST` 或 `DATE '...'` |
| INSERT 字符串→TIMESTAMP | ✅ 允许 | ❌ 报错，需 `CAST` 或 `TIMESTAMP '...'` |
| INSERT 字符串→BOOLEAN | ✅ 允许 | ❌ 报错，需 `TRUE`/`FALSE` 或 `CAST` |
| INSERT 字符串→INT | ✅ 允许 | ❌ 报错，需 `CAST('123' AS INT)` |
| INSERT 字符串→JSON | ✅ 允许 | ❌ 报错，需 `PARSE_JSON(...)` 或 `CAST` |
| UPDATE 字符串→DATE | ✅ 允许 | ❌ 报错，需 `CAST` |
| WHERE 字符串=DATE | ✅ 允许 | ✅ 允许（查询中可隐式比较） |

### 建表语法差异

```sql
-- Snowflake：CLUSTER BY
CREATE TABLE orders (id INT, dt DATE)
CLUSTER BY (dt);

-- ClickZetta：CLUSTERED BY + PARTITIONED BY
CREATE TABLE orders (
    id INT,
    dt DATE
)
PARTITIONED BY (dt)
CLUSTERED BY (id) INTO 8 BUCKETS;

-- ClickZetta 特有：Sort Key（内联索引）
CREATE TABLE orders (
    id INT,
    amount DECIMAL,
    INDEX amount_bf (amount) USING BLOOM_FILTER
);
```

---

## DML 差异

### INSERT

```sql
-- 两者基本相同，ClickZetta 额外支持：
INSERT OVERWRITE TABLE orders SELECT * FROM staging;  -- 覆盖写入（Hive 风格）
INSERT INTO orders PARTITION (dt='2024-01-01') VALUES (1, 100);  -- 静态分区
```

### UPDATE

```sql
-- Snowflake
UPDATE orders SET amount = amount * 1.1 WHERE status = 'VIP';

-- ClickZetta：相同语法，额外支持 ORDER BY + LIMIT
UPDATE orders SET amount = amount * 1.1
WHERE status = 'VIP'
ORDER BY created_at DESC
LIMIT 1000;
```

### MERGE INTO

```sql
-- ClickZetta 限制：WHEN NOT MATCHED 只能有一个
-- Snowflake 支持多个 WHEN NOT MATCHED

-- ClickZetta MERGE 示例（⚠️ UPDATE 必须在 DELETE 之前）
MERGE INTO target t
USING source s ON t.id = s.id
WHEN MATCHED THEN UPDATE SET t.amount = s.amount
WHEN MATCHED AND s.action = 'DELETE' THEN DELETE
WHEN NOT MATCHED THEN INSERT (id, amount) VALUES (s.id, s.amount);
```

---

## 查询语法差异

### SELECT 扩展

```sql
-- ClickZetta 特有：SELECT * EXCEPT(col)
SELECT * EXCEPT(sensitive_col) FROM users;

-- ClickZetta 特有：GROUP BY ALL（自动推断分组列）
SELECT year, month, SUM(amount)
FROM orders
GROUP BY ALL;

-- 两者都支持：GROUPING SETS / ROLLUP / CUBE
SELECT region, product, SUM(sales)
FROM orders
GROUP BY GROUPING SETS ((region), (product), ());
```

### JSON 查询

```sql
-- Snowflake：VARIANT 类型，用 : 访问
SELECT data:address:city FROM users;
SELECT data[0]:name FROM users;

-- ClickZetta：JSON 类型，用 [] 访问
SELECT data['address']['city'] FROM users;
SELECT data['phoneNumbers'][0]['number'] FROM users;

-- 两者都支持 PARSE_JSON
SELECT parse_json('{"name":"Alice"}')['name'];
```

### LATERAL VIEW（展开数组）

```sql
-- ClickZetta（Hive 风格）
SELECT e.id, s.skill
FROM employees e
LATERAL VIEW EXPLODE(e.skills) s AS skill;

-- Snowflake（用 FLATTEN）
SELECT e.id, f.value::STRING AS skill
FROM employees e,
LATERAL FLATTEN(input => e.skills) f;
```

### QUALIFY（窗口函数过滤）

```sql
-- Snowflake 支持 QUALIFY
SELECT * FROM orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) = 1;

-- ClickZetta：不支持 QUALIFY，用子查询替代
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS rn
    FROM orders
) t WHERE rn = 1;
```

### PIVOT / UNPIVOT

```sql
-- Snowflake 原生支持 PIVOT
SELECT * FROM sales
PIVOT (SUM(amount) FOR month IN ('Jan', 'Feb', 'Mar'));

-- ClickZetta：用 CASE WHEN 实现
SELECT
    product,
    SUM(CASE WHEN month = 'Jan' THEN amount END) AS Jan,
    SUM(CASE WHEN month = 'Feb' THEN amount END) AS Feb
FROM sales GROUP BY product;
```

---

## 流（Stream）差异

```sql
-- Snowflake Stream 元数据字段
METADATA$ACTION        -- 'INSERT' / 'DELETE'
METADATA$ISUPDATE      -- TRUE/FALSE
METADATA$ROW_ID        -- 行唯一标识

-- ClickZetta Table Stream 元数据字段
__change_type          -- 'INSERT' / 'UPDATE_BEFORE' / 'UPDATE_AFTER' / 'DELETE'
__commit_version       -- 提交版本号
__commit_timestamp     -- 提交时间戳
```

---

## 动态表（Dynamic Table）差异

```sql
-- Snowflake Dynamic Table
CREATE DYNAMIC TABLE product_sales
    TARGET_LAG = '1 minutes'
    WAREHOUSE = my_warehouse
AS SELECT ...;

-- ClickZetta Dynamic Table（不支持 TARGET_LAG）
CREATE DYNAMIC TABLE product_sales
    REFRESH INTERVAL 1 MINUTE VCLUSTER default_ap
AS SELECT ...;
```

---

## 对象存储（Stage vs Volume）

```sql
-- Snowflake：Stage
CREATE STAGE my_stage
    URL = 's3://bucket/path'
    STORAGE_INTEGRATION = my_integration;

COPY INTO orders FROM @my_stage/data.csv;

-- ClickZetta：Volume
CREATE EXTERNAL VOLUME my_volume
    LOCATION = 'oss://bucket/path'
    USING CONNECTION my_oss_conn;

COPY INTO orders FROM VOLUME my_volume USING CSV;
```

---

## 函数差异

### 日期函数

```sql
-- Snowflake
DATEADD(day, 7, order_date)
DATEDIFF(day, start_date, end_date)
DATE_TRUNC('month', order_date)
TO_DATE('2024-01-01')
CURRENT_TIMESTAMP()

-- ClickZetta（兼容 Hive/Spark 风格）
DATE_ADD(order_date, 7)           -- 或 order_date + INTERVAL 7 DAY
DATEDIFF(end_date, start_date)    -- 注意参数顺序相反！
DATE_TRUNC('month', order_date)   -- 相同
TO_DATE('2024-01-01')             -- 相同
CURRENT_TIMESTAMP()               -- 相同，也支持 NOW()
```

### 字符串函数

```sql
-- Snowflake
CHARINDEX('sub', str)     -- 查找子串位置
EDITDISTANCE(s1, s2)      -- 编辑距离
SOUNDEX(str)              -- 语音相似度
INITCAP(str)              -- 首字母大写

-- ClickZetta
INSTR(str, 'sub')         -- 查找子串位置（Hive 风格）
LOCATE('sub', str)        -- 也支持
LEVENSHTEIN(s1, s2)       -- 编辑距离
INITCAP(str)              -- 相同
```

### 条件函数

```sql
-- Snowflake
IFF(condition, true_val, false_val)
ZEROIFNULL(expr)
NULLIFZERO(expr)
DECODE(expr, val1, res1, val2, res2, default)

-- ClickZetta
IF(condition, true_val, false_val)   -- 或 CASE WHEN
COALESCE(expr, 0)                    -- 替代 ZEROIFNULL
NULLIF(expr, 0)                      -- 替代 NULLIFZERO
DECODE(expr, val1, res1, ...)        -- 支持（兼容）
```

### 聚合函数

```sql
-- Snowflake
LISTAGG(col, ',') WITHIN GROUP (ORDER BY col)
ARRAY_AGG(col)
OBJECT_AGG(key, value)
APPROX_COUNT_DISTINCT(col)

-- ClickZetta
GROUP_CONCAT(col ORDER BY col SEPARATOR ',')  -- 替代 LISTAGG
ARRAY_AGG(col)                                -- 相同
MAP_AGG(key, value)                           -- 替代 OBJECT_AGG
APPROX_COUNT_DISTINCT(col)                    -- 相同
```

---

## 权限体系差异

| 概念 | ClickZetta | Snowflake |
|---|---|---|
| 顶层容器 | WORKSPACE | DATABASE |
| 权限对象 | VCLUSTER / SCHEMA / TABLE / VIEW | WAREHOUSE / DATABASE / SCHEMA / TABLE |
| 角色授予 | `GRANT ROLE r TO USER u` | `GRANT ROLE r TO USER u` |
| 查看权限 | `SHOW GRANTS TO USER u` | `SHOW GRANTS TO USER u` |
| 系统角色 | instance_admin / workspace_admin / workspace_dev / workspace_analyst | ACCOUNTADMIN / SYSADMIN / USERADMIN |
