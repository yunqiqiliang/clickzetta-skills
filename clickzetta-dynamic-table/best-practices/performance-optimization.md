# Dynamic Table 性能优化指南

本文档从 SQL 写法、数据特征、管道设计三个维度，帮助用户写出增量刷新性能更好的 DT。

## 核心原则：增量刷新的代价模型

增量刷新的性能取决于三个因素：
1. **变更量占比**：每次刷新时，源表中有多少数据发生了变化。变更量越小，增量越划算
2. **算子类型**：不同 SQL 算子的增量代价差异很大
3. **数据局部性**：变更数据在 JOIN key / GROUP BY key / PARTITION BY key 上的分布是否集中

当变更量超过总数据量的较大比例时，增量刷新可能反而比全量刷新更慢，因为增量需要额外的变更数据计算、去重合并、状态表读写等开销。

## SQL 写法优化

### 1. 优先使用 INNER JOIN 而非 OUTER JOIN

INNER JOIN 的增量计算比 OUTER JOIN 更高效：
- INNER JOIN：只需要计算 A 的变更数据 JOIN B 的全量数据 + A 的全量数据 JOIN B 的变更数据
- LEFT/RIGHT/FULL OUTER JOIN：还需要额外处理 NULL 填充、反向撤回等逻辑

如果业务上可以保证参照完整性（即 JOIN key 一定能匹配），优先用 INNER JOIN。

```sql
-- ❌ 不必要的 LEFT JOIN（如果 product 一定存在）
SELECT o.*, p.name FROM orders o LEFT JOIN products p ON o.pid = p.id;

-- ✅ 改用 INNER JOIN
SELECT o.*, p.name FROM orders o INNER JOIN products p ON o.pid = p.id;
```

### 2. 减少不必要的 DISTINCT

每次增量刷新时，DISTINCT 需要对受影响的 key 做重算。如果上游数据已经去重，或者可以通过其他方式保证唯一性，去掉 DISTINCT。

```sql
-- ❌ 冗余的 DISTINCT
SELECT DISTINCT user_id, user_name FROM user_events;
```

### 3. 窗口函数必须有 PARTITION BY

没有 PARTITION BY 的窗口函数会导致每次增量刷新都全量重算整个窗口。加上 PARTITION BY 后，只需要重算受影响的分区。

```sql
-- ❌ 全局窗口，每次增量都全量重算
SELECT *, ROW_NUMBER() OVER (ORDER BY created_at DESC) AS rn FROM events;

-- ✅ 加上 PARTITION BY，只重算有变更的分区
SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY created_at DESC) AS rn FROM events;
```

### 4. 聚合 key 尽量使用简单列引用

复合表达式作为 GROUP BY key 会降低增量效率，因为引擎需要对表达式求值后才能判断哪些 key 受影响。

```sql
-- ❌ 复合表达式作为 GROUP BY key
SELECT DATE_TRUNC('hour', ts) AS hour, SUM(amount)
FROM transactions
GROUP BY DATE_TRUNC('hour', ts);

-- ✅ 如果可能，在上游预计算好 key 列
-- 或者拆分为两个 DT（见下文"管道拆分"）
```

### 5. 尽可能使用分区条件限制数据范围

在 DT 的 SQL 中对源表添加分区过滤条件，可以显著减少每次增量刷新需要扫描的数据量。

```sql
-- ❌ 不加分区条件，每次扫描全表
SELECT o.*, p.name
FROM orders o JOIN products p ON o.pid = p.id;

-- ✅ 通过分区条件限制数据范围
SELECT o.*, p.name
FROM orders o JOIN products p ON o.pid = p.id
WHERE o.ds = SESSION_CONFIGS()['dt.args.ds'];
```

## 管道拆分：复杂 DT 拆成多级

当一个 DT 的 SQL 包含多个 JOIN + 聚合 + 窗口函数时，考虑拆分为多个 DT，每个 DT 只做一件事。

好处：
- 每个 DT 的增量计算更简单、更快
- 中间 DT 可以被多个下游 DT 复用
- 出问题时更容易定位是哪一层的问题
- 不同层可以使用不同的优化策略

## 数据特征与增量效率

### 变更量占比

增量刷新在变更量占总数据量比例较小时效果最好。经验值：
- < 5%：增量刷新通常显著优于全量
- 5% ~ 20%：取决于具体算子和数据分布
- \> 20%：可能需要评估是否全量刷新更合适

### Append-Only 源表

如果源表只有 INSERT 没有 UPDATE/DELETE 可以显著优化：
- 增量引擎知道变更数据只有新增（无撤回），可以跳过去重合并等操作
- 聚合可以直接累加，不需要维护完整的中间状态

### 变更数据的分布

如果变更数据集中在少数 key 上（如最近时间段的数据），增量效率高。如果变更分散在大量 key 上，聚合和窗口函数需要重算大量分区，效率下降。