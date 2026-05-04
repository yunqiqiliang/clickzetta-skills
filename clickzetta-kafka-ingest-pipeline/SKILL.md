---
name: clickzetta-kafka-ingest-pipeline
description: |
  搭建 ClickZetta Lakehouse Kafka 数据接入管道，覆盖从连接验证、数据探查、目标表创建
  到 Pipe 持续导入的端到端工作流。支持两种接入路径：READ_KAFKA Pipe（推荐）和
  Kafka 外部表 + Table Stream Pipe。
  当用户说"Kafka 接入"、"Kafka 导入"、"Kafka Pipe"、"read_kafka"、"Kafka 数据管道"、
  "Kafka 外部表"、"Kafka 消费"、"消息队列导入"、"Kafka 到 Lakehouse"、
  "Kafka 实时导入"、"Kafka 持续导入"、"Kafka topic 导入"、"Kafka JSON 解析"、
  "Kafka 延迟监控"、"Kafka 积压"时触发。
  包含 READ_KAFKA 函数探查、JSON 多层嵌套解析、Kafka Pipe DDL、Kafka 外部表 + Table Stream、
  SASL 认证配置、生产调优（BATCH_SIZE / COPY_JOB_HINT / VCluster 规格）、
  延迟监控（pipe_latency / query_tag）等 ClickZetta 特有逻辑。
  Keywords: Kafka, READ_KAFKA, Pipe, streaming ingestion, topic, consumer
---

# Kafka 数据接入管道工作流

## 适用场景

- 将 Kafka Topic 数据持续导入 ClickZetta Lakehouse 表
- 需要近实时（分钟级）数据新鲜度
- Kafka 消息格式为 JSON / CSV / Avro
- 需要在导入前对 JSON 消息进行多层嵌套解析和转换
- 关键词：Kafka Pipe、read_kafka、Kafka 外部表、消息队列导入、Kafka 持续导入

## 两种接入路径

| 路径 | 适用场景 | 核心对象 |
|------|---------|---------|
| **READ_KAFKA Pipe**（推荐） | 通用场景，支持复杂 SQL 转换 | `CREATE PIPE ... AS INSERT INTO ... FROM TABLE(READ_KAFKA(...))` |
| **Kafka 外部表 + Table Stream Pipe** | 需要先落原始数据再增量消费 | Kafka 外部表 → Table Stream → Pipe COPY INTO |

**选择建议**：大多数场景用 READ_KAFKA Pipe 即可，更简洁高效。Kafka 外部表路径适合需要保留原始消息、多个下游消费同一 Topic 的场景。

## 前置依赖

- ClickZetta Lakehouse 账户，具备创建 Pipe、表、VCluster 等权限
- Kafka 集群网络可达（确认 bootstrap 地址和端口）
- 已知 Kafka Topic 名称和消息格式
- 认证信息（如需要）：SASL 用户名/密码

## ⚠️ 关键注意事项

- Kafka Pipe 仅支持 **PLAINTEXT** 和 **SASL_PLAINTEXT** 两种安全协议，不支持 SSL 证书方式
- Pipe 创建后**自动启动**，无需手动 RESUME
- Pipe 不支持修改 COPY 语句逻辑，需删除后重建
- 建议为 Kafka Pipe 分配**专用 GP 集群**，避免与其他查询争抢资源
- `RESET_KAFKA_GROUP_OFFSETS` 仅在创建时生效，会强制改写消费位点，谨慎使用

---

## 路径一：READ_KAFKA Pipe（推荐）

### 步骤 1：验证 Kafka 连接和探查数据

先用 `READ_KAFKA` 函数验证网络连通性和消息格式：

```sql
-- 无认证 Kafka
SELECT *
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'orders',
    KAFKA_GROUP_ID => 'test_explore',
    KAFKA_OFFSET => 'earliest',
    KAFKA_DATA_FORMAT => 'json'
  )
)
LIMIT 10;

-- SASL_PLAINTEXT 认证
SELECT *
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'orders',
    KAFKA_GROUP_ID => 'test_explore',
    KAFKA_OFFSET => 'earliest',
    KAFKA_DATA_FORMAT => 'json',
    KAFKA_SASL_USERNAME => 'my_user',
    KAFKA_SASL_PASSWORD => 'my_password'
  )
)
LIMIT 10;
```

