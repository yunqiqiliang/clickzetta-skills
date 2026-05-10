# Pipe SQL 参考

> **⚠️ ClickZetta 特有语法**
> - Kafka 读取函数是 `read_kafka(...)`，使用**位置参数**（不是命名参数 `=>`）
> - JSON 字段提取用 `parse_json(value::string)['field']::TYPE` 语法
> - Pipe 创建后默认自动启动，无需手动 RESUME
> - OSS Pipe 的 `PURGE=true` 紧跟在 `USING <format>` 之后（如 `USING CSV PURGE=true`）

Pipe 是 ClickZetta Lakehouse 的持续数据导入对象，通过 SQL 定义从 Kafka 或对象存储（OSS/S3/COS）自动、持续地将数据导入目标表，无需外部调度。

## CREATE PIPE — 从 Kafka 导入

```sql
CREATE [ OR REPLACE ] PIPE <pipe_name>
  VIRTUAL_CLUSTER = '<vcluster_name>'
  [ BATCH_INTERVAL_IN_SECONDS = '<seconds>' ]
  [ BATCH_SIZE_PER_KAFKA_PARTITION = '<count>' ]
  [ RESET_KAFKA_GROUP_OFFSETS = '<none|valid|earliest|latest|timestamp_ms>' ]
  [ COPY_JOB_HINT = '<json>' ]
AS
COPY INTO <target_table> FROM (
  SELECT <expr> [, ...]
  FROM read_kafka(
    '<bootstrap_servers>',   -- 必填：Kafka 集群地址
    '<topic>',               -- 必填：Topic 名称
    '',                      -- 保留（填空字符串）
    '<group_id>',            -- 必填：持久消费者组 ID
    '', '', '', '',          -- 位置参数留空，由 Pipe 自动管理
    'raw',                   -- key 格式（目前只支持 raw）
    'raw',                   -- value 格式（目前只支持 raw）
    0,                       -- max_errors
    MAP(<kafka_config>)      -- Kafka 配置参数
  )
);
```

**示例：**
```sql
-- 从 Kafka 持续导入 JSON 数据
CREATE OR REPLACE PIPE kafka_orders_pipe
  VIRTUAL_CLUSTER = 'default'
  BATCH_INTERVAL_IN_SECONDS = '60'
AS
COPY INTO ods.orders FROM (
  SELECT
    j['order_id']::STRING AS order_id,
    j['user_id']::STRING AS user_id,
    j['amount']::DECIMAL(10,2) AS amount,
    j['created_at']::TIMESTAMP AS created_at,
    CAST(`timestamp` AS TIMESTAMP) AS kafka_ts
  FROM (
    SELECT `timestamp`, parse_json(value::string) AS j
    FROM read_kafka(
      'kafka.example.com:9092',
      'orders',
      '',
      'lakehouse_consumer',
      '', '', '', '',
      'raw', 'raw', 0,
      MAP('kafka.security.protocol', 'PLAINTEXT')
    )
  )
);

-- SASL 认证
CREATE PIPE kafka_secure_pipe
  VIRTUAL_CLUSTER = 'pipe_vc'
  BATCH_INTERVAL_IN_SECONDS = '60'
AS
COPY INTO ods.secure_events FROM (
  SELECT parse_json(value::string)['id']::STRING AS id,
         CAST(`timestamp` AS TIMESTAMP) AS kafka_ts
  FROM read_kafka(
    'kafka.example.com:9092', 'secure_events', '', 'cz_secure',
    '', '', '', '', 'raw', 'raw', 0,
    MAP(
      'kafka.security.protocol', 'SASL_PLAINTEXT',
      'kafka.sasl.mechanism', 'PLAIN',
      'kafka.sasl.username', 'my_user',
      'kafka.sasl.password', 'my_password'
    )
  )
);
```

## 验证 Kafka 连接（创建 Pipe 前）

独立使用 `read_kafka` 探查数据时，可以在 MAP 中设置 `kafka.auto.offset.reset`：

```sql
-- 验证连接和数据格式
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
```

> ⚠️ **独立探查 vs Pipe 中的区别**：
> - 独立探查：可在 MAP 中设置 `kafka.auto.offset.reset` 为 `earliest` 读取历史数据
> - Pipe 中：位置参数必须留空，消费位点由 Pipe 的 `RESET_KAFKA_GROUP_OFFSETS` 参数控制

## CREATE PIPE — 从对象存储导入

```sql
CREATE [ OR REPLACE ] PIPE [ IF NOT EXISTS ] <pipe_name>
  VIRTUAL_CLUSTER = '<virtual_cluster_name>'
  INGEST_MODE = 'LIST_PURGE' | 'EVENT_NOTIFICATION'
  [ COPY_JOB_HINT = '<hint>' ]
AS
COPY INTO <target_table>
FROM VOLUME <volume_name>
USING <csv | parquet | orc | json> PURGE=true;
```

