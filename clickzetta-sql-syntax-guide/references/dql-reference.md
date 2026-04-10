# DQL 完整语法参考

> 基于 ClickZetta Lakehouse 产品文档整理，含与 Snowflake / Spark SQL 的差异标注

---

## SELECT 基本语法

```sql
[WITH cte_name AS (SELECT ...) [, ...]]
SELECT
    [/*+ HINTS */]
    [ALL | DISTINCT]
    select_expr [, ...]
    [EXCEPT (col1, col2, ...)]
FROM table_reference
[WHERE condition]
[GROUP BY [GROUPING SETS | ROLLUP | CUBE] {col | expr | position}]
[HAVING condition]
[ORDER BY col [ASC | DESC] [NULLS FIRST | NULLS LAST] [, ...]]
[LIMIT n [OFFSET m]]
```

---

## SELECT 扩展

### EXCEPT（排除列）

```sql
-- 排除指定列（ClickZetta 特有，Snowflake/Spark 也支持）
SELECT * EXCEPT(password, secret_key) FROM users;
SELECT * EXCEPT(meta, tags) FROM orders;
```

### DISTINCT

```sql
SELECT DISTINCT customer_id FROM orders;
SELECT ALL customer_id FROM orders;    -- 默认，保留重复
```

### LIMIT / OFFSET

```sql
SELECT * FROM orders LIMIT 100;
SELECT * FROM orders LIMIT 100 OFFSET 200;   -- 跳过前200行

-- ⚠️ ClickZetta 不支持 Snowflake 的 TOP N 语法
-- Snowflake: SELECT TOP 10 * FROM orders;
-- ClickZetta: SELECT * FROM orders LIMIT 10;
```

---

## FROM 子句

### JOIN

```sql
-- INNER JOIN
SELECT o.id, c.name FROM orders o
INNER JOIN customers c ON o.customer_id = c.id;

-- LEFT / RIGHT / FULL OUTER JOIN
SELECT o.id, c.name FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id;

-- CROSS JOIN
SELECT * FROM a CROSS JOIN b;

-- SELF JOIN
SELECT a.id, b.id FROM orders a JOIN orders b ON a.customer_id = b.customer_id;

-- USING 语法
SELECT * FROM orders JOIN customers USING (customer_id);

-- NATURAL JOIN
SELECT * FROM orders NATURAL JOIN customers;

-- SEMI JOIN（用 EXISTS 或 IN 实现）
SELECT * FROM orders WHERE EXISTS (
    SELECT 1 FROM customers WHERE customers.id = orders.customer_id
);

-- ANTI JOIN（用 NOT EXISTS 或 NOT IN 实现）
SELECT * FROM orders WHERE NOT EXISTS (
    SELECT 1 FROM customers WHERE customers.id = orders.customer_id
);
```

**与 Snowflake 差异：**
- Snowflake 支持 `ASOF JOIN`（时序连接）；ClickZetta 不支持
- Snowflake 支持 `MATCH_RECOGNIZE`；ClickZetta 不支持

### LATERAL VIEW（展开数组/MAP）

```sql
-- EXPLODE 展开数组
SELECT e.id, s.skill
FROM employees e
LATERAL VIEW EXPLODE(e.skills) s AS skill;

-- POSEXPLODE 带位置索引
SELECT e.id, ps.pos, ps.skill
FROM employees e
LATERAL VIEW POSEXPLODE(e.skills) ps AS pos, skill;

-- OUTER（空数组也保留行）
SELECT e.id, s.skill
FROM employees e
LATERAL VIEW OUTER EXPLODE(e.skills) s AS skill;

-- 展开 MAP
SELECT id, k, v
FROM t
LATERAL VIEW EXPLODE(meta_map) m AS k, v;
```

**与 Snowflake 差异：**
- Snowflake 用 `LATERAL FLATTEN(input => arr)`；ClickZetta 用 `LATERAL VIEW EXPLODE(arr)`
- Snowflake `f.value::STRING`；ClickZetta 直接用列别名

