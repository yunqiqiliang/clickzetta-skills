# DML 完整语法参考

> 基于 ClickZetta Lakehouse 产品文档整理，含与 Snowflake / Spark SQL 的差异标注

---

## ⚠️ 隐式类型转换规则（INSERT / UPDATE 通用）

**ClickZetta 对写入操作（INSERT/UPDATE）严格禁止隐式类型转换，必须显式 CAST。**
但 SELECT/WHERE/表达式中允许隐式转换。

### 完整规则表（已验证）

| 目标列类型 | 写入值 | INSERT/UPDATE | WHERE/SELECT |
|---|---|---|---|
| `DATE` | `'2024-01-15'`（字符串） | ❌ 报错 | ✅ 允许 |
| `TIMESTAMP` | `'2024-01-15 12:00:00'`（字符串） | ❌ 报错 | ✅ 允许 |
| `BOOLEAN` | `'true'` / `'false'`（字符串） | ❌ 报错 | ✅ 允许 |
| `BOOLEAN` | `1` / `0`（整数） | ❌ 报错 | ✅ 允许 |
| `JSON` | `'{"k":1}'`（字符串） | ❌ 报错 | ✅ 允许 |
| `INT` / `BIGINT` | `'123'`（字符串） | ❌ 报错 | ✅ 允许 |
| `BIGINT` | `100`（INT） | ✅ 允许 | ✅ 允许 |
| `DOUBLE` | `1.5`（FLOAT） | ✅ 允许 | ✅ 允许 |
| `BIGINT` | `1.5`（FLOAT） | ✅ 允许（截断） | ✅ 允许 |

### 各类型正确写法

```sql
-- DATE（以下写法等价）
INSERT INTO t VALUES (CAST('2024-01-15' AS DATE));
INSERT INTO t VALUES (DATE '2024-01-15');
INSERT INTO t VALUES (TO_DATE('2024-01-15'));
INSERT INTO t VALUES (DATE('2024-01-15'));   -- 函数形式，也支持

-- TIMESTAMP（以下写法等价）
INSERT INTO t VALUES (CAST('2024-01-15 12:00:00' AS TIMESTAMP));
INSERT INTO t VALUES (TIMESTAMP '2024-01-15 12:00:00');
INSERT INTO t VALUES (TO_TIMESTAMP('2024-01-15 12:00:00'));
INSERT INTO t VALUES (TIMESTAMP('2024-01-15 12:00:00'));  -- 函数形式，也支持
INSERT INTO t VALUES (CURRENT_TIMESTAMP());
INSERT INTO t VALUES (CURRENT_DATE() - INTERVAL 7 DAY);

-- BOOLEAN（只接受 TRUE/FALSE 字面量或 CAST）
INSERT INTO t VALUES (TRUE);
INSERT INTO t VALUES (FALSE);
INSERT INTO t VALUES (CAST(1 AS BOOLEAN));
INSERT INTO t VALUES (CAST('true' AS BOOLEAN));

-- JSON（必须用 PARSE_JSON 或 CAST）
INSERT INTO t VALUES (PARSE_JSON('{"key":"value"}'));
INSERT INTO t VALUES (CAST('{"key":"value"}' AS JSON));

-- INT/BIGINT（字符串必须 CAST）
INSERT INTO t VALUES (CAST('123' AS INT));
INSERT INTO t VALUES (CAST('456' AS BIGINT));
```

### UPDATE 同样适用

```sql
-- ❌ UPDATE 也不允许字符串隐式转换
UPDATE orders SET dt = '2024-06-01' WHERE id = 1;       -- 报错
UPDATE orders SET flag = 0 WHERE id = 1;                 -- 报错

-- ✅ 必须显式转换
UPDATE orders SET dt = CAST('2024-06-01' AS DATE) WHERE id = 1;
UPDATE orders SET flag = CAST(0 AS BOOLEAN) WHERE id = 1;
```

### WHERE 中字符串可以隐式比较

