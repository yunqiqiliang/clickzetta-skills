---
name: clickzetta-dynamic-table
description: |
  ClickZetta Dynamic Table（动态表）使用指南，覆盖动态表的创建、修改、增量计算配置和性能优化。
  包含 DT 声明策略（静态分区 DT vs 动态分区 DT）、SQL 支持矩阵、增量配置参考、刷新历史查询、
  ALTER 操作指南，以及维度表 JOIN、性能优化、非分区表风险等最佳实践。
  当用户说"Dynamic Table"、"动态表"、"自动刷新"、"增量刷新"、"物化视图"、
  "REFRESH interval"、"CREATE DYNAMIC TABLE"、
  "数据管道自动化"、"增量计算"、"自动物化"、"定时刷新"、
  "依赖刷新"、"SESSION_CONFIGS"、"静态分区DT"、"动态分区DT"、
  "状态表"、"state table"、"MERGE INTO"、"Table Stream"时触发。
  Keywords: dynamic table, incremental refresh, REFRESH interval, materialized, auto-refresh pipeline, SESSION_CONFIGS, partitioned DT, state table, MERGE INTO
---

# Dynamic Table 使用指南 — 目录索引

## 快速入门

```sql
-- 1. 创建 Dynamic Table（自动调度刷新）
CREATE DYNAMIC TABLE IF NOT EXISTS silver.orders_daily
REFRESH INTERVAL 60 MINUTE vcluster default
AS
SELECT DATE(created_at) AS order_date, region, SUM(amount) AS total_amount
FROM bronze.raw_orders
GROUP BY 1, 2;

-- 2. 查看状态与刷新历史
DESC DYNAMIC TABLE silver.orders_daily;
SHOW DYNAMIC TABLE REFRESH HISTORY WHERE name = 'orders_daily' LIMIT 10;

-- 3. 手动触发刷新
REFRESH DYNAMIC TABLE silver.orders_daily;

-- 4. 列出所有 Dynamic Table
SHOW TABLES IN silver WHERE is_dynamic;
-- 返回列：schema_name, table_name, is_view, is_materialized_view, is_external, is_dynamic
-- ⚠️ 列名是 table_name（不是 name），过滤用 WHERE table_name = 'xxx'

-- 5. 查看指定表是否为动态表
SHOW TABLES IN silver WHERE table_name = 'orders_daily';
```

### 调度方式

| 方式 | 语法 | 适用场景 |
|---|---|---|
| 自动调度 | `REFRESH INTERVAL 10 MINUTE vcluster <name>` | 系统按间隔自动刷新（推荐） |
| 指定开始时间 | `REFRESH START WITH TIMESTAMP '2025-01-01 00:00:00' INTERVAL 1 HOUR vcluster <name>` | 从指定时间开始调度 |
| 手动触发 | `REFRESH DYNAMIC TABLE my_dt;` | 外部调度器触发，适合静态分区 DT |

INTERVAL 支持的单位：`SECOND`、`MINUTE`、`HOUR`、`DAY`，最小值为 1 分钟。

> ⚠️ **VCluster 类型**：始终使用 GP 型集群（`vcluster default`），不要用 AP 型（`default_ap`）。AP 型集群不支持小文件合并，长期运行会导致查询性能下降。

### ⚠️ 刷新周期的时间基准

**`REFRESH INTERVAL N DAY/HOUR` 以动态表的创建时间（或上次刷新时间）为基准计算下次触发时间，不是从零点或整点开始对齐。**

例如：动态表在 23:17 创建，设置 `REFRESH INTERVAL 1 DAY`，则后续每次刷新约在 23:17 触发，而不是次日 00:00 或业务期望的 03:00。`START WITH TIMESTAMP` 仅影响首次刷新时间，不改变后续周期的基准。

**如需控制刷新时间窗口，有三种方案：**

1. **在目标时间点附近创建动态表**（最简单）
2. **创建后立即执行 `REFRESH` 重置基准**（推荐，见下方最佳实践）
3. **改用短间隔**（如 `4 HOUR`）减少偏差，业务容忍度允许时可接受

### 创建动态表的最佳实践：创建后立即执行首次刷新

