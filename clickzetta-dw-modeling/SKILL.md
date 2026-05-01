---
name: clickzetta-dw-modeling
description: |
  ClickZetta Lakehouse 数仓建模向导。通过问答引导用户完成从分层架构选择、数据源接入、
  管道方案、表类型推荐、分区/分桶策略、层间流转、数据质量卡点、调度 DAG 到 DDL 模板
  生成的完整数仓搭建流程。数据管道与建模一体化设计，不割裂。
  支持三种分层模式：传统数仓分层（ODS/DWD/DWS/ADS）、大奖牌架构（Bronze/Silver/Gold）、
  混合模式。核心原则：聚合计算层使用 Dynamic Table，不推荐物化视图。
  当用户说"数仓建模"、"分层设计"、"建模方案"、"ODS/DWD/DWS"、"Medallion"、
  "Bronze/Silver/Gold"、"事实表"、"维度表"、"宽表设计"、"星型模型"、"雪花模型"、
  "分层架构"、"数据分层"、"建模向导"、"怎么设计表结构"、"数仓架构"、
  "数据管道设计"、"数据流转"、"端到端数仓搭建"时触发。
---

# ClickZetta 数仓建模向导

阅读 [references/modeling-patterns.md](references/modeling-patterns.md) 了解各分层模式的详细模板。

---

## 使用方式

本 skill 是**向导式**的——不要直接给出方案，通过以下步骤引导用户做决策。**每一步等用户回答后再进入下一步**，不要跳步骤。

---

## 第一步：选择分层模式

> 你们的数仓采用哪种分层模式？
>
> **A. 传统数仓分层**（ODS → DWD → DWS → ADS）
> 适合：有成熟数仓团队、强调指标体系、BI 报表为主、数据来源相对规整
>
> **B. 大奖牌架构**（Bronze → Silver → Gold）
> 适合：数据湖场景、多源异构数据、探索性分析为主、希望保留原始数据
>
> **C. 混合模式**（Bronze/Silver + DWS/ADS）
> 适合：从数据湖向数仓演进、既要保留原始数据又要建立指标体系

---

## 第二步：业务场景与数据源

同时询问以下问题（数据源类型会影响后续所有决策）：

- **数据源类型**：MySQL / PostgreSQL / Kafka / OSS 文件 / 其他数据库？
- **数据更新方式**：实时流式 / CDC 增量 / 批量全量 / 混合？
- **数据量级**：日增量、总量大概多少？
- **主要查询场景**：BI 报表 / Ad-Hoc 分析 / 实时看板 / 数据科学？

---

## 第三步：数据接入管道方案

根据第二步的数据源类型，推荐对应的接入管道，并告知用户需要加载对应 skill 获取详细配置：

| 数据源 | 更新方式 | 推荐管道 | 对应 skill |
|---|---|---|---|
| MySQL / PostgreSQL | CDC 实时 | Binlog/WAL CDC 同步 | `clickzetta-cdc-sync-pipeline` |
| MySQL / PostgreSQL | 批量全量/增量 | 批量同步任务 | `clickzetta-batch-sync-pipeline` |
| Kafka | 实时流式 | Kafka Pipe 持续导入 | `clickzetta-kafka-ingest-pipeline` |
| OSS / S3 / COS | 文件持续到达 | OSS Pipe 持续导入 | `clickzetta-oss-ingest-pipeline` |
| 本地文件 / URL | 一次性批量 | COPY INTO | `clickzetta-file-import-pipeline` |
| 单表实时（MySQL/PG/Kafka） | 实时 | 单表实时同步任务 | `clickzetta-realtime-sync-pipeline` |
| 多源混合 | 混合 | 先用路由 skill 判断 | `clickzetta-data-ingest-pipeline` |

**ODS/Bronze 层的特殊考虑**（根据管道类型调整表结构）：
- CDC 接入 → 表需要保留 `_op`（操作类型：I/U/D）和 `_ts`（变更时间）字段
- Kafka 接入 → 表需要考虑消息 schema，JSON 字段用 `MAP<STRING,STRING>` 或 `STRING`
- 批量接入 → 表需要 `dw_batch_id` 或 `dw_insert_date` 标记批次

---

## 第四步：各层表类型推荐

结合数据源和分层模式给出推荐：

### 传统数仓分层

| 层次 | 定位 | 推荐表类型 | 说明 |
|---|---|---|---|
| ODS | 原始数据，贴源层 | 内部表 | 保留原始字段，不做业务转换 |
| DWD | 明细数据，清洗标准化 | 内部表 | 清洗、类型统一、去重 |
| DWS | 汇总数据，轻度聚合 | **Dynamic Table** | 基于 DWD 增量聚合，自动刷新 |
| ADS | 应用数据，指标输出 | **Dynamic Table** | 面向 BI/应用，按需刷新 |

### 大奖牌架构（Medallion）

| 层次 | 定位 | 推荐表类型 | 说明 |
|---|---|---|---|
| Bronze | 原始数据，零转换 | 内部表 | 保留原始格式，支持 Time Travel |
| Silver | 清洗标准化，可信数据 | 内部表 或 **Dynamic Table** | 去重、类型转换、业务规则 |
| Gold | 聚合指标，业务就绪 | **Dynamic Table** | 面向消费，增量刷新 |

