# BITMAP 用户画像参考

> 来源：https://www.yunqi.tech/documents/bitmap-type

BITMAP 是 ClickZetta 中用于高效存储和处理整数集合的数据类型，基于 Roaring Bitmap 压缩算法，特别适合用户画像、人群圈选、UV 统计等数据科学场景。

---

## 核心限制

- 支持 **64 位无符号整数**（0 到 2^64-1）
- **不支持**比较操作（<、>、=）
- **不支持** ORDER BY、GROUP BY、DISTINCT
- **不能**作为 PRIMARY KEY、PARTITION KEY、CLUSTER KEY

---

## 构建用户标签 BITMAP

```sql
-- 方式 1：从行数据聚合构建（最常用）
CREATE TABLE ds_workspace.user_tags AS
SELECT
    tag_name,
    group_bitmap_state(user_id) AS user_bitmap
FROM (
    -- 高消费用户
    SELECT 'high_value' AS tag_name, user_id
    FROM my_schema.orders
    WHERE total_amount_30d > 1000
    UNION ALL
    -- 近30天活跃用户
    SELECT 'active_30d' AS tag_name, user_id
    FROM my_schema.events
    WHERE event_date >= CURRENT_DATE - INTERVAL 30 DAY
    UNION ALL
    -- 已流失用户（90天未活跃）
    SELECT 'churned' AS tag_name, user_id
    FROM my_schema.users
    WHERE last_active_date < CURRENT_DATE - INTERVAL 90 DAY
) t
GROUP BY tag_name;

-- 方式 2：从数组构建
INSERT INTO ds_workspace.user_tags VALUES
    ('vip', bitmap_build(ARRAY(1001, 1002, 1003, 1004)));
```

---

## 人群圈选操作

```sql
-- 交集：同时满足多个标签（AND）
SELECT bitmap_count(
    bitmap_and(
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = 'high_value'),
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = 'active_30d')
    )
) AS target_count;

-- 并集：满足任一标签（OR）
SELECT bitmap_count(
    bitmap_or(
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = 'high_value'),
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = 'active_30d')
    )
) AS reach_count;

-- 差集：排除某类用户（ANDNOT）
SELECT bitmap_count(
    bitmap_andnot(
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = 'high_value'),
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = 'churned')
    )
) AS targetable_count;

-- 获取目标用户 ID 列表
SELECT bitmap_to_array(
    bitmap_andnot(
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = 'high_value'),
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = 'churned')
    )
) AS target_user_ids;
```

---

## UV 统计（去重计数）

```sql
-- 日活跃用户数（DAU）
SELECT
    event_date,
    bitmap_count(group_bitmap_state(user_id)) AS dau
FROM my_schema.events
GROUP BY event_date
ORDER BY event_date;

-- 周活跃用户数（WAU）—— 跨天去重
SELECT
    DATE_TRUNC('week', event_date) AS week_start,
    bitmap_count(
        bitmap_or_agg(daily_bitmap)  -- 合并多天 bitmap
    ) AS wau
FROM (
    SELECT event_date,
           group_bitmap_state(user_id) AS daily_bitmap
    FROM my_schema.events
    GROUP BY event_date
) t
GROUP BY 1;

-- 用户留存分析（新用户 vs 回访用户）
SELECT
    bitmap_count(
        bitmap_and(new_users.user_bitmap, return_users.user_bitmap)
    ) AS retained_users,
    bitmap_count(
        bitmap_andnot(new_users.user_bitmap, return_users.user_bitmap)
    ) AS lost_users
FROM
    (SELECT group_bitmap_state(user_id) AS user_bitmap
     FROM my_schema.events WHERE event_date = '2024-01-01') AS new_users,
    (SELECT group_bitmap_state(user_id) AS user_bitmap
     FROM my_schema.events WHERE event_date = '2024-01-08') AS return_users;
```

---

## 常用 BITMAP 函数速查

| 函数 | 说明 | 示例 |
|---|---|---|
| `group_bitmap_state(col)` | 聚合构建 BITMAP | `GROUP BY tag` |
| `bitmap_count(bm)` | 计算元素个数（UV） | `bitmap_count(user_bm)` |
| `bitmap_and(a, b)` | 交集 | 同时满足 A 和 B |
| `bitmap_or(a, b)` | 并集 | 满足 A 或 B |
| `bitmap_andnot(a, b)` | 差集 | 在 A 中但不在 B 中 |
| `bitmap_xor(a, b)` | 异或（只在一个中） | A、B 各自独有的 |
| `bitmap_to_array(bm)` | 转为整数数组 | 获取用户 ID 列表 |
| `bitmap_build(arr)` | 从数组构建 | `bitmap_build(ARRAY(1,2,3))` |
| `bitmap_contains(bm, val)` | 检查是否包含某值 | `bitmap_contains(bm, user_id)` |
| `bitmap_min(bm)` | 最小元素 | — |
| `bitmap_max(bm)` | 最大元素 | — |
| `to_bitmap(val)` | 单值转 BITMAP | `to_bitmap(user_id)` |
