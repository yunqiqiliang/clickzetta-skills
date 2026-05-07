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
REFRESH INTERVAL 60 MINUTE vcluster default_ap
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
| 指定开始时间 | `REFRESH START WITH '2025-01-01 00:00:00' INTERVAL 1 HOUR vcluster <name>` | 从指定时间开始调度 |
| 手动触发 | `REFRESH DYNAMIC TABLE my_dt;` | 外部调度器触发，适合静态分区 DT |

INTERVAL 支持的单位：`SECOND`、`MINUTE`、`HOUR`、`DAY`，最小值为 1 分钟。

> 建议使用 GP 型集群刷新动态表。动态表刷新过程中会自动执行小文件合并，AP 型集群不支持此功能。

### 开启增量刷新的前提

源表需开启变更跟踪：
```sql
ALTER TABLE bronze.raw_orders SET PROPERTIES ('change_tracking' = 'true');
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
| 刷新一直是 FULL 模式 | 源表未开启 change_tracking，或查询含不支持增量的算子 | 开启 change_tracking；参考 sql-limitations.md |
| 刷新延迟超过预期 | VCluster 资源不足，或查询复杂度高 | 升级 VCluster 规格；拆分管道 |
| `SUSPEND` 后数据不更新 | 已暂停 | 执行 `ALTER DYNAMIC TABLE ... RESUME` |
| 依赖链中下游不刷新 | 上游 Dynamic Table 刷新失败 | 先修复上游，再手动 `REFRESH` 下游 |
| 删除报错 | 有下游 Dynamic Table 依赖 | 先删除下游，再删除上游 |
| 增量结果与全量不一致 | 维度表变更未触发重算 | 执行全量刷新：`SET cz.optimizer.incremental.force.full.refresh = true` |
| 状态表损坏 | 系统异常 | `SET cz.optimizer.incremental.rebuild.rule.based.state.table = true` |
