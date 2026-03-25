---
name: clickzetta-query-optimizer
description: |
  诊断和优化 ClickZetta Lakehouse SQL 查询性能。覆盖执行计划分析、慢查询排查、
  结果缓存、小文件合并、Map Join 优化、Sort Key 推荐等完整调优工作流。
  当用户说"查询慢"、"SQL 性能优化"、"执行计划"、"EXPLAIN"、"查看 Job"、
  "慢查询"、"小文件"、"OPTIMIZE"、"结果缓存"、"Result Cache"、
  "Map Join"、"排序列"、"sort key"、"查询调优"、"性能诊断"时触发。
---

# ClickZetta 查询性能优化

## ⚠️ 注意事项

- `OPTIMIZE` 命令只能在**通用型（GENERAL PURPOSE）计算集群**运行，分析型集群不生效
- Result Cache 默认未开启，需手动 `SET cz.sql.enable.shortcut.result.cache = true`
- Map Join 小表限制为 **1GB**，超过则失败

---

## 诊断流程

```
查询慢
├── 1. 先看执行计划（EXPLAIN）
│   ├── 发现全表扫描 → 考虑加索引或设置 sort key
│   ├── 发现大表 JOIN → 考虑 MAPJOIN hint
│   └── 发现大量 Sort → 检查 ORDER BY 是否必要
├── 2. 查看 Job 历史（SHOW JOBS）
│   └── 找到慢 Job → 在 Studio Job Profile 查看详细执行统计
├── 3. 检查小文件问题
│   └── 频繁写入的表 → OPTIMIZE 合并小文件
└── 4. 利用缓存
    └── 重复查询 → 开启 Result Cache
```

---

## 步骤 1：分析执行计划

阅读 [references/explain.md](references/explain.md)

```sql
-- 快速查看物理执行计划
EXPLAIN SELECT ...;

-- 详细查看逻辑+物理执行计划
EXPLAIN EXTENDED SELECT ...;
```

重点关注：
- `PhysicalTableScan` 是否扫描了过多数据
- `PhysicalJoin` 的策略（是否触发 MapJoin）
- `PhysicalSort` 是否可以避免

---

## 步骤 2：查看慢查询 Job

阅读 [references/show-jobs.md](references/show-jobs.md)

```sql
-- 查看执行超过 2 分钟的 Job
SHOW JOBS IN VCLUSTER default_ap WHERE execution_time > interval 2 minute;

-- 查看最近 50 条 Job
SHOW JOBS LIMIT 50;
```

找到 Job ID 后，在 Studio → Job Profile 查看详细执行统计和执行计划图。

---

## 步骤 3：小文件优化

阅读 [references/optimize.md](references/optimize.md)

```sql
-- 手动合并小文件（异步，立即返回）
OPTIMIZE my_schema.orders;

-- 指定分区合并
OPTIMIZE my_schema.orders WHERE dt = '2024-01-01';

-- 同步执行（等待完成）
OPTIMIZE my_schema.orders OPTIONS('cz.sql.optimize.table.async' = 'false');

-- 写入时自动触发合并
SET cz.sql.compaction.after.commit = true;
```

---

## 步骤 4：开启结果缓存

阅读 [references/result-cache.md](references/result-cache.md)

```sql
-- 开启 Result Cache（SESSION 级别）
SET cz.sql.enable.shortcut.result.cache = true;

-- 关闭
SET cz.sql.enable.shortcut.result.cache = false;
```

命中缓存的查询通常在 15ms 内返回。在 Job Profile 中可看到 `JOB RESULT REUSE` 标记。

---

## 步骤 5：Map Join 与 Sort Key

阅读 [references/hints-and-sortkey.md](references/hints-and-sortkey.md)

```sql
-- Map Join：小表（<1GB）与大表 JOIN 时使用
SELECT /*+ MAPJOIN (small_table) */ *
FROM large_table t1
JOIN small_table t2 ON t1.id = t2.id;

-- 查看系统推荐的 Sort Key
SELECT * FROM information_schema.sortkey_candidates;

-- 应用推荐（直接执行 statement 列中的 SQL）
ALTER TABLE schema.table_name SET PROPERTIES("hint.sort.columns"="column_name");

-- 开启自动收集 Sort Key 推荐
ALTER WORKSPACE my_workspace SET PROPERTIES (auto_index='day');
```

---

## 常见问题

| 问题 | 排查方向 |
|---|---|
| 查询慢但执行计划看起来正常 | 检查小文件数量（`SHOW PARTITIONS EXTENDED`），考虑 OPTIMIZE |
| Result Cache 未命中 | 检查 SQL 是否完全一致、是否含 UDF 或非确定性函数、表数据是否有变更 |
| OPTIMIZE 无效 | 确认使用的是通用型（GP）集群，不是分析型集群 |
| Map Join 失败 | 小表超过 1GB，改用普通 JOIN 或拆分查询 |
| Sort Key 推荐为空 | 先执行 `ANALYZE TABLE`，再等待自动收集周期 |

---

## 参考文档

- [EXPLAIN](https://www.yunqi.tech/documents/EXPLAIN)
- [SHOW JOBS](https://www.yunqi.tech/documents/show-jobs)
- [Result Cache](https://www.yunqi.tech/documents/result_cache)
- [OPTIMIZE](https://www.yunqi.tech/documents/OPTIMIZE)
- [小文件优化](https://www.yunqi.tech/documents/small_file_optimization)
- [Map Join](https://www.yunqi.tech/documents/mapjoin)
- [推荐排序列](https://www.yunqi.tech/documents/auto-index)
