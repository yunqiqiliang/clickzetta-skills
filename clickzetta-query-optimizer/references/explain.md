# EXPLAIN 命令参考

> 来源：https://www.yunqi.tech/documents/EXPLAIN

## 语法

```sql
EXPLAIN [EXTENDED] query_statement
```

## 两种模式

### 基础模式（EXPLAIN）

显示物理执行计划，用于快速理解查询执行方式。

```sql
EXPLAIN SELECT * FROM orders LIMIT 5;
```

输出示例：
```
Type: DML
Plan: PhysicalTableSink() name=TableSink0 stage=stg0
  PhysicalTableScan(orders, a) as [0] name=TableScan1
```

### 扩展模式（EXPLAIN EXTENDED）

显示完整的逻辑执行计划 + 物理执行计划，包含表达式转换、系统列、优化过程。

```sql
EXPLAIN EXTENDED SELECT * FROM orders LIMIT 5;
```

输出包含：
- `[LogicalPlan]`：逻辑执行计划
- `[PhysicalPlan]`：物理执行计划
- 系统隐藏列信息（`__commit_version`、`__change_type` 等）

## 常见操作符说明

| 操作符 | 说明 | 性能特征 |
|---|---|---|
| PhysicalTableScan | 从表读取数据 | 基础 I/O 操作 |
| PhysicalTableSink | 输出查询结果 | 固定开销 |
| PhysicalSort | 对数据排序 | O(n log n)，可能成为瓶颈 |
| PhysicalFilter | 条件过滤 | 线性操作，早期过滤是最佳实践 |
| PhysicalHashAggregate | 聚合操作 | 根据 GROUP BY 基数变化 |
| PhysicalJoin | JOIN 操作 | 复杂度取决于 JOIN 策略和数据量 |

## 使用建议

- 先用 `EXPLAIN` 快速确认执行路径
- 发现异常（如全表扫描、大量 Sort）再用 `EXPLAIN EXTENDED` 深入分析
- 关注 PhysicalJoin 的策略：是否触发了 MapJoin（小表广播）