```sql
-- ✅ WHERE 中允许字符串与日期/数字比较
SELECT * FROM orders WHERE dt = '2024-01-15';
SELECT * FROM orders WHERE dt >= '2024-01-01' AND dt < '2025-01-01';
SELECT * FROM orders WHERE id = '123';
```

**与 Snowflake / Spark 差异：**
- Snowflake / Spark：INSERT/UPDATE 时字符串可隐式转为日期/布尔/数字类型
- ClickZetta：写入时**必须显式转换**，查询时可隐式比较

> **同样适用于 RESTORE TABLE**：`RESTORE TABLE t TO TIMESTAMP AS OF '2024-01-15'` 会报错，必须用 `CAST('2024-01-15 10:00:00' AS TIMESTAMP)` 或完整毫秒时间戳字符串。

---

## INSERT

```sql
-- 追加（单行）
INSERT INTO orders VALUES (1, 101, 100.0, 'pending');
INSERT INTO orders (id, customer_id, amount) VALUES (1, 101, 100.0);

-- 追加（多行）
INSERT INTO orders VALUES
    (1, 101, 100.0, 'pending'),
    (2, 102, 200.0, 'completed');

-- 从查询追加
INSERT INTO orders SELECT * FROM staging_orders WHERE status = 'new';

-- 覆盖整表
INSERT OVERWRITE TABLE orders SELECT * FROM new_orders;

-- 覆盖指定分区（静态分区）
INSERT OVERWRITE TABLE orders PARTITION (dt = '2024-01-01')
SELECT id, amount FROM staging WHERE dt = '2024-01-01';

-- 动态分区（自动根据数据值分区）
INSERT INTO orders PARTITION (dt)
SELECT id, amount, dt FROM staging;

-- 不推荐大量数据用 VALUES，适合测试
```

**与 Snowflake 差异：**
- Snowflake 无 `INSERT OVERWRITE`；用 `TRUNCATE` + `INSERT` 或 `MERGE` 替代
- Snowflake 无 `PARTITION` 子句（Snowflake 用 CLUSTER BY 自动管理）
- ClickZetta 支持 Hive 风格动态分区

**与 Spark SQL 差异：**
- 语法基本相同，ClickZetta 完全兼容 Spark INSERT 语法

---

## UPDATE

```sql
-- 基本更新
UPDATE orders SET status = 'cancelled' WHERE id = 123;

-- 多列更新
UPDATE orders
SET status = 'completed', updated_at = current_timestamp()
WHERE id = 123;

-- 子查询更新
UPDATE orders
SET amount = amount * 1.1
WHERE customer_id IN (
    SELECT id FROM customers WHERE tier = 'VIP'
);

-- 带 ORDER BY + LIMIT（分批更新）
UPDATE orders
SET status = 'archived'
WHERE created_at < '2020-01-01'
ORDER BY created_at ASC
LIMIT 10000;
```

**与 Snowflake 差异：**
- Snowflake `UPDATE ... FROM` 语法（JOIN 更新）→ ClickZetta 用子查询替代
- ClickZetta 额外支持 `ORDER BY + LIMIT`（Snowflake 不支持）

**与 Spark SQL 差异：**
- Spark SQL 不支持 `UPDATE`（Delta Lake 支持）；ClickZetta 原生支持

---

## DELETE

```sql
-- 基本删除
DELETE FROM orders WHERE id = 123;

-- 条件删除
DELETE FROM orders WHERE created_at < '2020-01-01';

-- 子查询删除
DELETE FROM orders
WHERE order_id IN (
    SELECT order_id FROM order_details WHERE status = 'cancelled'
);

-- 删除所有行（等价于 TRUNCATE，但会记录版本）
DELETE FROM orders WHERE 1 = 1;
```

**与 Snowflake 差异：**
- 语法基本相同

**与 Spark SQL 差异：**
- Spark SQL 不支持 `DELETE`（Delta Lake 支持）；ClickZetta 原生支持

---

## MERGE INTO（UPSERT）

