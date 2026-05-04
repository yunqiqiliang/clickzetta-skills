---
name: clickzetta-java-sdk
description: |
  使用 ClickZetta Java SDK 将数据批量或实时写入 Lakehouse 表。
  覆盖 BulkloadStream（本地文件/数据库批量上传）和 RealtimeStream（Kafka 实时消费写入）
  两种接口的完整使用模式，包括 Maven 依赖、连接 URL 格式、行写入 API、
  状态监控、Options 调优和常见错误处理。
  当用户说"Java SDK"、"BulkloadStream"、"RealtimeStream"、
  "Java 写入 Lakehouse"、"Java 批量上传"、"Kafka Java 写入"、
  "clickzetta-java"、"Maven 依赖"、"Java 数据导入"时触发。
---

# ClickZetta Java SDK

Java SDK 提供两种写入接口：
- **BulkloadStream** — 批量写入，适合定时 ETL、本地文件导入（不支持主键表，不适合 5 分钟以内的高频写入）
- **RealtimeStream** — 实时写入，适合 Kafka 消费、流式数据接入（秒级可查）

阅读 [references/bulkload.md](references/bulkload.md) 了解批量写入，[references/realtime.md](references/realtime.md) 了解实时写入。

---

## Maven 依赖

```xml
<!-- clickzetta-java 最新版本见 https://central.sonatype.com/artifact/com.clickzetta/clickzetta-java -->
<dependency>
    <groupId>com.clickzetta</groupId>
    <artifactId>clickzetta-java</artifactId>
    <version>1.3.1</version>
</dependency>
```

RealtimeStream + Kafka 还需要：

```xml
<dependency>
    <groupId>org.apache.kafka</groupId>
    <artifactId>kafka-clients</artifactId>
    <version>3.2.0</version>
</dependency>
```

---

## 连接 URL 格式

```java
// BulkloadStream 用 virtualcluster 参数
String url = MessageFormat.format(
    "jdbc:clickzetta://{0}.{1}/{2}?schema={3}&username={4}&password={5}&virtualcluster={6}",
    instance, region_endpoint, workspace, schema, username, password, vcluster
);

// RealtimeStream 用 vcluster 参数（注意拼写不同）
String url = MessageFormat.format(
    "jdbc:clickzetta://{0}.{1}/{2}?schema={3}&username={4}&password={5}&vcluster={6}",
    instance, region_endpoint, workspace, schema, username, password, vcluster
);

ClickZettaClient client = ClickZettaClient.newBuilder().url(url).build();
```

---

## BulkloadStream 快速示例

```java
// 创建 BulkloadStream
BulkloadStream stream = client.newBulkloadStreamBuilder()
    .schema("public")
    .table("orders")
    .operate(RowStream.BulkLoadOperate.APPEND)
    .build();

// 写入数据（列索引从 0 开始，顺序与建表 DDL 一致）
Row row = stream.createRow();
row.setValue(0, "order-001");   // STRING
row.setValue(1, 1);             // INT
row.setValue(2, 299.99);        // DOUBLE
stream.apply(row);              // ⚠️ 必须调用，否则数据不发送到服务端

// 关闭并等待完成
stream.close();
while (stream.getState() == StreamState.RUNNING) {
    Thread.sleep(1000);
}
if (stream.getState() == StreamState.FAILED) {
    throw new RuntimeException(stream.getErrorMessage());
}
client.close();
```

---

## RealtimeStream 快速示例

```java
// Options 调优
Options options = Options.builder()
    .withMutationBufferLinesNum(10)  // 缓冲行数
    .build();

// 创建 RealtimeStream
RealtimeStream stream = client.newRealtimeStreamBuilder()
    .operate(RowStream.RealTimeOperate.APPEND_ONLY)
    .options(options)
    .schema("public")
    .table("events")
    .build();

// 写入数据（用列名，不用索引）
Row row = stream.createRow(Stream.Operator.INSERT);
row.setValue("id", 1);
row.setValue("event", "{\"type\":\"click\"}");
stream.apply(row);
```

---

## 选择指南

| 场景 | 推荐接口 |
|---|---|
| 定时批量 ETL（每小时/每天） | BulkloadStream |
| Kafka 实时消费 | RealtimeStream |
| 5 分钟以内高频写入 | RealtimeStream |
| 主键表写入 | ❌ 两者均不支持，改用 JDBC + MERGE |

---

## 使用限制

| 限制 | BulkloadStream | RealtimeStream |
|---|---|---|
| 主键表 | ❌ 不支持 | ❌ 不支持 |
| 高频写入（< 5 分钟） | ❌ 不适合 | ✅ 支持 |
| 数据可见延迟 | 写完 close() 后可见 | ~1 分钟后可见 |
| Table Stream/Dynamic Table 可见 | close() 后 | ~1 分钟后 |
| 表结构变更 | 重建 Stream | 停止任务，变更后约 90 分钟重启 |
