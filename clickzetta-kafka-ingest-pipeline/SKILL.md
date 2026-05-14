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

## 向导：收集必要信息

开始搭建 Kafka 管道前，先收集以下信息（一次性问完）：

> 为了搭建 Kafka 接入管道，需要确认：
>
> **1. Kafka 连接信息**：
>    - Bootstrap 地址（如 `kafka.example.com:9092`）
>    - Topic 名称
>    - 是否需要认证？（SASL 用户名/密码，或无认证）
>
> **2. 消息格式**：JSON / CSV / Avro？如果是 JSON，是否有嵌套结构需要解析？
>
> **3. 目标表**：写入 Lakehouse 的哪个 schema 和表名？表是否已存在？
>
> **4. 接入路径**（不确定可跳过，我来推荐）：
>    - READ_KAFKA Pipe（推荐，通用场景）
>    - Kafka 外部表 + Table Stream（需要保留原始消息或多个下游消费同一 Topic）
>
> **5. 批量写入频率**：多久批量写入一次？（默认 60 秒）

**如果用户已经提供了足够信息，直接进入工作流，不再重复询问。**

---

## 适用场景

- 将 Kafka Topic 数据持续导入 ClickZetta Lakehouse 表
- 需要近实时（分钟级）数据新鲜度
- Kafka 消息格式为 JSON / CSV / Avro
- 需要在导入前对 JSON 消息进行多层嵌套解析和转换
- 关键词：Kafka Pipe、read_kafka、Kafka 外部表、消息队列导入、Kafka 持续导入

## 两种接入路径

| 路径 | 适用场景 | 核心对象 |
|------|---------|---------|
| **READ_KAFKA Pipe**（推荐） | 通用场景，支持复杂 SQL 转换 | `CREATE PIPE ... AS COPY INTO ... FROM (SELECT ... FROM read_kafka(...))` |
| **Kafka 外部表 + Table Stream Pipe** | 需要先落原始数据再增量消费 | Kafka 外部表 → Table Stream → Pipe `INSERT INTO ... SELECT` |

**选择建议**：大多数场景用 READ_KAFKA Pipe 即可，更简洁高效。Kafka 外部表路径适合需要保留原始消息、多个下游消费同一 Topic 的场景。

## 前置依赖

- ClickZetta Lakehouse 账户，具备创建 Pipe、表、VCluster 等权限
- Kafka 集群网络可达（确认 bootstrap 地址和端口）
- 已知 Kafka Topic 名称和消息格式
- 认证信息（如需要）：SASL 用户名/密码
- **执行环境（满足其一即可，优先使用 cz-cli）**：
  - **cz-cli 路径**：已安装 cz-cli（`pip install cz-cli`），并完成 `cz-cli configure` 配置
  - **MCP 路径**：clickzetta-mcp-server 工具可用（`LH_execute_query`、`LH_show_object_list` 等）

## 环境探测（执行前必读）

在开始任何操作前，先判断当前执行环境：

**第一步：检测 cz-cli 是否可用**
```bash
cz-cli --version
```
- 若命令存在 → **走 cz-cli 路径**（见本文档末尾"cz-cli 替代路径"章节）
- 若命令不存在 → 继续检测 MCP

**第二步：检测 MCP 是否可用（仅在 cz-cli 不可用时）**

尝试调用 `LH_execute_query` 工具执行一条简单 SQL（如 `SELECT 1`）。
- 若工具存在于 tool list → **走 MCP 路径**（本文档默认路径）
- 若工具不存在 → 停止执行，提示用户：
  > "当前环境既无 cz-cli 也无 MCP 工具，请安装其中之一后重试。
  > cz-cli 安装：`pip install cz-cli`，然后运行 `cz-cli configure`
  > MCP 安装：参考 clickzetta-mcp-server 配置文档"

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

> ⚠️ **READ_KAFKA 使用位置参数（positional parameters）**，不支持 `=>` 命名参数语法。参数顺序固定，不可省略。