> 探查用的 `KAFKA_GROUP_ID` 建议用临时名称（如 `test_explore`），避免影响正式消费组。

### 步骤 2：探查 JSON 结构并确定目标表 Schema

Kafka 的 key 和 value 都是 binary 类型。用 `$1` 引用整行 JSON，用 `$1:field::TYPE` 提取字段：

```sql
-- 将 value 转为字符串查看原始内容
SELECT CAST(value AS STRING) AS raw_value
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'orders',
    KAFKA_GROUP_ID => 'test_schema',
    KAFKA_OFFSET => 'earliest',
    KAFKA_DATA_FORMAT => 'json'
  )
)
LIMIT 5;

-- 提取 JSON 字段（单层）
SELECT
  $1:order_id::STRING AS order_id,
  $1:user_id::STRING AS user_id,
  $1:amount::DECIMAL(10,2) AS amount,
  $1:status::STRING AS status,
  $1:created_at::TIMESTAMP AS created_at
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'orders',
    KAFKA_GROUP_ID => 'test_schema',
    KAFKA_OFFSET => 'earliest',
    KAFKA_DATA_FORMAT => 'json'
  )
)
LIMIT 5;

-- 多层嵌套 JSON 解析（使用 PARSE_JSON 逐层展开）
SELECT
  $1:id::STRING AS id,
  $1:type::STRING AS event_type,
  PARSE_JSON($1:event::STRING):action::STRING AS action,
  PARSE_JSON(PARSE_JSON($1:event::STRING):payload::STRING):ref::STRING AS ref
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'events',
    KAFKA_GROUP_ID => 'test_nested',
    KAFKA_OFFSET => 'earliest',
    KAFKA_DATA_FORMAT => 'json'
  )
)
LIMIT 5;
```

> **最佳实践**：在 SELECT 中将所有嵌套 JSON 字符串都 `PARSE_JSON` 展开后再落表，避免下游查询重复计算。

### 步骤 3：创建目标表

根据探查结果创建目标表：

```sql
CREATE TABLE IF NOT EXISTS ods.kafka_orders (
    order_id    STRING,
    user_id     STRING,
    amount      DECIMAL(10,2),
    status      STRING,
    created_at  TIMESTAMP,
    __kafka_timestamp__ TIMESTAMP COMMENT 'Kafka 消息时间戳，用于端到端延迟监控'
);
```

> 建议额外添加 `__kafka_timestamp__` 字段记录 Kafka 消息时间戳，用于后续端到端延迟监控。

### 步骤 4：创建专用 VCluster（推荐）

```sql
CREATE VCLUSTER IF NOT EXISTS pipe_kafka_vc
  VCLUSTER_TYPE = GENERAL
  VCLUSTER_SIZE = 4
  AUTO_SUSPEND_IN_SECOND = 0
  COMMENT 'Kafka Pipe 专用集群，常驻运行';
```

> 数据新鲜度要求 1 分钟时，建议 VCluster 常驻（`AUTO_SUSPEND_IN_SECOND = 0`），避免冷启动延迟。

### 步骤 5：创建 Kafka Pipe

```sql
CREATE OR REPLACE PIPE kafka_orders_pipe
  VIRTUAL_CLUSTER = pipe_kafka_vc
  BATCH_INTERVAL_IN_SECONDS = 60
  BATCH_SIZE_PER_KAFKA_PARTITION = 500000
AS
INSERT INTO ods.kafka_orders (order_id, user_id, amount, status, created_at, __kafka_timestamp__)
SELECT
  $1:order_id::STRING,
  $1:user_id::STRING,
  $1:amount::DECIMAL(10,2),
  $1:status::STRING,
  $1:created_at::TIMESTAMP,
  CAST(timestamp AS TIMESTAMP)
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'orders',
    KAFKA_GROUP_ID => 'lakehouse_orders',
    KAFKA_DATA_FORMAT => 'json'
  )
);
```