**与 Spark SQL 差异：**
- 语法完全相同（ClickZetta 兼容 Hive/Spark 风格）

### TABLESAMPLE

```sql
-- SYSTEM 模式：按百分比采样（文件级）
SELECT * FROM orders TABLESAMPLE (10 PERCENT);

-- ROW 模式：按行数采样
SELECT * FROM orders TABLESAMPLE (100 ROWS);
```

### SEQUENCE（生成序列）

```sql
-- 生成整数序列（返回 ARRAY）
SELECT SEQUENCE(1, 5);                -- [1,2,3,4,5]
SELECT SEQUENCE(0, 10, 2);            -- [0,2,4,6,8,10]

-- 展开为行（ClickZetta 用 EXPLODE(SEQUENCE(...))，无 GENERATE_SERIES）
SELECT EXPLODE(SEQUENCE(1, 5)) AS n;  -- 5行：1,2,3,4,5
```

### EXPLODE 直接在 SELECT 中使用

```sql
-- Spark 风格：EXPLODE 直接在 SELECT 中
SELECT EXPLODE(ARRAY(1, 2, 3)) AS val;
SELECT POSEXPLODE(ARRAY('a', 'b', 'c')) AS (pos, val);

-- 等价的 LATERAL VIEW 写法
SELECT val FROM (SELECT ARRAY(1,2,3) AS arr) t
LATERAL VIEW EXPLODE(arr) lv AS val;
```



## WHERE 子句

```sql
-- 基本条件
WHERE amount > 100 AND status = 'completed'
WHERE status IN ('pending', 'processing')
WHERE status NOT IN ('cancelled', 'refunded')
WHERE amount BETWEEN 100 AND 1000
WHERE name LIKE '%Alice%'
WHERE name NOT LIKE '%test%'
WHERE tags IS NULL
WHERE tags IS NOT NULL

-- 正则匹配
WHERE name RLIKE '^[A-Z].*'
WHERE name REGEXP '^[A-Z].*'    -- 同 RLIKE

-- 子查询
WHERE customer_id IN (SELECT id FROM customers WHERE tier = 'VIP')
WHERE EXISTS (SELECT 1 FROM orders WHERE orders.customer_id = customers.id)
```

**与 Snowflake 差异：**
- Snowflake `ILIKE`（不区分大小写 LIKE）→ ClickZetta `ILIKE` ✅ 同样支持
- Snowflake `RLIKE` → ClickZetta 同样支持 `RLIKE` / `REGEXP`

---

## GROUP BY 扩展

```sql
-- 基本分组
SELECT region, SUM(amount) FROM orders GROUP BY region;
SELECT region, SUM(amount) FROM orders GROUP BY 1;    -- 按位置

-- GROUP BY ALL（自动推断所有非聚合列）
SELECT year, month, region, SUM(amount) FROM orders GROUP BY ALL;

-- GROUPING SETS（多维分组）
SELECT region, product, SUM(sales)
FROM orders
GROUP BY GROUPING SETS ((region, product), (region), (product), ());

-- ROLLUP（层级汇总）
SELECT region, city, SUM(amount)
FROM orders
GROUP BY ROLLUP (region, city);
-- 等价于 GROUPING SETS ((region, city), (region), ())

-- CUBE（全组合汇总）
SELECT region, product, channel, SUM(amount)
FROM orders
GROUP BY CUBE (region, product, channel);

-- HAVING
SELECT customer_id, SUM(amount) AS total
FROM orders
GROUP BY customer_id
HAVING total > 10000;
```

**与 Snowflake 差异：**
- `GROUP BY ALL` 两者都支持
- `GROUPING SETS / ROLLUP / CUBE` 两者都支持

---

## ORDER BY

```sql
SELECT * FROM orders ORDER BY amount DESC;
SELECT * FROM orders ORDER BY amount DESC NULLS LAST;
SELECT * FROM orders ORDER BY amount ASC NULLS FIRST;
SELECT * FROM orders ORDER BY 1 DESC, 2 ASC;    -- 按位置
```