```sql
-- 无认证 Kafka（位置参数语法）
SELECT *
FROM read_kafka(
  'kafka.example.com:9092',  -- bootstrap_servers（必填）
  'orders',                   -- topic（必填）
  '',                         -- topic_pattern（保留，填空字符串）
  'test_explore',             -- group_id（必填）
  '',                         -- starting_offsets（探查时可填 'earliest'，或留空用默认 latest）
  '',                         -- ending_offsets（留空）
  '',                         -- starting_timestamp（留空）
  '',                         -- ending_timestamp（留空）
  'raw',                      -- key_format（目前只支持 raw）
  'raw',                      -- value_format（目前只支持 raw）
  0,                          -- max_errors
  MAP(
    'kafka.security.protocol', 'PLAINTEXT',
    'kafka.auto.offset.reset', 'earliest'
  )
)
LIMIT 10;

-- SASL_PLAINTEXT 认证
SELECT *
FROM read_kafka(
  'kafka.example.com:9092',
  'orders',
  '',
  'test_explore',
  '', '', '', '',
  'raw',
  'raw',
  0,
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

> **参数说明**：
> - 探查用的 `group_id` 建议用临时名称（如 `test_explore`），避免影响正式消费组
> - `kafka.auto.offset.reset` 在 MAP 中设置为 `'earliest'` 可读取历史数据
> - key 和 value 都是 binary 类型，需要 CAST 转换后使用
> - **多 Broker 地址格式**：用逗号分隔多个 broker，Pipe 会自动故障转移
>   - ✅ 推荐：`'broker1:9092,broker2:9092,broker3:9092'`（高可用）
>   - ⚠️ 单 broker：`'broker1:9092'`（无故障转移，不推荐生产使用）

### 步骤 2：探查 JSON 结构并确定目标表 Schema

Kafka 的 key 和 value 都是 binary 类型。用 `value::string` 转换后查看内容，用 `parse_json()` 解析 JSON：

```sql
-- 将 value 转为字符串查看原始内容
SELECT key::string, value::string
FROM read_kafka(
  'kafka.example.com:9092',
  'orders',
  '',
  'test_schema',
  '', '', '', '',
  'raw', 'raw', 0,
  MAP('kafka.security.protocol', 'PLAINTEXT', 'kafka.auto.offset.reset', 'earliest')
)
LIMIT 5;

-- 解析 JSON 字段（使用 parse_json）
SELECT
  j['order_id']::STRING AS order_id,
  j['user_id']::STRING AS user_id,
  j['amount']::DECIMAL(10,2) AS amount,
  j['status']::STRING AS status,
  timestamp_millis(j['created_at']::BIGINT) AS created_at
FROM (
  SELECT parse_json(value::string) AS j
  FROM read_kafka(
    'kafka.example.com:9092',
    'orders',
    '',
    'test_schema',
    '', '', '', '',
    'raw', 'raw', 0,
    MAP('kafka.security.protocol', 'PLAINTEXT', 'kafka.auto.offset.reset', 'earliest')
  )
  LIMIT 5
);

-- 多层嵌套 JSON 解析（逐层 parse_json 展开）
SELECT
  j['id']::STRING AS id,
  j['type']::STRING AS event_type,
  parse_json(j['event']::STRING)['action']::STRING AS action,
  parse_json(parse_json(j['event']::STRING)['payload']::STRING)['ref']::STRING AS ref
FROM (
  SELECT parse_json(value::string) AS j
  FROM read_kafka(
    'kafka.example.com:9092',
    'events',
    '',
    'test_nested',
    '', '', '', '',
    'raw', 'raw', 0,
    MAP('kafka.security.protocol', 'PLAINTEXT', 'kafka.auto.offset.reset', 'earliest')
  )
  LIMIT 5
);
```

> **最佳实践**：在 SELECT 中将所有嵌套 JSON 字符串都 `parse_json` 展开后再落表，避免下游查询重复计算。

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
-- ⚠️ 注意：ClickZetta 不支持 CREATE OR REPLACE PIPE，需用 CREATE PIPE 或先 DROP 再 CREATE
CREATE PIPE kafka_orders_pipe
  VIRTUAL_CLUSTER = 'pipe_kafka_vc'
  BATCH_INTERVAL_IN_SECONDS = '60'
  BATCH_SIZE_PER_KAFKA_PARTITION = '500000'
AS
COPY INTO ods.kafka_orders FROM (
  SELECT
    j['order_id']::STRING,
    j['user_id']::STRING,
    j['amount']::DECIMAL(10,2),
    j['status']::STRING,
    j['created_at']::TIMESTAMP,
    CAST(`timestamp` AS TIMESTAMP) AS __kafka_timestamp__
  FROM (
    SELECT `timestamp`, parse_json(value::string) AS j
    FROM read_kafka(
      'kafka.example.com:9092',  -- bootstrap_servers
      'orders',                   -- topic
      '',                         -- reserved
      'lakehouse_orders',         -- group_id（正式消费组名）
      '', '', '', '',             -- 位置参数留空，由 Pipe 自动管理
      'raw',                      -- key_format
      'raw',                      -- value_format
      0,                          -- max_errors
      MAP('kafka.security.protocol', 'PLAINTEXT')
    )
  )
);
```

