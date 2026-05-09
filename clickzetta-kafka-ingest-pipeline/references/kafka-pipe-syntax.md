# Kafka Pipe SQL 语法参考

> 来源：https://www.yunqi.tech/documents/pipe-kafka 和 https://www.yunqi.tech/documents/pipe-kafka-bestpractice-1

> **⚠️ ClickZetta READ_KAFKA 使用位置参数（positional parameters）**
> - ❌ 不支持 `=>` 命名参数语法（如 `KAFKA_BROKER => 'host:port'`）
> - ❌ 不支持 `TABLE(READ_KAFKA(...))` 包装
> - ✅ 正确：`FROM read_kafka('broker', 'topic', '', 'group', '', '', '', '', 'raw', 'raw', 0, MAP(...))`

## CREATE PIPE（READ_KAFKA 方式）

```sql
CREATE [ OR REPLACE ] PIPE <pipe_name>
  VIRTUAL_CLUSTER = '<vcluster_name>'
  [ BATCH_INTERVAL_IN_SECONDS = '<seconds>' ]
  [ BATCH_SIZE_PER_KAFKA_PARTITION = '<count>' ]
  [ MAX_SKIP_BATCH_COUNT_ON_ERROR = '<count>' ]
  [ INITIAL_DELAY_IN_SECONDS = '<seconds>' ]
  [ RESET_KAFKA_GROUP_OFFSETS = '<offset_value>' ]
  [ COPY_JOB_HINT = '<json>' ]
AS
COPY INTO <target_table> FROM (
  SELECT <expr> [, ...]
  FROM read_kafka(
    '<bootstrap_servers>',   -- 位置 1：Kafka 集群地址（必填）
    '<topic_name>',          -- 位置 2：Topic 名称（必填）
    '',                      -- 位置 3：Topic pattern（保留，填空字符串）
    '<group_id>',            -- 位置 4：消费者组 ID（必填）
    '',                      -- 位置 5：starting_offsets（Pipe 中留空）
    '',                      -- 位置 6：ending_offsets（Pipe 中留空）
    '',                      -- 位置 7：starting_timestamp（Pipe 中留空）
    '',                      -- 位置 8：ending_timestamp（Pipe 中留空）
    'raw',                   -- 位置 9：key 格式（目前只支持 raw）
    'raw',                   -- 位置 10：value 格式（目前只支持 raw）
    0,                       -- 位置 11：max_errors
    MAP(<kafka_config>)      -- 位置 12：Kafka 配置参数
  )
);
```

### Pipe 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `VIRTUAL_CLUSTER` | 是 | — | 执行 Pipe 任务的计算集群 |
| `BATCH_INTERVAL_IN_SECONDS` | 否 | 60 | 批处理间隔（秒），即数据新鲜度 |
| `BATCH_SIZE_PER_KAFKA_PARTITION` | 否 | 500000 | 每个 Kafka 分区每批最大消息数 |
| `MAX_SKIP_BATCH_COUNT_ON_ERROR` | 否 | 30 | 出错时跳过批次的最大重试次数 |
| `INITIAL_DELAY_IN_SECONDS` | 否 | 0 | 首个作业调度延迟 |
| `RESET_KAFKA_GROUP_OFFSETS` | 否 | — | 启动时消费位点（仅创建时生效） |
| `COPY_JOB_HINT` | 否 | — | JSON 格式的作业参数 |

### RESET_KAFKA_GROUP_OFFSETS 可选值

| 值 | 说明 |
|----|------|
| `'none'` | 无操作，使用 Kafka `auto.offset.reset`（默认 latest） |
| `'valid'` | 检查当前位点是否过期，将过期分区重置到 earliest |
| `'earliest'` | 重置到最早位点 |
| `'latest'` | 重置到最新位点 |
| `'<毫秒时间戳>'` | 重置到指定时间戳对应位点（如 `'1737789688000'`） |

### READ_KAFKA 参数（在 Pipe 中 vs 独立使用）

| 特性 | 独立使用 read_kafka | 在 Pipe 中使用 |
|------|-------------------|---------------|
| 消费者组 | 临时，执行完即销毁 | 持久，保持消费位置 |
| 位置管理 | 在 MAP 中设置 `kafka.auto.offset.reset` | Pipe 自动管理，位置参数**必须留空** |
| 执行方式 | 一次性查询 | 持续调度执行 |
| 默认起始位置 | latest（可在 MAP 中改为 earliest） | latest（由 RESET_KAFKA_GROUP_OFFSETS 控制） |

### MAP 配置参数

| 参数 | 说明 |
|------|------|
| `kafka.security.protocol` | 安全协议：`PLAINTEXT` 或 `SASL_PLAINTEXT` |
| `kafka.sasl.mechanism` | SASL 机制：`PLAIN` |
| `kafka.sasl.username` | SASL 用户名 |
| `kafka.sasl.password` | SASL 密码 |
| `kafka.auto.offset.reset` | 独立探查时的起始位点（`earliest` / `latest`） |
| `cz.kafka.fetch.retry.enable` | 启用 fetch 重试（`true`/`false`） |
| `cz.kafka.fetch.retry.times` | 重试次数 |
| `cz.kafka.fetch.retry.intervalMs` | 重试间隔（毫秒） |

### JSON 字段提取语法