**关键参数：**
- `VIRTUAL_CLUSTER`：指定虚拟集群名称（OSS Pipe 必填）
- `INGEST_MODE = 'LIST_PURGE'`：通用模式，定期扫描文件列表，必须设置 `PURGE=true`
- `INGEST_MODE = 'EVENT_NOTIFICATION'`：事件通知模式，低延迟（仅阿里云 OSS + AWS S3），不需要 `PURGE=true`
- `PURGE=true`：紧跟在 `USING <format>` 之后（同一行），大写 PURGE，小写 true
- ⚠️ PIPE 不支持 COMMENT 子句
- ⚠️ PIPE 中的 COPY 语句不支持 OPTIONS 子句、`files`、`regexp`、`subdirectory` 参数

**示例：**
```sql
-- LIST_PURGE 模式（PURGE=true 紧跟 USING 之后）
CREATE OR REPLACE PIPE oss_events_pipe
  VIRTUAL_CLUSTER = 'default'
  INGEST_MODE = 'LIST_PURGE'
AS
COPY INTO ods.events
FROM VOLUME my_oss_volume
USING PARQUET PURGE=true;

-- CSV 格式（PIPE 中不支持 OPTIONS）
CREATE PIPE oss_csv_pipe
  VIRTUAL_CLUSTER = 'default'
  INGEST_MODE = 'LIST_PURGE'
AS
COPY INTO ods.csv_data
FROM VOLUME my_csv_volume
USING CSV PURGE=true;

-- EVENT_NOTIFICATION 模式（不需要 PURGE）
CREATE PIPE oss_event_pipe
  VIRTUAL_CLUSTER = 'default'
  INGEST_MODE = 'EVENT_NOTIFICATION'
  ALICLOUD_MNS_QUEUE = 'my-mns-queue-name'
AS
COPY INTO ods.events
FROM VOLUME my_oss_event_volume
USING PARQUET;
```

## 启停 Pipe

```sql
-- 暂停 Pipe
ALTER PIPE <pipe_name> SET PIPE_EXECUTION_PAUSED = true;

-- 恢复 Pipe
ALTER PIPE <pipe_name> SET PIPE_EXECUTION_PAUSED = false;
```

## 修改 Pipe 属性

```sql
-- 每次只能修改一个属性
ALTER PIPE <pipe_name> SET VIRTUAL_CLUSTER = 'new_vc';
ALTER PIPE <pipe_name> SET BATCH_INTERVAL_IN_SECONDS = '120';
ALTER PIPE <pipe_name> SET BATCH_SIZE_PER_KAFKA_PARTITION = '1000000';
ALTER PIPE <pipe_name> SET COPY_JOB_HINT = '{"cz.sql.split.kafka.strategy":"size","cz.mapper.kafka.message.size":"200000"}';
```

> ⚠️ 不支持修改 COPY/INSERT 语句逻辑，需删除 Pipe 后重建。
> ⚠️ `COPY_JOB_HINT` 修改会覆盖所有已有 hints，需一次性设置全部参数。

## DROP PIPE

```sql
DROP PIPE [ IF EXISTS ] <pipe_name>;
```

## SHOW PIPE

```sql
-- 列出当前 schema 下所有 Pipe
SHOW PIPES;

-- 查看 Pipe 详情（状态、延迟、定义）
DESC PIPE <pipe_name>;
DESC PIPE EXTENDED <pipe_name>;
```

## 注意事项

- Pipe 创建后默认自动启动，无需手动 RESUME
- Kafka Pipe 使用 consumer group 管理 offset，重建 Pipe 时保持相同 group_id 可从上次位点继续
- 对象存储 Pipe 通过文件列表或事件通知检测新文件，`load_history` 去重记录保留 7 天
- Pipe 不支持修改 AS 子句，需要删除后重建（不是 `CREATE OR REPLACE`）
- Kafka Pipe 仅支持 PLAINTEXT 和 SASL_PLAINTEXT 安全协议，不支持 SSL

## 参考文档

- [Pipe 简介](https://www.yunqi.tech/documents/pipe-summary)
- [借助 read_kafka 函数持续导入](https://www.yunqi.tech/documents/pipe-kafka)
- [借助 Kafka 外表 Table Stream 持续导入](https://www.yunqi.tech/documents/pipe-kafka-table-stream)
- [最佳实践：使用 Pipe 高效接入 Kafka 数据](https://www.yunqi.tech/documents/pipe-kafka-bestpractice-1)
- [使用 Pipe 持续导入对象存储数据](https://www.yunqi.tech/documents/pipe-storage-object)
