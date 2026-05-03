# ZettaPark Session 详细参考

> **定位**：ZettaPark 是 ClickZetta Lakehouse 的 DataFrame API 库，提供类似 PySpark/Snowpark 的编程体验。  
> **Python 版本**: 推荐 **Python 3.12**（最低 3.10，不支持 3.9 及以下）  
> 本文档基于 `clickzetta_quickstart/Zettapark/` 目录下的真实代码整理。

## 目录

1. [安装](#1-安装)
2. [创建 Session](#2-创建-session)
3. [Session 上下文操作](#3-session-上下文操作)
4. [核心导入](#4-核心导入)
5. [DataFrame 构建](#5-dataframe-构建)
6. [DataFrame 转换操作](#6-dataframe-转换操作)
7. [操作方法（触发执行）](#7-操作方法触发执行)
8. [写入数据](#8-写入数据)
9. [关闭 Session](#9-关闭-session)
10. [与 Python SDK 对比](#10-与-python-sdk-对比)
11. [适用场景](#11-适用场景)
12. [常见问题](#12-常见问题)

---

## 1. 安装

```bash
# 推荐：Python 3.12 环境
conda create -n lakehouse python=3.12 -y && conda activate lakehouse
pip install clickzetta-zettapark-python
```

验证安装：

```python
import clickzetta.zettapark as C
print(f"ZettaPark version: {C.__version__}")
```

---

## 2. 创建 Session

### 2.1 直接使用字典

```python
from clickzetta.zettapark.session import Session

config = {
    "service": "your-region.api.clickzetta.com",  # 按实例所在区域填写，参见 SKILL.md 区域地址表
    "username": "my_user",
    "password": "my_password",
    "instance": "my_instance",
    "workspace": "my_workspace",
    "schema": "public",
    "vcluster": "default_ap",
}

session = Session.builder.configs(config).create()
```

### 2.2 从 config.json 加载（推荐）

项目中的标准做法是将连接参数存放在 `config.json` 中（参见 `clickzetta_quickstart/Zettapark/config.json`）：

```json
{
    "username": "your_username",
    "password": "your_password",
    "service": "your-region.api.clickzetta.com",
    "instance": "your_instance_id",
    "workspace": "your_workspace",
    "schema": "public",
    "vcluster": "default_ap",
    "sdk_job_timeout": 10,
    "hints": {
        "sdk.job.timeout": 3,
        "query_tag": "Introduction to Zettapark for Python"
    }
}
```

加载并创建 Session：

```python
import json
from clickzetta.zettapark.session import Session

with open("config.json", "r") as f:
    config = json.load(f)

session = Session.builder.configs(config).create()
```

### 2.3 使用环境变量

```python
import os
from clickzetta.zettapark.session import Session

config = {
    "service": os.environ["CZ_SERVICE"],
    "username": os.environ["CZ_USERNAME"],
    "password": os.environ["CZ_PASSWORD"],
    "instance": os.environ["CZ_INSTANCE"],
    "workspace": os.environ["CZ_WORKSPACE"],
    "schema": os.environ.get("CZ_SCHEMA", "public"),
    "vcluster": os.environ.get("CZ_VCLUSTER", "default_ap"),
}

session = Session.builder.configs(config).create()
```

### 2.4 连接参数说明

| 参数 | 必填 | 说明 | 示例 |
|:--|:--|:--|:--|
| `service` | ✅ | API 端点（含区域前缀） | `cn-shanghai-alicloud.api.clickzetta.com` |
| `username` | ✅ | 登录用户名 | `my_user` |
| `password` | ✅ | 登录密码 | `my_password` |
| `instance` | ✅ | 实例标识 | `my_instance` |
| `workspace` | ✅ | 工作空间 | `gharchive` |
| `schema` | ✅ | 默认 Schema | `public` |
| `vcluster` | ✅ | 虚拟集群 | `default_ap` |
| `sdk_job_timeout` | ❌ | SDK 作业超时（秒） | `10` |
| `hints` | ❌ | 查询提示字典 | `{"sdk.job.timeout": 3}` |

---

## 3. Session 上下文操作

创建 Session 后，可以查询和切换当前上下文：

```python
# 查询当前 Schema
current_schema = session.get_current_schema()
print(f"Current schema: {current_schema}")

# 切换 Schema
session.use_schema("my_other_schema")

# 启用 SQL 简化器（可选）
session.sql_simplifier_enabled = True

# 查看可用虚拟集群
session.sql("SHOW VCLUSTERS").show()

# 查看可用 Schema
session.sql("SHOW SCHEMAS").show()
```

---

## 4. 核心导入

ZettaPark 提供以下常用模块：

```python
import clickzetta.zettapark as C
from clickzetta.zettapark import Session
from clickzetta.zettapark import functions as F
from clickzetta.zettapark import Window
from clickzetta.zettapark import Row
import clickzetta.zettapark.types as T
from clickzetta.zettapark.types import IntegerType, StringType, StructType, StructField
```

---

## 5. DataFrame 构建

ZettaPark 的核心是 DataFrame——一个延迟评估的关系数据集，只在触发操作方法（如 `show()`、`collect()`）时才执行。

### 5.1 从 SQL 查询创建

```python
df = session.sql("SELECT * FROM my_table LIMIT 10")
df.show()
```

### 5.2 从表创建

```python
df = session.table("sample_product_data")
df.show()
```

### 5.3 从本地数据创建

```python
# 单列
df1 = session.create_dataframe([1, 2, 3, 4]).to_df("a")
df1.show()

# 多列（使用 schema 列表）
df2 = session.create_dataframe([[1, 2, 3, 4]], schema=["a", "b", "c", "d"])
df2.show()

# 使用 Row 对象
from clickzetta.zettapark import Row
df3 = session.create_dataframe([Row(a=1, b=2, c=3, d=4)])
df3.show()

# 使用 StructType 指定完整 Schema
from clickzetta.zettapark.types import IntegerType, StringType, StructType, StructField

schema = StructType([
    StructField("a", IntegerType()),
    StructField("b", StringType()),
])
df4 = session.create_dataframe([[1, "click"], [3, "zetta"]], schema)
df4.show()
```

### 5.4 从范围创建

```python
df_range = session.range(1, 10, 2).to_df("a")
df_range.show()
```

---

## 6. DataFrame 转换操作

DataFrame 操作会被翻译成 SQL 在 Lakehouse 中执行，实现分布式计算。例如：

```python
df_filtered = df.filter((F.col("a") + F.col("b")) < 10)
```

会被翻译为：

```sql
SELECT `a`, `b` FROM (...) WHERE ((`a` + `b`) < CAST(10 AS INT))
```

### 6.1 过滤（filter）

```python
from clickzetta.zettapark import functions as F

# 等值过滤
df = session.table("sample_product_data").filter(F.col("id") == 1)
df.show()

# 表达式过滤
df = session.create_dataframe([[1, 3], [2, 10]], schema=["a", "b"])
df_filtered = df.filter((F.col("a") + F.col("b")) < 10)
df_filtered.show()
```

### 6.2 选择列（select）

```python
# 使用 F.col()
df = session.table("sample_product_data").select(
    F.col("id"), F.col("name"), F.col("serial_number")
)

# 使用下标访问
df_info = session.table("sample_product_data")
df1 = df_info.select(df_info["id"], df_info["name"], df_info["serial_number"])

# 使用属性访问
df2 = df_info.select(df_info.id, df_info.name, df_info.serial_number)

# 使用字符串列名
df3 = df_info.select("id", "name", "serial_number")
```

### 6.3 分组聚合（group_by / agg）

```python
df_campaign = session.table("CAMPAIGN_SPEND")

# 单一聚合
df_yearly = df_campaign.group_by(F.year("DATE"), "CHANNEL").sum("TOTAL_COST")
df_yearly.show()

# 多重聚合
df_campaign.group_by(F.year("DATE"), "CHANNEL").agg([
    F.sum("TOTAL_COST").as_("TOTAL_COST"),
    F.avg("TOTAL_COST").as_("AVG_COST"),
]).show()
```

### 6.4 连接（join）

```python
df_lhs = session.create_dataframe([["a", 1], ["b", 2]], schema=["key", "value1"])
df_rhs = session.create_dataframe([["a", 3], ["b", 4]], schema=["key", "value2"])

df_lhs.join(
    df_rhs,
    df_lhs.col("key") == df_rhs.col("key")
).select(
    df_lhs["key"].as_("key"), "value1", "value2"
).show()
```

自连接示例：

```python
import copy
df = session.table("sample_product_data")
df_copy = copy.copy(df)
df_joined = df.join(df_copy, F.col("id") == F.col("parent_id"))
```

---

## 7. 操作方法（触发执行）

DataFrame 是延迟评估的，以下方法会触发实际执行：

| 方法 | 说明 | 示例 |
|:--|:--|:--|
| `show(n)` | 打印前 n 行（默认 10） | `df.show()` |
| `collect()` | 返回所有行的 Row 列表 | `rows = df.collect()` |
| `to_pandas()` | 转为 Pandas DataFrame | `pd_df = df.to_pandas()` |
| `queries` | 查看将要执行的 SQL（不触发执行） | `df.queries` |

### 7.1 查看生成的 SQL

```python
df = session.table("CAMPAIGN_SPEND")
print(df.queries)
# {'queries': ['SELECT  *  FROM CAMPAIGN_SPEND'], 'post_actions': []}
```

### 7.2 转为 Pandas DataFrame

```python
pd_data = df_yearly.to_pandas()

# 配合可视化库使用
import seaborn as sns
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(16, 5))
sns.barplot(data=pd_data, x="year", y="total_cost", hue="channel", ax=ax)
plt.show()
```

---

## 8. 写入数据

### 8.1 保存为表

```python
# 覆盖写入
df.write.save_as_table("my_table", mode="overwrite")

# 追加写入
df.write.save_as_table("my_temp_table", mode="append")
```

> **注意**：ClickZetta 不支持 `table_type="transient"` 参数（该参数来自 Snowflake）。如需临时存储，直接使用普通表，并通过 `data_lifecycle` 属性设置 TTL 或手动清理。

### 8.2 通过 SQL 创建表并插入数据

```python
# 创建表
session.sql("""
    CREATE TABLE IF NOT EXISTS sample_product_data (
        id INT, parent_id INT, category_id INT,
        name STRING, serial_number STRING, key INT, third INT
    )
""").collect()

# 插入数据
session.sql("""
    INSERT INTO sample_product_data VALUES
    (1, 0, 5, 'Product 1', 'prod-1', 1, 10),
    (2, 1, 5, 'Product 1A', 'prod-1-A', 1, 20),
    (3, 1, 5, 'Product 1B', 'prod-1-B', 1, 30)
""").collect()
```

---

## 9. 关闭 Session

```python
session.close()
```

---

## 10. 与 Python SDK 对比

| 特性 | Python SDK (`clickzetta-connector-python`) | ZettaPark Session (`clickzetta-zettapark-python`) |
|:--|:--|:--|
| 返回类型 | Cursor（行级别） | DataFrame |
| API 风格 | DB-API 2.0 (`connect` → `cursor` → `execute`) | DataFrame API (`Session.builder` → `table` / `sql`) |
| 适用场景 | 简单 SQL 查询、脚本自动化 | ETL 管道、数据工程、数据探索 |
| 延迟执行 | 否（立即执行） | 是（调用 `show()` / `collect()` 时执行） |
| Pandas 集成 | `cursor.fetch_pandas_all()` | `df.to_pandas()` |
| 写入数据 | 通过 SQL INSERT | `df.write.save_as_table()` |
| 依赖包 | `clickzetta-connector-python` | `clickzetta-zettapark-python` |

---

## 11. 适用场景

- **数据工程 / ETL 管道**：使用 DataFrame 转换链构建数据处理流水线
- **数据探索**：在 Jupyter Notebook 中交互式分析数据
- **特征工程**：结合 `group_by`、`agg`、`Window` 函数生成特征
- **可视化前处理**：通过 `to_pandas()` 转换后配合 matplotlib / seaborn 绑图
- **批量数据写入**：通过 `save_as_table()` 将处理结果写回 Lakehouse

---

## 12. 常见问题

### Q: ZettaPark 和 PySpark 有什么关系？

ZettaPark 提供了类似 PySpark / Snowpark 的 DataFrame API，但底层执行引擎是 ClickZetta Lakehouse。代码风格高度相似，熟悉 PySpark 的开发者可以快速上手。

### Q: `show()` 和 `collect()` 有什么区别？

- `show()` 打印格式化的表格输出到控制台，默认显示前 10 行
- `collect()` 返回所有行的 `Row` 对象列表，适合程序化处理

### Q: 如何查看 DataFrame 将要执行的 SQL？

使用 `df.queries` 属性查看生成的 SQL，不会触发实际执行。

---

> **交叉引用**：
> - 主指南：[SKILL.md](../SKILL.md)
> - Python SDK 参考：[python-sdk.md](./python-sdk.md)
> - 配置文件管理：[config-file.md](./config-file.md)