```sql
-- key 和 value 都是 binary 类型，需要先转换
value::string                                    -- 转为字符串
parse_json(value::string)                        -- 解析为 JSON 对象
parse_json(value::string)['field']::TYPE         -- 提取顶层字段
parse_json(value::string)['nested']['key']::TYPE -- 提取嵌套字段

-- 推荐模式：在子查询中先 parse_json，外层直接用 j['field']
SELECT j['order_id']::STRING, j['amount']::DECIMAL(10,2)
FROM (
  SELECT parse_json(value::string) AS j
  FROM read_kafka(...)
)
```

### 完整示例

```sql
-- 无认证 Kafka Pipe
CREATE PIPE kafka_orders_pipe
  VIRTUAL_CLUSTER = 'default'
  BATCH_INTERVAL_IN_SECONDS = '60'
AS
COPY INTO ods.orders FROM (
  SELECT
    j['order_id']::STRING AS order_id,
    j['user_id']::STRING AS user_id,
    j['amount']::DECIMAL(10,2) AS amount,
    CAST(`timestamp` AS TIMESTAMP) AS kafka_ts
  FROM (
    SELECT `timestamp`, parse_json(value::string) AS j
    FROM read_kafka(
      'kafka.example.com:9092',
      'orders',
      '',
      'lakehouse_orders',
      '', '', '', '',
      'raw', 'raw', 0,
      MAP('kafka.security.protocol', 'PLAINTEXT')
    )
  )
);

-- SASL 认证 + 指定时间点消费
CREATE PIPE kafka_secure_pipe
  VIRTUAL_CLUSTER = 'pipe_vc'
  BATCH_INTERVAL_IN_SECONDS = '60'
  RESET_KAFKA_GROUP_OFFSETS = '1737789688000'
AS
COPY INTO ods.secure_events FROM (
  SELECT
    j['id']::STRING AS event_id,
    j['payload']::STRING AS payload,
    CAST(`timestamp` AS TIMESTAMP) AS kafka_ts
  FROM (
    SELECT `timestamp`, parse_json(value::string) AS j
    FROM read_kafka(
      'kafka.example.com:9092',
      'secure_events',
      '',
      'cz_secure',
      '', '', '', '',
      'raw', 'raw', 0,
      MAP(
        'kafka.security.protocol', 'SASL_PLAINTEXT',
        'kafka.sasl.mechanism', 'PLAIN',
        'kafka.sasl.username', 'my_user',
        'kafka.sasl.password', 'my_password'
      )
    )
  )
);
```

---

## 独立探查（验证连接和数据格式）

```sql
-- 无认证
SELECT value::string
FROM read_kafka(
  'kafka.example.com:9092',
  'orders',
  '',
  'test_explore',
  '', '', '', '',
  'raw', 'raw', 0,
  MAP('kafka.security.protocol', 'PLAINTEXT', 'kafka.auto.offset.reset', 'earliest')
)
LIMIT 10;

-- SASL 认证
SELECT value::string
FROM read_kafka(
  'kafka.example.com:9092',
  'orders',
  '',
  'test_explore',
  '', '', '', '',
  'raw', 'raw', 0,
  MAP(
    'kafka.security.protocol', 'SASL_PLAINTEXT',
    'kafka.sasl.mechanism', 'PLAIN',
    'kafka.sasl.username', 'my_user',
    'kafka.sasl.password', 'my_password',
    'kafka.auto.offset.reset', 'earliest'
  )
)
LIMIT 10;
```

---

## CREATE PIPE（Kafka 外部表 + Table Stream 方式）

### 步骤 1：创建 Kafka Storage Connection

```sql
CREATE STORAGE CONNECTION IF NOT EXISTS <conn_name>
  TYPE KAFKA
  BOOTSTRAP_SERVERS = ['<host1>:<port1>', '<host2>:<port2>']
  SECURITY_PROTOCOL = 'PLAINTEXT';
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

固定字段：`topic`, `partition`, `offset`, `timestamp`, `timestamp_type`, `headers`, `key`(BINARY), `value`(BINARY)

### 步骤 3：创建 Table Stream

```sql
CREATE TABLE STREAM <stream_name>
  ON TABLE <ext_table_name>
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'APPEND_ONLY');
```

### 步骤 4：创建 Pipe

```sql
CREATE PIPE <pipe_name>
  VIRTUAL_CLUSTER = '<vcluster_name>'
  BATCH_INTERVAL_IN_SECONDS = '60'
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
ALTER PIPE <pipe_name> SET BATCH_INTERVAL_IN_SECONDS = '120';
ALTER PIPE <pipe_name> SET BATCH_SIZE_PER_KAFKA_PARTITION = '1000000';
ALTER PIPE <pipe_name> SET VIRTUAL_CLUSTER = 'new_vc';
ALTER PIPE <pipe_name> SET COPY_JOB_HINT = '{"cz.sql.split.kafka.strategy":"size","cz.mapper.kafka.message.size":"200000"}';
```

> 不支持修改 COPY/INSERT 语句逻辑，需删除 Pipe 后重建。
> 修改 `COPY_JOB_HINT` 会覆盖所有已有 hints，需一次性设置全部参数。

---

## 监控

```sql
-- 查看 Pipe 详情（含延迟信息 pipe_latency）
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
- [Kafka 外部表](https://www.yunqi.tech/documents/kafka-external-table)
- [Kafka Storage Connection](https://www.yunqi.tech/documents/Kafka_connection)
