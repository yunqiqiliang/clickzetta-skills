# Dynamic Table 声明策略

DT 有两种创建语法：静态分区 DT 和动态分区 DT（非分区 DT 可视为动态分区的特例）。两者在创建语法、刷新方式、增量行为上有本质区别。

## 核心概念

### 静态分区 DT（Partitioned DT with SESSION_CONFIGS args）

SQL 中通过 `SESSION_CONFIGS()` 引用分区参数，每次 REFRESH 时指定具体的分区值。每个分区独立刷新，可以视为每个分区刷新单元都是一个彼此独立的 DT。

```sql
CREATE DYNAMIC TABLE order_daily (
    id BIGINT, amount DECIMAL(12,2), ds STRING
)
PARTITIONED BY (ds)
AS
SELECT id, amount, SESSION_CONFIGS()['dt.args.ds'] AS ds
FROM orders
WHERE ds = SESSION_CONFIGS()['dt.args.ds'];

-- 刷新时指定分区（在 Studio 任务中执行，dt.args.ds 通过任务参数传入）
REFRESH DYNAMIC TABLE order_daily PARTITION(ds = '2025-01-01');
```

### 动态分区 DT（Non-partitioned DT / DT without args）

SQL 中不引用 `SESSION_CONFIGS()`，或者虽然有分区但分区值由查询逻辑动态产生。每次 REFRESH 处理所有源表的增量数据。

动态分区 DT 不允许除 REFRESH 以外的任何命令修改数据（INSERT/UPDATE/DELETE/MERGE 均不可用），数据完全由 REFRESH 驱动。

因此以下 ETL 场景不适合使用动态分区 DT：
- 需要手动修补数据（如发现某几行数据有误，需要直接 UPDATE 修正）
- 需要按条件删除部分数据（如清理脏数据、删除过期记录）
- 需要 MERGE INTO 做 upsert（如 CDC 场景中消费 stream 合并到目标表）
- 需要 INSERT INTO 追加外部数据（如手动导入一批补录数据）
- 需要按分区独立回填或重刷（动态分区 DT 只能整表全量刷新，无法单独刷某个分区）
- 下游有其他任务需要往同一张表写入数据（DT 独占写入权）

```sql
CREATE DYNAMIC TABLE order_summary (
    category STRING, total_amount DECIMAL(12,2)
)
AS
SELECT category, SUM(amount) AS total_amount
FROM orders
GROUP BY category;

-- 刷新时不指定分区
REFRESH DYNAMIC TABLE order_summary;
```

## 两者的关键区别

| 维度 | 静态分区 DT | 动态分区 DT |
|------|-----------|-----------|
| SQL 中是否有 `SESSION_CONFIGS()` | 有，用于引用分区参数 | 无 |
| REFRESH 语法 | `REFRESH ... PARTITION(ds='xxx')` | `REFRESH ...`（无 PARTITION） |
| 增量范围 | 只处理指定分区的增量数据 | 处理所有源表的全部增量数据 |
| 调度方式 | 外部调度器按分区值逐个触发 | 外部调度器定时触发即可 |
| 数据生命周期 | 按分区管理，可独立回填/删除 | 整表管理 |
| 状态表 | 按分区独立维护 | 全局维护 |
| 适合的数据模式 | T+1 批处理、按时间分区的 ETL | 实时流、全局聚合、无明确分区键 |

## 选择决策树

```
你的数据有明确的时间/业务分区键吗？
│
├─ 是 → 原始 ETL 是按分区 INSERT OVERWRITE 的吗？
│       │
│       ├─ 是 → 使用静态分区 DT
│       │       （保持原有的分区粒度，每个分区独立刷新）
│       │
│       └─ 否 → 数据量大吗？需要按分区管理生命周期吗？
│               │
│               ├─ 是 → 使用静态分区 DT
│               │       （即使原来不是分区表，也建议加分区以便管理）
│               │
│               └─ 否 → 使用动态分区 DT
│                       （简单场景，不需要分区管理）
│
└─ 否 → 使用动态分区 DT
        （全局聚合、实时汇总等场景）
```

## 静态分区 DT 详解

### 适用场景

1. **T+1 批处理 ETL 迁移**
   - 原始 SQL 是 `INSERT OVERWRITE TABLE t PARTITION(ds='${ds}')` 模式
   - 每天/每小时按分区刷新一次
   - 需要支持历史分区回填

