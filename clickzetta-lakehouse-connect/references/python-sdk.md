# Python SDK — `clickzetta.connect()` 详细参考

> **包名**: `clickzetta-connector-python`
> **最低版本**: >= 0.8.92
> **返回**: [ClickZetta 连接主指南](../SKILL.md)

---

## 1. 安装

```bash
pip install clickzetta-connector-python
```

如果需要同时使用 SQLAlchemy 集成：

```bash
pip install clickzetta-connector-python clickzetta-sqlalchemy
```

---

## 2. 连接参数一览

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `service` | str | ✅ | 服务地址，如 `cn-shanghai-alicloud.api.clickzetta.com` |
| `instance` | str | ✅ | 实例名称 |
| `workspace` | str | ✅ | 工作空间（对应数据库） |
| `schema` | str | ✅ | Schema 名称，默认通常为 `public` |
| `username` | str | ✅ | 用户名 |
| `password` | str | ✅ | 密码 |
| `vcluster` | str | ✅ | 虚拟集群名称 |
| `hints` | dict | ❌ | SDK 运行时参数（见第 5 节） |

---

## 3. 完整代码示例

### 3.1 基础查询

```python
import clickzetta

# 建立连接（7 个必填参数）
conn = clickzetta.connect(
    service="your-region.api.clickzetta.com",  # 按实例所在区域填写，参见 SKILL.md 区域地址表
    username="your_username",
    password="your_password",
    instance="your_instance",
    workspace="your_workspace",
    schema="public",
    vcluster="default_ap"
)

try:
    cursor = conn.cursor()

    # 执行查询
    cursor.execute("SELECT * FROM my_table LIMIT 10")

    # 获取所有结果
    rows = cursor.fetchall()
    for row in rows:
        print(row)

    # 获取列名
    columns = [desc[0] for desc in cursor.description]
    print("列名:", columns)

finally:
    cursor.close()
    conn.close()
```

### 3.2 Cursor 操作详解

```python
cursor = conn.cursor()
cursor.execute("SELECT id, name, amount FROM orders WHERE status = 'active'")

# fetchone() — 逐行获取
first_row = cursor.fetchone()

# fetchmany(size) — 批量获取指定行数
batch = cursor.fetchmany(size=100)

# fetchall() — 获取剩余全部行
remaining = cursor.fetchall()

cursor.close()
```

### 3.3 DDL / DML 操作

```python
cursor = conn.cursor()

# 建表
cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        event_id   BIGINT,
        event_type STRING,
        event_time TIMESTAMP,
        payload    STRING
    )
""")

# 插入数据
cursor.execute("""
    INSERT INTO events VALUES
    (1, 'click', CURRENT_TIMESTAMP, '{"page": "/home"}')
""")

cursor.close()
```

---

## 4. 环境变量传参（推荐）

生产环境中，**绝对不要在代码中硬编码凭证**。使用环境变量：

```python
import os
import clickzetta

conn = clickzetta.connect(
    service=os.getenv("CLICKZETTA_SERVICE"),
    username=os.getenv("CLICKZETTA_USERNAME"),
    password=os.getenv("CLICKZETTA_PASSWORD"),
    instance=os.getenv("CLICKZETTA_INSTANCE"),
    workspace=os.getenv("CLICKZETTA_WORKSPACE"),
    schema=os.getenv("CLICKZETTA_SCHEMA", "public"),
    vcluster=os.getenv("CLICKZETTA_VCLUSTER", "default_ap")
)
```

对应的 `.env` 文件（需加入 `.gitignore`）：

```bash
CLICKZETTA_SERVICE=your-region.api.clickzetta.com
CLICKZETTA_INSTANCE=my_instance
CLICKZETTA_WORKSPACE=my_workspace
CLICKZETTA_SCHEMA=public
CLICKZETTA_USERNAME=my_user
CLICKZETTA_PASSWORD=my_secret
CLICKZETTA_VCLUSTER=default_ap
```

---

## 5. `hints` 参数详解

`hints` 是一个 `dict`，用于传递 SDK 运行时调优参数：

```python
conn = clickzetta.connect(
    service="your-region.api.clickzetta.com",  # 按实例所在区域填写，参见 SKILL.md 区域地址表
    username="your_username",
    password="your_password",
    instance="your_instance",
    workspace="your_workspace",
    schema="public",
    vcluster="default_ap",
    hints={
        "sdk.job.timeout": 300,
        "query_tag": "my-etl-job",
        "cz.sql.table.scan.push.down.filter": "true",
        "cz.storage.parquet.vector.index.read.memory.cache": "true"
    }
)
```

### 常用 hints

| Key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `sdk.job.timeout` | int | 300 | 查询超时（秒） |
| `query_tag` | str | — | 查询标签，用于审计追踪 |
| `cz.sql.table.scan.push.down.filter` | str | `"true"` | 启用过滤下推 |
| `cz.sql.table.scan.enable.ensure.filter` | str | `"true"` | 确保过滤条件生效 |
| `cz.storage.parquet.vector.index.read.memory.cache` | str | `"true"` | 向量索引内存缓存 |
| `cz.storage.parquet.vector.index.read.local.cache` | str | `"false"` | 向量索引本地磁盘缓存 |
| `cz.storage.always.prefetch.internal` | str | `"true"` | 预取优化 |
| `cz.optimizer.generate.columns.always.valid` | str | `"true"` | 列生成优化 |
| `cz.sql.index.prewhere.enabled` | str | `"true"` | 索引预过滤 |
| `cz.storage.parquet.enable.io.prefetch` | str | `"false"` | Parquet IO 预取 |

---

## 6. 适用场景

| 场景 | 推荐度 | 说明 |
|------|--------|------|
| 直接 SQL 查询 | ⭐⭐⭐ | 最简洁的方式执行 SQL |
| 脚本 & 自动化 | ⭐⭐⭐ | ETL 脚本、定时任务 |
| Jupyter Notebook | ⭐⭐⭐ | 数据探索与分析 |
| Cursor 逐行处理 | ⭐⭐⭐ | 大结果集逐行/分批处理 |
| DataFrame 操作 | ⭐ | 建议改用 [ZettaPark Session](zettapark-session.md) |
| Web 应用 ORM | ⭐ | 建议改用 [SQLAlchemy](sqlalchemy.md) |

---

## 7. 与其他连接方式的关系

- **ZettaPark Session** 底层也调用 `clickzetta.connect()`，但封装了 DataFrame API
- **SQLAlchemy** 使用 `clickzetta://` URL 协议，底层通过 connector 驱动
- **配置文件** 方式使用 `connections.json` 管理连接参数，最终也传递给 `clickzetta.connect()`

> 选择指南见 [SKILL.md 决策树](../SKILL.md#决策树)。
