---
name: clickzetta-sql-pipeline-manager
description: >
  管理 ClickZetta Lakehouse 的 SQL 数据管道对象，包括动态表（Dynamic Table）、
  物化视图（Materialized View）、表流（Table Stream）和 Pipe。
  覆盖创建、修改、暂停/恢复、删除、查看状态等完整生命周期操作。
  仅涉及 SQL 命令操作，不涉及 Lakehouse Studio 图形化界面。

  当用户说"创建动态表"、"创建物化视图"、"创建 Pipe"、"创建表流"、
  "暂停/恢复动态表"、"查看刷新历史"、"修改 TARGET_LAG"、"接入 Kafka"、
  "从对象存储持续导入"、"CDC 变更捕获"、"增量计算"、"实时 ETL"、
  "数据管道"、"pipeline"、"流式处理"、"动态表刷新失败"时触发。
---

# ClickZetta SQL 数据管道管理

## 对象类型速查

| 对象 | 适用场景 | 核心特点 |
|---|---|---|
| **Dynamic Table** | 实时/近实时增量 ETL | SQL 定义，自动增量刷新，秒/分钟级延迟 |
| **Materialized View** | 固定聚合加速查询 | 预计算存储，手动或定时全量刷新 |
| **Table Stream** | CDC 变更数据捕获 | 捕获 INSERT/UPDATE/DELETE，配合 Dynamic Table 消费 |
| **Pipe** | 持续数据摄入 | 从 Kafka 或对象存储自动持续导入，无需调度 |

## 决策树

```
用户需求
├── 持续从外部摄入数据（Kafka / OSS / S3）
│   └── → Pipe
├── 对已有表做实时/增量转换
│   ├── 需要感知 UPDATE/DELETE → Table Stream + Dynamic Table
│   └── 只需 INSERT 追加 → Dynamic Table（直接查源表）
├── 固定聚合，不要求实时
│   └── → Materialized View
└── 多层 ETL（ODS → DWD → DWS）
    └── → 多个 Dynamic Table 级联（TARGET_LAG = DOWNSTREAM）
```

## 步骤 0：确认连接

操作前先确认已连接到 ClickZetta Lakehouse。参考 `clickzetta-lakehouse-connect` skill 获取连接参数。

## 步骤 1：选择对象类型

根据决策树选择对象类型，阅读对应参考文件：

| 对象 | 参考文件 |
|---|---|
| Dynamic Table | [references/dynamic-table.md](references/dynamic-table.md) |
| Materialized View | [references/materialized-view.md](references/materialized-view.md) |
| Table Stream | [references/table-stream.md](references/table-stream.md) |
| Pipe | [references/pipe.md](references/pipe.md) |

## 步骤 2：生成并执行 SQL

阅读对应参考文件后，根据用户提供的参数生成完整可运行 SQL。

**必填参数检查：**
- Dynamic Table / Materialized View：`TARGET_LAG`（或 REFRESH 策略）、`VCLUSTER`、AS 查询
- Table Stream：源表名、MODE（STANDARD 或 APPEND_ONLY）
- Pipe（Kafka）：`KAFKA_BROKER`、`KAFKA_TOPIC`、`KAFKA_GROUP_ID`、目标表
- Pipe（对象存储）：Volume 路径、文件格式、目标表

若用户未提供 VCLUSTER，默认使用 `default_ap`。

## 步骤 3：验证

```sql
-- 验证动态表
SHOW TABLES WHERE is_dynamic = true;
SHOW DYNAMIC TABLE REFRESH HISTORY <name> LIMIT 5;

-- 验证物化视图
SHOW TABLES WHERE is_materialized_view = true;

-- 验证 Table Stream
SHOW TABLE STREAMS;
SELECT COUNT(*) FROM <stream_name>;  -- 查看待消费变更数

-- 验证 Pipe
SHOW PIPES;
```

---

## 典型场景示例

### 场景 A：Kafka → 动态表（实时 ETL）

