# Dynamic Table SQL 限制与支持矩阵

本文档列出 Dynamic Table 增量计算支持和不支持的 SQL 模式。

## JOIN 类型支持

| JOIN 类型 | 增量支持 | 说明 |
|-----------|---------|------|
| INNER JOIN | ✅ | 完全支持 |
| LEFT JOIN (LEFT OUTER) | ✅ | 完全支持 |
| RIGHT JOIN (RIGHT OUTER) | ✅ | 完全支持 |
| FULL OUTER JOIN | ✅ | 完全支持 |
| LEFT SEMI JOIN | ✅ | 完全支持 |
| LEFT ANTI JOIN | ✅ | 完全支持 |

## 聚合函数支持

### 支持增量计算的聚合函数

- `SUM`, `SUM0`, `COUNT`, `COUNT_IF`, `MIN`, `MAX`, `MIN_BY`, `MAX_BY`
- `AVG`, `STDDEV_SAMP`, `STDDEV_POP`, `VAR_SAMP`, `VAR_POP`
- `Percentile`, `Median`, `COUNT_DISTINCT`
- `BIT_OR`, `BIT_AND`, `BIT_XOR`, `BOOL_OR`, `BOOL_AND`
- `GROUP_BITMAP` 系列
- `COLLECT_SET`, `COLLECT_LIST`, `COLLECT_SET_ON_ARRAY`, `COLLECT_LIST_ON_ARRAY`
- `MAP_AGG`, `WM_CONCAT`

### 结果不稳定的聚合函数（增量结果可能与全量不一致）

- `ANY_VALUE`, `FIRST_VALUE`, `LAST_VALUE`
- `APPROX_COUNT_DISTINCT`, `APPROX_HISTOGRAM`, `APPROX_TOP_K`, `APPROX_PERCENTILE`
- `JSON_MERGE_AGG`

## 窗口函数支持

### 支持的窗口函数

- `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `PERCENT_RANK`
- `FIRST_VALUE`, `LAST_VALUE`, `NTH_VALUE`
- `COUNT`, `SUM`, `SUM0`, `MIN`, `MAX`, `AVG`
- `LEAD`, `LAG`, `CUME_DIST`, `NTILE`
- `COLLECT_LIST`, `COLLECT_SET`, `COLLECT_SET_ON_ARRAY`, `COLLECT_LIST_ON_ARRAY`

## ORDER BY / LIMIT / OFFSET

支持 `ORDER BY`、`LIMIT`、`OFFSET` 语法。

⚠️ 不建议在 DT 中使用全局 `ORDER BY`。全局排序在每次增量刷新时开销非常大，推荐将排序逻辑放在下游查询数据时执行，而非 ETL 建模阶段。

## 非确定性函数

非确定性函数（如 `NOW()`、`CURRENT_TIMESTAMP`、`CURRENT_DATE`、`random()` 等）在不参与计算逻辑时默认支持。具体来说，只要这些函数不出现在以下位置，就可以正常使用：
- 窗口函数的 `PARTITION BY` key
- `JOIN` key
- `GROUP BY` key
- 其他函数的入参

典型场景：在 SELECT 中直接输出数据处理时间，记录每条数据被 DT 刷新处理的时刻：

```sql
CREATE DYNAMIC TABLE order_with_process_time AS
SELECT
    id,
    amount,
    status,
    CURRENT_TIMESTAMP AS process_time  -- 记录刷新时的处理时间，直接输出到目标表
FROM orders
WHERE status = 'completed';
```

时间函数会在每次 REFRESH 时被常量折叠为当次刷新的时间戳。

## UDF / UDAF / UDTF

自定义函数需要在创建时声明为确定性函数（deterministic），才能在 DT 中使用增量计算。未声明确定性的自定义函数会导致增量计算被禁用。

## 源表类型限制

- **虚拟视图（VIEW）**：不能作为 DT 的输入表，会禁用增量计算
- **外部表（External Table）**：不支持增量计算
