---
name: clickzetta-dba-guide
description: |
  ClickZetta Lakehouse DBA 日常运维操作手册。集中覆盖 DBA 最常用的 8 类操作：
  用户与权限管理、计算集群运维、作业监控与诊断、数据恢复与保护、
  存储优化与维护、网络策略与安全、Schema 与对象管理、成本与资源分析。
  每个操作提供可直接执行的 SQL，并标注 ClickZetta 特有限制。
  当用户说"创建用户"、"授权"、"撤销权限"、"启停集群"、"调整集群规格"、
  "取消作业"、"慢查询"、"恢复误删表"、"UNDROP"、"RESTORE"、
  "小文件合并"、"OPTIMIZE"、"ANALYZE TABLE"、"网络策略"、"IP 白名单"、
  "动态脱敏"、"成本分析"、"存储用量"、"DBA 操作"时触发。
---

# ClickZetta Lakehouse DBA 运维手册

---

## 模块 1：用户与权限管理

### 用户管理

```sql
-- 创建用户（设置默认集群和 Schema）
CREATE USER alice DEFAULT_VCLUSTER default_ap DEFAULT_SCHEMA my_schema;

-- 修改用户默认集群
ALTER USER alice SET DEFAULT_VCLUSTER = analytics_cluster;

-- 删除用户（从当前工作空间移除）
DROP USER alice;

-- 查看所有用户
SHOW USERS;
```

### 角色管理

```sql
-- 创建自定义角色（仅工作空间级，仅 SQL）
CREATE ROLE data_engineer;

-- 将角色授予用户
GRANT ROLE data_engineer TO USER alice;

-- 撤销角色
REVOKE ROLE data_engineer FROM USER alice;

-- 查看所有角色
SHOW ROLES;

-- 查看用户权限
SHOW GRANTS TO USER alice;
SHOW GRANTS TO ROLE data_engineer;
```

### 权限授予

```sql
-- 授予 Schema 下所有表的读权限
GRANT SELECT ON ALL TABLES IN SCHEMA my_schema TO ROLE data_engineer;

-- 授予单张表的读写权限
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE my_schema.orders TO USER alice;

-- 授予创建表的权限
GRANT CREATE TABLE ON SCHEMA my_schema TO ROLE data_engineer;

-- 授予使用集群的权限
GRANT USE ON VCLUSTER default_ap TO ROLE data_engineer;

-- 授予 information_schema 查询权限
GRANT ALL ON ALL VIEWS IN SCHEMA information_schema TO ROLE data_engineer;

-- 批量授权（Schema 级别）
GRANT SELECT ON ALL TABLES IN SCHEMA ods TO ROLE analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA dwd TO ROLE analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA dws TO ROLE analyst;
```

### 权限撤销

```sql
-- 撤销表权限
REVOKE SELECT ON TABLE my_schema.orders FROM USER alice;

-- 撤销 Schema 创建权限
REVOKE CREATE TABLE ON SCHEMA my_schema FROM ROLE data_engineer;
```

### 动态脱敏（列级安全，邀测功能）

```sql
-- 创建脱敏函数（基于角色）
CREATE FUNCTION my_schema.phone_masking(phone STRING)
RETURNS STRING
AS CASE
  WHEN ARRAY_CONTAINS(current_roles(), 'data_admin') THEN phone
  ELSE CONCAT(SUBSTR(phone, 1, 3), '****', SUBSTR(phone, 8, 4))
END;

-- 绑定脱敏策略到列
ALTER TABLE my_schema.users
CHANGE COLUMN phone SET MASK my_schema.phone_masking;

-- 解除脱敏
ALTER TABLE my_schema.users
CHANGE COLUMN phone UNSET MASK;
```

**ClickZetta 特有限制：**
- 无超级用户，所有操作必须明确授权
- `instance_admin` 不能直接操作工作空间数据
- 自定义角色仅工作空间级，不支持实例级自定义角色

---

## 模块 2：计算集群运维

### 启停与状态

```sql
-- 启动集群
ALTER VCLUSTER my_cluster RESUME;
ALTER VCLUSTER IF EXISTS my_cluster RESUME;

-- 停止集群
ALTER VCLUSTER my_cluster SUSPEND;
ALTER VCLUSTER my_cluster SUSPEND FORCE;  -- 强制停止（中断运行中的作业）

-- 取消集群所有作业
ALTER VCLUSTER my_cluster CANCEL ALL JOBS;

-- 查看集群状态
SHOW VCLUSTERS;
SHOW VCLUSTERS WHERE state = 'RUNNING';
SHOW VCLUSTERS WHERE state = 'SUSPENDED';
DESC VCLUSTER my_cluster;
DESC VCLUSTER EXTENDED my_cluster;

-- 切换当前会话使用的集群
USE VCLUSTER my_cluster;
```