> ⚠️ **Pipe 中 READ_KAFKA 的关键区别**：
> - 位置参数（starting_offsets 等）**必须留空**，由 Pipe 自动管理消费位点
> - 不要设置 `kafka.auto.offset.reset`（由 Pipe 的 `RESET_KAFKA_GROUP_OFFSETS` 参数控制）
> - group_id 使用正式名称（如 `lakehouse_orders`），Pipe 会持久化消费位点

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

> **注意**：Pipe 中的 read_kafka 位置参数（starting_offsets 等）必须留空，由 Pipe 自动管理消费位点。与独立使用 read_kafka 探查时不同。

### 步骤 6：验证 Pipe 运行状态

```sql
-- 查看 Pipe 详情
DESC PIPE EXTENDED kafka_orders_pipe;
-- 关键字段：pipe_execution_paused（是否暂停）、pipe_latency（延迟信息）

-- 查看目标表数据
SELECT COUNT(*) FROM ods.kafka_orders;
SELECT * FROM ods.kafka_orders LIMIT 10;

-- 查看加载历史（保留 7 天）
SELECT * FROM load_history('ods.kafka_orders')
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

-- 删除 Connection（⚠️ 注意：用 DROP CONNECTION，不是 DROP STORAGE CONNECTION）
DROP CONNECTION IF EXISTS kafka_conn;
```

### 步骤 2：创建 Kafka 外部表

```sql
-- ⚠️ 必须显式指定列定义，不能省略
-- ⚠️ offset 是保留字，必须用反引号转义
CREATE EXTERNAL TABLE kafka_orders_ext (
  topic STRING,
  partition INT,
  `offset` BIGINT,
  `timestamp` TIMESTAMP,
  timestamp_type STRING,
  headers STRING,
  key BINARY,
  value BINARY
)
USING KAFKA
OPTIONS (
  'group_id' = 'lakehouse_ext_orders',
  'topics' = 'orders',
  'starting_offset' = 'earliest'
)
CONNECTION kafka_conn;
```

> **注意**：
> - 列定义是**必须的**，不指定会报错 `failed to detect columns`
> - `offset` 和 `timestamp` 是保留字，定义和查询时都需要反引号转义
> - 删除外部表用 `DROP TABLE`（❌ `DROP EXTERNAL TABLE` 会报语法错误）
> - 删除 Connection 用 `DROP CONNECTION`（❌ `DROP STORAGE CONNECTION` 会报语法错误）

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
-- ⚠️ 注意：Table Stream Pipe 使用 INSERT INTO ... SELECT 语法，不是 COPY INTO
CREATE PIPE kafka_ext_orders_pipe
  VIRTUAL_CLUSTER = 'pipe_kafka_vc'
  BATCH_INTERVAL_IN_SECONDS = '60'
AS
INSERT INTO ods.kafka_orders_from_ext
SELECT
  GET_JSON_OBJECT(CAST(value AS STRING), '$.order_id') AS order_id,
  GET_JSON_OBJECT(CAST(value AS STRING), '$.user_id') AS user_id,
  CAST(GET_JSON_OBJECT(CAST(value AS STRING), '$.amount') AS DECIMAL(10,2)) AS amount,
  CAST(`timestamp` AS TIMESTAMP) AS kafka_ts
FROM kafka_orders_stream;
```

> **清理外部表**：使用 `DROP TABLE kafka_orders_ext`（不是 `DROP EXTERNAL TABLE`）

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
-- 修改 VCluster
ALTER PIPE kafka_orders_pipe SET VIRTUAL_CLUSTER = 'new_vc';

-- 修改 COPY_JOB_HINT
ALTER PIPE kafka_orders_pipe SET COPY_JOB_HINT = '{"cz.sql.split.kafka.strategy":"size","cz.mapper.kafka.message.size":"200000"}';
```

