# 数据写入、特征工程、模型推理示例

## 数据写入

| 场景 | 方式 |
|------|------|
| ZettaPark 可用（Python 3.10+） | `save_as_table()` 或 `create_dataframe().write` |
| 本地 CSV/pandas 写入 | `session.create_dataframe(df).write.save_as_table()` |
| Python 3.9 / ZettaPark 不可用 | cursor 批量 INSERT（见下方） |
| **禁止** | `df.to_sql()`、SQLAlchemy `clickzetta://...` |

```python
# 方式 A：ZettaPark（推荐）
session.sql("""
    SELECT o.*, u.age_group FROM my_schema.orders_raw o
    LEFT JOIN my_schema.users u ON o.user_id = u.user_id
    WHERE o.amount > 0
""").write.mode("overwrite").save_as_table("ds_workspace.orders_clean")

# 方式 B：pandas → Lakehouse
session.create_dataframe(local_df).write.mode("append").save_as_table("ds_workspace.features_v1")

# 方式 C：cursor 批量 INSERT（fallback）
import clickzetta, os
conn = clickzetta.connect(
    service=os.environ["CLICKZETTA_SERVICE"], instance=os.environ["CLICKZETTA_INSTANCE"],
    workspace=os.environ["CLICKZETTA_WORKSPACE"], username=os.environ["CLICKZETTA_USERNAME"],
    password=os.environ["CLICKZETTA_PASSWORD"],
    vcluster=os.environ.get("CLICKZETTA_VCLUSTER", "default_ap"),
    schema=os.environ.get("CLICKZETTA_SCHEMA", "public"),
)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS ds_workspace.my_table (col1 STRING, col2 BIGINT, col3 DOUBLE)")
rows = local_df.values.tolist()
for i in range(0, len(rows), 500):
    batch = rows[i:i+500]
    vals = ",".join(f"({','.join(repr(v) for v in row)})" for row in batch)
    cursor.execute(f"INSERT INTO ds_workspace.my_table VALUES {vals}")
conn.close()
```

```sql
-- 设置中间表生命周期（30 天自动清理）
ALTER TABLE ds_workspace.orders_clean SET PROPERTIES ('data_lifecycle' = '30');
```

---

## 特征工程

```sql
-- SQL 侧（利用 Lakehouse 算力，推荐）
SELECT
    user_id,
    COUNT(*)                                                    AS order_cnt_30d,
    SUM(amount)                                                 AS total_amount_30d,
    AVG(amount)                                                 AS avg_amount_30d,
    STDDEV(amount)                                              AS std_amount_30d,
    DATEDIFF('day', MIN(order_date), MAX(order_date))           AS active_days,
    COUNT(DISTINCT DATE(order_date))                            AS active_day_cnt,
    NTILE(10) OVER (ORDER BY SUM(amount) DESC)                  AS revenue_decile
FROM my_schema.orders
WHERE order_date >= CURRENT_DATE - INTERVAL 30 DAY
GROUP BY user_id;
```

```python
# ZettaPark 侧（Python 逻辑）
from clickzetta.zettapark.functions import col, when

features = session.table("ds_workspace.orders_clean") \
    .with_column("is_high_value", when(col("amount") > 1000, 1).otherwise(0))

df = features.to_pandas()

from sklearn.preprocessing import StandardScaler
df[['amount_scaled']] = StandardScaler().fit_transform(df[['amount']])

session.create_dataframe(df).write.mode("overwrite").save_as_table("ds_workspace.features_final")
```

---

## 模型推理上线

### BITMAP 用户画像

```sql
CREATE TABLE ds_workspace.user_tags AS
SELECT tag_name, group_bitmap_state(user_id) AS user_bitmap
FROM my_schema.user_behavior GROUP BY tag_name;

-- 人群交集
SELECT bitmap_count(bitmap_and(
    (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = '高消费'),
    (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = '近30天活跃')
)) AS target_user_count;
```

### SQL UDF 批量推理

```sql
-- 调用已部署的模型 UDF（必须用完整 schema 路径）
INSERT INTO ds_workspace.predictions
SELECT user_id,
       ds_workspace.credit_score_model(total_amount_30d, order_cnt_30d, active_days, avg_amount_30d) AS score,
       CURRENT_TIMESTAMP() AS predict_time
FROM ds_workspace.features_final;
```

### 向量检索

```sql
SELECT candidate_id,
       cosine_distance(
           (SELECT embedding FROM ds_workspace.user_embeddings WHERE user_id = 'target'),
           embedding
       ) AS similarity
FROM ds_workspace.user_embeddings
WHERE user_id != 'target'
ORDER BY similarity LIMIT 10;
```
