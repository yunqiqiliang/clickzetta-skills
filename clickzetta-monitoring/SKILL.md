---
name: clickzetta-monitoring
description: |
  监控和分析 ClickZetta Lakehouse 作业运行状态、性能和资源使用情况。
  覆盖 SHOW JOBS 实时查看作业、information_schema.job_history 历史分析、
  慢查询识别、集群负载分析、缓存命中率统计、失败作业排查等完整监控工作流。
  当用户说"查看作业"、"作业历史"、"SHOW JOBS"、"慢查询"、"查询性能"、
  "集群负载"、"作业失败"、"查询失败"、"监控"、"job history"、
  "information_schema"、"缓存命中率"、"查询耗时"、"作业状态"时触发。
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
    ROUND(SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS success_rate
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
