# 数据科学统计分析函数参考

---

## 近似聚合函数（大表高效统计）

### approx_count_distinct — 近似 UV

```sql
-- 使用 HyperLogLog 算法，误差约 2%，比 COUNT(DISTINCT) 快 10x+
SELECT approx_count_distinct(user_id) AS approx_uv
FROM my_schema.events;

-- 按天统计 DAU
SELECT
    DATE(event_time) AS dt,
    approx_count_distinct(user_id) AS dau
FROM my_schema.events
GROUP BY 1
ORDER BY 1;
```

### approx_percentile — 近似分位数

```sql
-- 中位数、四分位数、P95、P99
SELECT
    approx_percentile(amount, 0.25) AS p25,
    approx_percentile(amount, 0.50) AS median,
    approx_percentile(amount, 0.75) AS p75,
    approx_percentile(amount, 0.95) AS p95,
    approx_percentile(amount, 0.99) AS p99
FROM my_schema.orders;

-- 分组分位数
SELECT
    category,
    approx_percentile(price, 0.5) AS median_price
FROM my_schema.products
GROUP BY category;
```

### approx_histogram — 近似直方图

```sql
-- 返回结构体数组：[{min, max, count}, ...]
SELECT approx_histogram(amount, 10) AS hist
FROM my_schema.orders;

-- 解析直方图（展开为行）
SELECT
    bucket.min AS bucket_min,
    bucket.max AS bucket_max,
    bucket.count AS bucket_count
FROM (
    SELECT EXPLODE(approx_histogram(amount, 10)) AS bucket
    FROM my_schema.orders
);
```

### approx_top_k — 近似 TOP-K 高频值

```sql
-- 找出出现最多的前 10 个城市
SELECT approx_top_k(city, 10) AS top_cities
FROM my_schema.orders;

-- 返回结构体数组：[{value, count}, ...]
-- 解析展开（字段名是 value 和 count）
SELECT item.value AS city, item.count AS cnt
FROM (
    SELECT EXPLODE(approx_top_k(city, 10)) AS item
    FROM my_schema.orders
)
ORDER BY cnt DESC;
```

---

## 精确统计函数

### percentile / median

```sql
-- 精确中位数（小表用，大表用 approx_percentile）
SELECT
    percentile(amount, 0.5)  AS exact_median,
    median(amount)           AS median_alias  -- 等价写法
FROM my_schema.orders;

-- 多分位数
SELECT percentile(amount, ARRAY(0.25, 0.5, 0.75, 0.9, 0.99))
FROM my_schema.orders;
```

---

## TABLESAMPLE 采样

```sql
-- ROW 模式：精确行级采样（适合 ML 训练集，< 1000万行）
SELECT * FROM my_schema.events TABLESAMPLE ROW (10);      -- 精确 10%
SELECT * FROM my_schema.events TABLESAMPLE ROW (5 ROWS);  -- 精确 5 行

-- SYSTEM 模式：文件级采样（适合大表快速预览，> 1000万行）
SELECT * FROM my_schema.events TABLESAMPLE SYSTEM (0.1) LIMIT 50000;  -- 约 0.1%

-- 分层采样（按类别等比例采样）
SELECT * FROM (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY RAND()) AS rn,
           COUNT(*) OVER (PARTITION BY category) AS cat_total
    FROM my_schema.products
)
WHERE rn <= CEIL(cat_total * 0.1);  -- 每类取 10%
```

| 场景 | 推荐模式 | 说明 |
|---|---|---|
| 快速数据预览 | SYSTEM | 极快，适合 > 100万行 |
| ML 训练集构建 | ROW | 精确随机，保证代表性 |
| 数据质量抽检 | SYSTEM | 快速抽样验证 |
| 统计分析 | ROW | 精确概率采样 |

> ⚠️ **注意**：TABLESAMPLE 在小表（< 数万行）上可能返回全部数据，百分比采样不精确。小表直接用 `LIMIT` 即可。

---

## 窗口函数（时序/排名特征）

```sql
-- 移动平均（7日）
SELECT
    dt,
    revenue,
    AVG(revenue) OVER (
        ORDER BY dt
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS revenue_7d_ma
FROM daily_stats;

-- 环比增长率
SELECT
    dt,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY dt)  AS prev_revenue,
    ROUND(100.0 * (revenue - LAG(revenue, 1) OVER (ORDER BY dt))
          / NULLIF(LAG(revenue, 1) OVER (ORDER BY dt), 0), 2) AS mom_growth_pct
FROM daily_stats;

-- 用户行为排名（RFM 分析）
SELECT
    user_id,
    total_amount,
    NTILE(5) OVER (ORDER BY total_amount DESC)  AS monetary_quintile,
    NTILE(5) OVER (ORDER BY order_cnt DESC)     AS frequency_quintile,
    NTILE(5) OVER (ORDER BY last_order_date DESC) AS recency_quintile
FROM user_rfm;

-- 去重保留最新（数据清洗常用）
SELECT * FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY user_id
               ORDER BY update_time DESC
           ) AS rn
    FROM my_schema.users_raw
) WHERE rn = 1;
```

---

## 数据质量检查模板

```sql
-- 一次性输出所有关键质量指标
SELECT
    COUNT(*)                                                    AS total_rows,
    COUNT(DISTINCT user_id)                                     AS unique_users,
    -- 缺失率
    ROUND(100.0 * COUNT(*) FILTER (WHERE user_id IS NULL)
          / COUNT(*), 2)                                        AS user_id_null_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE amount IS NULL)
          / COUNT(*), 2)                                        AS amount_null_pct,
    -- 异常值
    SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END)                AS negative_amount_cnt,
    SUM(CASE WHEN amount > 1000000 THEN 1 ELSE 0 END)          AS extreme_amount_cnt,
    -- 时间范围
    MIN(order_date)                                             AS earliest_date,
    MAX(order_date)                                             AS latest_date,
    -- 分布
    approx_percentile(amount, 0.5)                             AS median_amount,
    approx_percentile(amount, 0.99)                            AS p99_amount
FROM my_schema.orders;
```
