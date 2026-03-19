# SQLAlchemy 连接器详细参考

> **包名**: `clickzetta-sqlalchemy`（依赖 `clickzetta-connector-python`）
> **返回**: [ClickZetta 连接主指南](../SKILL.md)

## 目录

1. [安装](#1-安装)
2. [连接 URL 格式](#2-连接-url-格式)
3. [基础用法 — create_engine](#3-基础用法--create_engine)
4. [特殊字符处理](#4-特殊字符处理)
5. [connect_args 参数](#5-connect_args-参数)
6. [连接池配置](#6-连接池配置)
7. [完整生产配置示例](#7-完整生产配置示例)
8. [与 LangChain 集成](#8-与-langchain-集成)
9. [与 Apache Superset 集成](#9-与-apache-superset-集成)
10. [常见操作示例](#10-常见操作示例)
11. [适用场景](#11-适用场景)
12. [与 Python SDK 的区别](#12-与-python-sdk-的区别)
13. [常见问题](#13-常见问题)
14. [相关文档](#14-相关文档)

---

## 1. 安装

```bash
pip install clickzetta-connector-python clickzetta-sqlalchemy
```

验证安装：

```python
from sqlalchemy import create_engine
import clickzetta.connector  # 确认 connector 可用
print("SQLAlchemy + ClickZetta connector ready")
```

---

## 2. 连接 URL 格式

ClickZetta SQLAlchemy 连接 URL 遵循以下格式：

```
clickzetta://{username}:{password}@{service}/{workspace}?instance={instance}&schema={schema}&vcluster={vcluster}
```

| 组成部分 | 说明 | 示例 |
|----------|------|------|
| `clickzetta://` | 协议前缀（dialect） | 固定值 |
| `{username}` | 用户名（需 URL 编码） | `my_user` |
| `{password}` | 密码（需 URL 编码） | `MyP%40ssw0rd%21` |
| `@{service}` | 服务地址（含区域前缀） | `cn-shanghai-alicloud.api.clickzetta.com` |
| `/{workspace}` | 工作空间（对应数据库） | `my_workspace` |
| `?instance=` | 实例名称 | `my_instance` |
| `&schema=` | Schema 名称 | `public` |
| `&vcluster=` | 虚拟集群名称（必填） | `default_ap` |

---

## 3. 基础用法 — create_engine

```python
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# ⚠️ 用户名和密码中的特殊字符必须 URL 编码
password = quote_plus("MyP@ssw0rd!")
username = quote_plus("my_user")

url = (
    f"clickzetta://{username}:{password}"
    f"@your-region.api.clickzetta.com"  # 按实例所在区域填写，参见 SKILL.md 区域地址表
    f"/my_workspace"
    f"?instance=my_instance"
    f"&schema=public"
    f"&vcluster=default_ap"
)

engine = create_engine(url)

# 执行查询
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM my_table LIMIT 10"))
    for row in result:
        print(row)
```

---

## 4. 特殊字符处理

用户名或密码中包含 `@`、`/`、`:`、`?`、`#`、`%` 等特殊字符时，**必须**使用 `urllib.parse.quote_plus()` 进行 URL 编码，否则会导致 URL 解析失败。

```python
from urllib.parse import quote_plus

# 原始密码: P@ss/w0rd#123
password_encoded = quote_plus("P@ss/w0rd#123")
# 编码后: P%40ss%2Fw0rd%23123

username_encoded = quote_plus("user@domain.com")
# 编码后: user%40domain.com
```

> **常见错误**: 直接拼接含 `@` 的密码会导致 SQLAlchemy 将密码中的 `@` 误认为 host 分隔符。

---

## 5. connect_args 参数

通过 `connect_args` 传递超时时间和性能提示（hints）：

```python
engine = create_engine(
    url,
    connect_args={
        "timeout": 300,  # 连接超时（秒）
        "hints": {
            "sdk.job.timeout": 300,
            "query_tag": "analytics",
            "cz.storage.parquet.vector.index.read.memory.cache": "true",
            "cz.storage.parquet.vector.index.read.local.cache": "false",
            "cz.sql.table.scan.push.down.filter": "true",
            "cz.sql.table.scan.enable.ensure.filter": "true",
            "cz.storage.always.prefetch.internal": "true",
            "cz.optimizer.generate.columns.always.valid": "true",
            "cz.sql.index.prewhere.enabled": "true",
        },
    },
)
```

> 以上 hints 参数来自 `langchain-clickzetta/libs/clickzetta/langchain_clickzetta/engine.py` 中的默认性能优化配置。

---

## 6. 连接池配置

```python
engine = create_engine(
    url,
    pool_pre_ping=True,       # 每次取连接前检测连接是否有效
    pool_recycle=3600,         # 每小时回收连接（避免服务端超时断开）
    pool_size=5,               # 连接池常驻连接数
    max_overflow=10,           # 允许的溢出连接数（峰值 = pool_size + max_overflow）
)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pool_pre_ping` | `False` | 取连接前发送测试查询，检测连接是否存活 |
| `pool_recycle` | `-1` | 连接回收间隔（秒），建议设为 `3600` |
| `pool_size` | `5` | 连接池常驻连接数 |
| `max_overflow` | `10` | 超出 `pool_size` 后允许的临时连接数 |
| `pool_timeout` | `30` | 等待可用连接的超时时间（秒） |

---

## 7. 完整生产配置示例

```python
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

password = quote_plus("MyP@ssw0rd!")
username = quote_plus("my_user")

url = (
    f"clickzetta://{username}:{password}"
    f"@your-region.api.clickzetta.com"  # 按实例所在区域填写，参见 SKILL.md 区域地址表
    f"/my_workspace"
    f"?instance=my_instance"
    f"&schema=public"
    f"&vcluster=default_ap"
)

engine = create_engine(
    url,
    connect_args={
        "timeout": 300,
        "hints": {
            "sdk.job.timeout": 300,
            "query_tag": "production_analytics",
        },
    },
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
)

# 执行查询
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM orders"))
    count = result.scalar()
    print(f"Total orders: {count}")

# 使用完毕后释放连接池
engine.dispose()
```

---

## 8. 与 LangChain 集成

`langchain-clickzetta` 包提供了 `ClickZettaEngine` 类，内部封装了 SQLAlchemy 引擎的创建和管理。无需手动构建 URL。

```python
from langchain_clickzetta import ClickZettaEngine

# 使用 7 个必填参数初始化
engine = ClickZettaEngine(
    service="your-region.api.clickzetta.com",  # 按实例所在区域填写，参见 SKILL.md 区域地址表
    instance="my_instance",
    workspace="my_workspace",
    schema="public",
    username="my_user",
    password="my_password",
    vcluster="default_ap",
    connection_timeout=30,   # 可选
    query_timeout=300,       # 可选
)

# 方式 1: 使用内置查询方法（推荐）
results, columns = engine.execute_query("SELECT * FROM my_table LIMIT 5")
for row in results:
    print(row)  # dict 格式: {"col1": val1, "col2": val2, ...}

# 方式 2: 获取底层 SQLAlchemy Engine 对象
sa_engine = engine.get_sqlalchemy_engine()
with sa_engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.fetchone())

# 方式 3: 使用 SQLAlchemy 引擎执行查询
results = engine.execute_sql_with_engine("SELECT COUNT(*) FROM orders")
print(results)  # [{"count": 12345}]

# 关闭连接
engine.close()
```

### ClickZettaEngine 内部 URL 构建逻辑

`ClickZettaEngine.get_sqlalchemy_engine()` 内部按以下方式构建连接 URL：

```python
# 来自 langchain-clickzetta/libs/clickzetta/langchain_clickzetta/engine.py
from urllib.parse import quote_plus

password_encoded = quote_plus(password)
username_encoded = quote_plus(username)

url_parts = [
    f"clickzetta://{username_encoded}:{password_encoded}",
    f"@{service}",
    f"/{workspace}",
    f"?instance={instance}",
    f"&schema={schema}",
    f"&vcluster={vcluster}",
]
connection_url = "".join(url_parts)

engine = create_engine(
    connection_url,
    connect_args={
        "timeout": connection_timeout,
        "hints": hints,
    },
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

### 支持上下文管理器

```python
with ClickZettaEngine(
    service="your-region.api.clickzetta.com",  # 按实例所在区域填写，参见 SKILL.md 区域地址表
    instance="my_instance",
    workspace="my_workspace",
    schema="public",
    username="my_user",
    password="my_password",
    vcluster="default_ap",
) as engine:
    results, columns = engine.execute_query("SELECT 1 AS test")
    print(results)
# 退出 with 块时自动关闭连接
```

---

## 9. 与 Apache Superset 集成

### 9.1 Superset 连接配置

在 Superset 中添加 ClickZetta 数据源时，使用以下 SQLAlchemy URI：

```
clickzetta://{username}:{password}@{service}/{workspace}?instance={instance}&schema={schema}&vcluster={vcluster}
```

> 在 Superset UI 的 "Database" → "Add Database" → "SQLAlchemy URI" 字段中填入上述格式。

### 9.2 Superset Engine Spec

ClickZetta 为 Superset 提供了专用的 Engine Spec（`ClickZettaEngineSpec`），支持以下特性：

| 特性 | 说明 |
|------|------|
| `engine = "clickzetta"` | 引擎标识符 |
| `LimitMethod.WRAP_SQL` | 使用子查询包装方式添加 LIMIT |
| 自动去除反引号 | 通过 monkey-patch 禁用 dialect 的反引号引用 |
| 时间粒度表达式 | 支持 `DATE_TRUNC('SECOND'/'MINUTE'/'HOUR'/'DAY'/'WEEK'/'MONTH'/'YEAR', col)` |
| Schema 预查询 | 自动执行 `USE SCHEMA {schema}` 设置上下文 |

```python
# 来自 superset/superset/db_engine_specs/clickzetta.py

class ClickZettaEngineSpec(BaseEngineSpec):
    engine = "clickzetta"
    engine_name = "ClickZetta"
    disable_ssh_tunneling = True
    limit_method = LimitMethod.WRAP_SQL

    _time_grain_expressions = {
        None: "{col}",
        "PT1S": "DATE_TRUNC('SECOND', {col})",
        "PT1M": "DATE_TRUNC('MINUTE', {col})",
        "PT1H": "DATE_TRUNC('HOUR', {col})",
        "P1D": "DATE_TRUNC('DAY', {col})",
        "P1W": "DATE_TRUNC('WEEK', {col})",
        "P1M": "DATE_TRUNC('MONTH', {col})",
        "P1Y": "DATE_TRUNC('YEAR', {col})",
    }
```

### 9.3 反引号问题

ClickZetta SQL 不支持反引号（`` ` ``）作为标识符引用。Superset 的 Engine Spec 通过 monkey-patch `ClickZettaDialect` 的 `identifier_preparer_class` 自动移除反引号：

```python
# 来自 superset/superset/db_engine_specs/clickzetta.py
class NoQuoteIdentifierPreparer(original_preparer):
    def quote(self, ident, force=None):
        return ident  # 不加引号，直接返回标识符

    def quote_identifier(self, value):
        return value
```

同时，所有 SQL 语句在执行前会通过事件监听器清理反引号：

```python
@event.listens_for(engine, "before_cursor_execute", retval=True)
def remove_backticks_from_statement(conn, cursor, statement, parameters, context, executemany):
    cleaned_statement = re.sub(r'`([^`]+)`', r'\1', statement)
    return cleaned_statement, parameters
```

---

## 10. 常见操作示例

### 10.1 查询数据

```python
with engine.connect() as conn:
    # 简单查询
    result = conn.execute(text("SELECT * FROM customers LIMIT 10"))
    rows = result.fetchall()
    columns = result.keys()

    # 参数化查询
    result = conn.execute(
        text("SELECT * FROM orders WHERE status = :status"),
        {"status": "completed"}
    )
    for row in result:
        print(dict(row))
```

### 10.2 DDL 操作

```python
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            event_id    STRING,
            event_type  STRING,
            user_id     BIGINT,
            event_time  TIMESTAMP,
            properties  STRING
        )
    """))
    conn.commit()
```

### 10.3 结合 Pandas 使用

```python
import pandas as pd

# 读取数据到 DataFrame
df = pd.read_sql("SELECT * FROM sales_data LIMIT 1000", engine)
print(df.describe())

# 将 DataFrame 写入表（需要表已存在）
df.to_sql("sales_summary", engine, if_exists="append", index=False)
```

---

## 11. 适用场景

| 场景 | 说明 |
|------|------|
| **ORM 集成** | Django、Flask-SQLAlchemy 等框架通过 SQLAlchemy 连接 ClickZetta |
| **BI 工具** | Apache Superset、Metabase 等通过 SQLAlchemy URI 连接 |
| **LangChain 集成** | `langchain-clickzetta` 内部使用 SQLAlchemy 引擎执行 SQL Chain、Vector Store 操作 |
| **ETL 管道** | 使用 SQLAlchemy 作为统一数据库接口，配合 Pandas、dbt 等工具 |
| **数据分析** | 结合 Pandas `read_sql()` 快速获取数据进行分析 |

---

## 12. 与 Python SDK 的区别

| 维度 | Python SDK (`clickzetta.connect()`) | SQLAlchemy (`create_engine()`) |
|------|--------------------------------------|--------------------------------|
| 返回对象 | `Session`（连接对象） | `Engine`（引擎 + 连接池） |
| 连接管理 | 手动管理单连接 | 自动连接池管理 |
| 查询方式 | `cursor.execute()` + `fetchall()` | `conn.execute(text(...))` |
| 参数化查询 | `cursor.execute(sql, params)` | `conn.execute(text(sql), params)` |
| 生态兼容 | 仅 ClickZetta SDK | 兼容所有 SQLAlchemy 生态工具 |
| 适用场景 | 轻量脚本、ETL | ORM、BI 工具、LangChain |

---

## 13. 常见问题

### Q: `create_engine` 后连接失败？
检查以下几点：
1. `clickzetta-sqlalchemy` 是否已安装
2. 密码中的特殊字符是否已用 `quote_plus()` 编码
3. 7 个必填参数（service、instance、workspace、schema、username、password、vcluster）是否完整
4. 网络是否可达 service 地址

### Q: 查询报错 "backtick not supported"？
ClickZetta 不支持反引号引用标识符。如果使用 ORM 自动生成的 SQL 包含反引号，需要像 Superset Engine Spec 那样 patch dialect，或在 SQL 中避免使用保留字作为列名。

### Q: 如何在长时间运行的应用中保持连接？
设置 `pool_pre_ping=True` 和 `pool_recycle=3600`，确保连接池中的连接不会因服务端超时而失效。

### Q: `execute_sql_with_engine` 和 `execute_query` 有什么区别？
- `execute_query`: 使用 ClickZetta 原生 Session + Cursor 执行，性能更好
- `execute_sql_with_engine`: 使用 SQLAlchemy Engine 执行，兼容性更好

---

## 14. 相关文档

- [Python SDK 参考](python-sdk.md) — 原生 `clickzetta.connect()` 用法
- [ZettaPark Session 参考](zettapark-session.md) — DataFrame API 用法
- [配置文件管理](config-file.md) — `connections.json` 统一管理连接参数
