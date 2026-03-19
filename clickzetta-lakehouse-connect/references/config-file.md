# 配置文件管理 — connections.json 详细参考

本文档详细说明 ClickZetta Lakehouse 的连接配置文件格式、搜索路径、多连接管理以及 Docker 部署方式。所有内容基于 `mcp-clickzetta-server` 项目中的真实代码。

## 目录

- [JSON 配置文件格式](#json-配置文件格式)
- [五级搜索路径](#五级搜索路径)
- [多连接管理](#多连接管理)
- [环境变量备选](#环境变量备选)
- [Docker / Kubernetes 部署配置](#docker--kubernetes-部署配置)
- [system_config 参数说明](#system_config-参数说明)
- [适用场景](#适用场景)
- [常见问题排查](#常见问题排查)
- [完整配置模板](#完整配置模板)

---

## JSON 配置文件格式

配置文件 `connections.json` 包含两个顶层对象：`connections`（连接数组）和 `system_config`（系统级配置）。

### 基本结构

```json
{
  "connections": [
    {
      "is_default": true,
      "connection_name": "dev",
      "service": "cn-shanghai-alicloud.api.clickzetta.com",
      "username": "my_user",
      "password": "my_password",
      "instance": "my_instance",
      "workspace": "my_workspace",
      "schema": "public",
      "vcluster": "default_ap",
      "description": "开发环境",
      "hints": {
        "sdk.job.timeout": 300,
        "query_tag": "dev-queries"
      }
    }
  ],
  "system_config": {
    "allow_write": true,
    "prefetch": false,
    "log_level": "INFO",
    "exclude_tools": []
  }
}
```

### 连接字段说明

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|:--|:--|:--|:--|:--|
| `connection_name` | string | ✅ | — | 连接名称，用于在多连接中唯一标识 |
| `service` | string | ✅ | — | API 服务地址，如 `cn-shanghai-alicloud.api.clickzetta.com` |
| `username` | string | ✅ | — | 登录用户名 |
| `password` | string | ✅ | — | 登录密码 |
| `instance` | string | ✅ | — | 实例名称 |
| `workspace` | string | ✅ | — | 工作空间名称 |
| `schema` | string | ✅ | — | 默认 Schema |
| `vcluster` | string | ❌ | `"default_ap"` | 虚拟集群名称 |
| `is_default` | boolean | ❌ | `false` | 是否为默认连接 |
| `description` | string | ❌ | `""` | 连接描述信息 |
| `hints` | object | ❌ | 见下方 | SDK 运行时参数 |

### hints 默认值

当 `hints` 未配置时，系统自动使用以下默认值：

```json
{
  "sdk.job.timeout": 300,
  "query_tag": "Query from MCP Server",
  "cz.storage.parquet.vector.index.read.memory.cache": "true",
  "cz.storage.parquet.vector.index.read.local.cache": "false",
  "cz.sql.table.scan.push.down.filter": "true",
  "cz.sql.table.scan.enable.ensure.filter": "true",
  "cz.storage.always.prefetch.internal": "true",
  "cz.optimizer.generate.columns.always.valid": "true",
  "cz.sql.index.prewhere.enabled": "true",
  "cz.storage.parquet.enable.io.prefetch": "false"
}
```

---

## 五级搜索路径

`ConnectionManager` 按以下优先级（从高到低）搜索配置文件，找到第一个可访问的文件即停止：

| 优先级 | 路径 | 适用场景 |
|:--|:--|:--|
| 1（最高） | `/app/.clickzetta/lakehouse_connection/connections.json` | Docker 统一路径（推荐） |
| 2 | `/app/config/lakehouse_connection/connections.json` | 旧版 Docker 兼容路径 |
| 3 | `config/lakehouse_connection/connections.json` | 项目目录相对路径（本地开发） |
| 4 | `~/.clickzetta/connections.json` | 用户主目录（仅非 Docker 环境） |
| 5（最低） | `/app/.clickzetta/connections.json` | 简化 Docker 路径 |

> **Windows Docker 环境**：系统会自动检测并添加额外的 Windows Docker 友好路径。

### 搜索逻辑源码参考

```python
# 来自 connection_manager.py
class ConnectionManager:
    UNIFIED_CONFIG_FILE = "/app/.clickzetta/lakehouse_connection/connections.json"
    DOCKER_CONFIG_FILE = "/app/config/lakehouse_connection/connections.json"
    DEFAULT_CONFIG_FILE = "config/lakehouse_connection/connections.json"
    USER_CONFIG_FILE = os.path.expanduser("~/.clickzetta/connections.json")
    SIMPLE_CONFIG_FILE = "/app/.clickzetta/connections.json"
```

### 指定配置文件路径

也可以在初始化时直接指定配置文件路径，跳过搜索逻辑：

```python
from mcp_clickzetta_server.connection_manager import ConnectionManager

# 使用指定路径
conn_manager = ConnectionManager(config_file="/path/to/my/connections.json")
```

---

## 多连接管理

### 配置多个连接

在 `connections` 数组中定义多个连接，通过 `is_default` 标记默认连接：

```json
{
  "connections": [
    {
      "is_default": true,
      "connection_name": "dev",
      "service": "cn-shanghai-alicloud.api.clickzetta.com",
      "username": "dev_user",
      "password": "dev_password",
      "instance": "dev_instance",
      "workspace": "dev_workspace",
      "schema": "public",
      "vcluster": "default_ap",
      "description": "开发环境"
    },
    {
      "connection_name": "staging",
      "service": "cn-shanghai-alicloud.api.clickzetta.com",
      "username": "staging_user",
      "password": "staging_password",
      "instance": "staging_instance",
      "workspace": "staging_workspace",
      "schema": "public",
      "vcluster": "default_ap",
      "description": "预发布环境"
    },
    {
      "connection_name": "prod",
      "service": "cn-shanghai-alicloud.api.clickzetta.com",
      "username": "prod_user",
      "password": "prod_password",
      "instance": "prod_instance",
      "workspace": "prod_workspace",
      "schema": "public",
      "vcluster": "default_ap",
      "description": "生产环境",
      "hints": {
        "sdk.job.timeout": 600,
        "query_tag": "production-queries"
      }
    }
  ],
  "system_config": {
    "allow_write": false,
    "log_level": "WARNING"
  }
}
```

### 连接选择规则

1. 如果有 `is_default: true` 的连接，自动设为活跃连接
2. 如果有多个 `is_default: true`，使用最后一个
3. 如果没有默认连接，使用第一个有效连接
4. `service` 为 `"not_configured"` 的占位配置会被自动跳过

### 代码中切换连接

```python
from mcp_clickzetta_server.connection_manager import ConnectionManager

conn_manager = ConnectionManager()

# 列出所有可用连接
connections = conn_manager.list_connections()
for conn in connections:
    print(f"  {conn['name']}: {conn.get('description', '')}")

# 切换到指定连接
result = conn_manager.switch_connection("prod")
print(f"已切换到: {result}")

# 获取当前活跃连接配置
active_config = conn_manager.get_active_config()
print(f"当前连接: {active_config.connection_name}")
print(f"工作空间: {active_config.workspace}")

# 设置新的默认连接
conn_manager.set_default_connection("staging")

# 验证连接配置是否完整
validation = conn_manager.validate_connection("dev")
print(f"验证结果: {validation}")
```

---

## 环境变量备选

当没有找到配置文件时，系统会创建占位配置并启动。以下环境变量可用于配置连接参数：

### 连接参数环境变量

| 环境变量 | 对应字段 | 说明 |
|:--|:--|:--|
| `CLICKZETTA_SERVICE` | `service` | API 服务地址 |
| `CLICKZETTA_USERNAME` | `username` | 用户名 |
| `CLICKZETTA_PASSWORD` | `password` | 密码 |
| `CLICKZETTA_INSTANCE` | `instance` | 实例名称 |
| `CLICKZETTA_WORKSPACE` | `workspace` | 工作空间 |
| `CLICKZETTA_SCHEMA` | `schema` | 默认 Schema |
| `CLICKZETTA_VCLUSTER` | `vcluster` | 虚拟集群（默认 `default_ap`） |

### 系统配置环境变量覆盖

以下环境变量可覆盖 `system_config` 中的对应配置（优先级最高）：

| 环境变量 | 对应配置 | 示例值 |
|:--|:--|:--|
| `MCP_ALLOW_WRITE` | `allow_write` | `"true"` / `"false"` |
| `MCP_PREFETCH` | `prefetch` | `"true"` / `"false"` |
| `MCP_LOG_LEVEL` | `log_level` | `"DEBUG"` / `"INFO"` / `"WARNING"` / `"ERROR"` |
| `MCP_EXCLUDE_TOOLS` | `exclude_tools` | `"tool1,tool2,tool3"` |

### 相似度搜索环境变量

| 环境变量 | 对应配置 |
|:--|:--|
| `Similar_table_name` | `similar_search.table_name` |
| `Similar_embedding_column_name` | `similar_search.embedding_column_name` |
| `Similar_content_column_name` | `similar_search.content_column_name` |
| `Similar_other_columns_name` | `similar_search.other_columns_name` |
| `Similar_partition_scope` | `similar_search.partition_scope` |

### 云存储环境变量

| 环境变量 | 对应配置 |
|:--|:--|
| `AWS_ACCESS_KEY_ID` | `cloud_storage.aws_access_key_id` |
| `AWS_SECRET_ACCESS_KEY` | `cloud_storage.aws_secret_access_key` |
| `AWS_REGION` | `cloud_storage.aws_region` |

### 配置优先级

系统配置的加载优先级（从高到低）：

1. **环境变量**（最高优先级）
2. **配置文件中的 `system_config`**
3. **内置默认值**（最低优先级）

---

## Docker / Kubernetes 部署配置

### docker-compose.yml

```yaml
services:
  mcp-server:
    image: mcp-clickzetta-server:latest
    volumes:
      # 推荐：挂载到统一路径（优先级 1）
      - ./config/connections.json:/app/.clickzetta/lakehouse_connection/connections.json:ro
    environment:
      # 可选：通过环境变量覆盖系统配置
      - MCP_ALLOW_WRITE=false
      - MCP_LOG_LEVEL=INFO
```

### 使用旧版路径

```yaml
services:
  mcp-server:
    image: mcp-clickzetta-server:latest
    volumes:
      # 旧版兼容路径（优先级 2）
      - ./config/connections.json:/app/config/lakehouse_connection/connections.json:ro
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: clickzetta-config
data:
  connections.json: |
    {
      "connections": [
        {
          "is_default": true,
          "connection_name": "prod",
          "service": "cn-shanghai-alicloud.api.clickzetta.com",
          "username": "prod_user",
          "password": "prod_password",
          "instance": "prod_instance",
          "workspace": "prod_workspace",
          "schema": "public",
          "vcluster": "default_ap"
        }
      ],
      "system_config": {
        "allow_write": false,
        "log_level": "WARNING"
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
spec:
  template:
    spec:
      containers:
        - name: mcp-server
          volumeMounts:
            - name: config
              mountPath: /app/.clickzetta/lakehouse_connection/connections.json
              subPath: connections.json
              readOnly: true
      volumes:
        - name: config
          configMap:
            name: clickzetta-config
```

> **安全提示**：生产环境建议使用 Kubernetes Secret 替代 ConfigMap 存储密码。

---

## system_config 参数说明

### 核心参数

| 参数 | 类型 | 默认值 | 说明 |
|:--|:--|:--|:--|
| `allow_write` | boolean | `false` | 是否允许写操作（INSERT/UPDATE/DELETE） |
| `prefetch` | boolean | `true` | 是否启用数据预取 |
| `log_level` | string | `"INFO"` | 日志级别：`DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `exclude_tools` | array | `[]` | 需要排除的工具列表 |

---

## 适用场景

| 场景 | 推荐配置方式 | 说明 |
|:--|:--|:--|
| 本地开发 | `~/.clickzetta/connections.json` | 用户主目录，个人配置 |
| 团队共享 | `config/lakehouse_connection/connections.json` | 项目目录，可纳入版本管理 |
| Docker 部署 | 挂载到 `/app/.clickzetta/lakehouse_connection/` | 统一路径，推荐方式 |
| Kubernetes | ConfigMap / Secret | 声明式配置管理 |
| CI/CD 流水线 | 环境变量 | 无需配置文件，适合自动化 |
| 多环境切换 | 多连接 + `switch_connection()` | 在同一配置文件中管理多个环境 |

---

## 常见问题排查

### 配置文件未找到

```
WARNING: 未找到任何可用的配置文件
```

**解决方案**：
1. 确认文件存在于五级搜索路径之一
2. 检查文件权限：`chmod 600 connections.json`
3. Docker 环境检查挂载是否正确

### JSON 格式错误

```
ERROR: 配置文件JSON格式错误
```

**解决方案**：
1. 使用 JSON 验证工具检查格式
2. 确保所有字符串使用双引号
3. 检查是否有多余的逗号
4. 确保中文字符使用 UTF-8 编码保存

### 连接配置缺少必需字段

每个连接必须包含以下 7 个必需字段：

```
connection_name, service, username, password, instance, workspace, schema
```

### 占位配置被跳过

`service` 设置为 `"not_configured"` 的连接会被自动跳过。确保所有生产连接都配置了正确的 `service` 地址。

---

## 完整配置模板

参考项目中的模板文件：`config/connections-template.json`

```bash
# 复制模板并修改
cp config/connections-template.json ~/.clickzetta/connections.json
# 编辑配置
vim ~/.clickzetta/connections.json
# 设置文件权限（保护密码）
chmod 600 ~/.clickzetta/connections.json
```
