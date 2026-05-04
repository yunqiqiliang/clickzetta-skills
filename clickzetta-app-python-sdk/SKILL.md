---
name: clickzetta-app-python-sdk
description: |
  在 Python 应用程序中集成 ClickZetta Lakehouse 的官方 SDK 用法。
  覆盖 clickzetta-connector-python（SQL 查询、参数绑定、批量插入、异步执行）、
  clickzetta-ingestion-python（BulkLoad 批量上传，单线程与分布式模式）、
  SQLAlchemy dialect 集成，以及连接参数说明。
  当用户说"Python SDK"、"clickzetta-connector-python"、"clickzetta-ingestion-python"、
  "Python 查询 Lakehouse"、"Python 写入 Lakehouse"、"Python 批量上传"、
  "BulkLoad Python"、"SQLAlchemy Lakehouse"、"Python 连接 Lakehouse"、
  "executemany"、"execute_async"、"参数绑定 Python"时触发。
---

# ClickZetta Lakehouse — Python SDK

官方提供两个 Python 包：
- **`clickzetta-connector-python`** — SQL 查询接口（PEP-249 规范），支持参数绑定、批量插入、异步执行、SQLAlchemy dialect
- **`clickzetta-ingestion-python`** — 高吞吐批量上传（BulkLoad），数据直传对象存储，不消耗计算资源

阅读 [references/connector.md](references/connector.md) 了解 SQL 查询接口，[references/bulkload.md](references/bulkload.md) 了解批量上传。

---

## 安装

```bash
# SQL 查询接口
pip install clickzetta-connector-python -U

# 批量上传（按云环境选择）
pip install "clickzetta-ingestion-python[oss]" -U   # 阿里云
pip install "clickzetta-ingestion-python[s3]" -U    # AWS
pip install "clickzetta-ingestion-python[all]" -U   # 全部（安装较慢）
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

---

## 选择指南

| 场景 | 推荐方案 |
|---|---|
| 查询 / 小批量写入 | `clickzetta-connector-python` |
| 大批量数据导入（GB 级） | `clickzetta-ingestion-python` BulkLoad |
| SQLAlchemy / ORM 集成 | `clickzetta-connector-python`（内置 dialect） |
| 主键表写入 | JDBC + MERGE（两者均不支持直接写入主键表） |
