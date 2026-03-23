# Pipe SQL 参考

> **⚠️ ClickZetta 特有语法**
> - Kafka 读取函数是 `READ_KAFKA(...)`，不是 `KAFKA_SOURCE(...)` 或其他写法
> - 参数使用 `=>` 命名参数语法：`KAFKA_BROKER => 'host:port'`
> - JSON 字段提取用 `$1:field_name::TYPE` 语法（`$1` 表示整行 JSON）
> - Pipe 创建后默认自动启动，无需手动 RESUME

Pipe 是 ClickZetta Lakehouse 的持续数据导入对象，通过 SQL 定义从 Kafka 或对象存储（OSS/S3/COS）自动、持续地将数据导入目标表，无需外部调度。

## CREATE PIPE — 从 Kafka 导入

```sql
CREATE [ OR REPLACE ] PIPE <pipe_name>
  [ COMMENT = '<comment>' ]
  [ AUTO_INGEST = { TRUE | FALSE } ]
AS
INSERT INTO <target_table> [ ( <col1>, <col2>, ... ) ]
SELECT <expr> [, ...]
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => '<broker_host>:<port>',
    KAFKA_TOPIC  => '<topic_name>',
    KAFKA_GROUP_ID => '<consumer_group>',
    KAFKA_OFFSET => '<earliest | latest | <offset_value>>',
    KAFKA_DATA_FORMAT => '<json | csv | avro>',
    [ KAFKA_SASL_USERNAME => '<username>', ]
    [ KAFKA_SASL_PASSWORD => '<password>', ]
    [ KAFKA_SCHEMA_REGISTRY_URL => '<url>' ]
  )
);
```

**示例：**
```sql
-- 从 Kafka 持续导入 JSON 数据
CREATE OR REPLACE PIPE kafka_orders_pipe
  COMMENT '从 Kafka 持续导入订单数据'
AS
INSERT INTO ods.orders (order_id, user_id, amount, created_at)
SELECT
  $1:order_id::STRING,
  $1:user_id::STRING,
  $1:amount::DECIMAL(10,2),
  $1:created_at::TIMESTAMP
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'orders',
    KAFKA_GROUP_ID => 'lakehouse_consumer',
    KAFKA_OFFSET => 'latest',
    KAFKA_DATA_FORMAT => 'json'
  )
);
```

## CREATE PIPE — 从对象存储导入

```sql
CREATE [ OR REPLACE ] PIPE [ IF NOT EXISTS ] <pipe_name>
  VIRTUAL_CLUSTER = <virtual_cluster_name>
  INGEST_MODE = { LIST_PURGE | EVENT_NOTIFICATION }
  [ COPY_JOB_HINT = '<hint>' ]
AS
COPY INTO <target_table>
FROM '@<volume_name>/<path>/'
FILE_FORMAT = ( TYPE = '<csv | parquet | orc | json>' )
[ PATTERN = '<regex>' ];
```

**关键参数：**
- `VIRTUAL_CLUSTER`：指定虚拟集群名称（OSS Pipe 必填）
- `INGEST_MODE = LIST_PURGE`：通用模式，定期扫描文件列表
- `INGEST_MODE = EVENT_NOTIFICATION`：事件通知模式，低延迟（仅阿里云 OSS + AWS S3）

**示例：**
```sql
-- 从 OSS Volume 持续导入 Parquet 文件
CREATE OR REPLACE PIPE oss_events_pipe
  VIRTUAL_CLUSTER = default_ap
  INGEST_MODE = LIST_PURGE
AS
COPY INTO ods.events
FROM '@my_oss_volume/events/'
FILE_FORMAT = ( TYPE = 'parquet' )
PATTERN = '.*\.parquet';
```

## 启停 Pipe

```sql
-- 暂停 Pipe
ALTER PIPE <pipe_name> SET PIPE_EXECUTION_PAUSED = true;

-- 恢复 Pipe
ALTER PIPE <pipe_name> SET PIPE_EXECUTION_PAUSED = false;
```

## DROP PIPE

```sql
DROP PIPE [ IF EXISTS ] <pipe_name>;
```

## SHOW PIPE

```sql
-- 列出当前 schema 下所有 Pipe
SHOW PIPES;

-- 按名称过滤
SHOW PIPES LIKE 'kafka%';

-- 查看 Pipe 详情
DESC PIPE <pipe_name>;
```

## 验证 Kafka 连接（创建 Pipe 前）

```sql
-- 先用 READ_KAFKA 函数验证连接和数据格式
SELECT *
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'orders',
    KAFKA_GROUP_ID => 'test_group',
    KAFKA_OFFSET => 'earliest',
    KAFKA_DATA_FORMAT => 'json'
  )
)
LIMIT 10;
```

## 注意事项

- Pipe 创建后默认自动启动，无需手动 RESUME
- Kafka Pipe 使用 consumer group 管理 offset，重建 Pipe 时注意 group_id 和 offset 设置
- 对象存储 Pipe 通过文件列表或事件通知（EVENT_NOTIFICATION）检测新文件，避免重复导入
- Pipe 不支持修改 AS 子句，需要 `CREATE OR REPLACE`

## 参考文档

- [PIPE 导入语法](https://www.yunqi.tech/documents/pipe-syntax)
- [Pipe 简介](https://www.yunqi.tech/documents/pipe-summary)
- [借助 read_kafka 函数持续导入](https://www.yunqi.tech/documents/pipe-kafka)
- [借助 Kafka 外表 Table Stream 持续导入](https://www.yunqi.tech/documents/pipe-kafka-table-stream)
- [最佳实践：使用 Pipe 高效接入 Kafka 数据](https://www.yunqi.tech/documents/pipe-kafka-bestpractice-1)
- [使用 Pipe 持续导入对象存储数据](https://www.yunqi.tech/documents/pipe-storage-object)