```sql
-- 标准 MERGE（⚠️ 多个 WHEN MATCHED 时，UPDATE 必须在 DELETE 之前）
MERGE INTO target t
USING source s ON t.id = s.id
WHEN MATCHED AND s.is_deleted = 0 THEN UPDATE SET   -- UPDATE 在前
    t.amount = s.amount,
    t.status = s.status,
    t.updated_at = current_timestamp()
WHEN MATCHED AND s.is_deleted = 1 THEN DELETE        -- DELETE 在后
WHEN NOT MATCHED THEN INSERT (id, amount, status, created_at)
    VALUES (s.id, s.amount, s.status, current_timestamp());

-- 多个 WHEN MATCHED（UPDATE 必须在 DELETE 前）
MERGE INTO target t
USING source s ON t.id = s.id
WHEN MATCHED AND s.action = 'update' THEN UPDATE SET t.amount = s.amount
WHEN MATCHED AND s.action = 'delete' THEN DELETE
WHEN NOT MATCHED THEN INSERT VALUES (s.id, s.amount);

-- 从子查询 MERGE
MERGE INTO orders t
USING (
    SELECT id, SUM(amount) AS total FROM line_items GROUP BY id
) s ON t.id = s.id
WHEN MATCHED THEN UPDATE SET t.total = s.total
WHEN NOT MATCHED THEN INSERT (id, total) VALUES (s.id, s.total);
```

**⚠️ ClickZetta MERGE 限制：**
1. `WHEN NOT MATCHED` 只能有**一个**（Snowflake 支持多个）
2. 多个 `WHEN MATCHED` 时，`UPDATE` 必须在 `DELETE` 之前
3. 一个源行不能匹配多个目标行（否则报错）

**与 Snowflake 差异：**
- Snowflake 支持多个 `WHEN NOT MATCHED`；ClickZetta 只支持一个
- Snowflake `MERGE ... WHEN NOT MATCHED BY SOURCE THEN DELETE`；ClickZetta 不支持
- 语法结构基本相同

**与 Spark SQL 差异：**
- Spark SQL（Delta Lake）支持 `WHEN NOT MATCHED BY SOURCE`；ClickZetta 不支持
- 语法结构基本相同

---

## COPY INTO（批量导入/导出）

```sql
-- 从 Volume 导入
COPY INTO orders
FROM VOLUME my_oss_volume
USING CSV
OPTIONS('header' = 'true', 'sep' = ',')
SUBDIRECTORY 'data/2024/';

-- 从 Volume 导入（Parquet）
COPY INTO orders
FROM VOLUME my_oss_volume
USING PARQUET
FILES('part-00001.parquet', 'part-00002.parquet');

-- 正则匹配文件
COPY INTO orders
FROM VOLUME my_oss_volume
USING PARQUET
REGEXP '.*2024-0[1-6].parquet';

-- 覆盖导入
COPY OVERWRITE INTO orders
FROM VOLUME my_oss_volume
USING CSV OPTIONS('header' = 'true');

-- 导出到 Volume
COPY INTO VOLUME my_oss_volume
SUBDIRECTORY 'export/orders/'
FROM orders
USING PARQUET;

-- 导出查询结果
COPY INTO VOLUME my_oss_volume
SUBDIRECTORY 'export/2024/'
FROM (SELECT * FROM orders WHERE YEAR(created_at) = 2024)
USING CSV OPTIONS('header' = 'true');
```

**与 Snowflake 差异：**
- Snowflake `COPY INTO t FROM @stage/path/file.csv` → ClickZetta `COPY INTO t FROM VOLUME v USING CSV`
- Snowflake Stage 用 `@` 前缀；ClickZetta Volume 用对象名
- Snowflake `COPY INTO @stage FROM t` → ClickZetta `COPY INTO VOLUME v FROM t`
- Snowflake 支持 `PATTERN = '.*\.csv'`；ClickZetta 用 `REGEXP`
- Snowflake `FILE_FORMAT = (TYPE = CSV)` → ClickZetta `USING CSV OPTIONS(...)`