> ⚠️ 聚合层**不推荐物化视图**，使用 Dynamic Table：
> - CBO 增量计算，只刷新变化的分区，比物化视图全量刷新更高效
> - 支持 Time Travel 和数据恢复
> - 语法简洁，与普通表统一管理

---

## 第五步：分区与分桶策略

询问：主要过滤条件是什么？单表数据量大概多少？

```sql
-- 时间分区（大多数场景推荐）
PARTITIONED BY (days(event_date))    -- 按天
PARTITIONED BY (months(event_date))  -- 按月（数据量小时）

-- 分桶（大表 JOIN 优化，单表 > 1亿行时考虑）
CLUSTERED BY (user_id) INTO 32 BUCKETS  -- 分桶数建议 2 的幂次

-- 组合（大表标准配置）
PARTITIONED BY (days(event_date))
CLUSTERED BY (user_id) INTO 32 BUCKETS
```

注意：ClickZetta 分区用 `PARTITIONED BY (days(col))`，不是 `PARTITIONED BY (col)`。

---

## 第六步：层间流转设计

ODS/Bronze 数据进来后，各层之间如何流转：

| 流转路径 | 推荐方式 | 说明 |
|---|---|---|
| ODS → DWD / Bronze → Silver | SQL 任务（Studio 调度） | 清洗逻辑复杂，需要手动控制 |
| DWD → DWS / Silver → Gold | **Dynamic Table** | 聚合逻辑稳定，自动增量刷新 |
| DWS → ADS | **Dynamic Table** 或直接查询 | 简单指标用 Dynamic Table，复杂逻辑用 SQL 任务 |

加载 `clickzetta-sql-pipeline-manager` 获取 Dynamic Table 和 Table Stream 的详细语法。

---

## 第七步：数据质量卡点

各层质量职责：

| 层次 | 检查重点 | 建议时机 |
|---|---|---|
| ODS/Bronze | 完整性（NULL 比例）、格式合法性、CDC 操作类型分布 | 数据入库后 |
| DWD/Silver | 唯一性、业务规则合法性、关联完整性（LEFT JOIN 验证匹配率） | ETL 任务完成后 |
| DWS/Gold/ADS | 指标合理性（环比异常）、汇总一致性 | Dynamic Table 每次刷新后 |

---

## 第八步：调度 DAG 设计

询问数据更新频率，给出 DAG 结构建议：

```
典型日批 DAG（传统分层）：
数据同步任务（ODS 接入）
    └── DWD 清洗任务（SQL 任务，Studio 调度）
            └── 数据质量检查（DWD 层）
                    └── DWS 层（Dynamic Table 自动刷新，无需调度）
                            └── ADS 层（Dynamic Table 自动刷新）

典型实时 DAG（Medallion）：
Kafka/CDC 持续写入 Bronze
    └── Silver（Dynamic Table，TARGET_LAG = '10 minutes'）
            └── Gold（Dynamic Table，TARGET_LAG = '1 hour'）
```

Dynamic Table 的 `TARGET_LAG` 替代手动调度，减少 DAG 复杂度。

---

## 第九步：生成 DDL + 管道配置模板

根据前面所有决策，同时输出：

**1. 各层 DDL 模板**（加载 `clickzetta-sql-syntax-guide` 确认语法）

ODS/Bronze 层（以 CDC 接入为例）：
```sql
CREATE TABLE IF NOT EXISTS ods.orders (
    order_id        BIGINT,
    user_id         BIGINT,
    amount          DECIMAL(18, 2),
    status          STRING,
    created_at      TIMESTAMP,
    _op             STRING,     -- CDC 操作类型：I/U/D
    _ts             TIMESTAMP,  -- 变更时间
    dw_insert_time  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dw_source       STRING    DEFAULT 'mysql_orders'
)
PARTITIONED BY (days(created_at))
COMMENT 'ODS 订单原始表，贴源不转换';
```

DWD/Silver 层：
```sql
CREATE TABLE IF NOT EXISTS dwd.fact_orders (
    order_id        BIGINT,
    user_id         BIGINT,
    amount          DECIMAL(18, 2),
    status_code     INT,
    order_date      DATE,
    dw_insert_time  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
PARTITIONED BY (days(order_date))
CLUSTERED BY (user_id) INTO 32 BUCKETS
COMMENT 'DWD 订单事实表，清洗标准化';
```

DWS/Gold 层（Dynamic Table）：
```sql
CREATE DYNAMIC TABLE IF NOT EXISTS dws.user_order_daily
TARGET_LAG = '1 hour'
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

**2. 管道配置提示**

根据第三步选择的管道类型，告知用户加载对应 skill 完成管道配置：
- CDC 接入 → 加载 `clickzetta-cdc-sync-pipeline`
- Kafka 接入 → 加载 `clickzetta-kafka-ingest-pipeline`
- 批量接入 → 加载 `clickzetta-batch-sync-pipeline`

---

## 核心原则

1. **聚合层用 Dynamic Table，不用物化视图**
2. **数据源类型决定 ODS/Bronze 表结构**，CDC 需要 `_op`/`_ts` 字段
3. **分区用转换函数**：`days(col)` 不是 `col`
4. **ODS/Bronze 层零转换**，保留原始数据方便回溯
5. **数据质量分层设置**，不要全堆在最后一层
6. **建模和管道一体设计**，DDL 和管道配置同步输出
