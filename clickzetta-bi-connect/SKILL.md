---
name: clickzetta-bi-connect
description: |
  将 BI 工具和数据库客户端连接到 ClickZetta Lakehouse。覆盖 Apache Superset、
  Tableau、Metabase、DBeaver、DataGrip、帆软 FineBI 等主流工具的完整连接配置，
  包括 JDBC 连接字符串格式、SQLAlchemy URL 格式、驱动安装步骤。
  当用户说"连接 Superset"、"Tableau 连接 Lakehouse"、"Metabase"、"DBeaver"、
  "DataGrip"、"BI 工具"、"JDBC 连接"、"SQLAlchemy 连接"、"帆软"、"FineBI"、
  "数据库客户端"、"可视化工具连接"、"BI 报表"、"PowerBI"、"Navicat"、
  "MySQL 协议连接"时触发。
  Keywords: BI, Superset, Tableau, Metabase, DBeaver, DataGrip, FineBI, JDBC, connection
---

# ClickZetta BI 工具连接

阅读 [references/bi-tools.md](references/bi-tools.md) 了解各工具详细配置。

## 连接方式速查

| 工具 | 连接方式 |
|---|---|
| Apache Superset | SQLAlchemy URL |
| Tableau | JDBC + .taco 插件 |
| Metabase | 专用 .jar 驱动 |
| DBeaver / DataGrip | JDBC |
| 帆软 FineBI | JDBC 或 MySQL 协议 |
| PowerBI | MySQL 协议 |
| Navicat | MySQL 协议 |
| Python / ORM | SQLAlchemy |

---

## JDBC 连接字符串

```
jdbc:clickzetta://<instance>.<region_id>.api.clickzetta.com/<workspace>?username=<user>&password=<pwd>&schema=<schema>&virtualCluster=<vc_name>
```

**示例：**
```
jdbc:clickzetta://f8866243.cn-shanghai-alicloud.api.clickzetta.com/quick_start?username=alice&password=xxxx&schema=public&virtualCluster=default_ap
```

- 驱动类：`com.clickzetta.client.jdbc.ClickZettaDriver`
- 驱动下载：Maven `com.clickzetta:clickzetta-java` 或 [sonatype](https://central.sonatype.com/artifact/com.clickzetta/clickzetta-java/versions)

---

## SQLAlchemy URL（Superset / Python ORM）

```
clickzetta://<username>:<password>@<instance>.<region_id>.api.clickzetta.com/<workspace>?schema=<schema>&vcluster=<vc_name>
```

安装：
```bash
pip uninstall -y clickzetta-sqlalchemy clickzetta-connector
pip install clickzetta-connector -U
```

---

## Apache Superset

**Docker 快速启动：**
```bash
docker pull clickzetta/superset:2.1.0-1
docker run -p 8088:8088 clickzetta/superset:2.1.0-1
# 访问 http://localhost:8088，账号 admin/clickzetta
```

**配置数据库连接：**
1. Settings → Database Connections → + Database → 选择 **Other**
2. 填写 SQLAlchemy URI：
   ```
   clickzetta://username:password@instance.cn-shanghai-alicloud.api.clickzetta.com/workspace?vcluster=default_ap
   ```
3. TESTING CONNECTION → CONNECT

---

## Tableau

1. 将 JDBC JAR 放入 Tableau Drivers 目录
2. 将 `.taco` 插件放入 Connectors 目录
3. 启动时加 `-DDisableVerifyConnectorPluginSignature=true`
4. 连接：到服务器 → 更多 → **Lakehouse x 云器科技**

---

## Metabase

```bash
docker run -d -p 3000:3000 --name metabase metabase/metabase:v0.54.6
docker cp clickzetta.metabase-driver.jar metabase:/plugins/
docker restart metabase
```

访问 `http://localhost:3000` → Admin Settings → Databases → Add a database → 选择 ClickZetta

---

## DBeaver

1. 驱动管理器 → 新建驱动
2. 类名：`com.clickzetta.client.jdbc.ClickZettaDriver`
3. 添加 JDBC JAR 包
4. 新建连接 → 粘贴 JDBC 连接字符串

---

## MySQL 协议连接（PowerBI / Navicat / 帆软）

Lakehouse 支持通过 MySQL 协议连接，适用于不支持自定义 JDBC 驱动的工具。

**前置准备：**
1. 在管理中心为用户重置 MySQL 协议专用密码
2. 为用户设置默认计算集群（`ALTER USER username SET DEFAULT_VCLUSTER = default_ap`）

**用户名格式：** `<instance_name>.<workspace_name>.<username>`

**连接参数：**
- 主机：`<instance>.<region_id>.mysql.clickzetta.com`
- 端口：`3306`
- 用户名：`instance.workspace.username`（三段式拼接）
- 密码：MySQL 协议专用密码（非 Lakehouse 登录密码）

### PowerBI

1. 获取数据 → MySQL 数据库
2. 服务器：`instance.cn-shanghai-alicloud.mysql.clickzetta.com`
3. 用户名：`instance.workspace.username`
4. 密码：MySQL 协议专用密码
5. 数据连接模式选择 DirectQuery

### Navicat

1. 新建连接 → MySQL
2. 主机：`instance.cn-shanghai-alicloud.mysql.clickzetta.com`
3. 端口：`3306`
4. 用户名：`instance.workspace.username`
5. 密码：MySQL 协议专用密码

### 帆软 FineBI（MySQL 协议方式）

1. 管理系统 → 数据连接 → 新建数据连接 → MySQL
2. URL：`jdbc:mysql://instance.cn-shanghai-alicloud.mysql.clickzetta.com:3306/workspace`
3. 用户名：`instance.workspace.username`
4. 密码：MySQL 协议专用密码

> ⚠️ MySQL 协议连接有部分 SQL 语法限制，详见 [使用MySQL协议连接](https://www.yunqi.tech/documents/use-mysql-client)

---

## 常用地域代码

| 地域 | region_id |
|---|---|
| 阿里云上海 | `cn-shanghai-alicloud` |
| 腾讯云上海 | `ap-shanghai-tencentcloud` |
| 腾讯云北京 | `ap-beijing-tencentcloud` |
| AWS 新加坡 | `ap-southeast-1-aws` |

---

## 常见问题

| 问题 | 解决方案 |
|---|---|
| Superset 连接失败 | 确认已安装 `clickzetta-connector`，URL 格式正确 |
| Tableau 找不到 Lakehouse 连接器 | 确认 .taco 文件在正确目录，且启动时禁用签名校验 |
| DBeaver 驱动加载失败 | 确认 JAR 包版本与 Lakehouse 版本匹配 |
| 连接超时 | 检查网络，确认 instance/region_id 正确 |
| 无权限查询 | 确认用户已被 `CREATE USER` 添加到工作空间，且有 `USE VCLUSTER` 权限 |
| MySQL 协议连接失败 | 确认用户名为三段式格式（instance.workspace.username），密码为 MySQL 协议专用密码 |
| PowerBI DirectQuery 报错 | 确认已设置用户默认计算集群（`ALTER USER ... SET DEFAULT_VCLUSTER`） |