### 调整规格

```sql
-- 通用型（GP）：固定规格
ALTER VCLUSTER my_gp SET VCLUSTER_SIZE = 8;

-- 通用型（GP）：弹性规格
ALTER VCLUSTER my_gp SET MIN_VCLUSTER_SIZE = 2 MAX_VCLUSTER_SIZE = 16;

-- 分析型（AP）：调整副本数
ALTER VCLUSTER my_ap SET MIN_REPLICAS = 1 MAX_REPLICAS = 4;

-- 分析型（AP）：调整最大并发
ALTER VCLUSTER my_ap SET MAX_CONCURRENCY = 16;

-- 设置查询超时（秒，-1 表示无限制）
ALTER VCLUSTER my_cluster SET QUERY_RUNTIME_LIMIT_IN_SECOND = 3600;
```

### 自动停止与启动

```sql
-- 设置 60 秒无作业自动停止，有作业自动启动
ALTER VCLUSTER my_cluster SET
  AUTO_SUSPEND_IN_SECOND = 60
  AUTO_RESUME = TRUE;

-- 关闭自动停止
ALTER VCLUSTER my_cluster SET AUTO_SUSPEND_IN_SECOND = -1;
```

### AP 集群预加载缓存

```sql
-- 设置预加载表（集群启动时自动缓存最新数据）
ALTER VCLUSTER my_ap SET PRELOAD_TABLES = "sales.orders,sales.products";

-- 查看缓存状态
SHOW PRELOAD CACHED STATUS;
SHOW EXTENDED PRELOAD CACHED STATUS;
```

**ClickZetta 特有限制：**
- OPTIMIZE（小文件合并）仅 GP 集群支持，AP 集群不生效
- 分析型集群规格步长为 2^n（1/2/4/8/16...），通用型步长为 1

---

## 模块 3：作业监控与诊断

### 实时作业查看

```sql
-- 查看最近作业（最多 7 天，10000 条）
SHOW JOBS LIMIT 20;
SHOW JOBS IN VCLUSTER default_ap LIMIT 20;

-- 取消指定作业
CANCEL JOB '2026050118342658136171272';

-- 查看执行计划
EXPLAIN SELECT * FROM orders WHERE order_date = '2024-01-01';
EXPLAIN EXTENDED SELECT * FROM orders WHERE order_date = '2024-01-01';
```

### 历史作业分析（information_schema）

```sql
-- 慢查询 TOP 20（最近 7 天）
SELECT job_id, job_creator, execution_time, input_bytes, job_text
FROM information_schema.job_history
WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 7 DAY AS DATE)
  AND status = 'SUCCEED'
ORDER BY execution_time DESC
LIMIT 20;

-- 失败作业（最近 24 小时）
SELECT job_id, job_creator, error_message, start_time, job_text
FROM information_schema.job_history
WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 1 DAY AS DATE)
  AND status = 'FAILED'
ORDER BY start_time DESC;

-- 按用户统计 CRU 消耗（最近 30 天）
SELECT job_creator,
       COUNT(*) AS job_count,
       ROUND(SUM(cru), 2) AS total_cru,
       ROUND(AVG(execution_time), 1) AS avg_exec_sec
FROM information_schema.job_history
WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 30 DAY AS DATE)
  AND status = 'SUCCEED'
GROUP BY job_creator
ORDER BY total_cru DESC;

-- 按集群统计作业分布
SELECT virtual_cluster,
       COUNT(*) AS job_count,
       ROUND(SUM(cru), 2) AS total_cru
FROM information_schema.job_history
WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 7 DAY AS DATE)
GROUP BY virtual_cluster
ORDER BY total_cru DESC;
```

---

## 模块 4：数据恢复与保护

### 恢复误删对象

```sql
-- 查看已删除的表（delete_time 不为 NULL）
SHOW TABLES HISTORY IN my_schema;
SHOW TABLES HISTORY LIKE '%orders%';

-- 恢复误删的表/动态表/物化视图
UNDROP TABLE my_schema.orders;
UNDROP TABLE my_schema.my_dynamic_table;
UNDROP TABLE my_schema.my_mv;
```

### 回滚到历史版本

```sql
-- 查看表的版本历史
DESC HISTORY my_schema.orders;
-- 返回：version, time, total_rows, total_bytes, user, operation, job_id

-- 恢复到指定时间点（覆盖当前数据）
RESTORE TABLE my_schema.orders TO TIMESTAMP AS OF '2024-01-15 10:00:00';
RESTORE TABLE my_schema.orders TO TIMESTAMP AS OF CURRENT_TIMESTAMP - INTERVAL 2 HOURS;

-- 查询历史数据（不覆盖，仅查看）
SELECT * FROM my_schema.orders TIMESTAMP AS OF '2024-01-15 10:00:00';
```

