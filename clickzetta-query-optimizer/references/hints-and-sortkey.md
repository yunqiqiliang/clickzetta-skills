# Map Join 与 Sort Key 推荐参考

> 来源：https://www.yunqi.tech/documents/mapjoin 和 https://www.yunqi.tech/documents/auto-index

---

## Map Join（小表广播优化）

### 语法

```sql
SELECT /*+ MAPJOIN (small_table_alias) */ *
FROM large_table t1
JOIN small_table t2 ON t1.id = t2.id;
```

### 说明

- 将小表广播到各节点，在 Map 阶段完成 JOIN，避免 Shuffle
- **小表大小限制：1GB**，超过则 Map Join 失败或退化为普通 JOIN
- 适用于小表 JOIN 大表，不适用于大表 JOIN 大表

### 示例

```sql
-- 员工与部门关联
SELECT /*+ MAPJOIN (dept) */ *
FROM employees emp
JOIN departments dept ON emp.dept_id = dept.dept_id;

-- 订单与客户关联
SELECT /*+ MAPJOIN (customer) */ *
FROM orders o
JOIN customers customer ON o.customer_id = customer.customer_id;
```

---

## Sort Key 推荐（自动索引建议）

### 启用自动收集

```sql
-- 按天收集（推荐）
ALTER WORKSPACE workspace_name SET PROPERTIES (auto_index='day');

-- 自定义参数：天/月, 最近N分钟job, 最少重复次数, 最多job数
ALTER WORKSPACE workspace_name SET PROPERTIES (auto_index='day,150,5,100');
```

参数说明：
- 第 1 个参数：`day`（每天）或 `month`（每月 1 号），收集时间为晚上 6 点
- 第 2 个参数：使用最近多少分钟的 job（默认 150）
- 第 3 个参数：job 需要重复多少次才被采用（默认 5）
- 第 4 个参数：每列最多使用的 job 数（默认 100）

### 查询推荐结果

```sql
SELECT * FROM information_schema.sortkey_candidates;
```

返回字段：`table_name`、`col`（推荐列）、`statement`（可直接执行的 ALTER 语句）、`ratio`（估算提升效果百分比）

### 应用推荐

```sql
-- 直接执行 statement 列中的 SQL 即可设置 sort key
ALTER TABLE schema.table_name SET PROPERTIES("hint.sort.columns"="column_name");
```

### 建议

执行前先对表收集统计信息，提高推荐准确性：

```sql
ANALYZE TABLE schema.table_name;
```
