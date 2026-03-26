# ZettaPark 快速参考

> 来源：https://www.yunqi.tech/documents/ZettaparkQuickStart

## 安装

```bash
pip install clickzetta_zettapark_python -U -i https://pypi.tuna.tsinghua.edu.cn/simple
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
```

带 hints（超时、query_tag 等）：

```python
connection_parameters = {
    "username": "your_username",
    "password": "your_password",
    "service": "cn-shanghai-alicloud.api.clickzetta.com",
    "instance": "your_instance_id",
    "workspace": "your_workspace",
    "schema": "public",
    "vcluster": "default_ap",
    "hints": {
        "sdk.job.timeout": 300,
        "query_tag": "my_zettapark_app",
    }
}

session = Session.builder.configs(connection_parameters).create()
```

从 JSON 配置文件读取：

```python
import json
with open('config.json', 'r') as f:
    config = json.load(f)
session = Session.builder.configs(config).create()
```

验证连接：

```python
session.sql("SELECT current_user(), current_workspace(), current_vcluster()").show()
```

关闭会话：

```python
session.close()
```

---

## 构建 DataFrame

```python
# 从表创建
df = session.table("my_schema.my_table")

# 从 SQL 创建
df = session.sql("SELECT * FROM orders WHERE year = 2024")

# 从 Python 数据创建
df = session.create_dataframe([1, 2, 3, 4]).to_df("id")
df = session.create_dataframe([[1, "Alice"], [2, "Bob"]], schema=["id", "name"])

# 从 Row 对象创建
from clickzetta.zettapark import Row
df = session.create_dataframe([Row(id=1, name="Alice"), Row(id=2, name="Bob")])

# 带 Schema 创建
from clickzetta.zettapark.types import IntegerType, StringType, StructType, StructField
schema = StructType([StructField("id", IntegerType()), StructField("name", StringType())])
df = session.create_dataframe([[1, "Alice"], [2, "Bob"]], schema)

# 范围序列
df = session.range(1, 10, 2).to_df("n")  # 1,3,5,7,9
```

---

## DataFrame 转换操作

```python
from clickzetta.zettapark import functions as F

# 过滤行
df.filter(F.col("age") > 18)
df.filter(F.col("status") == "active")
df.where(F.col("amount") > 1000)

# 选择列
df.select("id", "name", "amount")
df.select(F.col("id"), F.col("name").as_("user_name"))

# 新增/修改列
df.with_column("total", F.col("price") * F.col("qty"))
df.with_column("upper_name", F.upper(F.col("name")))

# 重命名列
df.rename(F.col("old_name"), "new_name")

# 排序
df.sort(F.col("amount").desc())
df.order_by(F.col("created_at").asc())

# 去重
df.distinct()
df.drop_duplicates(["user_id"])

# 限制行数
df.limit(100)

# 删除列
df.drop("unnecessary_col")
```

---

## 聚合操作

```python
from clickzetta.zettapark import functions as F

# 分组聚合
df.group_by("category").agg(
    F.sum("amount").as_("total_amount"),
    F.count("*").as_("order_count"),
    F.avg("price").as_("avg_price"),
    F.max("amount").as_("max_amount"),
    F.min("amount").as_("min_amount"),
)

# 全局聚合
df.agg(F.count("*"), F.sum("amount"))
```

---

## JOIN 操作

```python
# 内连接
df_orders.join(df_customers, df_orders["customer_id"] == df_customers["id"])

# 左连接
df_orders.join(df_customers, df_orders["customer_id"] == df_customers["id"], "left")

# 选择连接后的列（避免列名冲突）
result = df_orders.join(df_customers, df_orders["customer_id"] == df_customers["id"]) \
    .select(df_orders["order_id"], df_customers["name"], df_orders["amount"])
```

---

## 执行与结果获取

```python
# 打印前 N 行（触发执行）
df.show()
df.show(20)

# 收集所有结果为 Row 列表
rows = df.collect()
for row in rows:
    print(row["id"], row["name"])

# 转换为 Pandas DataFrame
pandas_df = df.to_pandas()

# 获取行数
count = df.count()

# 获取列名
print(df.columns)

# 查看 Schema
df.schema.print_tree()
```

---

## 写入数据

```python
# 写入已有表（追加）
df.write.save_as_table("my_table", mode="append")

# 覆盖写入
df.write.save_as_table("my_table", mode="overwrite")

# 自动建表并写入（overwrite 会重建表）
df.write.save_as_table("new_table", mode="overwrite", table_type="transient")

# 写入指定 Schema 下的表
df.write.save_as_table("my_schema.my_table", mode="append")
```

---

## 执行 SQL

```python
# 执行 DDL/DML
session.sql("CREATE TABLE IF NOT EXISTS t (id INT, name STRING)").collect()
session.sql("INSERT INTO t VALUES (1, 'Alice')").collect()

# 执行查询并获取 DataFrame
df = session.sql("SELECT * FROM orders WHERE amount > 1000")
df.show()

# 切换 Schema
session.use_schema("my_schema")
```

---

## 文件操作（Volume）

```python
# 上传文件到 User Volume
session.file.put("/local/path/data.csv", "volume:user://~/data/")

# 下载文件
session.file.get("volume:user://~/data/data.csv", "/local/output/")

# 列出 User Volume 文件
session.sql("LIST USER VOLUME").show()
session.sql("SHOW USER VOLUME DIRECTORY").show()
```

---

## 常用 functions 速查

```python
from clickzetta.zettapark import functions as F

# 字符串
F.upper(col), F.lower(col), F.concat(col1, col2)
F.substring(col, 1, 3), F.trim(col), F.length(col)

# 数值
F.abs(col), F.round(col, 2), F.floor(col), F.ceil(col)
F.sqrt(col), F.pow(col, 2)

# 日期时间
F.current_date(), F.current_timestamp()
F.year(col), F.month(col), F.day(col)
F.date_add(col, 7), F.datediff(col1, col2)

# 条件
F.when(F.col("status") == "A", "Active").otherwise("Inactive")
F.coalesce(col1, col2)  # 第一个非 null 值
F.isnull(col), F.isnotnull(col)

# 聚合
F.count("*"), F.sum(col), F.avg(col), F.max(col), F.min(col)
F.count_distinct(col)

# 类型转换
F.col("amount").cast(IntegerType())
```