### 设置数据保留周期

```sql
-- 设置 Time Travel 保留 30 天（范围 0-90）
ALTER TABLE my_schema.orders SET PROPERTIES ('data_retention_days' = '30');

-- 查看当前设置
SHOW CREATE TABLE my_schema.orders;
```

**ClickZetta 特有限制：**
- `RESTORE TABLE` 目标时间点不能早于表创建时间
- `UNDROP` 需在 `data_retention_days` 保留期内（默认 1 天）
- 物化视图支持 UNDROP，但不支持 RESTORE

---

## 模块 5：存储优化与维护

### 小文件合并

```sql
-- 手动触发小文件合并（异步，仅 GP 集群）
OPTIMIZE my_schema.orders;

-- 同步执行（等待完成）
OPTIMIZE my_schema.orders OPTIONS('cz.sql.optimize.table.async' = 'false');

-- 只优化特定分区
OPTIMIZE my_schema.orders WHERE dt = '2024-01-01';
OPTIMIZE my_schema.orders WHERE dt = '2024-01-01' AND region = 'cn';

-- DML 写入时自动触发合并（GP 集群）
SET cz.sql.compaction.after.commit = true;
INSERT INTO my_schema.orders SELECT * FROM staging;
```

### 统计信息收集

```sql
-- 收集表统计信息（优化查询计划）
ANALYZE TABLE my_schema.orders COMPUTE STATISTICS;

-- 仅收集大小，不扫描数据（快速）
ANALYZE TABLE my_schema.orders COMPUTE STATISTICS NOSCAN;

-- 收集指定列的统计信息
ANALYZE TABLE my_schema.orders COMPUTE STATISTICS FOR COLUMNS order_date, customer_id;

-- 收集 Schema 下所有表
ANALYZE TABLES IN my_schema COMPUTE STATISTICS;
```

### 清空数据

```sql
-- 清空整张表（保留表结构）
TRUNCATE TABLE my_schema.staging;

-- 清空指定分区
TRUNCATE TABLE my_schema.orders WHERE dt = '2024-01-01';
```

### 查看存储用量

```sql
-- 当前 Schema 下大表排行
SELECT table_schema, table_name,
       ROUND(bytes / 1024.0 / 1024 / 1024, 2) AS size_gb,
       row_count
FROM information_schema.tables
WHERE table_type = 'MANAGED_TABLE'
ORDER BY bytes DESC
LIMIT 20;

-- Sort Key 推荐（系统自动分析）
SELECT table_name, col, statement, ratio
FROM information_schema.sortkey_candidates
ORDER BY ratio DESC;
```

---

## 模块 6：网络策略与安全

### 网络策略管理

```sql
-- 创建网络策略（白名单）
CREATE NETWORK POLICY office_policy
  ALLOWED_IP_LIST = ('10.0.0.0/8', '192.168.1.0/24')
  COMMENT = '办公网络白名单';

-- 创建网络策略（白名单 + 黑名单）
CREATE NETWORK POLICY strict_policy
  ALLOWED_IP_LIST = ('10.0.0.0/8')
  BLOCKED_IP_LIST = ('10.0.1.100')
  COMMENT = '严格访问控制';

-- 修改网络策略（覆盖式，必须包含所有 IP）
ALTER NETWORK POLICY office_policy
  ALLOWED_IP_LIST = ('10.0.0.0/8', '172.16.0.0/12')
  BLOCKED_IP_LIST = ('10.0.1.100');

-- 停用/启用策略
ALTER NETWORK POLICY office_policy INACTIVATE;
ALTER NETWORK POLICY office_policy ACTIVATE;

-- 删除策略
DROP NETWORK POLICY IF EXISTS office_policy;

-- 查看所有策略（注意：单数 POLICY，无 S）
SHOW NETWORK POLICY;

-- 查看策略详情
DESC NETWORK POLICY office_policy;
```

**关键规则（Deny 优先）：**
- 无任何策略时：允许所有 IP
- 有白名单策略时：不在白名单的 IP 被拒绝
- 黑名单命中时：无论白名单如何，该 IP 被拒绝
- MySQL 协议：只要有任何生效策略，所有 MySQL 流量均被拦截
- 策略生效延迟：最多 5 分钟

---

## 模块 7：Schema 与对象管理

### Schema 管理