---

## CTE（公用表表达式）

```sql
-- 基本 CTE
WITH
    monthly AS (
        SELECT DATE_TRUNC('month', created_at) AS month, SUM(amount) AS total
        FROM orders GROUP BY 1
    ),
    ranked AS (
        SELECT *, RANK() OVER (ORDER BY total DESC) AS rnk FROM monthly
    )
SELECT * FROM ranked WHERE rnk <= 5;

-- ⚠️ 递归 CTE（ClickZetta 不支持）
-- Snowflake/Databricks/Spark SQL 支持：
WITH RECURSIVE org_tree AS (
    SELECT id, name, parent_id, 0 AS level
    FROM employees WHERE parent_id IS NULL
    UNION ALL
    SELECT e.id, e.name, e.parent_id, t.level + 1
    FROM employees e JOIN org_tree t ON e.parent_id = t.id
)
SELECT * FROM org_tree ORDER BY level, id;

-- ClickZetta 替代方案：用 Python/ZettaPark 迭代实现
-- 或用多层 CTE 模拟有限深度的递归
WITH
    level0 AS (SELECT id, name, parent_id, 0 AS level FROM employees WHERE parent_id IS NULL),
    level1 AS (SELECT e.id, e.name, e.parent_id, 1 AS level FROM employees e JOIN level0 t ON e.parent_id = t.id),
    level2 AS (SELECT e.id, e.name, e.parent_id, 2 AS level FROM employees e JOIN level1 t ON e.parent_id = t.id)
SELECT * FROM level0 UNION ALL SELECT * FROM level1 UNION ALL SELECT * FROM level2;
```

**与 Snowflake 差异：**
- Snowflake 支持 `WITH RECURSIVE`；ClickZetta ❌ 不支持递归 CTE
- ClickZetta 仅支持非递归 CTE（普通 WITH 子句）
- 递归场景需用 Python/ZettaPark 迭代实现，或用多层 CTE 模拟有限深度

---

## 窗口函数

```sql
-- 基本语法
function_name() OVER (
    [PARTITION BY col1, col2]
    [ORDER BY col3 [ASC|DESC]]
    [ROWS|RANGE BETWEEN start AND end]
)

-- 排名函数
ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC)
RANK() OVER (ORDER BY score DESC)
DENSE_RANK() OVER (ORDER BY score DESC)
NTILE(4) OVER (ORDER BY amount)
PERCENT_RANK() OVER (ORDER BY amount)
CUME_DIST() OVER (ORDER BY amount)

-- 聚合窗口
SUM(amount) OVER (PARTITION BY customer_id)
AVG(amount) OVER (PARTITION BY dept ORDER BY date
                  ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
COUNT(*) OVER (PARTITION BY region)
MAX(amount) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)

-- 分析函数
LAG(amount, 1, 0) OVER (ORDER BY date)          -- 前1行，默认0
LEAD(amount, 1) OVER (ORDER BY date)             -- 后1行
FIRST_VALUE(amount) OVER (ORDER BY date)
LAST_VALUE(amount) OVER (ORDER BY date
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
NTH_VALUE(amount, 3) OVER (ORDER BY date)

-- Window Frame
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW    -- 从头到当前行
ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING            -- 前后3行
RANGE BETWEEN INTERVAL 7 DAY PRECEDING AND CURRENT ROW  -- 7天内
ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING    -- 当前行到末尾
```

**与 Snowflake 差异：**
- ClickZetta 同样支持 `QUALIFY` 直接过滤窗口函数结果：
  ```sql
  -- 两者都支持
  SELECT * FROM orders QUALIFY ROW_NUMBER() OVER (PARTITION BY cust ORDER BY dt DESC) = 1;
  -- 子查询写法也可以
  SELECT * FROM (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY cust ORDER BY dt DESC) AS rn FROM orders
  ) t WHERE rn = 1;
  ```