> ⚠️ **ALTER PIPE 支持的属性**（经验证）：
> - ✅ `PIPE_EXECUTION_PAUSED`
> - ✅ `VIRTUAL_CLUSTER`
> - ✅ `COPY_JOB_HINT`
> - ❌ `BATCH_INTERVAL_IN_SECONDS`（不支持修改，需删除重建 Pipe）
> - ❌ `BATCH_SIZE_PER_KAFKA_PARTITION`（不支持修改，需删除重建 Pipe）
>
> 每次 ALTER 只能修改一个属性。不支持修改 COPY/INSERT 语句逻辑，需删除重建。

### 修改 Pipe SQL 逻辑（需删除重建）

```sql
-- 1. 删除当前 Pipe
DROP PIPE kafka_orders_pipe;

-- 2. 重建 Pipe（不要设置 RESET_KAFKA_GROUP_OFFSETS，保持从上次位点继续）
-- ⚠️ 注意：ClickZetta 不支持 CREATE OR REPLACE PIPE，使用 CREATE PIPE
CREATE PIPE kafka_orders_pipe
  VIRTUAL_CLUSTER = 'pipe_kafka_vc'
  BATCH_INTERVAL_IN_SECONDS = '60'
AS
COPY INTO ods.kafka_orders FROM (
  SELECT
    j['order_id']::STRING,
    j['user_id']::STRING,
    j['amount']::DECIMAL(10,2),
    UPPER(j['status']::STRING),  -- 修改了转换逻辑
    j['created_at']::TIMESTAMP,
    CAST(`timestamp` AS TIMESTAMP) AS __kafka_timestamp__
  FROM (
    SELECT `timestamp`, parse_json(value::string) AS j
    FROM read_kafka(
      'kafka.example.com:9092',
      'orders',
      '',
      'lakehouse_orders',  -- 保持相同 group_id
      '', '', '', '',
      'raw', 'raw', 0,
      MAP('kafka.security.protocol', 'PLAINTEXT')
    )
  )
);
```

> **关键**：重建时保持相同的 `group_id`，且不设置 `RESET_KAFKA_GROUP_OFFSETS`，Pipe 会从上次消费位点继续。

---

## 生产调优

### 判断是否积压

多次执行 `DESC PIPE EXTENDED` 查看 `pipe_latency` 中的 `timeLag`：
- 在 0~90 秒波动 → 正常（60 秒新鲜度 + 一倍冗余）
- 持续上涨 → 积压，需调优

### 调优参数

| 问题 | 调优方向 | 操作 |
|------|---------|------|
| 每批读取不完一个周期的数据 | 增大 `BATCH_SIZE_PER_KAFKA_PARTITION` | 删除重建 Pipe 时设置更大的值（如 `BATCH_SIZE_PER_KAFKA_PARTITION = '1000000'`） |
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
SELECT parse_json(value::string)['id']::STRING, parse_json(value::string)['name']::STRING
FROM read_kafka(
  'kafka:9092', 'metrics', '', 'test',
  '', '', '', '', 'raw', 'raw', 0,
  MAP('kafka.security.protocol', 'PLAINTEXT', 'kafka.auto.offset.reset', 'earliest')
) LIMIT 5;

-- 2. 建表
CREATE TABLE ods.metrics (id STRING, name STRING, value DOUBLE, kafka_ts TIMESTAMP);

-- 3. 建 Pipe
CREATE PIPE metrics_pipe
  VIRTUAL_CLUSTER = 'pipe_vc'
  BATCH_INTERVAL_IN_SECONDS = '60'
AS
COPY INTO ods.metrics FROM (
  SELECT
    j['id']::STRING, j['name']::STRING, j['value']::DOUBLE,
    CAST(`timestamp` AS TIMESTAMP)
  FROM (
    SELECT `timestamp`, parse_json(value::string) AS j
    FROM read_kafka(
      'kafka:9092', 'metrics', '', 'cz_metrics',
      '', '', '', '', 'raw', 'raw', 0,
      MAP('kafka.security.protocol', 'PLAINTEXT')
    )
  )
);
```

### 场景 B：Kafka → ODS → DWD 实时 ETL

```sql
-- 1. Pipe 接入 ODS 层
CREATE PIPE kafka_events_pipe
  VIRTUAL_CLUSTER = 'pipe_vc'
  BATCH_INTERVAL_IN_SECONDS = '60'
