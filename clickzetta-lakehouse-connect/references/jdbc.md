# JDBC 连接详细参考

> **驱动包名**: `clickzetta-java`
> **Driver 类**: `com.clickzetta.client.jdbc.ClickZettaDriver`
> **返回**: [ClickZetta 连接主指南](../SKILL.md) §4.4

---

## 目录

1. [JDK 环境要求](#1-jdk-环境要求)
2. [获取驱动](#2-获取驱动)
3. [JDBC URL 格式](#3-jdbc-url-格式)
4. [Driver 类名](#4-driver-类名)
5. [Java 代码完整示例](#5-java-代码完整示例)
6. [Properties 文件格式](#6-properties-文件格式)
7. [SQLLine 使用方法](#7-sqlline-使用方法)
8. [BI 工具集成](#8-bi-工具集成)
9. [适用场景](#9-适用场景)
10. [Spring Boot 集成示例](#10-spring-boot-集成示例)
11. [常见问题](#11-常见问题)
12. [与其他连接方式对比](#12-与其他连接方式对比)
13. [交叉引用](#13-交叉引用)

---

## 1. JDK 环境要求

| JDK 版本 | 支持情况 | 额外要求 |
|----------|---------|---------|
| JDK 8    | ✅ 完全支持 | 无 |
| JDK 9+   | ✅ 支持 | 需添加 `--add-opens` JVM 参数 |

### JDK 9+ 模块系统参数

JDK 9 引入了模块系统（JPMS），ClickZetta JDBC 驱动需要访问 `java.base/java.nio` 内部 API。
必须在启动时添加以下 JVM 参数：

```bash
java --add-opens=java.base/java.nio=ALL-UNNAMED \
     -cp "your-classpath/*" your.MainClass
```

> **来源**：`sqlline_cz/sqlline` 脚本中的实际判断逻辑：
> ```bash
> JAVA_VERSION=$($JAVA_HOME/bin/java -version 2>&1 | head -n 1 | cut -d '"' -f 2 | cut -d '.' -f 1-2)
> if (( $(echo "$JAVA_VERSION > 1.8" | bc -l) )); then
>     JAVA_OPTS="--add-opens=java.base/java.nio=ALL-UNNAMED"
> fi
> ```

---

## 2. 获取驱动

### 2.1 Maven 依赖

```xml
<dependency>
    <groupId>com.clickzetta</groupId>
    <artifactId>clickzetta-java</artifactId>
    <version>最新版本</version>
</dependency>
```

### 2.2 直接下载 JAR

```bash
# 下载最新 shaded JAR（含所有依赖）
wget https://autolake-dev-beijing.oss-cn-beijing.aliyuncs.com/clickzetta-tool/release/clickzetta-java-latest-jar-with-dependencies.jar
```

> **来源**：`sqlline_cz/setup.sh` 中的实际下载地址。

---

## 3. JDBC URL 格式

### 3.1 标准格式（通过 API 网关）

```
jdbc:clickzetta://<instance>.<service>/<workspace>?virtualCluster=<vcluster>&schema=<schema>
```

| 组成部分 | 说明 | 示例 |
|---------|------|------|
| `<instance>` | 实例 ID | `your_instance` |
| `<service>` | 服务地址（含区域前缀） | `cn-shanghai-alicloud.api.clickzetta.com` |
| `<workspace>` | 工作空间名 | `your_workspace` |
| `virtualCluster` | 虚拟集群名 | `default_ap` |
| `schema` | Schema 名 | `public` |

**完整示例**：

```
jdbc:clickzetta://your_instance.cn-shanghai-alicloud.api.clickzetta.com/your_workspace?virtualCluster=default_ap&schema=public
```

> **来源**：`sqlline_cz/clickzetta.properties` 中的实际 URL。

### 3.2 直连格式（Direct Service）

用于直接连接服务端口，跳过 API 网关：

```
jdbc:clickzetta://<host>:<port>/<workspace>?schema=<schema>&vcluster=<vcluster>&access_mode=direct_service
```

**完整示例**：

```
jdbc:clickzetta://21.47.94.153.204:8523/ql_test21_workspace?schema=ql_test21_schema&vcluster=cz_gp_ql_test21&access_mode=direct_service
```

> **来源**：`sqlline_cz/cz_perf_ql_21.properties` 中的实际配置。

### 3.3 URL 参数对照表

| 参数 | 标准模式 | 直连模式 | 说明 |
|------|---------|---------|------|
| `virtualCluster` | ✅ 使用 | — | 虚拟集群（标准模式参数名） |
| `vcluster` | — | ✅ 使用 | 虚拟集群（直连模式参数名） |
| `schema` | ✅ | ✅ | 目标 Schema |
| `access_mode` | 不需要 | `direct_service` | 连接模式 |

> ⚠️ **注意**：标准模式中虚拟集群参数名为 `virtualCluster`（驼峰命名），
> 直连模式中为 `vcluster`。与 Python SDK 的 `virtual_cluster` 均不同。

---

## 4. Driver 类名

```
com.clickzetta.client.jdbc.ClickZettaDriver
```

在代码中加载驱动：

```java
Class.forName("com.clickzetta.client.jdbc.ClickZettaDriver");
```

> 现代 JDBC 4.0+ 驱动支持自动发现（通过 `META-INF/services/java.sql.Driver`），
> 但显式加载可以确保兼容性。

---

## 5. Java 代码完整示例

### 5.1 基本查询

```java
import java.sql.*;

public class ClickZettaJDBCExample {
    public static void main(String[] args) throws Exception {
        String url = "jdbc:clickzetta://your_instance.cn-shanghai-alicloud.api.clickzetta.com"
                   + "/my_workspace"
                   + "?virtualCluster=default_ap&schema=public";
        String user = "my_user";
        String password = "my_password";

        // 加载驱动
        Class.forName("com.clickzetta.client.jdbc.ClickZettaDriver");

        try (Connection conn = DriverManager.getConnection(url, user, password);
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT * FROM my_table LIMIT 10")) {

            ResultSetMetaData meta = rs.getMetaData();
            int colCount = meta.getColumnCount();

            // 打印列名
            for (int i = 1; i <= colCount; i++) {
                System.out.print(meta.getColumnName(i) + "\t");
            }
            System.out.println();

            // 打印数据
            while (rs.next()) {
                for (int i = 1; i <= colCount; i++) {
                    System.out.print(rs.getString(i) + "\t");
                }
                System.out.println();
            }
        }
    }
}
```

### 5.2 使用 Properties 对象

```java
import java.sql.*;
import java.util.Properties;

public class ClickZettaPropsExample {
    public static void main(String[] args) throws Exception {
        String url = "jdbc:clickzetta://your_instance.cn-shanghai-alicloud.api.clickzetta.com"
                   + "/my_workspace"
                   + "?virtualCluster=default_ap&schema=public";

        Properties props = new Properties();
        props.setProperty("user", "my_user");
        props.setProperty("password", "my_password");

        Class.forName("com.clickzetta.client.jdbc.ClickZettaDriver");

        try (Connection conn = DriverManager.getConnection(url, props)) {
            // 使用 PreparedStatement 防止 SQL 注入
            String sql = "SELECT * FROM my_table WHERE id = ?";
            try (PreparedStatement pstmt = conn.prepareStatement(sql)) {
                pstmt.setInt(1, 42);
                try (ResultSet rs = pstmt.executeQuery()) {
                    while (rs.next()) {
                        System.out.println(rs.getString(1));
                    }
                }
            }
        }
    }
}
```

### 5.3 DDL 操作

```java
try (Connection conn = DriverManager.getConnection(url, user, password);
     Statement stmt = conn.createStatement()) {

    // 创建表
    stmt.execute("CREATE TABLE IF NOT EXISTS test_table ("
               + "  id BIGINT, "
               + "  name STRING, "
               + "  created_at TIMESTAMP"
               + ")");

    // 插入数据
    stmt.execute("INSERT INTO test_table VALUES (1, 'Alice', CURRENT_TIMESTAMP)");

    // 查询验证
    try (ResultSet rs = stmt.executeQuery("SELECT * FROM test_table")) {
        while (rs.next()) {
            System.out.printf("id=%d, name=%s, created_at=%s%n",
                rs.getLong("id"),
                rs.getString("name"),
                rs.getTimestamp("created_at"));
        }
    }
}
```

---

## 6. Properties 文件格式

ClickZetta JDBC 支持通过 `.properties` 文件配置连接参数，常用于 SQLLine 等工具。

### 6.1 标准连接配置

```properties
# clickzetta.properties — 标准 API 网关连接
url: jdbc:clickzetta://your_instance.cn-shanghai-alicloud.api.clickzetta.com/your_workspace?virtualCluster=default_ap&schema=public
driver: com.clickzetta.client.jdbc.ClickZettaDriver
user: my_user
password: my_password
```

> **来源**：`sqlline_cz/clickzetta.properties` 的实际格式。

### 6.2 直连配置

```properties
# cz_perf.properties — 直连服务端口
url: jdbc:clickzetta://21.47.94.153.204:8523/my_workspace?schema=my_schema&vcluster=my_vcluster&access_mode=direct_service
driver: com.clickzetta.client.jdbc.ClickZettaDriver
user: my_user
password: my_password
```

> **来源**：`sqlline_cz/cz_perf_ql_21.properties` 的实际格式。

### 6.3 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `url` | ✅ | JDBC 连接 URL |
| `driver` | ✅ | 驱动类全限定名，固定为 `com.clickzetta.client.jdbc.ClickZettaDriver` |
| `user` | ✅ | 用户名 |
| `password` | ✅ | 密码 |

> ⚠️ **格式注意**：properties 文件中使用冒号 `:` 或等号 `=` 作为分隔符均可。
> 实际代码中两种格式都有使用（`clickzetta.properties` 使用冒号+空格，
> `cz_perf_ql_21.properties` 使用冒号无空格）。

---

## 7. SQLLine 使用方法

[SQLLine](https://github.com/julianhyde/sqlline) 是一个基于 JDBC 的命令行 SQL 客户端。
ClickZetta 提供了预配置的 SQLLine 启动脚本。

### 7.1 环境准备

```bash
# 1. 确保 JAVA_HOME 已设置
export JAVA_HOME=/path/to/jdk

# 2. 下载 ClickZetta JDBC 驱动
cd sqlline_cz/
bash setup.sh

# 3. 目录结构应包含：
#    sqlline_cz/
#    ├── clickzetta.properties          # 连接配置
#    ├── clickzetta-java-*-shaded.jar   # JDBC 驱动
#    ├── sqlline-1.12.0-jar-with-dependencies.jar  # SQLLine
#    ├── sqlline                        # 启动脚本
#    └── log4j.properties              # 日志配置（可选）
```

### 7.2 使用 Properties 文件连接

```bash
# 使用默认配置文件
./sqlline -p clickzetta.properties

# 使用指定配置文件（如性能测试环境）
./sqlline -p cz_perf_ql_21.properties
```

### 7.3 使用命令行参数连接

```bash
./sqlline \
  -u "jdbc:clickzetta://your_instance.cn-shanghai-alicloud.api.clickzetta.com/my_workspace?virtualCluster=default_ap&schema=public" \
  -n my_user \
  -p my_password \
  -d com.clickzetta.client.jdbc.ClickZettaDriver
```

### 7.4 SQLLine 常用命令

| 命令 | 说明 |
|------|------|
| `!tables` | 列出所有表 |
| `!columns <table>` | 查看表结构 |
| `!describe <table>` | 描述表信息 |
| `!quit` | 退出 |
| `!help` | 帮助 |
| `!outputformat csv` | 切换输出为 CSV 格式 |
| `!outputformat table` | 切换输出为表格格式 |

### 7.5 启用调试日志

```bash
# 设置环境变量启用 debug 日志
export SQLLINE_DEBUG_ENABLE=TRUE
./sqlline -p clickzetta.properties

# 日志输出到 debug.log 和 error.log
```

> **来源**：`sqlline_cz/sqlline` 脚本中的环境变量检测：
> ```bash
> if [[ $SQLLINE_DEBUG_ENABLE == "TRUE" ]] || [[ $SQLLINE_DEBUG_ENABLE == "true" ]]; then
>     JAVA_OPTS="$JAVA_OPTS -Dlog4j.configuration=file:log4j.properties"
> fi
> ```

### 7.6 日志配置

`log4j.properties` 配置示例（来自 `sqlline_cz/log4j.properties`）：

```properties
# 根日志级别
log4j.rootLogger = info,D,E

# DEBUG 级别日志 → debug.log
log4j.appender.D = org.apache.log4j.FileAppender
log4j.appender.D.File = ./debug.log
log4j.appender.D.Append = true
log4j.appender.D.Threshold = DEBUG
log4j.appender.D.layout = org.apache.log4j.PatternLayout
log4j.appender.D.layout.ConversionPattern = %d{yyyy-MM-dd HH:mm:ss}  [ %t:%r ] - [ %p ]  %m%n

# ERROR 级别日志 → error.log
log4j.appender.E = org.apache.log4j.FileAppender
log4j.appender.E.File = ./error.log
log4j.appender.E.Append = true
log4j.appender.E.Threshold = ERROR
log4j.appender.E.layout = org.apache.log4j.PatternLayout
log4j.appender.E.layout.ConversionPattern = %d{yyyy-MM-dd HH:mm:ss}  [ %t:%r ] - [ %p ]  %m%n
```

---

## 8. BI 工具集成

### 8.1 通用 JDBC 配置

大多数 BI 工具（DBeaver、DataGrip、Tableau 等）支持自定义 JDBC 驱动：

1. **添加驱动 JAR**：将 `clickzetta-java-*-shaded.jar` 添加到工具的驱动目录
2. **配置驱动类**：`com.clickzetta.client.jdbc.ClickZettaDriver`
3. **填写 URL**：使用标准 JDBC URL 格式
4. **输入凭据**：用户名和密码

### 8.2 DBeaver 配置步骤

1. 菜单 → Database → Driver Manager → New
2. Driver Name: `ClickZetta`
3. Class Name: `com.clickzetta.client.jdbc.ClickZettaDriver`
4. URL Template: `jdbc:clickzetta://{host}/{database}?virtualCluster={server}&schema={schema}`
5. Libraries → Add File → 选择 `clickzetta-java-*-shaded.jar`
6. 创建新连接时选择 ClickZetta 驱动

---

## 9. 适用场景

| 场景 | 说明 |
|------|------|
| Java 应用集成 | 通过标准 JDBC API 在 Java 应用中查询数据 |
| SQLLine 命令行 | 交互式 SQL 执行和调试 |
| BI 工具连接 | DBeaver、DataGrip、Tableau 等通过 JDBC 连接 |
| ETL 工具 | 支持 JDBC 的 ETL 工具（如 Kettle、Talend） |
| 性能测试 | 使用直连模式进行性能基准测试 |
| Spring Boot | 配置为 DataSource 在 Spring 应用中使用 |

---

## 10. Spring Boot 集成示例

```yaml
# application.yml
spring:
  datasource:
    url: jdbc:clickzetta://your_instance.cn-shanghai-alicloud.api.clickzetta.com/my_workspace?virtualCluster=default_ap&schema=public
    username: my_user
    password: my_password
    driver-class-name: com.clickzetta.client.jdbc.ClickZettaDriver
```

---

## 11. 常见问题

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `ClassNotFoundException: com.clickzetta.client.jdbc.ClickZettaDriver` | JDBC 驱动 JAR 不在 classpath 中 | 确保 shaded JAR 在 classpath 中 |
| `java.lang.reflect.InaccessibleObjectException` | JDK 9+ 模块系统限制 | 添加 `--add-opens=java.base/java.nio=ALL-UNNAMED` |
| `Connection refused` | 服务地址或端口错误 | 检查 URL 中的 service 地址和端口 |
| `Authentication failed` | 用户名或密码错误 | 检查 user/password 配置 |
| `Workspace not found` | 工作空间名称错误 | 确认 URL 路径中的 workspace 名称 |
| `Virtual cluster not found` | 虚拟集群名称错误或参数名错误 | 标准模式用 `virtualCluster`，直连用 `vcluster` |

---

## 12. 与其他连接方式对比

| 特性 | JDBC | Python SDK | SQLAlchemy |
|------|------|-----------|------------|
| 语言 | Java | Python | Python |
| 驱动类型 | JDBC Type 4 | 原生 Python | 基于 Python SDK |
| 连接池 | 应用层管理 | 无内置 | 内置连接池 |
| BI 工具支持 | ✅ 广泛 | ❌ | ✅ 通过 SQLAlchemy |
| DataFrame API | ❌ | ❌ | ❌ |
| 适合场景 | Java 应用、BI 工具 | Python 脚本 | ORM、Web 框架 |

---

## 13. 交叉引用

- [主连接指南 §4.4](../SKILL.md) — JDBC 快速入门
- [Python SDK 参考](python-sdk.md) — Python 原生连接
- [SQLAlchemy 参考](sqlalchemy.md) — SQLAlchemy 集成
- [配置文件管理参考](config-file.md) — JSON 配置文件方式
