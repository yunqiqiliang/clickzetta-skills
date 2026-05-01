---
name: clickzetta-lakehouse-connect
description: Guide for connecting to ClickZetta Lakehouse via SDK/JDBC. Covers Python SDK (clickzetta.connect), ZettaPark Session (DataFrame API), SQLAlchemy (ORM/BI tools), and JDBC (Java). Use this skill when user needs to configure a connection from external tools or code — NOT for querying data inside czcode (use execute_sql/list_objects tools instead). Trigger for: "Python SDK 连接", "JDBC 连接", "SQLAlchemy 配置", "ZettaPark 怎么用", "连接报错", "clickzetta-connector-python", "clickzetta-sqlalchemy".
---

# ClickZetta Lakehouse 连接指南

## 指令

### 步骤 0：自动获取连接参数（优先）

**在询问用户之前，先尝试从本地配置文件自动读取连接参数。**

按以下优先级查找配置文件（找到第一个即停止）：
1. `/app/.clickzetta/lakehouse_connection/connections.json`
2. `config/lakehouse_connection/connections.json`
3. `~/.clickzetta/connections.json`
4. `/app/.clickzetta/connections.json`

找到配置文件后：
- 解析 JSON，提取 `connections` 数组
- 根据用户描述的区域/环境匹配对应连接（如"阿里云上海"匹配 `service` 含 `cn-shanghai-alicloud` 的连接）
- 若有 `is_default: true` 且用户未指定区域，使用默认连接
- **不要将密码或完整配置输出到对话中**，仅内部使用

若配置文件不存在或无匹配连接，再向用户询问：service、instance、workspace、username、password、schema、vcluster。

### 步骤 1：确认连接方式

根据用户场景选择连接方式，阅读对应参考文件：

| 用户需求 | 参考文件 |
|:--|:--|
| Python 脚本 / 自动化 / 执行 SQL | [references/python-sdk.md](references/python-sdk.md) |
| DataFrame / 数据工程 | [references/zettapark-session.md](references/zettapark-session.md) |
| ORM / Web 应用 / BI 工具（Superset） | [references/sqlalchemy.md](references/sqlalchemy.md) |
| Java 应用 / BI 工具（DBeaver） | [references/jdbc.md](references/jdbc.md) |
| 多环境配置文件管理 | [references/config-file.md](references/config-file.md) |

不确定时参考决策树：
- 需要 DataFrame 操作 → ZettaPark Session
- 需要 ORM / SQLAlchemy 集成 → SQLAlchemy
- Java 应用 → JDBC
- 其他 Python 场景（含直接执行 SQL）→ Python SDK

### 步骤 2：确认 service 地址

`service` 参数必须包含区域前缀，根据实例所在区域选择：

**云器 Lakehouse（国内版，`clickzetta.com`）**

| 云厂商 | 区域 | service 地址 |
|:--|:--|:--|
| 阿里云 | 华东2（上海） | `cn-shanghai-alicloud.api.clickzetta.com` |
| 腾讯云 | 华东（上海） | `ap-shanghai-tencentcloud.api.clickzetta.com` |
| 腾讯云 | 华北（北京） | `ap-beijing-tencentcloud.api.clickzetta.com` |
| 腾讯云 | 华南（广州） | `ap-guangzhou-tencentcloud.api.clickzetta.com` |
| AWS | 中国（北京） | `cn-north-1-aws.api.clickzetta.com` |

**Singdata Lakehouse（国际版，`singdata.com`）**

| 云厂商 | 区域 | service 地址 |
|:--|:--|:--|
| 阿里云 | 亚太东南1（新加坡） | `ap-southeast-1-alicloud.api.singdata.com` |
| AWS | 亚太（新加坡） | `ap-southeast-1-aws.api.singdata.com` |

控制台：`https://{instance}.{region}.app.clickzetta.com`

### 步骤 3：执行查询或提供可运行代码

**若用户要求执行查询（如 SHOW SCHEMAS、SELECT、SHOW TABLES 等）：**

1. 确认 `clickzetta-connector-python` 已安装：
   ```bash
   pip3 show clickzetta-connector-python
   ```
   若未安装，执行：`pip3 install clickzetta-connector-python --user`

