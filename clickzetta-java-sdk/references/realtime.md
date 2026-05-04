# RealtimeStream 实时写入参考

> 适合：Kafka 消费写入、高频实时数据接入（秒级可查）、主键表 CDC 写入

## Maven 依赖

```xml
<dependency>
    <groupId>com.clickzetta</groupId>
    <artifactId>clickzetta-java</artifactId>
    <version>1.3.1</version>
</dependency>
<dependency>
    <groupId>org.apache.kafka</groupId>
    <artifactId>kafka-clients</artifactId>
    <version>3.2.0</version>
</dependency>
```

## 使用限制

- 实时写入的数据可以秒级查询
- table stream、dynamic table 需等待约 **1 分钟**才能看到写入数据
- 表结构变更时，需停止任务，变更后约 **90 分钟**重新启动

## 操作模式

| 模式 | 适用表 | 可用 Operator |
|---|---|---|
| `RealTimeOperate.APPEND_ONLY` | 普通表 | `Stream.Operator.INSERT` |
| `RealTimeOperate.CDC` | 主键表 | `Stream.Operator.UPSERT`、`Stream.Operator.DELETE_IGNORE` |

## 普通表写入（APPEND_ONLY）

```java
// RealtimeStream URL 用 vcluster= 参数（注意：不是 virtualcluster=）
String url = MessageFormat.format(
    "jdbc:clickzetta://{0}/{1}?schema={2}&username={3}&password={4}&vcluster={5}",
    "your_instance.cn-shanghai-alicloud.api.clickzetta.com",
    workspace, schema, user, password, vc
);
Options options = Options.builder().withMutationBufferLinesNum(10).build();
ClickZettaClient client = ClickZettaClient.newBuilder().url(url).build();

RealtimeStream stream = client.newRealtimeStreamBuilder()
    .operate(RowStream.RealTimeOperate.APPEND_ONLY)
    .options(options)
    .schema(schema)
    .table("events")
    .build();

// ⚠️ RealtimeStream 用列名（不是索引）
Row row = stream.createRow(Stream.Operator.INSERT);
row.setValue("id", 1);
row.setValue("event", "{\"type\":\"click\"}");
stream.apply(row);
```

## 主键表写入（CDC 模式）

```java
// 建表（主键表）
// CREATE TABLE orders (`txid` STRING PRIMARY KEY, `amount` DOUBLE, `status` STRING);

RealtimeStream stream = client.newRealtimeStreamBuilder()
    .operate(RowStream.RealTimeOperate.CDC)
    .options(options)
    .schema(schema)
    .table("orders")
    .build();

// UPSERT：存在则更新，不存在则插入
Row row = stream.createRow(Stream.Operator.UPSERT);
row.setValue("txid", "order-001");
row.setValue("amount", 299.99);
row.setValue("status", "paid");
stream.apply(row);

// DELETE_IGNORE：删除，目标行不存在时自动忽略
Row delRow = stream.createRow(Stream.Operator.DELETE_IGNORE);
delRow.setValue("txid", "order-001");
stream.apply(delRow);
```

## 完整示例：Kafka → Lakehouse

### KafkaReader 类

```java
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import java.util.Collections;
import java.util.Properties;

public class KafkaReader {
    private KafkaConsumer<String, String> consumer;

    public KafkaReader() {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "test-group");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,
            "org.apache.kafka.common.serialization.StringDeserializer");
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,
            "org.apache.kafka.common.serialization.StringDeserializer");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "true");
        props.put(ConsumerConfig.AUTO_COMMIT_INTERVAL_MS_CONFIG, "1000");
        consumer = new KafkaConsumer<>(props);
    }

    public KafkaConsumer<String, String> readFromTopic(String topic) {
        consumer.subscribe(Collections.singleton(topic));
        return consumer;
    }
}
```

### Kafka2Lakehouse 主类