```sql
-- Step 1: 创建 Pipe 持续摄入 Kafka 数据到 ODS 层
CREATE OR REPLACE PIPE kafka_orders_pipe AS
INSERT INTO ods.orders (order_id, user_id, amount, status, created_at)
SELECT
  $1:order_id::STRING,
  $1:user_id::STRING,
  $1:amount::DECIMAL(10,2),
  $1:status::STRING,
  $1:created_at::TIMESTAMP
FROM TABLE(
  READ_KAFKA(
    KAFKA_BROKER => 'kafka.example.com:9092',
    KAFKA_TOPIC  => 'orders',
    KAFKA_GROUP_ID => 'lakehouse_ingest',
    KAFKA_OFFSET => 'latest',
    KAFKA_DATA_FORMAT => 'json'
  )
);

-- Step 2: 动态表做 DWD 层清洗（每分钟增量刷新）
CREATE OR REPLACE DYNAMIC TABLE dwd.orders_clean
  TARGET_LAG = '1 minutes'
  VCLUSTER = default_ap
AS
SELECT
  order_id,
  user_id,
  amount,
  UPPER(status) AS status,
  created_at,
  DATE(created_at) AS dt
FROM ods.orders
WHERE amount > 0;

-- Step 3: 动态表做 DWS 层聚合（跟随上游刷新）
CREATE OR REPLACE DYNAMIC TABLE dws.order_hourly
  TARGET_LAG = DOWNSTREAM
  VCLUSTER = default_ap
AS
SELECT
  DATE_TRUNC('hour', created_at) AS hour,
  status,
  COUNT(*) AS order_cnt,
  SUM(amount) AS total_amount
FROM dwd.orders_clean
GROUP BY 1, 2;
```

### 场景 B：Table Stream + Dynamic Table（CDC UPSERT）

```sql
-- Step 1: 在源表上创建 Stream 捕获变更
CREATE TABLE STREAM ods.orders_stream
  ON TABLE ods.orders
  MODE = STANDARD;

-- Step 2: 动态表消费 Stream，MERGE 到目标表
CREATE OR REPLACE DYNAMIC TABLE dwd.orders_latest
  TARGET_LAG = '2 minutes'
  VCLUSTER = default_ap
AS
SELECT order_id, user_id, amount, status, created_at
FROM ods.orders_stream
WHERE _change_type IN ('insert', 'update_postimage');
```

### 场景 C：物化视图加速 BI 查询

```sql
-- 创建每小时刷新的物化视图
CREATE OR REPLACE MATERIALIZED VIEW dws.mv_daily_revenue
  COMMENT '每日收入汇总，供 BI 工具查询'
  REFRESH AUTO EVERY '1 hours'
  VCLUSTER = default_ap
AS
SELECT
  DATE(created_at) AS day,
  region,
  SUM(amount) AS revenue,
  COUNT(DISTINCT user_id) AS uv
FROM dwd.orders_clean
GROUP BY 1, 2;

-- 手动触发刷新
REFRESH MATERIALIZED VIEW dws.mv_daily_revenue;
```

### 场景 D：运维操作

```sql
-- 暂停动态表（如集群维护）
ALTER DYNAMIC TABLE dwd.orders_clean SUSPEND;

-- 恢复
ALTER DYNAMIC TABLE dwd.orders_clean RESUME;

-- 查看刷新历史排查失败
SHOW DYNAMIC TABLE REFRESH HISTORY dwd.orders_clean LIMIT 10;

-- 暂停 Pipe
ALTER PIPE kafka_orders_pipe PAUSE;

-- 恢复 Pipe
ALTER PIPE kafka_orders_pipe RESUME;
```

---

## 常见错误

| 错误 | 原因 | 解决方案 |
|---|---|---|
| `VCluster not available` | 计算集群未启动或名称错误 | 确认 VCLUSTER 名称，检查集群状态 |
| 动态表刷新失败 | SQL 查询报错或源表结构变更 | `SHOW DYNAMIC TABLE REFRESH HISTORY` 查看错误详情 |
| Stream 数据为空 | 已被消费或超出保留周期 | 检查源表 `data_retention_days`，确认是否已消费 |
| Pipe 停止摄入 | Kafka offset 问题或连接断开 | `DESC PIPE` 查看状态，检查 Kafka 连接 |
| `Cannot ALTER AS clause` | 尝试用 ALTER 修改动态表 SQL | 改用 `CREATE OR REPLACE DYNAMIC TABLE` |

---

## 参考文档

- [增量计算概述](https://www.yunqi.tech/documents/streaming_data_pipeline_overview)
- [Dynamic Table](https://www.yunqi.tech/documents/dynamic-table)
- [Table Stream 变化数据捕获](https://www.yunqi.tech/documents/table_stream)
- [物化视图](https://www.yunqi.tech/documents/materialized_ddl)
- [Pipe 简介](https://www.yunqi.tech/documents/pipe-summary)
- [使用 Dynamic Table 开展实时 ETL](https://www.yunqi.tech/documents/tutorials-streaming-data-pipeline-with_dynamic-table)
- [通过流和任务实现 SCD](https://www.yunqi.tech/documents/SlowlyChangingDimensionsInLakehouseUsingStreamsandTasks)
- [LLM 全量文档索引](https://yunqi.tech/llms-full.txt)