```sql
-- 创建 Schema
CREATE SCHEMA ods;
CREATE SCHEMA IF NOT EXISTS dwd;

-- 修改 Schema 注释
ALTER SCHEMA ods SET COMMENT 'ODS 原始数据层';

-- 重命名 Schema
ALTER SCHEMA old_name RENAME TO new_name;

-- 删除 Schema（级联删除所有对象）
DROP SCHEMA IF EXISTS temp_schema CASCADE;

-- 切换默认 Schema
USE SCHEMA my_schema;
```

### 表管理

```sql
-- 修改表：加列
ALTER TABLE my_schema.orders ADD COLUMN (discount DECIMAL(5,2) COMMENT '折扣率');

-- 修改表：改列注释
ALTER TABLE my_schema.orders CHANGE COLUMN order_id SET COMMENT '订单唯一标识';

-- 修改表：设置生命周期
ALTER TABLE my_schema.orders SET PROPERTIES ('data_lifecycle' = '90');

-- 修改表：设置 Sort Key
ALTER TABLE my_schema.orders SET PROPERTIES ('hint.sort.columns' = 'order_date');

-- 重命名表
ALTER TABLE my_schema.orders RENAME TO my_schema.orders_v2;

-- 删除表（可 UNDROP 恢复）
DROP TABLE IF EXISTS my_schema.temp_table;

-- 删除动态表
DROP DYNAMIC TABLE IF EXISTS my_schema.my_dt;

-- 删除物化视图
DROP MATERIALIZED VIEW IF EXISTS my_schema.my_mv;
```

### 批量对象查看

```sql
-- 统计各类型对象数量
SELECT
  CASE WHEN is_view THEN 'VIEW'
       WHEN is_materialized_view THEN 'MV'
       WHEN is_dynamic THEN 'DT'
       WHEN is_external THEN 'EXTERNAL'
       ELSE 'TABLE' END AS type,
  COUNT(*) AS cnt
FROM (SHOW TABLES IN my_schema)
GROUP BY 1;

-- 查找大于 30 天未更新的表（潜在废弃表）
SELECT table_schema, table_name, last_modify_time,
       ROUND(bytes / 1024.0 / 1024 / 1024, 2) AS size_gb
FROM information_schema.tables
WHERE table_type = 'MANAGED_TABLE'
  AND last_modify_time < CURRENT_TIMESTAMP - INTERVAL 30 DAY
ORDER BY bytes DESC;
```

---

## 模块 8：成本与资源分析（需 INSTANCE ADMIN）

```sql
-- 本月各工作空间计算费用
SELECT workspace_name, sku_name,
       ROUND(SUM(measurements_consumption), 2) AS total_cru,
       ROUND(SUM(amount), 2) AS total_yuan
FROM SYS.information_schema.instance_usage
WHERE measurement_start >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY workspace_name, sku_name
ORDER BY total_yuan DESC;

-- 本月各工作空间存储费用
SELECT workspace_name, sku_name,
       ROUND(SUM(measurements_consumption), 4) AS consumption,
       measurements_unit,
       ROUND(SUM(amount), 4) AS total_yuan
FROM SYS.information_schema.storage_metering
WHERE measurement_start >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY workspace_name, sku_name, measurements_unit
ORDER BY workspace_name, total_yuan DESC;

-- 跨空间存储用量排行
SELECT workspace_name,
       ROUND(workspace_storage / 1024.0 / 1024 / 1024, 2) AS storage_gb
FROM SYS.information_schema.workspaces
WHERE delete_time IS NULL
ORDER BY workspace_storage DESC;

-- 跨空间大表排行（大于 10GB）
SELECT table_catalog, table_schema, table_name,
       ROUND(bytes / 1024.0 / 1024 / 1024, 2) AS size_gb, row_count
FROM SYS.information_schema.tables
WHERE delete_time IS NULL AND bytes > 10 * 1024 * 1024 * 1024
ORDER BY bytes DESC;
```

---

## ClickZetta DBA 特有注意事项

| 场景 | 注意事项 |
|---|---|
| 权限体系 | 无超级用户；`instance_admin` 不能直接操作工作空间数据 |
| 自定义角色 | 仅工作空间级，不支持实例级；只能 SQL 创建，不支持 Web 端 |
| OPTIMIZE | 仅 GP 集群支持；AP 集群不支持小文件合并 |
| UNDROP | 需在 `data_retention_days` 保留期内（默认 1 天） |
| RESTORE | 目标时间点不能早于表创建时间 |
| 网络策略 | Deny 优先；MySQL 协议有任何策略即全部拦截；生效延迟最多 5 分钟 |
| 动态脱敏 | 邀测功能，需联系技术支持开通 |
| 集群规格 | AP 集群步长 2^n；GP 集群步长 1；同步型最小 0.25 CRU |