---

## 子查询

```sql
-- 标量子查询
SELECT id, (SELECT MAX(amount) FROM orders) AS max_amount FROM orders;

-- IN 子查询
SELECT * FROM orders WHERE customer_id IN (SELECT id FROM customers WHERE tier = 'VIP');

-- EXISTS 子查询
SELECT * FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);

-- 相关子查询
SELECT * FROM orders o
WHERE amount > (SELECT AVG(amount) FROM orders WHERE customer_id = o.customer_id);

-- FROM 子查询（派生表）
SELECT t.region, t.total FROM (
    SELECT region, SUM(amount) AS total FROM orders GROUP BY region
) t WHERE t.total > 100000;
```

---

## JSON 查询

```sql
-- 访问 JSON 字段（用 [] 而非 Snowflake 的 :）
SELECT data['address']['city'] AS city FROM users;
SELECT data['phoneNumbers'][0]['number'] AS phone FROM users;
SELECT data['scores'][2] AS third_score FROM users;

-- 构建 JSON
SELECT PARSE_JSON('{"name":"Alice","age":30}') AS info;
SELECT TO_JSON(STRUCT(name, age)) AS json_str FROM users;

-- 类型转换
SELECT CAST(data['age'] AS INT) AS age FROM users;
SELECT data['amount']::DOUBLE AS amount FROM orders;    -- :: 语法也支持

-- JSON 聚合
SELECT customer_id, TO_JSON(COLLECT_LIST(STRUCT(id, amount))) AS orders_json
FROM orders GROUP BY customer_id;
```

**与 Snowflake 差异：**
- Snowflake `data:key` 冒号语法 → ClickZetta `data['key']` 方括号语法
- Snowflake `data:key::STRING` → ClickZetta `CAST(data['key'] AS STRING)` 或 `data['key']::STRING`
- Snowflake `OBJECT_CONSTRUCT(k, v)` → ClickZetta `MAP_AGG(k, v)` 或 `STRUCT(...)` + `TO_JSON`
- Snowflake `PARSE_JSON` → ClickZetta 相同

---

## STRUCT / ARRAY / MAP 操作

```sql
-- 构建 STRUCT
SELECT STRUCT(name, age, email) AS user_info FROM users;              -- ✅ 支持（无字段名，默认 col1, col2...）
SELECT named_struct('name', name, 'age', age, 'email', email) AS user_info FROM users;  -- ✅ 支持（有字段名）
-- ⚠️ SELECT STRUCT(name AS n, age AS a) 不支持 AS 语法（Snowflake/Spark 支持）

-- 构建 ARRAY / MAP
SELECT ARRAY(1, 2, 3) AS nums;
SELECT MAP('k1', 1, 'k2', 2) AS m;

-- 访问
SELECT address.city FROM users;                    -- STRUCT 字段
SELECT skills[0] FROM employees;                   -- ARRAY 索引（0-based）
SELECT meta_map['key'] FROM t;                     -- MAP 访问

-- 数组函数
SELECT SIZE(skills) AS cnt FROM employees;
SELECT ARRAY_CONTAINS(skills, 'Python') FROM employees;
SELECT ARRAY_AGG(order_id) FROM orders GROUP BY customer_id;
SELECT COLLECT_LIST(order_id) FROM orders GROUP BY customer_id;   -- 同 ARRAY_AGG
SELECT COLLECT_SET(status) FROM orders GROUP BY customer_id;      -- 去重
SELECT SORT_ARRAY(skills) FROM employees;
SELECT ARRAY_DISTINCT(tags) FROM articles;
SELECT ARRAY_UNION(a, b) FROM t;
SELECT ARRAY_INTERSECT(a, b) FROM t;
SELECT ARRAY_EXCEPT(a, b) FROM t;
SELECT FLATTEN(nested_array) FROM t;               -- 展平嵌套数组

-- 高阶函数
SELECT TRANSFORM(skills, x -> UPPER(x)) FROM employees;
SELECT FILTER(scores, x -> x > 90) FROM students;
-- ⚠️ AGGREGATE(arr, init, (acc,x)->...) 不支持，用 ARRAY_AGG + SUM 替代
-- ⚠️ REDUCE(arr, init, (acc,x)->...) 不支持（Spark 名称）
SELECT EXISTS(scores, x -> x > 100) FROM students;
SELECT FORALL(scores, x -> x >= 0) FROM students;
SELECT ZIP_WITH(a, b, (x, y) -> x + y) FROM t;

-- MAP 函数
SELECT MAP_KEYS(meta) FROM t;
SELECT MAP_VALUES(meta) FROM t;
SELECT MAP_ENTRIES(meta) FROM t;
SELECT MAP_CONCAT(m1, m2) FROM t;
SELECT MAP_FILTER(meta, (k, v) -> v > 0) FROM t;
SELECT MAP_TRANSFORM_VALUES(meta, (k, v) -> v * 2) FROM t;
```