2. **滑动窗口计算**
   - 如：最近 7 天的聚合、环比计算
   - SQL 中引用 `SESSION_CONFIGS()['dt.args.ds']` 和 `sub_days(...)` 做窗口范围

3. **需要按分区管理数据生命周期**
   - 通过 `data_lifecycle` 自动清理过期分区
   - 可以单独回填某个分区而不影响其他分区

4. **自引用 DT（日环比、SCD）**
   - 当前分区依赖上一个分区的结果
   - 必须用静态分区，因为需要明确指定"当前分区"和"上一分区"

### 刷新方式

> ⚠️ **重要**：静态分区 DT 的 `dt.args.*` 参数**仅在 Studio 任务中可用**，不能在交互式 SQL 中使用 `SET dt.args.xxx`。
> 必须通过 Studio 创建调度任务，在任务参数中配置 `dt.args.ds` 等值。

```sql
-- 在 Studio 任务中，参数通过任务配置传入，REFRESH 语句指定分区值：
REFRESH DYNAMIC TABLE my_dt PARTITION(ds = '2025-01-15');

-- 多级分区
REFRESH DYNAMIC TABLE my_dt PARTITION(pt = '20250411', pt_hour = '01');
```

### 注意事项

- 回填时使用 `SET cz.optimizer.incremental.backfill.enabled = TRUE`（此配置在交互式 SQL 中可用）
- `dt.args.*` 参数仅在 Studio 任务中可用，不能在交互式 SQL 中 SET
- `cz.optimizer.*` 配置项在交互式 SQL 中可用

## 动态分区 DT 详解

### 适用场景

1. **实时流数据聚合**
   - 源表持续写入，DT 定时刷新
   - 不需要按分区管理，每次处理所有新增数据

2. **全局汇总表**
   - 如：全局 TopN、全局计数、全局去重
   - 没有明确的分区键

3. **简单的 JOIN + 过滤**
   - 不涉及分区参数的简单转换
   - 如：事实表 JOIN 维度表，输出宽表

4. **多源表合并（UNION ALL）**
   - 多个源表的数据合并到一张表
   - 不需要按分区管理

### 刷新方式

```sql
-- 直接刷新，处理所有源表的增量
REFRESH DYNAMIC TABLE my_dt;
```

### 注意事项

- 每次刷新处理所有源表的全部增量，如果源表变更量大，刷新可能较慢
- 状态表全局维护，随着数据量增长可能膨胀
- 不支持按分区回填，只能全量刷新整表
- 适合变更量占比小的场景（< 5%）

## 分区粒度选择

当选择静态分区 DT 时，还需要决定分区粒度：

| 数据模式 | 推荐分区粒度 | 说明 |
|---------|------------|------|
| 严格有序的时间序列（如日志） | 分钟级 (`dt_min`) | 数据量大、写入频繁 |
| 大致有序、少量迟到数据 | 小时级 (`dt_hour`) | 平衡粒度和管理复杂度 |
| T+1 批量导入 | 天级 (`ds`) | 最常见的 ETL 场景 |
| 按业务周期 | 周/月级 | 报表类场景 |
| 多级分区 | 天 + 小时 (`ds`, `hour`) | 需要更细粒度的生命周期管理 |

选择原则：
- 粒度越细，每次刷新处理的数据量越小，增量效率越高
- 粒度越细，分区数越多，管理和调度越复杂
- 粒度应与数据写入频率匹配：如果数据每小时写入一次，分区粒度不应细于小时

## 从原始 ETL 判断分区策略

| 原始 ETL 模式 | 推荐 DT 分区策略 |
|--------------|----------------|
| `INSERT OVERWRITE TABLE t PARTITION(ds='${ds}')` | 静态分区 DT，天级 |
| `INSERT OVERWRITE TABLE t PARTITION(ds='${ds}', hour='${hour}')` | 静态分区 DT，天+小时级 |
| `INSERT OVERWRITE TABLE t PARTITION(ds)` （动态分区写入） | 动态分区 DT 或静态分区 DT（取决于是否需要按分区管理） |
| `INSERT INTO TABLE t SELECT ...` （无分区） | 动态分区 DT |
| `INSERT OVERWRITE TABLE t SELECT ...` （全表覆盖） | 动态分区 DT |