```java
import com.clickzetta.client.ClickZettaClient;
import com.clickzetta.client.RealtimeStream;
import com.clickzetta.client.RowStream;
import com.clickzetta.platform.client.api.Options;
import com.clickzetta.platform.client.api.Row;
import com.clickzetta.platform.client.api.Stream;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import java.text.MessageFormat;
import java.time.Duration;

public class Kafka2Lakehouse {
    private static ClickZettaClient client;
    private static final String password = "";
    private static final String table = "realtime_stream";
    private static final String workspace = "";
    private static final String schema = "public";
    private static final String user = "";
    private static final String vc = "default";
    static RealtimeStream realtimeStream;

    public static void main(String[] args) throws Exception {
        initialize();
        KafkaReader kafkaReader = new KafkaReader();
        final KafkaConsumer<String, String> consumer = kafkaReader.readFromTopic("lakehouse-stream");
        int i = 1;
        while (true) {
            ConsumerRecords<String, String> records = consumer.poll(Duration.ofSeconds(1));
            for (ConsumerRecord<String, String> record : records) {
                Row row = realtimeStream.createRow(Stream.Operator.INSERT);
                row.setValue("id", i++);
                row.setValue("event", record.value());
                realtimeStream.apply(row);
            }
        }
    }

    private static void initialize() throws Exception {
        String url = MessageFormat.format(
            "jdbc:clickzetta://{0}/{1}?schema={2}&username={3}&password={4}&vcluster={5}",
            "your_instance.cn-shanghai-alicloud.api.clickzetta.com",
            workspace, schema, user, password, vc
        );
        Options options = Options.builder().withMutationBufferLinesNum(10).build();
        client = ClickZettaClient.newBuilder().url(url).build();
        realtimeStream = client.newRealtimeStreamBuilder()
            .operate(RowStream.RealTimeOperate.APPEND_ONLY)
            .options(options)
            .schema(schema)
            .table(table)
            .build();
    }
}
```

## 关键 API

| API | 说明 |
|---|---|
| `realtimeStream.createRow(Stream.Operator.INSERT)` | 普通表插入行 |
| `realtimeStream.createRow(Stream.Operator.UPSERT)` | 主键表 upsert 行 |
| `realtimeStream.createRow(Stream.Operator.DELETE_IGNORE)` | 主键表删除行 |
| `row.setValue(String columnName, Object value)` | 按列名设值（不是索引） |
| `realtimeStream.apply(row)` | 发送行到服务端 |
| `Options.builder().withMutationBufferLinesNum(n)` | 设置缓冲行数（默认 10） |

## BulkloadStream vs RealtimeStream 对比

| 维度 | BulkloadStream | RealtimeStream |
|---|---|---|
| 列设值方式 | `setValue(int index, value)` | `setValue(String name, value)` |
| URL 参数 | `virtualcluster=` | `vcluster=` |
| createRow 参数 | 无参数 | `Stream.Operator.INSERT/UPSERT/DELETE_IGNORE` |
| 适用频率 | 低频（≥5 分钟/批） | 高频（秒级） |
| 数据可见延迟 | close() 后可见 | ~1 分钟后可见 |
| 主键表 | ❌ | ✅ CDC 模式 |

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 连接失败 | URL 参数名错误 | RealtimeStream 用 `vcluster=`，不是 `virtualcluster=` |
| 列名找不到 | 列名拼写错误 | 列名区分大小写，与建表 DDL 保持一致 |
| 表结构变更后写入失败 | 旧 Stream 实例缓存了旧 schema | 停止任务，变更后等约 90 分钟再重启 |
| dynamic table 看不到数据 | 实时写入有 ~1 分钟确认延迟 | 等待 1 分钟后再查询 |

## Maven 依赖

```xml
<dependency>
    <groupId>com.clickzetta</groupId>
    <artifactId>clickzetta-java</artifactId>
    <version>1.3.1</version>
</dependency>
<dependency>
    <groupId>org.apache.kafka</groupId>
    <artifactId>kafka-clients</artifactId>
    <version>3.2.0</version>
</dependency>
```

## 使用限制

- 实时写入的数据可以秒级查询
- table stream、dynamic table 需等待约 **1 分钟**才能看到写入数据
- 表结构变更时，需停止任务，变更后约 **90 分钟**重新启动

## 完整示例：Kafka → Lakehouse

### 建表

```sql
CREATE TABLE realtime_stream (id INT, event JSON);
```

### 步骤 1：KafkaReader 类

