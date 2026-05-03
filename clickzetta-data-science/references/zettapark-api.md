# ZettaPark API 数据科学常用操作

> 来源：https://www.yunqi.tech/documents/ZettaparkQuickStart
> **Python 版本**：推荐 3.12（最低 3.10）。安装：`python3.12 -m venv .venv && pip install clickzetta_zettapark_python`

---

## Session 创建

```python
from clickzetta.zettapark.session import Session
import os
from dotenv import load_dotenv

load_dotenv()

session = Session.builder.configs({
    "service":   os.environ["CLICKZETTA_SERVICE"],
    "instance":  os.environ["CLICKZETTA_INSTANCE"],
    "workspace": os.environ["CLICKZETTA_WORKSPACE"],
    "username":  os.environ["CLICKZETTA_USERNAME"],
    "password":  os.environ["CLICKZETTA_PASSWORD"],
    "vcluster":  os.environ["CLICKZETTA_VCLUSTER"],
    "schema":    os.environ.get("CLICKZETTA_SCHEMA", "public"),
    "hints": {
        "sdk.job.timeout": 300,
        "query_tag": "ds_notebook"
    }
}).create()
```

---

## 数据读取

```python
# 读取整张表
df = session.table("my_schema.orders")

# 执行 SQL 查询
df = session.sql("SELECT * FROM my_schema.orders WHERE amount > 100")

# 转为 pandas（小数据集）
pandas_df = df.to_pandas()

# 分批读取大表（避免 OOM）
pandas_df = session.sql("""
    SELECT * FROM my_schema.events
    TABLESAMPLE ROW (1)   -- 1% 精确采样
""").to_pandas()

# 只获取前 N 行
pandas_df = df.limit(10000).to_pandas()
```

---

## DataFrame 变换

```python
from clickzetta.zettapark.functions import col, when, lit, sum as F_sum, count as F_count, avg as F_avg

# 过滤
df_filtered = df.filter(col("amount") > 0)
df_filtered = df.filter((col("status") == "COMPLETED") & (col("amount") > 100))

# 选择列
df_selected = df.select("user_id", "amount", "order_date")

# 新增列
df = df.with_column("log_amount", col("amount").cast("double"))
df = df.with_column("is_high_value", when(col("amount") > 1000, 1).otherwise(0))

# 聚合
agg_df = df.group_by("user_id").agg(
    F_sum("amount").alias("total_amount"),
    F_count("order_id").alias("order_cnt"),
    F_avg("amount").alias("avg_amount")
)

# JOIN
result = orders.join(users, orders["user_id"] == users["user_id"], "left")

# 排序
df_sorted = df.sort(col("amount").desc())
```

---

## 数据写回

```python
# 覆盖写入（常用于特征表更新）
df.write.mode("overwrite").save_as_table("ds_workspace.features_v1")

# 追加写入（常用于预测结果）
df.write.mode("append").save_as_table("ds_workspace.predictions")

# pandas DataFrame 写回
import pandas as pd
local_df = pd.DataFrame({"user_id": [1, 2], "score": [0.8, 0.6]})
session.create_dataframe(local_df).write.mode("overwrite") \
    .save_as_table("ds_workspace.model_scores")
```

---

## 与 pandas/scikit-learn 集成

```python
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier

# 1. 从 Lakehouse 拉特征
features_df = session.sql("""
    SELECT user_id, total_amount_30d, order_cnt_30d,
           active_days, avg_amount_30d, label
    FROM ds_workspace.features_final
""").to_pandas()

# 2. 本地处理
X = features_df.drop(["user_id", "label"], axis=1)
y = features_df["label"]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2)

# 3. 训练模型
model = GradientBoostingClassifier(n_estimators=100)
model.fit(X_train, y_train)

# 4. 预测并写回
features_df["predicted_score"] = model.predict_proba(X_scaled)[:, 1]
session.create_dataframe(
    features_df[["user_id", "predicted_score"]]
).write.mode("overwrite").save_as_table("ds_workspace.predictions")

# 5. 保存模型
import joblib
joblib.dump(model, "models/gbm_model.pkl")
joblib.dump(scaler, "models/scaler.pkl")
```

---

## 注意事项

- `to_pandas()` 会把数据全部拉到本地内存，大表必须先 `TABLESAMPLE` 或 `LIMIT`
- `collect()` 返回 Row 对象列表，`to_pandas()` 返回 DataFrame，数据科学场景用后者
- ZettaPark 的 DataFrame 操作是懒执行，只有 `to_pandas()`/`collect()`/`show()`/`save_as_table()` 才真正触发计算
- 写回时推荐用 `ds_workspace` 这样的专属 Schema，与生产数据隔离