**与 Snowflake 差异：**
- Snowflake `ARRAY_SIZE` → ClickZetta `SIZE`
- Snowflake `ARRAY_CONTAINS(val, arr)` 参数顺序相反 → ClickZetta `ARRAY_CONTAINS(arr, val)`
- Snowflake `OBJECT_KEYS(obj)` → ClickZetta `MAP_KEYS(map)`
- Snowflake 无高阶函数（TRANSFORM/FILTER）；ClickZetta 支持

---

## PIVOT / UNPIVOT

```sql
-- ClickZetta 不支持原生 PIVOT 语法
-- 用 CASE WHEN 实现行转列
SELECT
    product,
    SUM(CASE WHEN month = 'Jan' THEN amount ELSE 0 END) AS Jan,
    SUM(CASE WHEN month = 'Feb' THEN amount ELSE 0 END) AS Feb,
    SUM(CASE WHEN month = 'Mar' THEN amount ELSE 0 END) AS Mar
FROM sales
GROUP BY product;

-- UNPIVOT 用 LATERAL VIEW + STACK 实现
SELECT id, month, amount
FROM sales
LATERAL VIEW STACK(3,
    'Jan', jan_amount,
    'Feb', feb_amount,
    'Mar', mar_amount
) t AS month, amount;
```

**与 Snowflake 差异：**
- Snowflake 原生支持 `PIVOT` / `UNPIVOT` 语法；ClickZetta 不支持，需手动实现

---

## SET 操作

```sql
-- ⚠️ ClickZetta 不支持 UNION/UNION ALL/INTERSECT/EXCEPT 集合操作
-- Snowflake/Spark SQL 支持：
SELECT id FROM orders_2023
UNION ALL
SELECT id FROM orders_2024;

-- ClickZetta 替代方案：

-- 1. UNION ALL → 用多个查询分别执行，应用层合并结果
-- 或在 Python/ZettaPark 中合并 DataFrame

-- 2. INTERSECT → 用 INNER JOIN + DISTINCT 替代
SELECT DISTINCT a.id 
FROM orders_2023 a
INNER JOIN orders_2024 b ON a.id = b.id;

-- 3. EXCEPT → 用 LEFT JOIN + WHERE NULL 替代
SELECT a.id 
FROM orders_2023 a
LEFT JOIN orders_2024 b ON a.id = b.id
WHERE b.id IS NULL;

-- 4. UNION（去重）→ 用 UNION ALL + DISTINCT 替代
SELECT DISTINCT id FROM (
    SELECT id FROM orders_2023
    UNION ALL
    SELECT id FROM orders_2024
);
```

---

## HINTS（查询提示）

```sql
-- MAPJOIN（强制广播小表）
SELECT /*+ MAPJOIN(small_table) */ *
FROM large_table l JOIN small_table s ON l.id = s.id;

-- 向量索引探索因子
SET cz.vector.index.search.ef = 128;
```
