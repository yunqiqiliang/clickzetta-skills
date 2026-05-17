# DDL 完整语法参考

> 基于 ClickZetta Lakehouse 产品文档整理，含与 Snowflake / Spark SQL 的差异标注

---

## SCHEMA 操作

```sql
-- 创建
CREATE SCHEMA IF NOT EXISTS my_schema COMMENT '说明';

-- 修改
ALTER SCHEMA my_schema RENAME TO new_schema;
ALTER SCHEMA my_schema SET COMMENT '新注释';

-- 删除（级联删除所有对象）
DROP SCHEMA IF EXISTS my_schema;

-- 查看
SHOW SCHEMAS;
SHOW SCHEMAS EXTENDED;                          -- 含 type 列（MANAGED/EXTERNAL）
SHOW SCHEMAS LIKE 'sales%';
SHOW SCHEMAS WHERE schema_name = 'public';

-- 切换
USE SCHEMA my_schema;
USE my_schema;                                  -- SCHEMA 关键字可省略
```

**与 Snowflake 差异：**
- Snowflake 用 `USE DATABASE` + `USE SCHEMA`；ClickZetta 无 DATABASE 层，直接 `USE SCHEMA`
- Snowflake 支持 `CREATE OR REPLACE SCHEMA`；ClickZetta 不支持，用 `IF NOT EXISTS`

---

## TABLE 操作

### CREATE TABLE

```sql
-- 基本建表
CREATE TABLE IF NOT EXISTS orders (
    id          BIGINT,
    customer_id INT,
    amount      DECIMAL(18, 2)  NOT NULL,
    status      STRING          DEFAULT 'pending',
    created_at  TIMESTAMP,
    tags        ARRAY<STRING>,
    meta        JSON,
    COMMENT '订单表'
);

-- 主键表（ENABLE VALIDATE RELY：SQL写入也去重）
CREATE TABLE pk_orders (
    id     BIGINT PRIMARY KEY,
    amount DECIMAL(18, 2)
);

-- 主键表（DISABLE NOVALIDATE RELY：仅实时写入去重，SQL写入不去重）
CREATE TABLE cdc_orders (
    id     BIGINT PRIMARY KEY DISABLE NOVALIDATE RELY,
    amount DECIMAL(18, 2)
);

-- 自增列（仅 BIGINT，不保证连续）
CREATE TABLE auto_id_table (
    id  BIGINT IDENTITY(1),    -- 从1开始
    col STRING
);

-- 生成列（确定性表达式，不可手动插入）
CREATE TABLE orders_with_year (
    id         BIGINT,
    created_at TIMESTAMP,
    year       INT GENERATED ALWAYS AS (YEAR(created_at))
);

-- 默认值（支持非确定性函数）
CREATE TABLE t_default (
    id         INT,
    created_at TIMESTAMP DEFAULT current_timestamp(),
    status     STRING    DEFAULT 'active',
    score      DOUBLE    DEFAULT random()
);

-- 分区表（Iceberg 隐藏分区）
CREATE TABLE orders_partitioned (
    id         BIGINT,
    amount     DECIMAL(18, 2),
    created_at TIMESTAMP
)
PARTITIONED BY (days(created_at));             -- 按天分区

-- 分区转换函数
-- years(col)   months(col)   days(col)   hours(col)
-- bucket(N, col)   truncate(col, W)

-- 分桶表
CREATE TABLE orders_bucketed (
    id         BIGINT,
    customer_id INT,
    amount     DECIMAL(18, 2)
)
CLUSTERED BY (customer_id)
SORTED BY (id ASC)
INTO 16 BUCKETS;

-- 数据保留周期
CREATE TABLE orders (id BIGINT)
PROPERTIES ('data_lifecycle' = '30');          -- 保留30天

-- CTAS（从查询建表）
CREATE TABLE orders_copy AS
SELECT * FROM orders WHERE status = 'completed';

-- 外部表（映射对象存储）
CREATE EXTERNAL TABLE ext_orders (
    id     BIGINT,
    amount DECIMAL(18, 2)
)
LOCATION 'oss://bucket/orders/'
STORED AS PARQUET;
```