**关键参数说明：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `VIRTUAL_CLUSTER` | — | 必填，指定执行 Pipe 的计算集群 |
| `BATCH_INTERVAL_IN_SECONDS` | 60 | 批处理间隔（秒），即数据新鲜度 |
| `BATCH_SIZE_PER_KAFKA_PARTITION` | 500000 | 每个 Kafka 分区每批最大消息数 |
| `MAX_SKIP_BATCH_COUNT_ON_ERROR` | 30 | 出错时跳过批次的最大重试次数 |
| `INITIAL_DELAY_IN_SECONDS` | 0 | 首个作业调度延迟 |
| `RESET_KAFKA_GROUP_OFFSETS` | — | 可选，指定起始消费位点（仅创建时生效） |

**RESET_KAFKA_GROUP_OFFSETS 可选值：**

| 值 | 说明 |
|----|------|
| `'none'` | 无操作，使用 Kafka 的 `auto.offset.reset` 配置（默认 latest） |
| `'valid'` | 检查当前位点是否过期，将过期分区重置到 earliest |
| `'earliest'` | 重置到最早位点（消费全部历史数据） |
| `'latest'` | 重置到最新位点（仅消费新数据） |
| `'1737789688000'` | 重置到指定毫秒时间戳对应的位点 |

> **注意**：Pipe 中的 READ_KAFKA 不要设置 `KAFKA_OFFSET` 参数（由 Pipe 自动管理消费位点），与独立使用 READ_KAFKA 探查时不同。

### 步骤 6：验证 Pipe 运行状态

```sql
-- 查看 Pipe 详情
DESC PIPE EXTENDED kafka_orders_pipe;
-- 关键字段：pipe_execution_paused（是否暂停）、pipe_latency（延迟信息）

-- 查看目标表数据
SELECT COUNT(*) FROM ods.kafka_orders;
SELECT * FROM ods.kafka_orders LIMIT 10;

-- 查看加载历史（保留 7 天）
SELECT * FROM TABLE(load_history('ods.kafka_orders'))
ORDER BY last_load_time DESC
LIMIT 20;

-- 通过 query_tag 查看 Pipe 作业
SHOW JOBS WHERE query_tag = 'pipe.my_workspace.ods.kafka_orders_pipe';
```

---

## 路径二：Kafka 外部表 + Table Stream Pipe

适合需要保留原始消息、或多个下游消费同一 Topic 的场景。

### 步骤 1：创建 Kafka Storage Connection

```sql
CREATE STORAGE CONNECTION IF NOT EXISTS kafka_conn
  TYPE KAFKA
  BOOTSTRAP_SERVERS = ['kafka.example.com:9092']
  SECURITY_PROTOCOL = 'PLAINTEXT';
```

### 步骤 2：创建 Kafka 外部表

```sql
CREATE EXTERNAL TABLE kafka_orders_ext
  USING KAFKA
  OPTIONS (
    'group_id' = 'lakehouse_ext_orders',
    'topics' = 'orders',
    'starting_offset' = 'earliest'
  )
  CONNECTION kafka_conn;
```

外部表固定字段：`topic`、`partition`、`offset`、`timestamp`、`timestamp_type`、`headers`、`key`（BINARY）、`value`（BINARY）

### 步骤 3：创建 Table Stream

```sql
CREATE TABLE STREAM kafka_orders_stream
  ON TABLE kafka_orders_ext
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'APPEND_ONLY');
```

### 步骤 4：创建目标表和 Pipe

