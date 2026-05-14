---
name: clickzetta-sql-pipeline-manager
description: >
  管理 ClickZetta Lakehouse 的 SQL 数据管道对象，包括动态表（Dynamic Table）、
  物化视图（Materialized View）、表流（Table Stream）和 Pipe。
  覆盖创建、修改、暂停/恢复、删除、查看状态等完整生命周期操作。
  仅涉及 SQL 命令操作，不涉及 Lakehouse Studio 图形化界面。

  当用户说"创建动态表"、"创建物化视图"、"创建 Pipe"、"创建表流"、
  "暂停/恢复动态表"、"查看刷新历史"、"修改刷新频率"、"接入 Kafka"、
  "从对象存储持续导入"、"CDC 变更捕获"、"增量计算"、"实时 ETL"、
  "数据管道"、"pipeline"、"流式处理"、"动态表刷新失败"、
  "帮我设计 ETL"、"构建数据管道"、"数据接入方案"、
  "Medallion Architecture"、"Bronze Silver Gold"、"奖章架构"、
  "湖仓分层"、"Bronze 层"、"Silver 层"、"Gold 层"时触发。
  Keywords: SQL pipeline, dynamic table, materialized view, table stream, Pipe, data pipeline
---

# ClickZetta SQL 数据管道管理

## ⚠️ ClickZetta 与标准 SQL / Snowflake 的关键语法差异

这些是最容易写错的地方，必须使用 ClickZetta 特有语法：

| 功能 | ❌ 错误写法（Snowflake/标准SQL） | ✅ ClickZetta 正确写法 |
|---|---|---|
| 动态表计算集群 | `WAREHOUSE = compute_wh` | `vcluster default`（直接跟名称，不带等号） |
| 动态表刷新调度 | `TARGET_LAG = '1 minutes'` | `REFRESH INTERVAL 1 MINUTE vcluster default` |
| Kafka 读取函数 | `TABLE(READ_KAFKA(KAFKA_BROKER => ...))` | `read_kafka('broker', 'topic', '', 'group', '', '', '', '', 'raw', 'raw', 0, MAP(...))` — 位置参数 |
| 物化视图定时刷新 | `REFRESH EVERY 1 HOUR` | `REFRESH INTERVAL 60 MINUTE vcluster default`（与动态表语法相同） |
| 物化视图手动刷新 | `REFRESH MATERIALIZED VIEW` 放在 CREATE 里 | 单独执行 `REFRESH MATERIALIZED VIEW <name>;` |
| 修改动态表 SQL | `ALTER DYNAMIC TABLE ... AS ...` | `CREATE OR REPLACE DYNAMIC TABLE ...`（ALTER 不支持修改 AS 子句） |
| JSON 字段访问 | `$1:field::TYPE` 或 `data:key` | `parse_json(value::string)['field']::TYPE` 或 `data['key']` |
| COPY INTO 导入格式 | `FILE_FORMAT = (TYPE = CSV)` | `USING CSV OPTIONS(...)` |
| COPY INTO 导出格式 | `USING CSV` | `FILE_FORMAT = (TYPE = CSV)` |

---

## 向导：明确操作意图

收到请求后，先判断用户意图，选择对应工作流：

> 你想做什么？
>
> **A. 设计并创建新的数据管道**（从数据源到各层 DT 的完整 SQL）→ 进入 Pipeline Wizard
> **B. 管理已有管道对象**（修改 DT 刷新间隔、暂停/恢复、查看刷新历史）→ 直接执行对应操作
> **C. 排查管道问题**（DT 刷新失败、Pipe 停止摄入、Stream 积压）→ 进入故障排查流程

**如果用户已经明确说了要做什么（如"帮我创建一个 Kafka 到 DWD 的管道"、"暂停这个动态表"），直接执行，不再询问。**

---

## Pipeline Wizard（管道设计向导）

当用户想设计或构建一个完整的数据管道时，这是最高优先级的模式。触发词包括：
"帮我设计/构建 ETL"、"完整的数据管道"、"从 Kafka/OSS 接入数据"、"ODS→DWD→DWS"、"端到端 pipeline"、
"Medallion Architecture"、"Bronze/Silver/Gold"、"奖章架构"、"湖仓分层"。

