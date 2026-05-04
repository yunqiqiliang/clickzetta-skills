---
name: clickzetta-dw-modeling
description: |
  ClickZetta Lakehouse 数仓建模向导。先自主探索用户的数据现状，再给出有依据的
  具体建议让用户选择，而不是让用户填空回答问卷。
  覆盖三种分层模式：传统数仓分层（ODS/DWD/DWS/ADS）、大奖牌架构（Bronze/Silver/Gold）、
  混合模式。数据管道与建模一体化设计，DDL 和管道配置同步输出。
  核心原则：聚合计算层使用 Dynamic Table，不推荐物化视图。
  当用户说"数仓建模"、"分层设计"、"建模方案"、"ODS/DWD/DWS"、"Medallion"、
  "Bronze/Silver/Gold"、"事实表"、"维度表"、"宽表设计"、"星型模型"、"雪花模型"、
  "分层架构"、"数据分层"、"建模向导"、"怎么设计表结构"、"数仓架构"、
  "数据管道设计"、"数据流转"、"端到端数仓搭建"时触发。
  Keywords: data warehouse, modeling, star schema, medallion, ODS, DWD, DWS, ADS, layering
---

# ClickZetta 数仓建模向导

阅读 [references/modeling-patterns.md](references/modeling-patterns.md) 了解各分层模式的详细模板。

---

## 工作模式：先探索，再建议

**不要问问卷式问题。先动手看数据，再给出有依据的选择题。**

用户最多只需要回答 2 个问题：
1. 选择 agent 给出的方案选项（A/B/C）
2. 补充 agent 看不到的信息（业务用途、查询场景）

---

## 第一阶段：自主探索数据现状

收到建模需求后，立即执行以下探索，**不要先问用户任何问题**：

```sql
-- Step 1: 看有哪些 schema
SHOW SCHEMAS;

-- Step 2: 看各 schema 下的表（对每个看起来有业务数据的 schema 执行）
SHOW TABLES IN <schema>;

-- Step 3: 查表大小和行数（先 describe_table 确认字段名）
SELECT table_schema, table_name, table_type,
       ROUND(bytes/1024.0/1024/1024, 2) AS size_gb,
       row_count,
       last_modify_time
FROM information_schema.tables
WHERE table_type = 'MANAGED_TABLE'
ORDER BY bytes DESC NULLS LAST
LIMIT 20;

-- Step 4: 对最大的 2-3 张表抽样，了解字段和数据特征
SELECT * FROM <schema>.<table> LIMIT 5;
```

**探索时的判断逻辑：**

| 观察到的特征 | 推断 |
|---|---|
| 表名含 order/user/product/trade | 业务库原始数据，适合做 ODS/Bronze |
| 表名含 log/event/track/click | 埋点/日志数据，数据量大，需要分区 |
| 表名含 dw/ods/dwd/dws/ads | 已有分层，评估现有结构是否合理 |
| 表名含 tmp/temp/bak | 临时表，不纳入建模范围 |
| 字段含 _op/_ts/binlog | CDC 同步过来的数据 |
| 字段含 event_time/log_time | 时序数据，按时间分区 |
| 单表 > 10GB | 需要分区+分桶 |

---

## 第二阶段：给出有依据的建议

基于探索结果，向用户呈现三部分内容：

### 1. 数据现状摘要（agent 自己总结，不问用户）

```
我看了一下你的数据：
- `raw` schema：orders(2.3GB/1200万行)、users(450MB)、products(120MB)
  → 字段特征像是从 MySQL 同步的业务库，orders 有 _op/_ts 字段（CDC 接入）
- `events` schema：user_events(18GB/8亿行)
  → 字段含 event_time、event_type，是埋点日志数据
- 没有发现已有的分层结构
```

### 2. 方案选项（给 A/B 或 A/B/C，不超过 3 个）

```
基于以上数据，建议两个方向：

A. 传统数仓分层
   raw → ODS（现有数据直接复用）
   新建 DWD（清洗标准化）+ DWS（聚合，用 Dynamic Table）+ ADS（指标输出）
   适合：BI 报表为主，有明确的指标体系需求

B. 大奖牌架构（Medallion）
   raw → Bronze（现有数据直接复用）
   新建 Silver（标准化）+ Gold（指标，用 Dynamic Table）
   适合：多场景复用，既做 BI 又做数据科学
```

### 3. 只问一个问题

```
你们主要用这些数据做什么？
- BI 报表（固定报表，指标体系明确）→ 推荐 A
- 多场景（报表+分析+数据科学）→ 推荐 B
- 实时看板（分钟级延迟）→ 告诉我，方案会有调整
```

---

## 第三阶段：方案确认后的完整输出

用户选择方向后，**一次性给出完整方案**，不再追问：

### 分层结构设计

根据选择的模式，给出各层定义、表类型推荐：

**传统分层表类型：**

| 层次 | 推荐表类型 | 说明 |
|---|---|---|
| ODS | 内部表 | 贴源，不转换 |
| DWD | 内部表 | 清洗标准化 |
| DWS | **Dynamic Table** | 增量聚合，自动刷新 |
| ADS | **Dynamic Table** | 面向应用，按需刷新 |