```sql
-- 目标表
CREATE TABLE IF NOT EXISTS ods.kafka_orders_from_ext (
    order_id   STRING,
    user_id    STRING,
    amount     DECIMAL(10,2),
    kafka_ts   TIMESTAMP
);

-- Pipe（从 Table Stream 消费）
CREATE PIPE kafka_ext_orders_pipe
  VIRTUAL_CLUSTER = pipe_kafka_vc
  BATCH_INTERVAL_IN_SECONDS = 60
AS
COPY INTO ods.kafka_orders_from_ext
SELECT
  GET_JSON_OBJECT(CAST(value AS STRING), '$.order_id') AS order_id,
  GET_JSON_OBJECT(CAST(value AS STRING), '$.user_id') AS user_id,
  CAST(GET_JSON_OBJECT(CAST(value AS STRING), '$.amount') AS DECIMAL(10,2)) AS amount,
  CAST(timestamp AS TIMESTAMP) AS kafka_ts
FROM kafka_orders_stream;
```

---

## 监控与运维

### 查看 Kafka 消费延迟

```sql
DESC PIPE EXTENDED kafka_orders_pipe;
```

关键字段 `pipe_latency`（JSON 格式）：
- `lastConsumeTimestamp`：上一次消费的位点时间
- `offsetLag`：Kafka 数据堆积量
- `timeLag`：消费延迟（毫秒），当前时间减去上一次消费位点。异常时为 -1

> 当数据新鲜度为 60 秒且算力冗余一倍时，`timeLag` 应在 0~90 秒之间波动。持续上涨说明 Pipe 积压。

### 端到端延迟监控（需要 `__kafka_timestamp__` 字段）

```sql
-- 查看最近 1 小时的端到端延迟
SELECT
  MAX(DATEDIFF('second', __kafka_timestamp__, CURRENT_TIMESTAMP())) AS max_delay_seconds,
  AVG(DATEDIFF('second', __kafka_timestamp__, CURRENT_TIMESTAMP())) AS avg_delay_seconds
FROM ods.kafka_orders
WHERE __kafka_timestamp__ >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR;
```

### 暂停 / 恢复 Pipe

```sql
-- 暂停
ALTER PIPE kafka_orders_pipe SET PIPE_EXECUTION_PAUSED = true;

-- 恢复
ALTER PIPE kafka_orders_pipe SET PIPE_EXECUTION_PAUSED = false;
```

### 修改 Pipe 属性

```sql
-- 修改批处理间隔
ALTER PIPE kafka_orders_pipe SET BATCH_INTERVAL_IN_SECONDS = 120;

-- 修改每分区批大小
ALTER PIPE kafka_orders_pipe SET BATCH_SIZE_PER_KAFKA_PARTITION = 1000000;

-- 修改 VCluster
ALTER PIPE kafka_orders_pipe SET VIRTUAL_CLUSTER = 'new_vc';
```

> 每次 ALTER 只能修改一个属性。不支持修改 COPY/INSERT 语句逻辑，需删除重建。

### 修改 Pipe SQL 逻辑（需删除重建）

```sql
-- 1. 删除当前 Pipe
DROP PIPE kafka_orders_pipe;

-- 2. 重建 Pipe（不要设置 RESET_KAFKA_GROUP_OFFSETS，保持从上次位点继续）
CREATE PIPE kafka_orders_pipe
  VIRTUAL_CLUSTER = pipe_kafka_vc
  BATCH_INTERVAL_IN_SECONDS = 60
AS
INSERT INTO ods.kafka_orders (order_id, user_id, amount, status, created_at, __kafka_timestamp__)
SELECT
  $1:order_id::STRING,
  $1:user_id::STRING,
  $1:amount::DECIMAL(10,2),
  UPPER($1:status::STRING),  -- 修改了转换逻辑
  $1:created_at::TIMESTAMP,
  CAST(timestamp AS TIMESTAMP)
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'orders',
    KAFKA_GROUP_ID => 'lakehouse_orders',  -- 保持相同 group_id
    KAFKA_DATA_FORMAT => 'json'
  )
);
```

> **关键**：重建时保持相同的 `KAFKA_GROUP_ID`，且不设置 `RESET_KAFKA_GROUP_OFFSETS`，Pipe 会从上次消费位点继续。

---

