# 非分区表 + 持续写入：DT 风险告警与 MERGE INTO 替代建议

## 触发条件

当用户要创建的 DT 同时满足以下条件时，**必须向用户发出告警**：

1. DT 本身是非分区表（没有 `PARTITIONED BY`，也没有 `SESSION_CONFIGS()` 引用）
2. 源表也是非分区表，且数据会持续写入（如 Kafka 消费落地表、CDC 明细表）
3. SQL 中包含按主键去重的窗口函数模式：`ROW_NUMBER() OVER (PARTITION BY key ORDER BY ts DESC) WHERE rn = 1`

## 告警内容

向用户说明以下三个风险：

### 风险 1：存储无限膨胀

非分区的 DT 和非分区的源表都没有自动的数据生命周期管理机制（`data_lifecycle` 仅对分区表生效）。随着数据持续写入：
- 源表数据量无限增长
- DT 的状态表全局维护，随数据量线性膨胀
- 目标表数据量同步增长
- 三者叠加，存储成本持续上升且不可控

### 风险 2：源表归档引发性能灾难

当存储膨胀到一定程度，运维人员通常会对源表进行归档——将历史数据迁移到冷存储或归档表，然后从源表中删除以释放空间。此时：

- DT 会捕获源表的删除事件，并将其反映到增量计算结果中
- `ROW_NUMBER() OVER (PARTITION BY key ORDER BY ts DESC) WHERE rn = 1` 的删除处理代价极高：
  - 窗口函数无法增量处理删除——需要回读该 key 下的所有历史数据重新排序
  - 非分区表没有分区边界来限制回读范围，可能需要扫描整张表
  - 大规模归档会产生海量删除变更，每个 key 都需要独立回算
- 一次源表归档可能导致 DT REFRESH 耗时从秒级飙升到小时级甚至失败

### 风险 3：无法过滤归档产生的删除事件

DT 的增量引擎自动捕获源表的所有变更（INSERT / UPDATE / DELETE），用户无法干预这个过程。SQL 中的 `WHERE op <> 'DELETE'` 过滤的是业务层面的删除标记，而不是源表物理删除产生的删除变更。用户没有任何手段告诉 DT "这些删除是归档操作，请忽略"。

## 推荐替代方案

建议用户使用 MERGE INTO + Table Stream 替代：

```sql
-- Step 1: 源表开启变更跟踪
ALTER TABLE source_table SET PROPERTIES ('change_tracking' = 'true');

-- Step 2: 创建 Table Stream
CREATE TABLE STREAM source_stream ON TABLE source_table
WITH (TABLE_STREAM_MODE = 'STANDARD', SHOW_INITIAL_ROWS = TRUE);

-- Step 3: 创建目标表
CREATE TABLE target_table (
    id BIGINT,
    col1 STRING,
    col2 INT,
    event_time TIMESTAMP
);

-- Step 4: 定时调度 MERGE INTO 消费 Stream
MERGE INTO target_table t
USING (
    SELECT id, col1, col2, event_time,
        CASE WHEN `value` IS NULL OR `value` = '' THEN 'DELETE' ELSE 'UPSERT' END AS op
    FROM source_stream
) s ON t.id = s.id
WHEN MATCHED AND s.op = 'UPSERT' THEN UPDATE SET
    t.col1 = s.col1, t.col2 = s.col2, t.event_time = s.event_time
WHEN NOT MATCHED AND s.op = 'UPSERT' THEN INSERT
    (id, col1, col2, event_time) VALUES (s.id, s.col1, s.col2, s.event_time);
```

MERGE INTO + Table Stream 的优势：
- **每次计算独立**：只消费 Stream 中的增量数据，不依赖源表全量状态
- **归档免疫**：源表归档时，可在 USING 子查询中通过 WHERE 条件过滤归档产生的删除事件
- **目标表独立管理**：目标表的生命周期与源表解耦，可独立制定归档策略
- **offset 自动推进**：MERGE INTO 消费 Stream 后 offset 自动推进，下次只处理新变更

## 告警话术模板

当检测到用户的 DT 满足触发条件时，使用以下话术：

> ⚠️ **风险提示**：您正在创建一个非分区的 Dynamic Table，且源表也是非分区的持续写入表。这种组合存在以下长期运维风险：
>
> 1. **存储无限膨胀**：源表、DT 目标表、DT 状态表三者都会持续增长，且无法通过 `data_lifecycle` 自动清理
> 2. **源表归档会引发性能灾难**：当您需要对源表进行归档（迁移历史数据后删除）时，DT 会捕获这些删除事件。由于 SQL 中包含 `ROW_NUMBER() ... WHERE rn = 1` 的去重逻辑，每个被删除的 key 都需要回读历史数据重新排序，非分区表没有边界限制，可能导致 REFRESH 性能严重回退
> 3. **无法过滤归档删除**：DT 增量引擎自动捕获源表所有变更，您无法告诉 DT 忽略归档操作产生的删除
>
> **建议**：对于这类"非分区 CDC 明细表合并为结果表"的场景，推荐使用 MERGE INTO + Table Stream 方案。每次只消费增量数据，源表归档时可通过 WHERE 条件过滤删除事件，不会影响下游。

## 判断逻辑

在帮助用户创建 DT 时，按以下顺序检查：

1. DT 是否有 `PARTITIONED BY` 或 `SESSION_CONFIGS()` → 如果有，不触发告警
2. 源表是否是持续写入的非分区表（如 Kafka 消费表、CDC 明细表）→ 如果不是，不触发告警
3. SQL 是否包含 `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ... DESC) WHERE rn = 1` 模式 → 如果包含，风险最高，必须告警
4. 即使没有 ROW_NUMBER，只要满足条件 1+2，也应提醒用户注意存储膨胀风险
