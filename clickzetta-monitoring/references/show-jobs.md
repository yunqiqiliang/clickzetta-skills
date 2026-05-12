# SHOW JOBS 参考

> 来源：https://www.yunqi.tech/documents/show-jobs

## 语法

```sql
SHOW JOBS [IN VCLUSTER vc_name] [LIKE 'pattern'] [WHERE <expr>] [LIMIT num];
```

## 参数说明

- `IN VCLUSTER vc_name`：（可选）指定计算集群，筛选该集群下的作业
- `WHERE <expr>`：（可选）按字段过滤，支持 SHOW JOBS 显示的所有字段
- `LIMIT num`：（可选）限制返回数量，范围 1-10000
- `LIKE 'pattern'`：（可选）按 job_id 模式匹配（支持 `%` 和 `_`）

默认显示最近 7 天内的作业，最多 10000 条。

## 示例

```sql
-- 查看所有作业（最近7天）
SHOW JOBS;

-- 查看指定集群的作业
SHOW JOBS IN VCLUSTER default_ap;

-- 查看执行时间超过2分钟的作业
SHOW JOBS IN VCLUSTER default_ap WHERE execution_time > INTERVAL 2 MINUTE;

-- 限制返回100条
SHOW JOBS LIMIT 100;

-- 按 job_id 模糊匹配
SHOW JOBS LIKE '2024%';
```

## 作业状态说明

| 状态 | 含义 |
|---|---|
| 初始化 | SQL 编译优化阶段 |
| 集群启动中 | 等待 VCluster 启动 |
| 等待执行 | 排队等待资源 |
| 正在执行 | 正在处理数据 |
| 执行成功 | 运行结束 |
| 执行失败 | 运行失败 |