**Medallion 表类型：**

| 层次 | 推荐表类型 | 说明 |
|---|---|---|
| Bronze | 内部表 | 零转换，保留原始 |
| Silver | 内部表 或 Dynamic Table | 清洗标准化 |
| Gold | **Dynamic Table** | 聚合指标，自动刷新 |

> ⚠️ 聚合层**不推荐物化视图**，使用 Dynamic Table：CBO 增量计算，只刷新变化分区，支持 Time Travel。

### 数据接入管道

根据探索到的数据源特征，直接给出管道推荐（不再问用户）：

| 数据源特征 | 推荐管道 | 对应 skill |
|---|---|---|
| 有 _op/_ts 字段（CDC） | CDC 同步 | `clickzetta-cdc-sync-pipeline` |
| Kafka 消息数据 | Kafka Pipe | `clickzetta-kafka-ingest-pipeline` |
| OSS/S3 文件 | OSS Pipe | `clickzetta-oss-ingest-pipeline` |
| 普通数据库表（无 CDC 标记） | 批量同步 | `clickzetta-batch-sync-pipeline` |

**ODS/Bronze 层表结构调整（根据管道类型）：**
- CDC 接入 → 保留 `_op`（I/U/D）和 `_ts` 字段，不要删除
- 批量接入 → 增加 `dw_batch_date` 标记批次
- Kafka 接入 → JSON 消息用 `STRING` 或 `MAP<STRING,STRING>` 存储

### 分区与分桶策略

根据探索到的表大小自动推荐：

```sql
-- 单表 < 1GB：不分区
-- 单表 1GB-100GB：按天分区
PARTITIONED BY (days(event_date))

-- 单表 > 100GB：按天分区 + 分桶
PARTITIONED BY (days(event_date))
CLUSTERED BY (user_id) INTO 32 BUCKETS
```

注意：ClickZetta 分区用 `PARTITIONED BY (days(col))`，不是 `PARTITIONED BY (col)`。

### 层间流转

```
ODS/Bronze → DWD/Silver：SQL 任务（Studio 调度，清洗逻辑需手动控制）
DWD/Silver → DWS/Gold：Dynamic Table（TARGET_LAG 控制延迟，自动增量）
DWS → ADS：Dynamic Table 或直接查询
```

加载 `clickzetta-sql-pipeline-manager` 获取 Dynamic Table 详细语法。

### 数据质量卡点

| 层次 | 检查重点 | 时机 |
|---|---|---|
| ODS/Bronze | NULL 比例、CDC _op 分布 | 入库后 |
| DWD/Silver | 唯一性、关联完整性（LEFT JOIN 验证匹配率） | ETL 后 |
| DWS/Gold/ADS | 指标环比异常、汇总一致性 | Dynamic Table 刷新后 |

### 调度 DAG

```
日批场景：
数据同步（ODS 接入）→ DWD 清洗任务 → 数据质量检查
                                          ↓
                              DWS/Gold（Dynamic Table 自动刷新，无需调度）

实时场景：
CDC/Kafka 持续写入 Bronze → Silver（TARGET_LAG='10min'）→ Gold（TARGET_LAG='1h'）
```

### DDL 模板

加载 `clickzetta-sql-syntax-guide` 确认语法，生成各层 DDL：

```sql
-- ODS/Bronze（以 CDC 接入为例）
CREATE TABLE IF NOT EXISTS ods.orders (
    order_id       BIGINT,
    user_id        BIGINT,
    amount         DECIMAL(18, 2),
    status         STRING,
    created_at     TIMESTAMP,
    _op            STRING,    -- CDC 操作类型：I/U/D
    _ts            TIMESTAMP, -- 变更时间
    dw_insert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
PARTITIONED BY (days(created_at))
COMMENT 'ODS 订单原始表，贴源不转换';

-- DWD/Silver
CREATE TABLE IF NOT EXISTS dwd.fact_orders (
    order_id       BIGINT,
    user_id        BIGINT,
    amount         DECIMAL(18, 2),
    status_code    INT,
    order_date     DATE,
    dw_insert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
PARTITIONED BY (days(order_date))
CLUSTERED BY (user_id) INTO 32 BUCKETS
COMMENT 'DWD 订单事实表，清洗标准化';

-- DWS/Gold（Dynamic Table，不用物化视图）
CREATE DYNAMIC TABLE IF NOT EXISTS dws.user_order_daily
  REFRESH interval 1 HOUR
  VCLUSTER default_ap
AS
SELECT
    user_id,
    order_date,
    COUNT(order_id)  AS order_cnt,
    SUM(amount)      AS total_amount,
    AVG(amount)      AS avg_amount
FROM dwd.fact_orders
WHERE status_code = 1
GROUP BY user_id, order_date;
```

---

## 核心原则

1. **先探索数据，再给建议**——不问问卷，看完数据再说
2. **给选择题，不给填空题**——用户选 A/B，不要让用户凭空描述
3. **聚合层用 Dynamic Table，不用物化视图**
4. **建模和管道一体**——DDL 和管道配置同步输出
5. **分区用转换函数**：`days(col)` 不是 `col`
6. **ODS/Bronze 零转换**，保留原始数据方便回溯
