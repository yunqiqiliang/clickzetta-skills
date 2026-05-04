---
name: clickzetta-semantic-view
description: |
  创建和查询 ClickZetta Lakehouse 语义视图（Semantic View）。语义视图是架构级逻辑
  数据模型对象，通过声明逻辑表、维度、指标、过滤器，将复杂的多表 JOIN 和聚合逻辑封装
  为业务友好的语义层，使用 semantic_view() 函数查询，无需手写 JOIN。
  当前为邀测功能（1.3 版本起）。
  当用户说"创建语义视图"、"semantic view"、"语义层"、"定义指标"、"定义维度"、
  "semantic_view() 怎么用"、"统一指标口径"、"业务语义模型"、"逻辑表"、
  "DIMENSIONS"、"METRICS"、"FILTERS"、"DROP SEMANTIC VIEW"、
  "SHOW SEMANTIC VIEWS"时触发。
  Keywords: semantic view, dimension, metric, logical model, unified metrics, semantic layer
---

# ClickZetta 语义视图（Semantic View）

阅读 [references/semantic-view-reference.md](references/semantic-view-reference.md) 了解完整语法。

---

## 概述

语义视图是 ClickZetta Lakehouse 的**架构级逻辑数据模型对象**，解决两类核心问题：

- **数据分析**：统一维度和指标定义，业务用户无需编写复杂 JOIN 即可查询跨表数据
- **数据治理**：集中管理表关系、维度、指标定义，确保全组织使用相同数据口径

> ⚠️ 当前为**邀测功能**（1.3 版本），需联系技术支持开通。

---

## 四大组件

| 组件 | 关键字 | 说明 |
|---|---|---|
| 逻辑表 | `TABLES` | 映射物理表，声明主键和外键关系，引擎自动处理 JOIN |
| 维度 | `DIMENSIONS` | 分类属性（谁/什么/哪里/何时），支持计算维度 |
| 指标 | `METRICS` | 聚合度量（SUM/AVG/COUNT/MIN/MAX），业务 KPI |
| 过滤器 | `FILTERS` | 预定义可重用过滤条件（语义注解，不可直接传入查询） |

---

## 创建语义视图

```sql
CREATE SEMANTIC VIEW <视图名>
TABLES (
    <表别名> AS <schema>.<物理表>
        PRIMARY KEY (<列名>)
        [ FOREIGN KEY (<列名>) REFERENCES <其他表别名> ]
        [ WITH SYNONYMS ('<同义词>') ]
        [ COMMENT = '<说明>' ]
    [ , ... ]
)
[ FILTERS (
    <表别名>.<过滤器名> AS <布尔表达式>
    [ , ... ]
) ]
DIMENSIONS (
    { <表别名>.<维度名> | <维度名> } AS <表达式>
        [ WITH SYNONYMS = ('<同义词>' [ , ... ]) ]
        [ is_unique = { true | false } ]
        [ is_time = { true | false } ]
        [ enum_values = [ <值1>, <值2>, ... ] ]
        [ COMMENT = '<说明>' ]
    [ , ... ]
)
METRICS (
    <表别名>.<指标名> AS <聚合表达式>
        [ COMMENT = '<说明>' ]
    [ , ... ]
)
[ COMMENT = '<视图说明>' ];
```

### 完整示例（TPC-H 收入分析）

```sql
DROP SEMANTIC VIEW IF EXISTS tpch_rev_analysis;
CREATE SEMANTIC VIEW tpch_rev_analysis
TABLES (
    customers AS tpch.customer
        PRIMARY KEY (c_custkey)
        COMMENT = '客户主表',
    orders AS tpch.orders
        PRIMARY KEY (o_orderkey)
        FOREIGN KEY (o_custkey) REFERENCES customers
        WITH SYNONYMS ('销售订单')
        COMMENT = '订单表',
    line_items AS tpch.lineitem
        PRIMARY KEY (l_orderkey, l_linenumber)
        FOREIGN KEY (l_orderkey) REFERENCES orders
        COMMENT = '订单明细'
)
FILTERS (
    customers.is_building AS customers.c_mktsegment = 'BUILDING'
)
DIMENSIONS (
    customers.customer_name AS c_name
        WITH SYNONYMS = ('客户名称', 'customer name')
        is_unique = true
        COMMENT = '客户名称',
    orders.order_date AS o_orderdate
        is_time = true
        COMMENT = '下单日期',
    orders.order_year AS YEAR(o_orderdate)
        COMMENT = '下单年份',
    orders.order_status AS o_orderstatus
        enum_values = ['O', 'F', 'P']
        COMMENT = '订单状态'
)
METRICS (
    customers.customer_count AS COUNT(c_custkey)
        COMMENT = '客户总数',
    orders.avg_order_value AS AVG(o_totalprice)
        COMMENT = '平均订单金额',
    orders.total_revenue AS SUM(o_totalprice)
        COMMENT = '总收入'
)
COMMENT = '收入分析语义视图';
```