### 层次命名约定

用户可能使用不同的分层命名，含义相同，按用户偏好保留原始命名：

| 用户说的 | 含义 | Schema 命名建议 |
|---|---|---|
| Bronze / Silver / Gold | Medallion Architecture | `bronze` / `silver` / `gold` |
| ODS / DWD / DWS | 国内数仓分层惯例 | `ods` / `dwd` / `dws` |
| Raw / Cleansed / Aggregated | 通用英文描述 | `raw` / `cleansed` / `agg` |

**不要把 Bronze 映射成 ODS、Silver 映射成 DWD 等——保留用户选择的命名，在 SQL 中直接使用对应的 schema 和表名前缀。**

**Schema 命名必须加业务/项目前缀，避免与其他项目冲突。** 如果用户未提供前缀，询问项目名称或业务域名称，然后生成带前缀的 Schema 名：

```sql
-- ❌ 容易重名，不要这样生成
CREATE SCHEMA IF NOT EXISTS bronze;

-- ✅ 加项目前缀
CREATE SCHEMA IF NOT EXISTS ecommerce_bronze;
CREATE SCHEMA IF NOT EXISTS ecommerce_silver;
CREATE SCHEMA IF NOT EXISTS ecommerce_gold;
```

### 需求收集

**如果用户已经提供了足够信息（数据来源、字段、层次需求、项目前缀），直接生成完整 SQL，不要再问。**

如果信息不完整，一次性问清楚以下 5 点（合并成一个问题，不要逐一追问）：

> 为了生成完整的 pipeline SQL，需要确认几个信息：
> 1. **项目/业务前缀**：Schema 名称的前缀是什么（如 `ecommerce`、`risk`、`ads`）？多个项目共用 Workspace 时必须加前缀避免冲突。
> 2. **数据来源**：Kafka（broker/topic）/ 对象存储（Volume 路径/格式）/ 已有表（是否有 UPDATE/DELETE）？
> 3. **字段结构**：目标表的字段名和类型？
> 4. **层次需求**：需要几层？每层做什么处理（清洗/聚合/维度建模）？
> 5. **刷新频率**：实时（秒级）/ 近实时（分钟级）/ 低频（小时/天）？

### 生成完整 SQL

收到回答后，生成完整的端到端 SQL，包含以下所有部分：

```
1. Schema 创建（CREATE SCHEMA IF NOT EXISTS，使用用户指定的层次名称）
2. 入口层建表（如果是外部摄入）
3. 数据入口（Pipe 或 Table Stream，根据来源选择）
4. 中间层动态表（清洗/过滤，REFRESH interval N MINUTE VCLUSTER name）
5. 服务层动态表（聚合/维度，REFRESH interval N MINUTE VCLUSTER name）
6. 各动态表创建后立即执行 REFRESH DYNAMIC TABLE（重置刷新基准）
7. 验证命令（SHOW + REFRESH HISTORY）
8. 运维操作（SUSPEND/RESUME）
```

**SQL 生成后，将各段代码保存为 Studio 任务（代码资产化）：**

数据管道开发场景下，所有 SQL 都应保存为 Studio 任务，作为可管理的代码资产：

```bash
# 建表 DDL → 保存为 DRAFT 任务（不配 Cron）
cz-cli task save-content <ddl_task_name> --content "<ddl_sql>"

# ETL/转换 SQL → 保存为调度任务（配 Cron + 依赖）
cz-cli task save-content <etl_task_name> --content "<etl_sql>"
cz-cli task save-cron <etl_task_name> --cron '0 30 2 * * ? *'
cz-cli task deploy <etl_task_name>
```

> Dynamic Table DDL 也应保存为 DRAFT 任务（`03_ddl_dws_ads`），方便后续查阅和多环境迁移。

**⚠️ DDL 任务 vs 数据流转任务的调度规则（硬性约束，不得违反）：**

