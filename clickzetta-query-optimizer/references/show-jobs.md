# SHOW JOBS 参考

> 来源：https://www.yunqi.tech/documents/show-jobs

## 语法

```sql
SHOW JOBS [IN VCLUSTER vc_name] [LIKE 'pattern'] [WHERE <expr>] [LIMIT num];
```

## 参数说明

- `IN VCLUSTER vc_name`：（可选）筛选指定计算集群下的作业
- `WHERE <expr>`：（可选）按字段过滤，支持 SHOW JOBS 返回的所有字段
- `LIMIT num`：（可选）限制返回数量，范围 1-10000
- `LIKE 'pattern'`：（可选）按 job_id 模式匹配，支持 `%` 和 `_`

默认显示最近 7 天内提交的任务，最多 10000 条。

## 示例

```sql
-- 查看执行时间超过 2 分钟的作业
SHOW JOBS IN VCLUSTER default_ap WHERE execution_time > interval 2 minute;

-- 查看指定集群的所有作业
SHOW JOBS IN VCLUSTER default_ap;

-- 限制返回 100 条
SHOW JOBS LIMIT 100;

-- 查看指定集群最近 50 条
SHOW JOBS IN VCLUSTER default_ap LIMIT 50;

-- 按 job_id 模式匹配
SHOW JOBS LIKE 'job_2024%';
```

## 注意事项

- 只能查看最近 7 天内的作业记录
- 未指定 VCLUSTER 时显示所有集群的作业
