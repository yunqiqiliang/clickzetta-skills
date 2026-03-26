# DML 完整语法参考

> 基于 ClickZetta Lakehouse 产品文档整理，含与 Snowflake / Spark SQL 的差异标注

---

## ⚠️ 日期/时间类型写入规则

**ClickZetta 不允许字符串隐式转换为 DATE/TIMESTAMP 类型（INSERT 时）。**
必须显式转换，否则报错：`implicit cast not allowed`

```sql
-- ❌ 错误：字符串不能隐式转为 DATE/TIMESTAMP
INSERT INTO orders VALUES (1, '2024-01-15', '2024-01-15 12:30:00');

-- ✅ 正确方式 1：CAST 显式转换
INSERT INTO orders VALUES (1, CAST('2024-01-15' AS DATE), CAST('2024-01-15 12:30:00' AS TIMESTAMP));

-- ✅ 正确方式 2：TO_DATE / TO_TIMESTAMP 函数
INSERT INTO orders VALUES (1, TO_DATE('2024-01-15'), TO_TIMESTAMP('2024-01-15 12:30:00'));

-- ✅ 正确方式 3：DATE / TIMESTAMP 字面量
INSERT INTO orders VALUES (1, DATE '2024-01-15', TIMESTAMP '2024-01-15 12:30:00');

-- ✅ 正确方式 4：当前时间函数
INSERT INTO orders VALUES (1, CURRENT_DATE(), CURRENT_TIMESTAMP());

-- ✅ 正确方式 5：INTERVAL 运算
INSERT INTO orders VALUES (1, CURRENT_DATE() - INTERVAL 7 DAY, CURRENT_TIMESTAMP() - INTERVAL 1 HOUR);
```

**注意：WHERE 条件中字符串可以与日期比较（隐式转换允许）：**
```sql
-- ✅ WHERE 中字符串可以与 DATE 比较
SELECT * FROM orders WHERE dt = '2024-01-15';
SELECT * FROM orders WHERE dt >= '2024-01-01' AND dt < '2025-01-01';
```

**与 Snowflake / Spark 差异：**
- Snowflake / Spark：INSERT 时字符串可隐式转为日期类型
- ClickZetta：INSERT 时**必须显式转换**，WHERE 中可隐式比较

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