| 任务类型 | 判断标准 | 调度配置 | Studio 状态 |
|---|---|---|---|
| DDL 任务 | 包含 `CREATE / DROP / ALTER TABLE/SCHEMA` | **禁止配置 Cron，禁止配置依赖** | DRAFT |
| 数据流转任务 | 数据同步、ETL 转换、数据质量检查 | 配置 Cron + 上下游依赖 | PUBLISHED |
| Dynamic Table | DWS/ADS 聚合层 | **不建 Studio 任务**，系统自动刷新 | — |

> AI 生成 SQL 管道时，如果涉及 Studio 任务编排，必须遵守以上规则。不得为 DDL 语句生成 Cron 调度配置。

**来源 → 入口对象的选择规则：**
- Kafka → `CREATE PIPE ... AS COPY INTO ... FROM (SELECT ... FROM read_kafka('broker', 'topic', '', 'group', '', '', '', '', 'raw', 'raw', 0, MAP(...)))`
- 对象存储（OSS/S3/COS）→ `CREATE PIPE ... VIRTUAL_CLUSTER = 'name' INGEST_MODE = 'LIST_PURGE' AS COPY INTO ... FROM VOLUME <volume_name> USING <format> PURGE=true`
- 已有表 + 有 UPDATE/DELETE → `CREATE TABLE STREAM ... WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD')`，中间层过滤 `__change_type IN ('INSERT', 'UPDATE_AFTER', 'DELETE')`
- 已有表 + 仅 INSERT → Dynamic Table 直接 `FROM` 源表

**刷新频率规则：**
- 第一个转换层（Bronze→Silver 或 ODS→DWD）设置用户指定的刷新频率（如 `REFRESH INTERVAL 1 MINUTE vcluster default`）
- 下游层根据业务需求设置各自的刷新频率（如 `REFRESH INTERVAL 5 MINUTE vcluster default`）

---

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
└── 多层 ETL（ODS→DWD→DWS 或 Bronze→Silver→Gold）
    └── → 多个 Dynamic Table 级联（各层设置独立 REFRESH interval）
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
- Dynamic Table：`REFRESH INTERVAL N MINUTE vcluster name`、AS 查询
- Table Stream：源表名、MODE（STANDARD 或 APPEND_ONLY）
- Pipe（Kafka）：bootstrap_servers、topic、group_id、目标表（位置参数语法）
- Pipe（对象存储）：Volume 路径、文件格式、目标表、`PURGE=true`（LIST_PURGE 模式）

若用户未提供 VCLUSTER，默认使用 `default`（GP 型集群）。

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
-- ⚠️ 注意：ClickZetta 不支持 CREATE OR REPLACE PIPE，需用 CREATE PIPE 或先 DROP 再 CREATE
CREATE PIPE kafka_orders_pipe
  VIRTUAL_CLUSTER = 'default'
  BATCH_INTERVAL_IN_SECONDS = '60'
AS
COPY INTO ods.orders FROM (
  SELECT
    j['order_id']::STRING,
    j['user_id']::STRING,
    j['amount']::DECIMAL(10,2),
    j['status']::STRING,
    j['created_at']::TIMESTAMP
  FROM (
    SELECT parse_json(value::string) AS j
    FROM read_kafka(
      'kafka.example.com:9092',  -- bootstrap_servers
      'orders',                   -- topic
      '',                         -- reserved
      'lakehouse_ingest',         -- group_id
      '', '', '', '',             -- 位置参数留空，由 Pipe 管理
      'raw', 'raw', 0,
      MAP('kafka.security.protocol', 'PLAINTEXT')
    )
  )
);

-- Step 2: 动态表做 DWD 层清洗（每分钟增量刷新）
CREATE OR REPLACE DYNAMIC TABLE dwd.orders_clean
  REFRESH INTERVAL 1 MINUTE vcluster default
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

-- Step 3: 动态表做 DWS 层聚合（每 5 分钟刷新）
CREATE OR REPLACE DYNAMIC TABLE dws.order_hourly
  REFRESH INTERVAL 5 MINUTE vcluster default
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
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD');

-- Step 2: 动态表消费 Stream，过滤出最新状态
CREATE OR REPLACE DYNAMIC TABLE dwd.orders_latest
  REFRESH INTERVAL 2 MINUTE vcluster default
