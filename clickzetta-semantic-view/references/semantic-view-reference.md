# 语义视图完整语法参考

> 来源：https://www.yunqi.tech/documents/semantic_view
> 功能状态：邀测（1.3 版本起）

---

## CREATE SEMANTIC VIEW 完整语法

```sql
CREATE SEMANTIC VIEW <视图名称>
TABLES (
    <逻辑表定义> [ , ... ]
)
[ FILTERS (
    <过滤器定义> [ , ... ]
) ]
DIMENSIONS (
    <维度定义> [ , ... ]
)
METRICS (
    <指标定义> [ , ... ]
)
[ COMMENT = '<视图说明>' ];
```

**约束**：`DIMENSIONS` 和 `METRICS` 至少包含其中一个。

---

## 逻辑表定义语法

```sql
<表别名> AS <schema>.<物理表名>
    PRIMARY KEY ( <列名> [ , ... ] )
    [ FOREIGN KEY ( <列名> ) REFERENCES <其他逻辑表别名> ]
    [ WITH SYNONYMS ( '<同义词>' [ , ... ] ) ]
    [ COMMENT = '<说明>' ]
```

| 参数 | 说明 |
|---|---|
| `<表别名> AS <schema>.<物理表>` | 为物理表指定逻辑别名，后续维度/指标/外键均用此别名引用 |
| `PRIMARY KEY` | 主键列，用于确定表间关系类型（一对多/一对一） |
| `FOREIGN KEY ... REFERENCES` | 外键关系，引擎据此自动处理 JOIN；引用目标必须是逻辑表别名 |
| `WITH SYNONYMS` | 逻辑表同义词，增强可发现性 |

**注意**：被外键引用的表必须在 TABLES 子句中先定义。

---

## 过滤器定义语法

```sql
<逻辑表别名>.<过滤器名> AS <布尔表达式>
```

示例：
```sql
FILTERS (
    customers.is_building AS customers.c_mktsegment = 'BUILDING',
    orders.is_open AS orders.o_orderstatus = 'O'
)
```

**重要**：FILTERS 是面向 AI/元数据层的语义注解，**不能**作为 `semantic_view()` 函数参数直接传入。若要在查询中过滤，需将对应列定义为 DIMENSION，再用外层 WHERE 子句。

---

## 维度定义语法

```sql
{ <逻辑表别名>.<维度名> | <维度名> } AS <表达式>
    [ WITH SYNONYMS = ( '<同义词>' [ , ... ] ) ]
    [ is_unique = { true | false } ]
    [ is_time = { true | false } ]
    [ enum_values = [ <值1>, <值2>, ... ] ]
    [ COMMENT = '<说明>' ]
```

| 参数 | 说明 |
|---|---|
| `AS <表达式>` | 可以是列名，也可以是计算表达式（如 `YEAR(o_orderdate)`） |
| `WITH SYNONYMS` | 维度同义词，用户可用不同业务术语引用同一维度 |
| `is_unique = true` | 标识该维度值唯一（如客户名称），帮助引擎优化 |
| `is_time = true` | 标识为时间类型维度（如订单日期） |
| `enum_values` | 限定允许的枚举值，提升查询准确性 |

---

## 指标定义语法

```sql
<逻辑表别名>.<指标名> AS <聚合表达式>
    [ COMMENT = '<说明>' ]
```

支持的聚合函数：`COUNT`、`AVG`、`SUM`、`MIN`、`MAX`

示例：
```sql
METRICS (
    orders.total_revenue AS SUM(o_totalprice)
        COMMENT = '总收入',
    orders.avg_order_value AS AVG(o_totalprice)
        COMMENT = '平均订单金额',
    customers.customer_count AS COUNT(c_custkey)
        COMMENT = '客户总数'
)
```

---

## semantic_view() 查询函数语法

```sql
SELECT *
FROM semantic_view(
    <视图名称>,
    DIMENSIONS <维度名> [ , DIMENSIONS <维度名> ... ],
    METRICS <指标名> [ , METRICS <指标名> ... ]
)
[ WHERE <过滤条件> ];
```

- 维度名可用限定名（`表别名.维度名`）或短名（名称唯一时）
- 结果自动按指定维度分组，无需写 GROUP BY
- WHERE 子句中的列名使用短名（不含表别名前缀）

---

## 管理命令

| 命令 | 说明 |
|---|---|
| `CREATE SEMANTIC VIEW` | 创建语义视图 |
| `DROP SEMANTIC VIEW IF EXISTS <名称>` | 删除语义视图 |
| `SHOW SEMANTIC VIEWS` | 列出当前 Schema 所有语义视图 |
| `SHOW SEMANTIC VIEWS IN <schema>` | 列出指定 Schema 的语义视图 |
| `DESC EXTENDED <名称>` | 查看详细定义（逻辑表/维度/指标/外键/索引） |

---

## 最佳实践

```sql
-- 1. 幂等创建（始终先删再建）
DROP SEMANTIC VIEW IF EXISTS my_view;
CREATE SEMANTIC VIEW my_view ...;

-- 2. 使用有意义的业务术语命名
-- 好：customer_name, total_revenue, order_date
-- 差：c_name, sum_totalprice, o_orderdate

-- 3. 合理设置维度元数据
-- is_time=true 用于日期/时间维度
-- is_unique=true 用于主键类维度（如客户ID、订单号）
-- enum_values 用于状态类维度（如订单状态）

-- 4. 计算维度示例
DIMENSIONS (
    orders.order_year AS YEAR(o_orderdate)   -- 从日期提取年份
        COMMENT = '下单年份',
    orders.order_month AS MONTH(o_orderdate) -- 从日期提取月份
        COMMENT = '下单月份'
)
```
