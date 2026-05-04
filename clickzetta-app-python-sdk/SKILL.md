---
name: clickzetta-app-python-sdk
description: |
  在 Python 应用程序中集成 ClickZetta Lakehouse 的官方 SDK 用法。
  覆盖 clickzetta-connector-python（SQL 查询、参数绑定、批量插入、异步执行）、
  clickzetta-ingestion-python（BulkLoad 批量上传，单线程与分布式模式）、
  clickzetta-ingestion-python-v2（IGS 实时写入，秒级可查，支持主键表 CDC）、
  SQLAlchemy dialect 集成，以及连接参数说明。
  当用户说"Python SDK"、"clickzetta-connector-python"、"clickzetta-ingestion-python"、
  "Python 查询 Lakehouse"、"Python 写入 Lakehouse"、"Python 批量上传"、
  "BulkLoad Python"、"SQLAlchemy Lakehouse"、"Python 连接 Lakehouse"、
  "executemany"、"execute_async"、"参数绑定 Python"、
  "IGS 实时写入"、"实时写入 Python"、"ingestion-python-v2"、
  "主键表写入 Python"、"CDC 写入"、"UPSERT Python"时触发。
---

# ClickZetta Lakehouse — Python SDK

官方提供三个 Python 包：
- **`clickzetta-connector-python`** — SQL 查询接口（PEP-249 规范），支持参数绑定、批量插入、异步执行、SQLAlchemy dialect
- **`clickzetta-ingestion-python`** — 高吞吐批量上传（BulkLoad），数据直传对象存储，不消耗计算资源
- **`clickzetta-ingestion-python-v2`** — IGS 实时写入，秒级可查，支持主键表 CDC（UPSERT/DELETE）

阅读 [references/connector.md](references/connector.md) 了解 SQL 查询接口，[references/bulkload.md](references/bulkload.md) 了解批量上传，[references/realtime.md](references/realtime.md) 了解 IGS 实时写入。

---

## 安装

```bash
# SQL 查询接口
pip install clickzetta-connector-python -U

# 批量上传（按云环境选择）
pip install "clickzetta-ingestion-python[oss]" -U   # 阿里云
pip install "clickzetta-ingestion-python[s3]" -U    # AWS
pip install "clickzetta-ingestion-python[all]" -U   # 全部（安装较慢）

# IGS 实时写入
pip install clickzetta-ingestion-python-v2
```

> 注意：旧版 `clickzetta-connector` 已停止维护，请迁移到 `clickzetta-connector-python`。

---

## 连接参数

```python
from clickzetta import connect

conn = connect(
    username='your_username',
    password='your_password',
    service='api.clickzetta.com',      # region.api.clickzetta.com
    instance='your_instance',
    workspace='your_workspace',
    schema='public',
    vcluster='default'
)
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `username` | ✅ | 用户名 |
| `password` | ✅ | 密码 |
| `service` | ✅ | 连接地址，格式 `region.api.clickzetta.com` |
| `instance` | ✅ | 实例名，在 Studio 工作空间 JDBC 连接串中查看 |
| `workspace` | ✅ | 工作空间名 |
| `vcluster` | ✅ | 虚拟集群名 |
| `schema` | ✅ | 默认 schema |

---

## 快速示例

```python
# 查询
cursor = conn.cursor()
cursor.execute('SELECT * FROM orders LIMIT 10')
results = cursor.fetchall()
cursor.close()
conn.close()

# 参数绑定（防 SQL 注入）
cursor.execute('INSERT INTO test (id, name) VALUES (?, ?)', binding_params=[1, 'test'])

# 批量插入
data = [(1, 'a'), (2, 'b'), (3, 'c')]
cursor.executemany('INSERT INTO test (id, name) VALUES (?, ?)', data)
```

## IGS 实时写入快速示例（ingestion-python-v2）

普通表（APPEND_ONLY）：

```python
from clickzetta.connector.v0.connection import connect
from clickzetta.connector.v0.enums import RealtimeOperation
from clickzetta_ingestion.realtime.realtime_options import RealtimeOptionsBuilder, FlushMode
from clickzetta_ingestion.realtime.arrow_stream import RowOperator

with connect(**CONN_ARGS) as conn:
    stream = conn.get_realtime_stream(
        schema='your_schema',
        table='your_table',
        operate=RealtimeOperation.APPEND_ONLY,
        options=RealtimeOptionsBuilder().with_flush_mode(FlushMode.AUTO_FLUSH_BACKGROUND).build()
    )
    row = stream.create_row(RowOperator.INSERT)
    row.set_value('id', 1)
    row.set_value('name', 'alice')
    stream.apply(row)
    stream.close()
```

主键表 CDC（UPSERT / DELETE）：

```python
# 建表：CREATE TABLE users (id STRING NOT NULL PRIMARY KEY, name STRING, age INT);

with connect(**CONN_ARGS) as conn:
    stream = conn.get_realtime_stream(
        schema='your_schema',
        table='users',
        operate=RealtimeOperation.CDC,           # 主键表必须用 CDC
        options=RealtimeOptionsBuilder().with_flush_mode(FlushMode.AUTO_FLUSH_SYNC).build()
    )
    # UPSERT
    row = stream.create_row(RowOperator.UPSERT)
    row.set_value('id', 'u1')
    row.set_value('name', 'bob')
    row.set_value('age', 25)
    stream.apply(row)
    # DELETE_IGNORE
    row = stream.create_row(RowOperator.DELETE_IGNORE)
    row.set_value('id', 'u1')
    stream.apply(row)
    stream.close()
```

---

## 选择指南

| 场景 | 推荐方案 |
|---|---|
| 查询 / 小批量写入 | `clickzetta-connector-python` |
| 大批量数据导入（GB 级，间隔 ≥ 5 分钟） | `clickzetta-ingestion-python` BulkLoad |
| 高频小批写入（间隔 < 5 分钟，秒级可查） | `clickzetta-ingestion-python-v2` 实时写入 |
| 主键表写入（UPSERT / DELETE） | `clickzetta-ingestion-python-v2` CDC 模式 |
| SQLAlchemy / ORM 集成 | `clickzetta-connector-python`（内置 dialect） |