AS
SELECT order_id, user_id, amount, status, created_at
FROM ods.orders_stream
WHERE __change_type IN ('INSERT', 'UPDATE_AFTER');
```

### 场景 C：物化视图加速 BI 查询

```sql
-- 创建每小时刷新的物化视图
-- ⚠️ 注意：ClickZetta 不支持 CREATE OR REPLACE MATERIALIZED VIEW
-- 方法 1: 先 DROP 再 CREATE（推荐）
DROP MATERIALIZED VIEW IF EXISTS dws.mv_daily_revenue;
CREATE MATERIALIZED VIEW dws.mv_daily_revenue
  COMMENT '每日收入汇总，供 BI 工具查询'
  REFRESH INTERVAL 60 MINUTE vcluster default
AS
SELECT
  DATE(created_at) AS day,
  region,
  SUM(amount) AS revenue,
  COUNT(DISTINCT user_id) AS uv
FROM dwd.orders_clean
GROUP BY 1, 2;

-- 方法 2: 使用 BUILD DEFERRED + DISABLE QUERY REWRITE（复杂，不推荐）
-- CREATE OR REPLACE MATERIALIZED VIEW ... BUILD DEFERRED DISABLE QUERY REWRITE AS ...

-- 手动触发刷新
REFRESH MATERIALIZED VIEW dws.mv_daily_revenue;

-- 删除物化视图（⚠️ 注意：必须用 DROP MATERIALIZED VIEW，不能用 DROP TABLE）
DROP MATERIALIZED VIEW dws.mv_daily_revenue;
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
ALTER PIPE kafka_orders_pipe SET PIPE_EXECUTION_PAUSED = true;

-- 恢复 Pipe
ALTER PIPE kafka_orders_pipe SET PIPE_EXECUTION_PAUSED = false;
```

### 场景 E：参数化动态表（按分区刷新）

通过 `SESSION_CONFIGS()` 函数定义参数化查询，在刷新时传入分区值控制全量或增量刷新范围：

```sql
-- 创建参数化动态表（使用 SESSION_CONFIGS 定义参数）
CREATE OR REPLACE DYNAMIC TABLE dwd.orders_partitioned
  REFRESH INTERVAL 30 MINUTE vcluster default
AS
SELECT order_id, user_id, amount, status, created_at, DATE(created_at) AS dt
FROM ods.orders
WHERE dt = SESSION_CONFIGS('target_date', CAST(CURRENT_DATE() AS STRING));

-- 手动触发刷新并传入参数
REFRESH DYNAMIC TABLE dwd.orders_partitioned
  WITH PROPERTIES ('target_date' = '2024-06-15');