2. 使用步骤 0 获取的连接参数直接执行查询，将结果格式化后展示给用户。

**若用户要求生成代码：**

阅读对应参考文件后，根据参数生成完整可运行代码。所有参数均为必填，`vcluster` 默认值为 `default_ap`。

密码含特殊字符时（SQLAlchemy URI），提醒用户用 `urllib.parse.quote_plus()` 编码。

## 示例

### 示例 0：自动读取配置并执行查询

```python
import json, os, clickzetta

# 按优先级查找配置文件
config_paths = [
    "/app/.clickzetta/lakehouse_connection/connections.json",
    "config/lakehouse_connection/connections.json",
    os.path.expanduser("~/.clickzetta/connections.json"),
    "/app/.clickzetta/connections.json",
]
config = None
for path in config_paths:
    if os.path.exists(path):
        with open(path) as f:
            config = json.load(f)
        break

# 选择目标连接（示例：匹配阿里云上海）
conn_cfg = next(
    (c for c in config["connections"] if "cn-shanghai-alicloud" in c.get("service", "")),
    None
) or next((c for c in config["connections"] if c.get("is_default")), config["connections"][0])

conn = clickzetta.connect(
    service=conn_cfg["service"],
    instance=conn_cfg["instance"],
    workspace=conn_cfg["workspace"],
    schema=conn_cfg.get("schema", "public"),
    username=conn_cfg["username"],
    password=conn_cfg["password"],
    vcluster=conn_cfg.get("vcluster", "default_ap")
)
cursor = conn.cursor()
cursor.execute("SHOW SCHEMAS")
for row in cursor.fetchall():
    print(row[0])
cursor.close()
conn.close()
```

### 示例 1：Python SDK 连接并查询

```python
import clickzetta

conn = clickzetta.connect(
    service="cn-shanghai-alicloud.api.clickzetta.com",
    instance="my_instance",
    workspace="my_workspace",
    schema="public",
    username="my_user",
    password="my_password",
    vcluster="default_ap"
)
cursor = conn.cursor()
cursor.execute("SELECT * FROM orders LIMIT 10")
for row in cursor.fetchall():
    print(row)
cursor.close()
conn.close()
```

### 示例 2：ZettaPark 按 region 汇总 revenue

```python
from clickzetta.zettapark.session import Session
from clickzetta.zettapark import functions as F

session = Session.builder.configs({
    "service": "cn-shanghai-alicloud.api.clickzetta.com",
    "instance": "my_instance", "workspace": "my_workspace",
    "schema": "public", "username": "my_user",
    "password": "my_password", "vcluster": "default_ap"
}).create()

session.table("sales") \
    .group_by(F.col("region")) \
    .agg(F.sum("revenue").as_("total_revenue")) \
    .write.save_as_table("sales_summary", mode="overwrite")
session.close()
```

## 故障排除

| 错误信息 | 原因 | 解决方案 |
|:--|:--|:--|
| `Connection refused` | service 地址不正确或网络不通 | 检查 service 是否匹配区域（参见步骤 2 区域表） |
| `Authentication failed` | 用户名或密码错误 | 核实 username 和 password |
| `Workspace not found` | 工作空间名称不存在 | 在控制台确认 workspace 拼写 |
| `Instance not found` | 实例名称不存在 | 在控制台确认 instance 拼写 |
| `Timeout` | 查询超时 | 增大 `hints` 中的 `sdk.job.timeout`（默认 300 秒） |
| `VCluster not available` | 虚拟集群未启动或名称错误 | 确认 vcluster 名称，检查集群状态 |
| SQLAlchemy URL 解析错误 | 密码含特殊字符 | 用 `urllib.parse.quote_plus()` 对密码 URL 编码 |
| `ClassNotFoundException` | JDBC 驱动未在 classpath | 确保 `clickzetta-java` JAR 已加入 classpath |

## 安装

| 连接方式 | 安装命令 |
|:--|:--|
| Python SDK | `pip install clickzetta-connector-python` |
| ZettaPark | `pip install clickzetta-zettapark-python` |
| SQLAlchemy | `pip install clickzetta-connector-python clickzetta-sqlalchemy` |
| JDBC | Maven: `com.clickzetta:clickzetta-java` |