**与 Snowflake 差异：**
- Snowflake `CREATE OR REPLACE TABLE` → ClickZetta `CREATE TABLE IF NOT EXISTS`
- Snowflake `CLUSTER BY (col)` → ClickZetta `CLUSTERED BY (col) INTO N BUCKETS`
- Snowflake `AUTOINCREMENT` → ClickZetta `IDENTITY[(seed)]`
- Snowflake `TRANSIENT TABLE` → ClickZetta 无对应（用 `data_lifecycle` 控制保留期）
- Snowflake `TEMPORARY TABLE` → ClickZetta 无临时表概念
- Snowflake `COPY GRANTS` → ClickZetta 不支持

**与 Spark SQL 差异：**
- Spark `USING PARQUET` → ClickZetta 不需要（默认 Parquet）
- Spark `TBLPROPERTIES` → ClickZetta `PROPERTIES`
- Spark `LOCATION` 外部表语法基本相同

### ALTER TABLE

```sql
-- 重命名
ALTER TABLE orders RENAME TO orders_v2;

-- 注释
ALTER TABLE orders SET COMMENT '新注释';

-- 数据保留周期
ALTER TABLE orders SET PROPERTIES ('data_retention_days' = '7');

-- 添加列
ALTER TABLE orders ADD COLUMN region STRING AFTER status;
ALTER TABLE orders ADD COLUMN region STRING FIRST;

-- 添加复杂类型嵌套字段
ALTER TABLE t ADD COLUMN address.zip STRING;           -- STRUCT 嵌套
ALTER TABLE t ADD COLUMN items.ELEMENT.price DOUBLE;   -- ARRAY<STRUCT> 嵌套

-- 修改列类型（有限制）
ALTER TABLE orders ALTER COLUMN amount TYPE DOUBLE;

-- 重命名列
ALTER TABLE orders RENAME COLUMN old_col TO new_col;

-- 删除列
ALTER TABLE orders DROP COLUMN unnecessary_col;

-- 修改列注释
ALTER TABLE orders ALTER COLUMN amount COMMENT '订单金额';

-- 添加索引（含 ARRAY/JSON 列的表必须单独添加）
-- ⚠️ 索引语法：BLOOMFILTER（不是 USING BLOOM_FILTER）
CREATE BLOOMFILTER INDEX IF NOT EXISTS id_bf ON TABLE orders(id);
CREATE BLOOMFILTER INDEX IF NOT EXISTS name_bf ON TABLE orders(name)
    PROPERTIES ('analyzer' = 'ngram', 'n' = '3');  -- ngram 分词

-- 倒排索引
CREATE INVERTED INDEX IF NOT EXISTS content_inv ON TABLE articles(content);

-- 向量索引（建表时内联）
-- 见 CREATE TABLE 示例

-- 删除索引（⚠️ 不需要 ON table_name）
DROP INDEX IF EXISTS id_bf;
DROP INDEX id_bf;
```

**与 Snowflake 差异：**
- Snowflake `ALTER TABLE ... ADD COLUMN` 只能加到末尾；ClickZetta 支持 `FIRST/AFTER/BEFORE`
- Snowflake 不支持 `DROP COLUMN`（需重建表）；ClickZetta 支持
- Snowflake 无 BLOOM_FILTER/INVERTED/VECTOR 索引

### DROP / TRUNCATE TABLE

```sql
-- 删除表（可 UNDROP 恢复）
DROP TABLE IF EXISTS orders;
DROP TABLE my_schema.orders;

-- 清空表（保留结构）
TRUNCATE TABLE orders;
TRUNCATE TABLE IF EXISTS orders;               -- ✅ 支持 IF EXISTS

-- 清空指定分区
TRUNCATE TABLE orders PARTITION (dt = '2024-01-01');
TRUNCATE TABLE orders PARTITION (dt > '2024-01-01');
TRUNCATE TABLE orders PARTITION (dt >= '2024-01-01' AND dt < '2024-02-01');
```

**与 Snowflake 差异：**
- Snowflake `TRUNCATE TABLE` 不支持分区条件；ClickZetta 支持
- Snowflake `DROP TABLE ... PURGE` 立即删除；ClickZetta 删除后在保留期内可 UNDROP

---

## VIEW 操作

```sql
-- 创建视图
CREATE VIEW IF NOT EXISTS order_summary AS
SELECT customer_id, COUNT(*) AS cnt, SUM(amount) AS total
FROM orders GROUP BY customer_id;

-- 替换视图（ClickZetta 支持 OR REPLACE，与 Snowflake 相同）
CREATE OR REPLACE VIEW order_summary AS
SELECT customer_id, SUM(amount) AS total FROM orders GROUP BY customer_id;

-- 带列别名和注释
CREATE VIEW order_summary (cust_id COMMENT '客户ID', total COMMENT '总金额')
COMMENT '订单汇总视图'
AS SELECT customer_id, SUM(amount) FROM orders GROUP BY 1;

-- 删除
DROP VIEW IF EXISTS order_summary;

-- 查看
SHOW TABLES WHERE is_view = true;
SHOW TABLES IN my_schema WHERE is_view = true;
```