AS
COPY INTO ods.events FROM (
  SELECT
    j['event_id']::STRING, j['user_id']::STRING, j['action']::STRING, j['ts']::TIMESTAMP
  FROM (
    SELECT parse_json(value::string) AS j
    FROM read_kafka(
      'kafka:9092', 'user_events', '', 'cz_events',
      '', '', '', '', 'raw', 'raw', 0,
      MAP('kafka.security.protocol', 'PLAINTEXT')
    )
  )
);

-- 2. Dynamic Table 清洗到 DWD 层
-- ⚠️ 注意：Dynamic Table 支持 CREATE OR REPLACE，与 Pipe 不同
CREATE OR REPLACE DYNAMIC TABLE dwd.events_clean
  REFRESH INTERVAL 1 MINUTE vcluster default
AS
SELECT event_id, user_id, UPPER(action) AS action, ts, DATE(ts) AS dt
FROM ods.events
WHERE event_id IS NOT NULL AND action IS NOT NULL;

-- 3. Dynamic Table 聚合到 DWS 层
CREATE OR REPLACE DYNAMIC TABLE dws.events_hourly
  REFRESH INTERVAL 5 MINUTE vcluster default
AS
SELECT DATE_TRUNC('hour', ts) AS hour, action, COUNT(*) AS cnt, COUNT(DISTINCT user_id) AS uv
FROM dwd.events_clean
GROUP BY 1, 2;
```

### 场景 C：SASL 认证 + 指定时间点消费

```sql
CREATE PIPE kafka_auth_pipe
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

## 故障排除

| 问题 | 排查方向 |
|------|---------|
| READ_KAFKA 语法报错 `Syntax error at or near '('` | ❌ 不要用 `TABLE(READ_KAFKA(...))` 或 `=>` 命名参数。✅ 正确：`FROM read_kafka('broker', 'topic', '', 'group', '', '', '', '', 'raw', 'raw', 0, MAP(...))` |
| READ_KAFKA 报错 `cannot resolve column` | 使用了 `=` 赋值语法（如 `KAFKA_BROKER = 'xxx'`）。READ_KAFKA 只支持位置参数 |
| READ_KAFKA 探查无数据 | 检查 broker 地址/端口、topic 名称、网络连通性；在 MAP 中设置 `'kafka.auto.offset.reset', 'earliest'` |
| Pipe 创建后无数据加载 | `DESC PIPE EXTENDED` 检查是否暂停；确认 group_id 的消费位点（默认 latest，新数据才会消费） |
| Table Stream Pipe 语法报错 `Syntax error at or near 'SELECT'` | ❌ 不要用 `COPY INTO ... SELECT`。✅ 正确：`INSERT INTO ... SELECT FROM stream` |
| `CREATE OR REPLACE PIPE` 报错 AlreadyExist | ❌ ClickZetta 不支持 `CREATE OR REPLACE PIPE`。Pipe 不存在时 `CREATE OR REPLACE` 会创建成功，但 Pipe 已存在时报 AlreadyExist 错误。✅ 正确：用 `DROP PIPE` + `CREATE PIPE` 重建（与 Dynamic Table 不同，DT 支持 `CREATE OR REPLACE`） |
| JSON 解析报错 | 使用 `parse_json(value::string)['field']::TYPE` 语法；嵌套 JSON 需逐层 `parse_json()` 展开 |
| SASL 认证失败 | 确认安全协议为 SASL_PLAINTEXT（不支持 SSL）；在 MAP 中设置 `kafka.sasl.mechanism`、`kafka.sasl.username`、`kafka.sasl.password` |
| 消费延迟持续增大 | 增大 `BATCH_SIZE_PER_KAFKA_PARTITION`；增大 VCluster 规格；使用 `COPY_JOB_HINT` 切分 task |
| 重建 Pipe 后数据重复 | 保持相同 group_id 且不设置 `RESET_KAFKA_GROUP_OFFSETS` |
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

---

## cz-cli 替代路径