---

## 查询语义视图

使用 `semantic_view()` 表函数，**无需手写 JOIN 和 GROUP BY**：

```sql
-- 基础查询：按订单日期统计平均订单金额
SELECT * FROM semantic_view(
    tpch_rev_analysis,
    DIMENSIONS orders.order_date,
    METRICS orders.avg_order_value
);

-- 多维度查询：按日期和客户名称
SELECT * FROM semantic_view(
    tpch_rev_analysis,
    DIMENSIONS orders.order_date,
    DIMENSIONS customers.customer_name,
    METRICS orders.avg_order_value
);

-- 使用短名称（名称唯一时可省略表别名前缀）
SELECT * FROM semantic_view(
    tpch_rev_analysis,
    DIMENSIONS order_date,
    DIMENSIONS customer_name,
    METRICS avg_order_value
);

-- 加 WHERE 过滤（需将过滤列定义为 DIMENSION）
SELECT * FROM semantic_view(
    tpch_rev_analysis,
    DIMENSIONS customers.customer_name,
    DIMENSIONS orders.order_status,
    METRICS orders.total_revenue
) WHERE order_status = 'O';
```

### 与传统 SQL 对比

```sql
-- 传统 SQL（需手写 JOIN + GROUP BY）
SELECT o.o_orderdate, c.c_name, AVG(o.o_totalprice)
FROM tpch.orders o
JOIN tpch.customer c ON o.o_custkey = c.c_custkey
GROUP BY o.o_orderdate, c.c_name;

-- 语义视图（自动处理 JOIN 和聚合）
SELECT * FROM semantic_view(
    tpch_rev_analysis,
    DIMENSIONS order_date,
    DIMENSIONS customer_name,
    METRICS avg_order_value
);
```

---

## 管理命令

```sql
-- 删除（推荐先删再建，确保幂等）
DROP SEMANTIC VIEW IF EXISTS tpch_rev_analysis;

-- 列出当前 Schema 的所有语义视图
SHOW SEMANTIC VIEWS;
SHOW SEMANTIC VIEWS IN my_schema;

-- 查看详细定义（逻辑表、维度、指标、外键）
DESC EXTENDED tpch_rev_analysis;
```

---

## 注意事项

1. **TABLES 定义顺序**：被外键引用的表必须先定义（如 `customers` 必须在 `orders` 之前）
2. **FILTERS 是语义注解**：`FILTERS` 中的命名过滤器不能作为 `semantic_view()` 的参数，WHERE 子句只能引用 `DIMENSIONS` 中定义的列名（短名），不能用物理列名
3. **WHERE 只能用 DIMENSION 短名**：`WHERE customer_name = 'Alice'` ✅，`WHERE c_name = 'Alice'` ❌
4. **短名称 vs 限定名称**：名称在视图内唯一时可用短名称，有冲突时必须用 `表别名.名称`
5. **幂等创建**：始终先 `DROP SEMANTIC VIEW IF EXISTS` 再创建，避免重复执行报错
6. **计算维度**：DIMENSIONS 支持表达式，如 `YEAR(CAST(order_date AS DATE))` 提取年份
7. **指标聚合函数**：仅支持 `COUNT`、`AVG`、`SUM`、`MIN`、`MAX`
8. **DIMENSIONS 和 METRICS 可单独使用**：可以只查 METRICS（全局聚合），也可以只查 DIMENSIONS（去重列表）