**注意：** ClickZetta 的 `CREATE OR REPLACE VIEW` 与 Snowflake 相同，但 `CREATE OR REPLACE TABLE` 不支持。

---

## INDEX 操作

```sql
-- 查看索引
SHOW INDEX FROM table_name;
SHOW INDEX FROM my_schema.table_name;

-- 查看索引详情
DESC INDEX index_name;
DESC INDEX EXTENDED index_name;

-- 构建存量数据索引（仅向量索引和倒排索引，不支持 Bloom Filter）
BUILD INDEX index_name ON table_name;
BUILD INDEX index_name ON table_name WHERE partition_col = '2024-01-01';
```

---

## 查看对象信息

```sql
-- 表结构
DESC table_name;
DESC EXTENDED table_name;                      -- 含大小、记录数等扩展信息
DESCRIBE TABLE table_name;                     -- 同 DESC

-- 列信息
SHOW COLUMNS IN table_name;
SHOW COLUMNS FROM table_name IN schema_name;

-- 建表语句
SHOW CREATE TABLE table_name;

-- 表列表
SHOW TABLES;
SHOW TABLES IN my_schema;
SHOW TABLES LIKE 'order%';
SHOW TABLES WHERE is_view = false AND is_materialized_view = false;
SHOW TABLES WHERE is_dynamic = true;
SHOW TABLES WHERE is_external = true;

-- 分区信息
SHOW PARTITIONS table_name;
SHOW PARTITIONS EXTENDED table_name;           -- 含文件数、大小、修改时间
SHOW PARTITIONS table_name PARTITION (dt = '2024-01-01');
SHOW PARTITIONS table_name WHERE total_rows > 1000;

-- 历史版本
DESC HISTORY table_name;
SHOW TABLES HISTORY;                           -- 含已删除的表
```

---

## SYNONYM（同义词）操作

```sql
-- 为表创建同义词（跨 Schema 访问）
CREATE SYNONYM my_orders FOR TABLE other_schema.orders;

-- 为 Volume 创建同义词
CREATE SYNONYM my_vol FOR VOLUME other_schema.data_volume;

-- 为函数创建同义词
CREATE SYNONYM my_func FOR FUNCTION other_schema.udf_name;

-- 查看同义词
SHOW SYNONYMS;
SHOW SYNONYMS IN my_schema;
SHOW SYNONYMS LIKE 'my_%';

-- 删除同义词（需指定对象类型）
DROP SYNONYM my_orders FOR TABLE;
DROP SYNONYM my_vol FOR VOLUME;
DROP SYNONYM my_func FOR FUNCTION;
```

> 同义词支持的对象类型：TABLE（含普通表、Table Stream、物化视图、动态表）、VOLUME、FUNCTION。
> 使用场景：跨 Schema 访问、数据一致性维护、应用层解耦。

---

## Time Travel & 数据恢复

```sql
-- 查询历史版本
SELECT * FROM orders TIMESTAMP AS OF '2024-01-01 00:00:00';
SELECT * FROM orders TIMESTAMP AS OF CURRENT_TIMESTAMP() - INTERVAL 12 HOURS;
SELECT * FROM orders TIMESTAMP AS OF CAST('2024-01-01' AS TIMESTAMP);

-- 恢复表到历史版本（表未删除）
RESTORE TABLE orders TO TIMESTAMP AS OF '2024-01-01 00:00:00';

-- 恢复已删除的表
UNDROP TABLE orders;
UNDROP TABLE my_schema.orders;

-- 设置保留周期（0-90天，默认1天）
ALTER TABLE orders SET PROPERTIES ('data_retention_days' = '7');
```

**与 Snowflake 差异：**
- Snowflake `AT (TIMESTAMP => ...)` → ClickZetta `TIMESTAMP AS OF ...`
- Snowflake `BEFORE (STATEMENT => ...)` → ClickZetta 不支持按 statement_id 回溯
- Snowflake `UNDROP TABLE` → ClickZetta 相同
- Snowflake 默认保留 1 天（Enterprise 90 天）；ClickZetta 默认 1 天，最长 90 天
