# Kafka Pipe SQL 语法参考

> 来源：https://www.yunqi.tech/documents/pipe-kafka 和 https://www.yunqi.tech/documents/pipe-kafka-bestpractice-1

## CREATE PIPE（READ_KAFKA 方式）

```sql
CREATE [ OR REPLACE ] PIPE <pipe_name>
  VIRTUAL_CLUSTER = <vcluster_name>
  [ BATCH_INTERVAL_IN_SECONDS = <seconds> ]
  [ BATCH_SIZE_PER_KAFKA_PARTITION = <count> ]
  [ MAX_SKIP_BATCH_COUNT_ON_ERROR = <count> ]
  [ INITIAL_DELAY_IN_SECONDS = <seconds> ]
  [ RESET_KAFKA_GROUP_OFFSETS = '<offset_value>' ]
AS
INSERT INTO <target_table> [ ( <col1>, <col2>, ... ) ]
SELECT <expr> [, ...]
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => '<broker_host>:<port>',
    KAFKA_TOPIC  => '<topic_name>',
    KAFKA_GROUP_ID => '<consumer_group>',
    KAFKA_DATA_FORMAT => '<json | csv | avro>',
    [ KAFKA_SASL_USERNAME => '<username>', ]
    [ KAFKA_SASL_PASSWORD => '<password>' ]
  )
);
```

### 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `VIRTUAL_CLUSTER` | 是 | — | 执行 Pipe 任务的计算集群 |
| `BATCH_INTERVAL_IN_SECONDS` | 否 | 60 | 批处理间隔（秒），即数据新鲜度 |
| `BATCH_SIZE_PER_KAFKA_PARTITION` | 否 | 500000 | 每个 Kafka 分区每批最大消息数 |
| `MAX_SKIP_BATCH_COUNT_ON_ERROR` | 否 | 30 | 出错时跳过批次的最大重试次数 |
| `INITIAL_DELAY_IN_SECONDS` | 否 | 0 | 首个作业调度延迟 |
| `RESET_KAFKA_GROUP_OFFSETS` | 否 | — | 启动时消费位点（仅创建时生效） |

### RESET_KAFKA_GROUP_OFFSETS 可选值

| 值 | 说明 |
|----|------|
| `'none'` | 无操作，使用 Kafka `auto.offset.reset`（默认 latest） |
| `'valid'` | 检查当前位点是否过期，将过期分区重置到 earliest |
| `'earliest'` | 重置到最早位点 |
| `'latest'` | 重置到最新位点 |
| `'<毫秒时间戳>'` | 重置到指定时间戳对应位点（如 `'1737789688000'`） |

### READ_KAFKA 参数（在 Pipe 中 vs 独立使用）

| 特性 | 独立使用 READ_KAFKA | 在 Pipe 中使用 |
|------|-------------------|---------------|
| 消费者组 | 临时，执行完即销毁 | 持久，保持消费位置 |
| 位置管理 | 手动指定 `KAFKA_OFFSET` | Pipe 自动管理，**不要设置** `KAFKA_OFFSET` |
| 执行方式 | 一次性查询 | 持续调度执行 |
| 默认起始位置 | earliest（探查历史数据） | latest（处理新数据） |

### JSON 字段提取语法

```sql
-- $1 表示整行 JSON
$1:field_name::TYPE              -- 提取顶层字段
$1:nested.field::TYPE            -- 提取嵌套字段（点号访问）
PARSE_JSON($1:field::STRING)     -- 将字符串字段解析为 JSON 对象
```

---

## CREATE PIPE（Kafka 外部表 + Table Stream 方式）

### 步骤 1：创建 Kafka Storage Connection

```sql
CREATE STORAGE CONNECTION IF NOT EXISTS <conn_name>
  TYPE KAFKA
  BOOTSTRAP_SERVERS = ['<host1>:<port1>', '<host2>:<port2>']
  SECURITY_PROTOCOL = '<PLAINTEXT | SASL_PLAINTEXT>';
```

