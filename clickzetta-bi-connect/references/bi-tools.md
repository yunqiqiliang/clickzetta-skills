# BI 工具连接参考

> 来源：https://www.yunqi.tech/documents/ecosystem-all 等

## 连接方式总览

| 工具 | 连接方式 | 说明 |
|---|---|---|
| Apache Superset | SQLAlchemy URL | 需安装 clickzetta-connector |
| Tableau | JDBC + 插件 | 需下载 .taco 插件 |
| Metabase | 专用驱动 | 需下载 .jar 驱动 |
| DBeaver | JDBC | 通用数据库客户端 |
| DataGrip | JDBC | JetBrains 数据库 IDE |
| 帆软 FineBI | JDBC | 国产 BI 工具 |

---

## JDBC 连接字符串格式

```
jdbc:clickzetta://<instance_name>.<region_id>.api.clickzetta.com/<workspace_name>?username=<user>&password=<pwd>&schema=<schema>&virtualCluster=<vc_name>
```

示例：
```
jdbc:clickzetta://f8866243.cn-shanghai-alicloud.api.clickzetta.com/quick_start?username=alice&password=xxxx&schema=public&virtualCluster=default_ap
```

JDBC 驱动类：`com.clickzetta.client.jdbc.ClickZettaDriver`

JDBC 驱动下载：
- Maven: `com.clickzetta:clickzetta-java`
- 直接下载：https://central.sonatype.com/artifact/com.clickzetta/clickzetta-java/versions

---

## SQLAlchemy URL 格式

```
clickzetta://<username>:<password>@<instance_name>.<region_id>.api.clickzetta.com/<workspace_name>?schema=<schema>&vcluster=<vc_name>
```

示例：
```
clickzetta://alice:xxxx@f8866243.cn-shanghai-alicloud.api.clickzetta.com/quick_start?schema=public&vcluster=default_ap
```

安装：
```bash
pip uninstall -y clickzetta-sqlalchemy clickzetta-connector && pip install clickzetta-connector -U
```

---

## Apache Superset

### 快速启动（Docker）

```bash
docker pull clickzetta/superset:2.1.0-1
docker run -p 8088:8088 clickzetta/superset:2.1.0-1
# 访问 http://localhost:8088，默认账号 admin/clickzetta
```

### 本地安装

```bash
pip uninstall -y clickzetta-sqlalchemy clickzetta-connector
pip install clickzetta-connector -U
pip install 'apache-superset>=2.1'

export FLASK_APP=superset
superset db upgrade
superset fab create-admin
superset init
superset run -p 8088 --with-threads --reload --debugger
```

### 配置数据库连接

1. Settings → Database Connections → + Database
2. 选择 **Other** 数据库类型
3. 填写 SQLAlchemy URI：
   ```
   clickzetta://username:password@instance.region.api.clickzetta.com/workspace?vcluster=default_ap
   ```
4. 点击 TESTING CONNECTION 验证，通过后 CONNECT

---

## Tableau

### 前提条件

1. 下载 JDBC 驱动 JAR 包
2. 下载 Tableau 插件：`clickzetta_jdbc-v0.0.1.taco`

### 安装步骤

**放置 JDBC 驱动：**
- Windows: `C:\Program Files\Tableau\Drivers`
- macOS: `~/Library/Tableau/Drivers`
- Linux: `/opt/tableau/tableau_driver/jdbc`

**放置 Tableau 插件（.taco 文件）：**
- Windows: `C:\Users\[User]\Documents\My Tableau Repository\Connectors`
- macOS: `/Users/[user]/Documents/My Tableau Repository/Connectors`

**启动 Tableau（禁用签名校验）：**
```bash
# macOS
/Applications/Tableau\ Desktop\ [version].app/Contents/MacOS/Tableau -DDisableVerifyConnectorPluginSignature=true

# Windows
tableau.exe -DDisableVerifyConnectorPluginSignature=true
```

**连接：** 左侧导航 → 到服务器 → 更多 → Lakehouse x 云器科技 → 填写服务器/用户名/密码

---

## Metabase

### Docker 部署

```bash
docker pull metabase/metabase:v0.54.6
docker run -d -p 3000:3000 --name metabase metabase/metabase:v0.54.6

# 下载并安装云器驱动
docker cp clickzetta.metabase-driver.jar metabase:/plugins/clickzetta.metabase-driver.jar
docker restart metabase
```

驱动下载：`clickzetta.metabase-driver.jar`（联系云器技术支持获取）

### 配置连接

1. 访问 `http://localhost:3000`
2. Admin Settings → Databases → Add a database
3. 选择 ClickZetta Lakehouse，填写连接信息
4. Test connection → Save

---

## DBeaver

### 配置步骤

1. 数据库 → 驱动管理器 → 新建驱动
2. 填写：
   - 驱动名称：`Clickzetta`
   - 类名：`com.clickzetta.client.jdbc.ClickZettaDriver`
   - URL 模板：`jdbc:clickzetta://{instanceName}.{service}/{workspaceName}?virtualCluster={vc_name}`
3. 选择库 → 添加 JDBC JAR 包
4. 新建连接 → 搜索 Clickzetta → 粘贴 JDBC 连接字符串 → 填写用户名密码

---

## 地域代码（region_id）速查

| 云厂商 | 地域 | region_id |
|---|---|---|
| 阿里云 | 华东2（上海） | cn-shanghai-alicloud |
| 腾讯云 | 华东（上海） | ap-shanghai-tencentcloud |
| 腾讯云 | 华北（北京） | ap-beijing-tencentcloud |
| 腾讯云 | 华南（广州） | ap-guangzhou-tencentcloud |
| AWS | 中国（北京） | cn-north-1-aws |
| 阿里云（新加坡） | 亚太东南1 | ap-southeast-1-alicloud |
| AWS（新加坡） | 亚太（新加坡） | ap-southeast-1-aws |