```

> **适用场景**：传统按天/按小时全量 ETL 任务改造为增量任务时，用 SESSION_CONFIGS 替换调度变量（如 `${bizdate}`），实现参数化分区刷新。

### 场景 F：动态表 DML 操作（手动修正数据）

⚠️ **重要**：ClickZetta 动态表**不支持 DML 操作**（INSERT/UPDATE/DELETE）。如需修正数据，有以下方案：

**方案 1：重建动态表（推荐）**
```sql
-- 1. 在源表中修正数据
-- 2. 等待动态表自动刷新（下一次 REFRESH INTERVAL 会全量刷新）
```

**方案 2：使用普通表替代动态表**
```sql
-- 对于需要频繁手动修正的场景，建议使用普通表 + 定时调度任务
-- 而不是动态表
CREATE TABLE dwd.orders_manual (
  order_id STRING,
  user_id STRING,
  amount DECIMAL(10,2),
  status STRING,
  created_at TIMESTAMP,
  dt DATE
);
```

> ⚠️ **动态表限制**：
> - 动态表是只读的，不支持 INSERT/UPDATE/DELETE
> - 数据修正应在源表进行，动态表会自动刷新
> - 如需手动控制数据，使用普通表 + Studio 调度任务

---

## 常见错误

| 错误 | 原因 | 解决方案 |
|---|---|---|
| `VCluster not available` | 计算集群未启动或名称错误 | 确认 VCLUSTER 名称，检查集群状态 |
| 动态表刷新失败 | SQL 查询报错或源表结构变更 | `SHOW DYNAMIC TABLE REFRESH HISTORY WHERE name = 'xxx'` 查看错误详情 |
| Stream 数据为空 | 已被消费或超出保留周期 | 检查源表 `data_retention_days`，确认是否已消费 |
| Pipe 停止摄入 | Kafka offset 问题或连接断开 | `DESC PIPE EXTENDED` 查看状态，检查 Kafka 连接 |
| `Cannot ALTER AS clause` | 尝试用 ALTER 修改动态表 SQL | 改用 `CREATE OR REPLACE DYNAMIC TABLE` |
| `CREATE OR REPLACE PIPE` 语法报错 | ClickZetta 不支持该语法 | 用 `CREATE PIPE` 或先 `DROP PIPE` 再 `CREATE` |
| `CREATE OR REPLACE MATERIALIZED VIEW` 语法报错 | 仅支持 `REWRITE DISABLED + BUILD DEFER` 模式 | 推荐用 `DROP MATERIALIZED VIEW` + `CREATE MATERIALIZED VIEW` |
| `DROP TABLE` 删除物化视图报错 | 对象类型不匹配 | 用 `DROP MATERIALIZED VIEW`（不是 `DROP TABLE`） |
| 动态表 DML 报错 `not allowed` | 动态表不支持 DML | 在源表修正数据，或使用普通表 + 调度任务 |
| `SET cz.sql.dt.allow.dml` 报错 | 不支持 session statement | 动态表不支持 DML 操作，改用其他方案 |

---

## 交付验收 Checklist

管道创建完成后，**必须逐项验证**，不得跳过：

```sql
-- 1. 行数比对：各层行数与预期一致
SELECT COUNT(*) FROM ods.<table>;   -- ODS 行数 ≈ 源端
SELECT COUNT(*) FROM dwd.<table>;   -- DWD 行数 ≤ ODS（清洗后）
SELECT COUNT(*) FROM dws.<table>;   -- DWS 行数符合聚合逻辑

-- 2. Dynamic Table 刷新状态
SHOW DYNAMIC TABLE REFRESH HISTORY <schema>.<table> LIMIT 5;
-- 确认最近一次 status = SUCCESS，refresh_mode = INCREMENTAL 或 FULL

-- 3. 关键字段非空率
SELECT
  COUNT(*) AS total,
  COUNT(key_field) AS non_null,
  ROUND(COUNT(key_field) * 100.0 / COUNT(*), 2) AS non_null_pct
FROM <schema>.<table>;
-- 核心业务字段非空率应 > 99%

-- 4. 主键唯一性（DWD 层事实表）
SELECT key_col, COUNT(*) AS cnt
FROM dwd.<table>
GROUP BY key_col
HAVING cnt > 1
LIMIT 10;
-- 结果为空 = 无重复，符合预期

-- 5. Pipe 摄入状态（如有）
SHOW PIPES;
-- status = RUNNING，last_ingested_timestamp 持续更新
```

**验收标准：**
- [ ] 各层行数与预期一致
- [ ] Dynamic Table 最近刷新状态为 SUCCESS
- [ ] 关键字段非空率 > 99%
- [ ] DWD 层主键无重复
- [ ] Pipe 状态 RUNNING（如有）
- [ ] 所有 DDL 任务为 DRAFT 状态（如涉及 Studio 任务）
- [ ] DWS/ADS 层无冗余 Studio 调度任务

---

## 参考文档

- [增量计算概述](https://www.yunqi.tech/documents/streaming_data_pipeline_overview)
- [Dynamic Table](https://www.yunqi.tech/documents/dynamic-table)
- [Table Stream 变化数据捕获](https://www.yunqi.tech/documents/table_stream)
- [物化视图](https://www.yunqi.tech/documents/materialized_ddl)
- [Pipe 简介](https://www.yunqi.tech/documents/pipe-summary)
- [使用 Dynamic Table 开展实时 ETL](https://www.yunqi.tech/documents/tutorials-streaming-data-pipeline-with_dynamic-table)
- [LLM 全量文档索引](https://yunqi.tech/llms-full.txt)