### 步骤 2：创建 Kafka 外部表

```sql
CREATE EXTERNAL TABLE <ext_table_name>
  USING KAFKA
  OPTIONS (
    'group_id' = '<consumer_group>',
    'topics' = '<topic_name>',
    'starting_offset' = '<earliest | latest>'
  )
  CONNECTION <conn_name>;
```

固定字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| topic | STRING | Kafka 主题名称 |
| partition | INT | 分区 ID |
| offset | BIGINT | 分区内偏移量 |
| timestamp | TIMESTAMP_LTZ | 消息时间戳 |
| timestamp_type | STRING | 时间戳类型 |
| headers | MAP<STRING, BINARY> | 消息头 |
| key | BINARY | 消息键 |
| value | BINARY | 消息体 |

### 步骤 3：创建 Table Stream

```sql
CREATE TABLE STREAM <stream_name>
  ON TABLE <ext_table_name>
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'APPEND_ONLY');
```

### 步骤 4：创建 Pipe

```sql
CREATE PIPE <pipe_name>
  VIRTUAL_CLUSTER = <vcluster_name>
  [ BATCH_INTERVAL_IN_SECONDS = <seconds> ]
AS
COPY INTO <target_table>
SELECT <expr> [, ...]
FROM <stream_name>;
```

---

## ALTER PIPE

```sql
-- 暂停
ALTER PIPE <pipe_name> SET PIPE_EXECUTION_PAUSED = true;

-- 恢复
ALTER PIPE <pipe_name> SET PIPE_EXECUTION_PAUSED = false;

-- 修改属性（每次只能改一个）
ALTER PIPE <pipe_name> SET BATCH_INTERVAL_IN_SECONDS = 120;
ALTER PIPE <pipe_name> SET BATCH_SIZE_PER_KAFKA_PARTITION = 1000000;
ALTER PIPE <pipe_name> SET VIRTUAL_CLUSTER = 'new_vc';
ALTER PIPE <pipe_name> SET COPY_JOB_HINT = '{"cz.sql.split.kafka.strategy":"size","cz.mapper.kafka.message.size":"200000"}';
```

> 不支持修改 COPY/INSERT 语句逻辑，需删除 Pipe 后重建。
> 修改 `COPY_JOB_HINT` 会覆盖所有已有 hints，需一次性设置全部参数。

---

## 监控

```sql
-- 查看 Pipe 详情（含延迟信息）
DESC PIPE <pipe_name>;
DESC PIPE EXTENDED <pipe_name>;

-- 查看所有 Pipe
SHOW PIPES;

-- 查看加载历史
SELECT * FROM TABLE(load_history('<schema>.<table>'))
ORDER BY last_load_time DESC LIMIT 20;

-- 通过 query_tag 查看 Pipe 作业
-- 格式：pipe.<workspace_name>.<schema_name>.<pipe_name>
SHOW JOBS WHERE query_tag = 'pipe.my_workspace.ods.kafka_orders_pipe';
```

---

## DROP PIPE

```sql
DROP PIPE [ IF EXISTS ] <pipe_name>;
```

## 参考文档

- [Pipe 简介](https://www.yunqi.tech/documents/pipe-summary)
- [借助 read_kafka 函数持续导入](https://www.yunqi.tech/documents/pipe-kafka)
- [借助 Kafka 外表 Table Stream 持续导入](https://www.yunqi.tech/documents/pipe-kafka-table-stream)
- [最佳实践：使用 Pipe 高效接入 Kafka 数据](https://www.yunqi.tech/documents/pipe-kafka-bestpractice-1)
- [read_kafka 函数](https://www.yunqi.tech/documents/read_kafka)
- [Kafka 外部表](https://www.yunqi.tech/documents/kafka-external-table)
- [PIPE 导入语法](https://www.yunqi.tech/documents/pipe-syntax)