## 生产调优

### 判断是否积压

多次执行 `DESC PIPE EXTENDED` 查看 `pipe_latency` 中的 `timeLag`：
- 在 0~90 秒波动 → 正常（60 秒新鲜度 + 一倍冗余）
- 持续上涨 → 积压，需调优

### 调优参数

| 问题 | 调优方向 | 操作 |
|------|---------|------|
| 每批读取不完一个周期的数据 | 增大 `BATCH_SIZE_PER_KAFKA_PARTITION` | `ALTER PIPE ... SET BATCH_SIZE_PER_KAFKA_PARTITION = 1000000` |
| 作业需要多轮才能完成 | 增大 VCluster 规格（使 core 数 ≥ partition 数） | `ALTER VCLUSTER ... SET VCLUSTER_SIZE = 16` |
| partition 少但数据量大 | 按条数切分 task | `ALTER PIPE ... SET COPY_JOB_HINT = '{"cz.sql.split.kafka.strategy":"size","cz.mapper.kafka.message.size":"200000"}'` |

### COPY_JOB_HINT 参数

| Key | 默认值 | 说明 |
|-----|--------|------|
| `cz.sql.split.kafka.strategy` | `simple` | `simple`=每 partition 一个 task；`size`=按条数切分 |
| `cz.mapper.kafka.message.size` | `1000000` | 当 strategy=size 时，每个 task 处理的消息条数 |

> ⚠️ **格式要求**：`COPY_JOB_HINT` 必须是合法 JSON，键值都要用双引号包围：
> ```sql
> -- ✅ 正确
> ALTER PIPE my_pipe SET COPY_JOB_HINT = '{"cz.sql.split.kafka.strategy":"size","cz.mapper.kafka.message.size":"200000"}';
> -- ❌ 错误（非 JSON 格式）
> ALTER PIPE my_pipe SET COPY_JOB_HINT = 'cz.sql.split.kafka.strategy=size';
> ```
> 修改 `COPY_JOB_HINT` 会覆盖所有已有 hints，需一次性设置全部参数。

---

## 典型场景

### 场景 A：简单 JSON Topic 接入

```sql
-- 1. 探查
SELECT $1:id::STRING, $1:name::STRING, $1:value::DOUBLE
FROM TABLE(READ_KAFKA(
  KAFKA_BROKER => 'kafka:9092', KAFKA_TOPIC => 'metrics',
  KAFKA_GROUP_ID => 'test', KAFKA_OFFSET => 'earliest', KAFKA_DATA_FORMAT => 'json'
)) LIMIT 5;

-- 2. 建表
CREATE TABLE ods.metrics (id STRING, name STRING, value DOUBLE, kafka_ts TIMESTAMP);

-- 3. 建 Pipe
CREATE PIPE metrics_pipe VIRTUAL_CLUSTER = pipe_vc AS
INSERT INTO ods.metrics
SELECT $1:id::STRING, $1:name::STRING, $1:value::DOUBLE, CAST(timestamp AS TIMESTAMP)
FROM TABLE(READ_KAFKA(
  KAFKA_BROKER => 'kafka:9092', KAFKA_TOPIC => 'metrics',
  KAFKA_GROUP_ID => 'cz_metrics', KAFKA_DATA_FORMAT => 'json'
));
```

### 场景 B：Kafka → ODS → DWD 实时 ETL