```java
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import java.util.Collections;
import java.util.Properties;

public class KafkaReader {
    private KafkaConsumer<String, String> consumer;

    public KafkaReader() {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "test-group");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,
            "org.apache.kafka.common.serialization.StringDeserializer");
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,
            "org.apache.kafka.common.serialization.StringDeserializer");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "true");
        props.put(ConsumerConfig.AUTO_COMMIT_INTERVAL_MS_CONFIG, "1000");
        consumer = new KafkaConsumer<>(props);
    }

    public KafkaConsumer<String, String> readFromTopic(String topic) {
        consumer.subscribe(Collections.singleton(topic));
        return consumer;
    }
}
```

### 步骤 2：Kafka2Lakehouse 主类

```java
import com.clickzetta.client.ClickZettaClient;
import com.clickzetta.client.RealtimeStream;
import com.clickzetta.client.RowStream;
import com.clickzetta.platform.client.api.Options;
import com.clickzetta.platform.client.api.Row;
import com.clickzetta.platform.client.api.Stream;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;

import java.text.MessageFormat;
import java.time.Duration;

public class Kafka2Lakehouse {
    private static ClickZettaClient client;
    private static final String password = "";
    private static final String table = "realtime_stream";
    private static final String workspace = "";
    private static final String schema = "public";
    private static final String user = "";
    private static final String vc = "default";
    static RealtimeStream realtimeStream;
    static KafkaReader kafkaReader;

    public static void main(String[] args) throws Exception {
        initialize();
        kafkaReader = new KafkaReader();
        final KafkaConsumer<String, String> consumer = kafkaReader.readFromTopic("lakehouse-stream");

        while (true) {
            int i = 1;
            try {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofSeconds(1));
                for (ConsumerRecord<String, String> record : records) {
                    Row row = realtimeStream.createRow(Stream.Operator.INSERT);
                    i++;
                    // ⚠️ RealtimeStream 用列名（不是索引）
                    row.setValue("id", i);
                    row.setValue("event", record.value());
                    realtimeStream.apply(row);
                }
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }
    }

    private static void initialize() throws Exception {
        // RealtimeStream URL 用 vcluster= 参数（注意：不是 virtualcluster=）
        String url = MessageFormat.format(
            "jdbc:clickzetta://{0}/{1}?schema={2}&username={3}&password={4}&vcluster={5}",
            "your_instance.cn-shanghai-alicloud.api.clickzetta.com",
            workspace, schema, user, password, vc
        );
        Options options = Options.builder().withMutationBufferLinesNum(10).build();
        client = ClickZettaClient.newBuilder().url(url).build();
        realtimeStream = client.newRealtimeStreamBuilder()
            .operate(RowStream.RealTimeOperate.APPEND_ONLY)
            .options(options)
            .schema(schema)
            .table(table)
            .build();
    }
}
```

## 关键 API

| API | 说明 |
|---|---|
| `realtimeStream.createRow(Stream.Operator.INSERT)` | 创建行对象，指定操作类型 |
| `row.setValue(String columnName, Object value)` | 按列名设值（不是索引） |
| `realtimeStream.apply(row)` | 发送行到服务端 |
| `Options.builder().withMutationBufferLinesNum(n)` | 设置缓冲行数（默认 10） |

## BulkloadStream vs RealtimeStream 对比

| 维度 | BulkloadStream | RealtimeStream |
|---|---|---|
| 列设值方式 | `setValue(int index, value)` | `setValue(String name, value)` |
| URL 参数 | `virtualcluster=` | `vcluster=` |
| createRow 参数 | 无参数 | `Stream.Operator.INSERT` |
| 适用频率 | 低频（≥5 分钟/批） | 高频（秒级） |
| 数据可见延迟 | close() 后可见 | ~1 分钟后可见 |
| 主键表 | ❌ | ❌ |

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 连接失败 | URL 参数名错误 | RealtimeStream 用 `vcluster=`，不是 `virtualcluster=` |
| 列名找不到 | 列名拼写错误 | 列名区分大小写，与建表 DDL 保持一致 |
| 表结构变更后写入失败 | 旧 Stream 实例缓存了旧 schema | 停止任务，变更后等约 90 分钟再重启 |
| dynamic table 看不到数据 | 实时写入有 ~1 分钟确认延迟 | 等待 1 分钟后再查询 |
