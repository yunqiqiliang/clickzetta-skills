---
name: clickzetta-zettapark
description: |
  使用 ZettaPark Python 库操作 ClickZetta Lakehouse 数据。ZettaPark 提供类 pandas 的
  DataFrame API，将 Python 操作翻译为 SQL 在 Lakehouse 中分布式执行。
  覆盖 Session 创建、DataFrame 构建与转换（filter/select/join/groupBy）、
  结果收集（collect/to_pandas/show）、写入表（save_as_table）、
  文件操作（PUT/GET）、执行 SQL 等完整工作流。
  当用户说"ZettaPark"、"zettapark"、"DataFrame API"、"Python 操作 Lakehouse"、
  "save_as_table"、"session.table"、"session.sql"、"collect()"、"to_pandas"、
  "Python 数据工程"、"Python 写入 Lakehouse"、"Python 读取 Lakehouse"、
  "clickzetta_zettapark_python"时触发。
---

# ClickZetta ZettaPark

ZettaPark 是 ClickZetta Lakehouse 的 Python DataFrame 框架，将 Python 操作翻译为 SQL 在 Lakehouse 中分布式执行，提供类 pandas 的开发体验。

阅读 [references/zettapark-api.md](references/zettapark-api.md) 了解完整 API。

## 安装

> ⚠️ **Python 版本要求**：推荐 **Python 3.12**（最低 3.10，不支持 3.9 及以下）

```bash
# 方式 1：venv（Python 内置，推荐）
python3.12 -m venv .venv
source .venv/bin/activate   # macOS/Linux  |  .venv\Scripts\activate (Windows)
pip install clickzetta_zettapark_python -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方式 2：pyenv（需要切换 Python 版本时）
pyenv install 3.12.9 && pyenv local 3.12.9
python -m venv .venv && source .venv/bin/activate
pip install clickzetta_zettapark_python -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方式 3：conda（数据科学环境）
conda create -n lakehouse python=3.12 -y && conda activate lakehouse
pip install clickzetta_zettapark_python -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 创建会话

```python
from clickzetta.zettapark.session import Session

connection_parameters = {
    "username": "your_username",
    "password": "your_password",
    "service": "cn-shanghai-alicloud.api.clickzetta.com",
    "instance": "your_instance_id",
    "workspace": "your_workspace",
    "schema": "public",
    "vcluster": "default_ap",
}

session = Session.builder.configs(connection_parameters).create()

# 验证连接
session.sql("SELECT current_user(), current_workspace()").show()
```

---

## 核心工作流

### 读取数据

```python
from clickzetta.zettapark import functions as F

# 从表读取
df = session.table("orders")
df = session.table("my_schema.orders")

# 从 SQL 读取
df = session.sql("SELECT * FROM orders WHERE year = 2024")

# 从 Python 数据创建
df = session.create_dataframe([[1, "Alice", 100.0], [2, "Bob", 200.0]],
                               schema=["id", "name", "amount"])
```

### 转换数据

```python
# 过滤、选择、新增列
result = (
    session.table("orders")
    .filter(F.col("status") == "completed")
    .select("order_id", "customer_id", "amount")
    .with_column("tax", F.col("amount") * 0.1)
    .sort(F.col("amount").desc())
    .limit(100)
)
```

### 聚合

```python
summary = (
    session.table("orders")
    .group_by("category")
    .agg(
        F.sum("amount").as_("total"),
        F.count("*").as_("cnt"),
        F.avg("amount").as_("avg_amount"),
    )
)
summary.show()
```

### JOIN

```python
orders = session.table("orders")
customers = session.table("customers")

result = orders.join(
    customers,
    orders["customer_id"] == customers["id"],
    "left"
).select(
    orders["order_id"],
    customers["name"],
    orders["amount"]
)
```

### 写入数据

```python
# 追加到已有表
df.write.save_as_table("result_table", mode="append")

# 覆盖写入（自动建表）
df.write.save_as_table("result_table", mode="overwrite")
```

### 获取结果

```python
# 打印预览
df.show(20)

# 收集为 Row 列表
rows = df.collect()
for row in rows:
    print(row["id"], row["name"])

# 转为 Pandas DataFrame（小数据量）
pandas_df = df.to_pandas()

# 获取行数
print(df.count())
```

---

## 典型场景

### 场景 1：ETL 数据处理

```python
from clickzetta.zettapark.session import Session
from clickzetta.zettapark import functions as F

session = Session.builder.configs(config).create()

# 读取原始数据
raw = session.table("bronze.raw_orders")

# 清洗转换
cleaned = (
    raw
    .filter(F.isnotnull(F.col("order_id")))
    .filter(F.col("amount") > 0)
    .with_column("order_date", F.col("created_at").cast("DATE"))
    .with_column("year_month", F.date_format(F.col("order_date"), "yyyy-MM"))
    .select("order_id", "customer_id", "amount", "order_date", "year_month")
)

# 写入 Silver 层
cleaned.write.save_as_table("silver.orders_cleaned", mode="overwrite")

session.close()
```

### 场景 2：特征工程（机器学习）

```python
from clickzetta.zettapark import functions as F

customer = session.table("clickzetta_sample_data.tpch_100g.customer")
orders = session.table("clickzetta_sample_data.tpch_100g.orders")

# 构建客户消费特征
customer_features = (
    orders
    .group_by("o_custkey")
    .agg(
        F.sum("o_totalprice").as_("total_spend"),
        F.count("*").as_("order_count"),
        F.avg("o_totalprice").as_("avg_order_value"),
        F.max("o_orderdate").as_("last_order_date"),
    )
    .join(customer, orders["o_custkey"] == customer["c_custkey"])
    .select("c_custkey", "c_name", "total_spend", "order_count", "avg_order_value")
)

customer_features.write.save_as_table("ml_features.customer_features", mode="overwrite")
```

### 场景 3：从本地文件导入

```python
import json
import gzip
from clickzetta.zettapark.session import Session

session = Session.builder.configs(config).create()

# 读取本地 JSON 数据
data = []
with gzip.open('data.json.gz', 'rt', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            data.append(json.loads(line))

# 创建 DataFrame 并写入
df = session.create_dataframe(data)
df.write.save_as_table("my_table", mode="overwrite")

session.close()
```

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| `collect()` 超时 | 数据量过大或集群规格不足 | 增大 `sdk.job.timeout`，或先 `limit()` 测试 |
| `to_pandas()` 内存溢出 | 结果集过大 | 先聚合/过滤再转 pandas，或分批处理 |
| 列名冲突（JOIN 后） | 两表有同名列 | 用 `df_left["col"]` 明确指定来源 |
| `save_as_table` 报错 | 表已存在且 mode 不对 | 使用 `mode="overwrite"` 或 `mode="append"` |