> 仅在 cz-cli 可用且 MCP 不可用时使用本节。步骤编号与上方 MCP 路径对应。
> 所有操作通过 `cz-cli agent run` 委托给内置 agent 完成，agent 内置完整的 MCP 工具访问能力。

### 路径一：READ_KAFKA Pipe（cz-cli 版）

#### 步骤 1-2：验证 Kafka 连接和探查数据结构

```bash
cz-cli agent run "验证 Kafka 连接并探查数据结构：broker 地址 <kafka-host:9092>，topic <topic-name>，消费组 test_explore，从 earliest 开始读取 10 条消息，展示原始 JSON 内容和字段结构" \
  --format a2a --dangerously-skip-permissions
```

#### 步骤 3：创建目标表

```bash
cz-cli agent run "在 schema <my_schema> 下创建目标表 <table_name>，字段包括：<field1> <type1>, <field2> <type2>，以及 __kafka_timestamp__ TIMESTAMP 字段用于延迟监控" \
  --format a2a --dangerously-skip-permissions
```

#### 步骤 4：创建专用 VCluster（可选）

```bash
cz-cli agent run "创建名为 pipe_kafka_vc 的 GENERAL 类型 VCluster，大小 4，AUTO_SUSPEND_IN_SECOND 设为 0（常驻运行），用于 Kafka Pipe 专用" \
  --format a2a --dangerously-skip-permissions
```

#### 步骤 5：创建 Kafka Pipe

```bash
cz-cli agent run "创建 Kafka Pipe，名称 <pipe_name>，使用 VCluster pipe_kafka_vc，BATCH_INTERVAL_IN_SECONDS=60，从 Kafka broker <host:port> 的 topic <topic> 消费数据（消费组 <group_id>，JSON 格式），将字段 <field1>, <field2> 写入目标表 <schema>.<table>" \
  --format a2a --dangerously-skip-permissions
```

#### 步骤 6：验证 Pipe 运行状态

```bash
cz-cli agent run "查看 Pipe <pipe_name> 的详细状态，包括是否暂停、延迟信息，以及目标表 <schema>.<table> 的数据量和最近加载历史" \
  --format a2a --dangerously-skip-permissions
```

---

### 路径二：Kafka 外部表 + Table Stream Pipe（cz-cli 版）

#### 步骤 1-4：完整创建流程

```bash
# 步骤 1：创建 Kafka Storage Connection
cz-cli agent run "创建 Kafka Storage Connection，名称 kafka_conn，bootstrap servers 为 <kafka-host:9092>，安全协议 PLAINTEXT" \
  --format a2a --dangerously-skip-permissions

# 步骤 2：创建 Kafka 外部表
cz-cli agent run "创建 Kafka 外部表 kafka_<topic>_ext，使用 Connection kafka_conn，消费组 lakehouse_ext_<topic>，topic 为 <topic>，从 earliest 开始" \
  --format a2a --dangerously-skip-permissions

# 步骤 3：创建 Table Stream
cz-cli agent run "在 Kafka 外部表 kafka_<topic>_ext 上创建 APPEND_ONLY 模式的 Table Stream，名称 kafka_<topic>_stream" \
  --format a2a --dangerously-skip-permissions

# 步骤 4：创建目标表和 Pipe
cz-cli agent run "创建目标表 <schema>.<target_table>，然后创建 Pipe kafka_ext_<topic>_pipe，使用 VCluster pipe_kafka_vc，BATCH_INTERVAL_IN_SECONDS=60，从 Table Stream kafka_<topic>_stream 消费数据，解析 JSON value 字段写入目标表" \
  --format a2a --dangerously-skip-permissions
```

---

### 监控与运维（cz-cli 版）

```bash
# 查看 Pipe 延迟状态
cz-cli agent run "查看 Pipe <pipe_name> 的延迟信息，包括 timeLag 和 offsetLag，判断是否有积压" \
  --format a2a --dangerously-skip-permissions

# 暂停/恢复 Pipe
cz-cli agent run "暂停 Pipe <pipe_name>" \
  --format a2a --dangerously-skip-permissions

cz-cli agent run "恢复 Pipe <pipe_name>" \
  --format a2a --dangerously-skip-permissions

# 修改 Pipe 属性
cz-cli agent run "修改 Pipe <pipe_name> 的 BATCH_INTERVAL_IN_SECONDS 为 120" \
  --format a2a --dangerously-skip-permissions
```
