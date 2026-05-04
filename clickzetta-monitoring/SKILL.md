---
name: clickzetta-monitoring
description: |
  监控和分析 ClickZetta Lakehouse 作业运行状态、性能和资源使用情况，
  以及通过 INFORMATION_SCHEMA 查询元数据（表、列、Schema、工作空间等）。
  覆盖 SHOW JOBS 实时查看作业、information_schema.job_history 历史分析、
  慢查询识别、集群负载分析、缓存命中率统计、失败作业排查、
  information_schema.tables/columns/schemas 元数据查询等完整监控与治理工作流。
  当用户说"查看作业"、"作业历史"、"SHOW JOBS"、"慢查询"、"查询性能"、
  "集群负载"、"作业失败"、"查询失败"、"监控"、"job history"、
  "information_schema"、"缓存命中率"、"查询耗时"、"作业状态"、
  "元数据查询"、"查看所有表"、"表大小"、"列信息"、"资产盘点"时触发。
---

# ClickZetta 作业监控与分析

阅读 [references/show-jobs.md](references/show-jobs.md) 了解 SHOW JOBS 语法。
阅读 [references/job-history-analysis.md](references/job-history-analysis.md) 了解历史分析查询。

---

## 实时查看作业（SHOW JOBS）

```sql
-- 查看所有作业（最近7天）
SHOW JOBS;

-- 查看指定集群的作业
SHOW JOBS IN VCLUSTER default_ap;

-- 查看执行时间超过2分钟的慢查询
SHOW JOBS WHERE execution_time > INTERVAL 2 MINUTE;

-- 查看失败的作业
SHOW JOBS WHERE status = 'FAILED';

-- 限制返回数量
SHOW JOBS IN VCLUSTER default_ap LIMIT 50;
```

---

## 历史作业分析（information_schema）

### 集群负载分析

```sql
SELECT
    virtual_cluster,
    COUNT(*) AS job_count,
    AVG(execution_time) AS avg_seconds,
    ROUND(SUM(CASE WHEN status = 'SUCCEED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS success_rate
FROM sys.information_schema.job_history
WHERE start_time >= CURRENT_DATE() - INTERVAL 7 DAY
GROUP BY virtual_cluster
ORDER BY job_count DESC;
```

### 慢查询 TOP 20

```sql
SELECT job_id, virtual_cluster, execution_time, status, start_time
FROM sys.information_schema.job_history
WHERE start_time >= CURRENT_DATE() - INTERVAL 7 DAY
ORDER BY execution_time DESC
LIMIT 20;
```

### 失败作业统计

```sql
SELECT
    virtual_cluster,
    COUNT(*) AS failed_count,
    DATE(start_time) AS date
FROM sys.information_schema.job_history
WHERE status = 'FAILED'
  AND start_time >= CURRENT_DATE() - INTERVAL 7 DAY
GROUP BY virtual_cluster, DATE(start_time)
ORDER BY date DESC;
```

### 高峰期识别

```sql
SELECT
    HOUR(start_time) AS hour_of_day,
    COUNT(*) AS job_count,
    AVG(execution_time) AS avg_execution_time
FROM sys.information_schema.job_history
WHERE start_time >= CURRENT_DATE() - INTERVAL 7 DAY
GROUP BY HOUR(start_time)
ORDER BY hour_of_day;
```

---

## query_tag 标记与过滤

给作业打标，便于按来源过滤：

```sql
-- 在 SQL 中设置 query_tag
SET query_tag = 'etl_daily';
SELECT * FROM orders;

-- 按 query_tag 过滤作业历史
SELECT job_id, execution_time, status
FROM sys.information_schema.job_history
WHERE start_time >= CURRENT_DATE() - INTERVAL 7 DAY
  AND query_tag = 'etl_daily';
```

JDBC URL 中设置：
```
jdbc:clickzetta://instance.region.api.clickzetta.com/workspace?query_tag=my_app
```

---

## 常见问题排查

| 现象 | 排查方向 |
|---|---|
| 作业长时间"等待执行" | 集群资源不足，考虑扩容 VCluster |
| 作业长时间"集群启动中" | VCluster 冷启动慢，联系技术支持 |
| 大量失败作业 | 查看 job_id 详情，检查 SQL 语法或权限 |
| 平均执行时间突然变长 | 检查数据量变化、索引状态、缓存命中率 |

---

## INFORMATION_SCHEMA 元数据查询

除了 `job_history`，INFORMATION_SCHEMA 还提供丰富的元数据视图，用于资产盘点和治理。

### 空间级视图（当前工作空间）

```sql
-- 查看当前空间下所有 Schema
SELECT * FROM information_schema.schemas;

-- 查看所有表及其大小、行数
SELECT table_schema, table_name, table_type, row_count, bytes
FROM information_schema.tables
ORDER BY bytes DESC;

-- 查看所有列的详细信息（字段名、类型、是否可空、注释）
SELECT table_schema, table_name, column_name, data_type, is_nullable, comment
FROM information_schema.columns
WHERE table_schema = 'public';

-- 查看排序列推荐
SELECT * FROM information_schema.sortkey_candidates;
```

### 实例级视图（需要 instance_admin 权限，使用 sys 库）

```sql
-- 查看实例下所有工作空间
SELECT * FROM sys.information_schema.workspaces;

-- 查看实例下所有 Schema（跨工作空间）
SELECT * FROM sys.information_schema.schemas;

-- 查看实例用量（费用分析）
SELECT * FROM sys.information_schema.instance_usage
WHERE start_time >= CURRENT_DATE() - INTERVAL 7 DAY;
```

### 常用元数据分析场景

```sql
-- 找出最大的 10 张表
SELECT table_schema, table_name, row_count, bytes
FROM information_schema.tables
WHERE table_type = 'TABLE'
ORDER BY bytes DESC
LIMIT 10;

-- 找出没有注释的表
SELECT table_schema, table_name
FROM information_schema.tables
WHERE comment IS NULL OR comment = '';

-- 找出没有注释的字段
SELECT table_schema, table_name, column_name
FROM information_schema.columns
WHERE (comment IS NULL OR comment = '')
  AND table_schema NOT IN ('information_schema');

-- 统计各 Schema 下的表数量和总存储
SELECT table_schema,
       COUNT(*) AS table_count,
       SUM(bytes) AS total_storage
FROM information_schema.tables
GROUP BY table_schema
ORDER BY total_storage DESC;
```
