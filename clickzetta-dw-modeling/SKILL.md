---
name: clickzetta-dw-modeling
description: |
  ClickZetta Lakehouse 数仓建模向导。通过问答引导用户完成分层架构选择、表类型推荐、
  DDL 模板生成、分区/分桶策略、数据质量卡点设计和调度依赖规划。
  支持三种分层模式：传统数仓分层（ODS/DWD/DWS/ADS）、大奖牌架构（Bronze/Silver/Gold）、
  混合模式。核心原则：聚合计算层优先使用 Dynamic Table，不推荐物化视图。
  当用户说"数仓建模"、"分层设计"、"建模方案"、"ODS/DWD/DWS"、"Medallion"、
  "Bronze/Silver/Gold"、"事实表"、"维度表"、"宽表设计"、"星型模型"、"雪花模型"、
  "分层架构"、"数据分层"、"建模向导"、"怎么设计表结构"、"数仓架构"时触发。
---

# ClickZetta 数仓建模向导

阅读 [references/modeling-patterns.md](references/modeling-patterns.md) 了解各分层模式的详细模板。

---

## 使用方式

本 skill 是**向导式**的——不要直接给出方案，而是通过以下步骤引导用户做决策。每一步都要等用户回答后再进入下一步。

---

## 第一步：选择分层模式

向用户提问：

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

## 第二步：了解业务场景

根据选择的分层模式，询问：

- 数据源类型（MySQL/Kafka/OSS/其他数据库）
- 数据量级（日增量、总量）
- 主要查询场景（BI 报表/Ad-Hoc/实时看板/数据科学）
- 团队规模和技术栈偏好

---

## 第三步：各层表类型推荐

### 传统数仓分层

| 层次 | 定位 | 推荐表类型 | 说明 |
|---|---|---|---|
| ODS | 原始数据，贴源层 | 内部表（Managed Table） | 保留原始字段，不做业务转换 |
| DWD | 明细数据，清洗标准化 | 内部表 | 数据清洗、类型统一、去重 |
| DWS | 汇总数据，轻度聚合 | **Dynamic Table** | 基于 DWD 增量聚合，自动刷新 |
| ADS | 应用数据，指标输出 | **Dynamic Table** | 面向 BI/应用，按需刷新 |

> ⚠️ DWS/ADS 层**不推荐物化视图**，使用 Dynamic Table：
> - Dynamic Table 支持 CBO 增量计算，只刷新变化的分区
> - 语法更简洁，与普通表统一管理
> - 支持 Time Travel 和数据恢复

### 大奖牌架构（Medallion）

| 层次 | 定位 | 推荐表类型 | 说明 |
|---|---|---|---|
| Bronze | 原始数据，不做转换 | 内部表 或 外部表 | 保留原始格式，支持 Time Travel |
| Silver | 清洗标准化，可信数据 | 内部表 或 **Dynamic Table** | 去重、类型转换、业务规则应用 |
| Gold | 聚合指标，业务就绪 | **Dynamic Table** | 面向消费，增量刷新 |

### 混合模式

Bronze/Silver 参考大奖牌架构，DWS/ADS 参考传统分层。

---

## 第四步：分区与分桶策略

询问用户：

- 主要过滤条件是什么（时间字段？业务 ID？）
- 单表数据量（影响是否需要分桶）

**推荐原则：**

```sql
-- 时间分区（推荐，适合大多数场景）
PARTITIONED BY (days(event_date))   -- 按天分区
PARTITIONED BY (months(event_date)) -- 按月分区（数据量小时）

-- 分桶（适合大表 JOIN 优化）
CLUSTERED BY (user_id) INTO 32 BUCKETS

-- 组合（大表常用）
PARTITIONED BY (days(event_date))
CLUSTERED BY (user_id) INTO 32 BUCKETS
```

**注意：**
- ClickZetta 分区用 `PARTITIONED BY (days(col))`，不是 `PARTITIONED BY (col)`
- 分桶数建议为 2 的幂次（16/32/64）

---

## 第五步：数据质量卡点设计

各层质量职责：

| 层次 | 质量检查重点 | 建议时机 |
|---|---|---|
| ODS/Bronze | 完整性（NULL 比例）、格式合法性 | 数据入库后 |
| DWD/Silver | 唯一性、业务规则合法性、关联完整性 | ETL 任务完成后 |
| DWS/Gold/ADS | 指标合理性（环比异常检测）、汇总一致性 | 每次刷新后 |

---

## 第六步：调度依赖设计

询问用户数据更新频率，给出 DAG 结构建议：

```
典型日批 DAG：
数据同步任务（ODS/Bronze）
    └── DWD/Silver 清洗任务
            └── DWS/Gold 聚合任务（Dynamic Table 自动刷新，可不加调度）
                    └── 数据质量检查任务
                            └── ADS 应用层任务
```

**Dynamic Table 的调度优势：**
- DWS/Gold 层使用 Dynamic Table 后，无需手动调度刷新
- 设置 `TARGET_LAG` 控制最大延迟（如 `TARGET_LAG = '1 hour'`）
- 上游数据变化时自动触发增量计算

---

## 第七步：生成 DDL 模板

根据前面的决策，生成对应层次的 DDL 模板。加载 `clickzetta-sql-syntax-guide` 确认语法。

### ODS/Bronze 层模板

```sql
CREATE TABLE IF NOT EXISTS ods.orders (
    order_id        BIGINT,
    user_id         BIGINT,
    amount          DECIMAL(18, 2),
    status          STRING,
    created_at      TIMESTAMP,
    -- 数仓元数据字段
    dw_insert_time  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dw_source       STRING    DEFAULT 'mysql_orders'
)
PARTITIONED BY (days(created_at))
COMMENT 'ODS 订单原始表，贴源不转换';
```

### DWD/Silver 层模板

```sql
CREATE TABLE IF NOT EXISTS dwd.fact_orders (
    order_id        BIGINT,
    user_id         BIGINT,
    amount          DECIMAL(18, 2),
    status_code     INT,        -- 标准化后的状态码
    order_date      DATE,       -- 从 created_at 提取
    dw_insert_time  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
PARTITIONED BY (days(order_date))
CLUSTERED BY (user_id) INTO 32 BUCKETS
COMMENT 'DWD 订单事实表，清洗标准化';
```

### DWS/Gold 层模板（Dynamic Table）

```sql
-- 不推荐物化视图，使用 Dynamic Table
CREATE DYNAMIC TABLE IF NOT EXISTS dws.user_order_daily
TARGET_LAG = '1 hour'
AS
SELECT
    user_id,
    order_date,
    COUNT(order_id)      AS order_cnt,
    SUM(amount)          AS total_amount,
    AVG(amount)          AS avg_amount
FROM dwd.fact_orders
WHERE status_code = 1
GROUP BY user_id, order_date;
```

---

## 核心原则总结

1. **聚合层用 Dynamic Table，不用物化视图**
2. **分区字段用转换函数**：`days(col)` 不是 `col`
3. **ODS/Bronze 层保留原始数据**，不做业务转换，方便回溯
4. **数据质量检查分层设置**，不要全堆在最后一层
5. **Dynamic Table 的 TARGET_LAG 替代手动调度**，减少 DAG 复杂度
