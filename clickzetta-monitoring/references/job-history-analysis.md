# information_schema 作业历史分析参考

> 来源：https://www.yunqi.tech/documents/job_history_analysis_with_information_schema

## 数据源

表名：`sys.information_schema.job_history`

### 关键字段

| 字段 | 类型 | 说明 |
|---|---|---|
| workspace_name | String | 工作空间名称 |
| virtual_cluster | String | 计算集群名称 |
| job_id | String | 作业唯一标识 |
| execution_time | Float | 执行时长（秒） |
| start_time | Timestamp | 开始时间 |
| status | String | 状态（SUCCEED/FAILED/CANCELLED/...） |
| input_tables | String | 输入表（JSON 格式） |
| input_bytes | String | 读取字节数 |
| cache_hit | String | 缓存命中字节数 |

---

## 常用分析查询

### 1. 集群负载分析（近 30 天）

```sql
SELECT
    virtual_cluster,
    COUNT(*) AS job_count,
    SUM(execution_time) AS total_execution_time,
    AVG(execution_time) AS avg_execution_time,
    ROUND(SUM(CASE WHEN status = 'SUCCEED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS success_rate
FROM sys.information_schema.job_history
WHERE start_time >= CURRENT_DATE() - INTERVAL 30 DAY
GROUP BY virtual_cluster
ORDER BY total_execution_time DESC;
```

### 2. 慢查询分析（执行时间 TOP 20）

```sql
SELECT
    job_id,
    virtual_cluster,
    execution_time,
    status,
    start_time
FROM sys.information_schema.job_history
WHERE start_time >= CURRENT_DATE() - INTERVAL 7 DAY
ORDER BY execution_time DESC
LIMIT 20;
```

### 3. 失败作业分析

```sql
SELECT
    virtual_cluster,
    COUNT(*) AS failed_count,
    DATE(start_time) AS date
FROM sys.information_schema.job_history
WHERE status = 'FAILED'
  AND start_time >= CURRENT_DATE() - INTERVAL 7 DAY
GROUP BY virtual_cluster, DATE(start_time)
ORDER BY date DESC, failed_count DESC;
```

### 4. 缓存命中率分析

```sql
SELECT
    virtual_cluster,
    SUM(CAST(input_bytes AS BIGINT)) AS total_input_bytes,
    SUM(CAST(cache_hit AS BIGINT)) AS total_cache_hit,
    ROUND(SUM(CAST(cache_hit AS BIGINT)) * 100.0 /
          NULLIF(SUM(CAST(input_bytes AS BIGINT)), 0), 2) AS cache_hit_rate
FROM sys.information_schema.job_history
WHERE start_time >= CURRENT_DATE() - INTERVAL 7 DAY
  AND input_bytes IS NOT NULL
GROUP BY virtual_cluster;
```

### 5. 按小时统计作业量（识别高峰期）

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