```sql
-- ✅ 推荐写法：创建后立即 REFRESH，重置刷新基准时间，实现"开箱即用"
CREATE DYNAMIC TABLE IF NOT EXISTS dws.user_order_daily
REFRESH INTERVAL 1 DAY vcluster default
AS
SELECT user_id, DATE(created_at) AS dt, COUNT(*) AS order_cnt
FROM dwd.fact_orders
GROUP BY 1, 2;

REFRESH DYNAMIC TABLE dws.user_order_daily;
-- 立即触发首次计算，同时将刷新基准时间重置为当前时刻
```

### 手动刷新命令

```sql
-- ✅ 正确：手动触发刷新
REFRESH DYNAMIC TABLE schema.table_name;

-- ❌ 错误：不存在此语法
ALTER DYNAMIC TABLE schema.table_name REFRESH;
```

### 开启增量刷新的前提

源表需开启变更跟踪：
```sql
ALTER TABLE bronze.raw_orders SET PROPERTIES ('change_tracking' = 'true');
```

### 增量刷新 vs 全量刷新

通过 `SHOW DYNAMIC TABLE REFRESH HISTORY` 的 `refresh_mode` 字段可查看刷新模式：
- `INCREMENTAL`：增量刷新（仅处理变更数据，高效）
- `FULL`：全量刷新（重新计算所有数据）
- `NO_DATA`：无数据变更，跳过刷新

**触发全量刷新的条件**：
| 条件 | 说明 |
|---|---|
| 源表未开启 `change_tracking` | 系统无法识别增量数据 |
| 查询含不支持增量的算子 | 如某些复杂 JOIN、子查询 |
| `CREATE OR REPLACE` 修改了计算逻辑 | 如修改 WHERE、GROUP BY、JOIN key |
| 手动设置强制全量 | `SET cz.optimizer.incremental.force.full.refresh = true` |
| 维度表变更 | 被 JOIN 的维度表数据变化时，增量结果可能不一致 |

**确认是否支持增量刷新**：
```sql
SET cz.optimizer.explain.can.incrementalize = true;
EXPLAIN REFRESH DYNAMIC TABLE my_dt;
-- 查看 CanBeIncrementalized 字段：Yes = 支持增量，No = 不支持（会给出原因）
```

---

## dt-creator/
创建 Dynamic Table 的参考资料（声明策略、SQL 支持矩阵、增量配置、刷新历史查询）。

## dynamic-table-alter/
修改 Dynamic Table 的结构和属性（suspend/resume、加列删列、改刷新间隔等）。

## best-practices/
Dynamic Table 最佳实践与避坑指南（维度表 JOIN 场景、性能优化、非分区表风险告警）。

---

## 常见问题排障

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 刷新一直是 FULL 模式 | 源表未开启 change_tracking，或查询含不支持增量的算子 | 开启 change_tracking；用 `EXPLAIN REFRESH` 检查 |
| 刷新延迟超过预期 | VCluster 资源不足，或查询复杂度高 | 升级 VCluster 规格；拆分管道 |
| `SUSPEND` 后数据不更新 | 已暂停 | 执行 `ALTER DYNAMIC TABLE ... RESUME` |
| 依赖链中下游不刷新 | 上游 Dynamic Table 刷新失败 | 先修复上游，再手动 `REFRESH` 下游 |
| 删除报错 | 有下游 Dynamic Table 依赖 | 先删除下游，再删除上游 |
| 增量结果与全量不一致 | 维度表变更未触发重算 | 执行全量刷新：`SET cz.optimizer.incremental.force.full.refresh = true` |
| 状态表损坏 | 系统异常 | `SET cz.optimizer.incremental.rebuild.rule.based.state.table = true` |
| 手动 REFRESH 后历史未显示 | 刷新历史有短暂延迟 | 等待几秒后重新查询 `SHOW DYNAMIC TABLE REFRESH HISTORY` |
| AP 集群刷新后查询变慢 | AP 集群不支持小文件合并 | 改用 GP 型集群（`CREATE OR REPLACE` 重建） |
| 刷新时间与预期不符（如期望 03:00 实际 23:00） | REFRESH INTERVAL 以创建时间为基准，不对齐整点 | 在目标时间点附近创建 DT，或创建后立即执行 `REFRESH DYNAMIC TABLE` 重置基准 |
