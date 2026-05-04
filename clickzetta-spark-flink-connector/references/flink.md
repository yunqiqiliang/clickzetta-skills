# Flink Write Connector 详细参考

## Maven 依赖

```xml
<dependency>
    <groupId>com.clickzetta</groupId>
    <artifactId>igs-flink-connector-1.15</artifactId>  <!-- 按 Flink 版本替换 -->
    <version>联系 ClickZetta 支持获取版本号</version>
</dependency>
<!-- Flink 核心（provided） -->
<dependency>
    <groupId>org.apache.flink</groupId>
    <artifactId>flink-streaming-java</artifactId>
    <version>1.15.2</version>
    <scope>provided</scope>
</dependency>
<dependency>
    <groupId>org.apache.flink</groupId>
    <artifactId>flink-table-api-java-bridge</artifactId>
    <version>1.15.2</version>
    <scope>provided</scope>
</dependency>
```

## 两种写入模式

### 模式 1：igs-dynamic-table（CDC，支持主键表）

```sql
-- 目标表必须有主键
CREATE TABLE lakehouse_orders_sink (
    order_id   INT,
    customer   STRING,
    amount     DOUBLE,
    status     STRING,
    updated_at TIMESTAMP(3),
    PRIMARY KEY (order_id) NOT ENFORCED
) WITH (
    'connector'        = 'igs-dynamic-table',
    'curl'             = 'jdbc:clickzetta://your_instance.cn-shanghai-alicloud.api.clickzetta.com/default?username=user&password=***&schema=public&virtualcluster=default_ap',
    'schema-name'      = 'public',
    'table-name'       = 'orders',
    'sink.parallelism' = '1',          -- 主键表必须为 1
    'properties'       = 'authentication:true'
);
```

### 模式 2：igs-dynamic-table-append-only（仅追加，无主键表）

```sql
CREATE TABLE lakehouse_events_sink (
    event_id   BIGINT,
    user_id    BIGINT,
    event_type STRING,
    event_time TIMESTAMP(3)
) WITH (
    'connector'        = 'igs-dynamic-table-append-only',
    'curl'             = 'jdbc:clickzetta://your_instance.cn-shanghai-alicloud.api.clickzetta.com/default?username=user&password=***&schema=public&virtualcluster=default_ap',
    'schema-name'      = 'public',
    'table-name'       = 'events',
    'sink.parallelism' = '4',          -- 无主键表可提高并行度
    'properties'       = 'authentication:true'
);
```

## 完整 CDC 同步示例（MySQL → Lakehouse）

```sql
-- 1. MySQL CDC 源表
CREATE TABLE mysql_orders_source (
    order_id   INT,
    customer   STRING,
    amount     DOUBLE,
    status     STRING,
    updated_at TIMESTAMP(3),
    PRIMARY KEY (order_id) NOT ENFORCED
) WITH (
    'connector' = 'mysql-cdc',
    'hostname'  = 'mysql-host',
    'port'      = '3306',
    'username'  = 'cdc_user',
    'password'  = 'cdc_password',
    'database-name' = 'orders_db',
    'table-name'    = 'orders'
);

-- 2. Lakehouse Sink（CDC 模式）
CREATE TABLE lakehouse_orders_sink (
    order_id   INT,
    customer   STRING,
    amount     DOUBLE,
    status     STRING,
    updated_at TIMESTAMP(3),
    PRIMARY KEY (order_id) NOT ENFORCED
) WITH (
    'connector'        = 'igs-dynamic-table',
    'curl'             = 'jdbc:clickzetta://...',
    'schema-name'      = 'public',
    'table-name'       = 'orders',
    'sink.parallelism' = '1',
    'properties'       = 'authentication:true'
);

-- 3. 同步
INSERT INTO lakehouse_orders_sink SELECT * FROM mysql_orders_source;
```

## Buffer 与 Flush 调优

```sql
-- 在 WITH 子句中添加调优参数
'mutation.buffer.lines.num'  = '500'    -- 每批缓冲行数（默认 100）
'mutation.buffer.space'      = '10MB'   -- 缓冲区大小（默认 5MB）
'mutation.buffer.max.num'    = '8'      -- 并发缓冲区数（默认 5）
'mutation.flush.interval'    = '5000'   -- flush 间隔毫秒（默认 10000）
'flush.mode'                 = 'AUTO_FLUSH_BACKGROUND'  -- 异步 flush（默认）
```

## Checkpoint 配置（Java）

```java
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

// 生产环境必须开启 checkpoint
env.enableCheckpointing(60000);  // 每 60 秒一次
env.getCheckpointConfig().setCheckpointingMode(CheckpointingMode.EXACTLY_ONCE);
env.getCheckpointConfig().setMaxConcurrentCheckpoints(1);
env.getCheckpointConfig().setMinPauseBetweenCheckpoints(30000);
env.getCheckpointConfig().setCheckpointTimeout(120000);
```

## 私有网络访问

```sql
-- 内网访问（VPC 内部）
'properties' = 'authentication:true,isInternal:true,isDirect:false'
```

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 写入主键表数据不更新 | 使用了 append-only 模式 | 改用 `igs-dynamic-table` 模式 |
| 并行度 > 1 时数据乱序 | 主键表要求顺序写入 | 主键表 `sink.parallelism` 必须设为 `1` |
| checkpoint 失败 | 未配置 checkpoint 或超时 | 增大 `setCheckpointTimeout`，检查网络 |
| 连接超时 | 网络不通或认证失败 | 检查 `curl` 中的 username/password，确认 VPC 配置 |