```sql
-- 1. Pipe 接入 ODS 层
CREATE PIPE kafka_events_pipe VIRTUAL_CLUSTER = pipe_vc AS
INSERT INTO ods.events (event_id, user_id, action, ts)
SELECT $1:event_id::STRING, $1:user_id::STRING, $1:action::STRING, $1:ts::TIMESTAMP
FROM TABLE(READ_KAFKA(
  KAFKA_BROKER => 'kafka:9092', KAFKA_TOPIC => 'user_events',
  KAFKA_GROUP_ID => 'cz_events', KAFKA_DATA_FORMAT => 'json'
));

-- 2. Dynamic Table 清洗到 DWD 层
CREATE OR REPLACE DYNAMIC TABLE dwd.events_clean
  REFRESH interval 1 MINUTE VCLUSTER default_ap
AS
SELECT event_id, user_id, UPPER(action) AS action, ts, DATE(ts) AS dt
FROM ods.events
WHERE event_id IS NOT NULL AND action IS NOT NULL;

-- 3. Dynamic Table 聚合到 DWS 层
CREATE OR REPLACE DYNAMIC TABLE dws.events_hourly
  REFRESH interval 5 MINUTE VCLUSTER default_ap
AS
SELECT DATE_TRUNC('hour', ts) AS hour, action, COUNT(*) AS cnt, COUNT(DISTINCT user_id) AS uv
FROM dwd.events_clean
GROUP BY 1, 2;
```

### 场景 C：SASL 认证 + 指定时间点消费

```sql
CREATE PIPE kafka_auth_pipe
  VIRTUAL_CLUSTER = pipe_vc
  BATCH_INTERVAL_IN_SECONDS = 60
  RESET_KAFKA_GROUP_OFFSETS = '1737789688000'
AS
INSERT INTO ods.secure_events (event_id, payload, kafka_ts)
SELECT $1:id::STRING, $1:payload::STRING, CAST(timestamp AS TIMESTAMP)
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'secure_events',
    KAFKA_GROUP_ID => 'cz_secure',
    KAFKA_DATA_FORMAT => 'json',
    KAFKA_SASL_USERNAME => 'my_user',
    KAFKA_SASL_PASSWORD => 'my_password'
  )
);
```

---

## 故障排除

| 问题 | 排查方向 |
|------|---------|
| READ_KAFKA 探查无数据 | 检查 broker 地址/端口、topic 名称、网络连通性；尝试 `KAFKA_OFFSET => 'earliest'` |
| Pipe 创建后无数据加载 | `DESC PIPE EXTENDED` 检查是否暂停；确认 group_id 的消费位点（默认 latest，新数据才会消费） |
| JSON 解析报错 | 检查 `$1:field::TYPE` 语法；嵌套 JSON 需先 `PARSE_JSON()` 展开 |
| SASL 认证失败 | 确认安全协议为 SASL_PLAINTEXT（不支持 SSL）；检查用户名密码 |
| 消费延迟持续增大 | 增大 `BATCH_SIZE_PER_KAFKA_PARTITION`；增大 VCluster 规格；使用 `COPY_JOB_HINT` 切分 task |
| 重建 Pipe 后数据重复 | 保持相同 `KAFKA_GROUP_ID` 且不设置 `RESET_KAFKA_GROUP_OFFSETS` |
| 重建 Pipe 后数据丢失 | 检查 group_id 的位点是否过期；如需回溯用 `RESET_KAFKA_GROUP_OFFSETS` 指定时间戳 |
| `COPY_JOB_HINT` 修改后参数丢失 | `SET COPY_JOB_HINT` 会覆盖所有已有 hints，需一次性设置全部参数 |
| Pipe 作业 Failover | 查看作业详情；通常为 Kafka 连接中断或 Lakehouse 服务升级，会自动恢复 |

---

## 参考文档

- [Pipe 简介](https://www.yunqi.tech/documents/pipe-summary)
- [借助 read_kafka 函数持续导入](https://www.yunqi.tech/documents/pipe-kafka)
- [借助 Kafka 外表 Table Stream 持续导入](https://www.yunqi.tech/documents/pipe-kafka-table-stream)
- [最佳实践：使用 Pipe 高效接入 Kafka 数据](https://www.yunqi.tech/documents/pipe-kafka-bestpractice-1)
- [read_kafka 函数](https://www.yunqi.tech/documents/read_kafka)
- [Kafka 外部表](https://www.yunqi.tech/documents/kafka-external-table)
- [Kafka Storage Connection](https://www.yunqi.tech/documents/Kafka_connection)
- [PIPE 导入语法](https://www.yunqi.tech/documents/pipe-syntax)
