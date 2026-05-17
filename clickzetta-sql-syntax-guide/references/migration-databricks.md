# Databricks → ClickZetta 迁移指南

> 覆盖从 Databricks（Delta Lake）迁移到 ClickZetta Lakehouse 时的 SQL 兼容性问题，所有结论均经过真实 Lakehouse 验证。

---

## 对象概念映射

| Databricks | ClickZetta | 说明 |
|---|---|---|
| Catalog（内部数据） | WORKSPACE | 顶层命名空间，Catalog.Schema.Table ≈ Workspace.Schema.Table |
| Catalog（外部数据源） | EXTERNAL CATALOG | 联邦查询外部系统时的三层命名空间顶层（catalog.schema.table） |
| Database / Schema | SCHEMA | 相同 |
| Cluster / SQL Warehouse | VCLUSTER | 计算集群 |
| Delta Table（普通表） | TABLE | ClickZetta 默认 Parquet 存储，支持 Iceberg 格式 |
| Delta Table（增量计算） | DYNAMIC TABLE | 自动增量刷新，替代 DLT Pipeline |
| External Location | STORAGE CONNECTION + EXTERNAL VOLUME | STORAGE CONNECTION 负责认证，EXTERNAL VOLUME 负责挂载路径 |
| Unity Catalog（元数据治理） | 无完整对应 | ClickZetta 通过 RBAC + SCHEMA 权限管理实现部分治理能力 |
| Unity Catalog（外部数据联邦查询） | EXTERNAL CATALOG | 支持 Hive、Iceberg REST、Databricks Unity Catalog 联邦查询 |
| Structured Streaming | PIPE + TABLE STREAM | PIPE 负责持续摄入，TABLE STREAM 负责 CDC 变更捕获 |
| APPLY CHANGES INTO（DLT CDC） | TABLE STREAM + MERGE INTO | 先建 Stream 捕获变更，再用 MERGE 消费 |
| Auto Loader | PIPE（EVENT_NOTIFICATION 模式） | 文件上传即触发加载，仅支持 OSS/S3 |

---

## DDL 差异

### CREATE TABLE

```sql
-- Databricks Delta Lake
CREATE TABLE orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    customer_id INT,
    amount DECIMAL(18,2),
    status STRING DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT current_timestamp(),
    meta STRUCT<city: STRING, zip: STRING>,
    tags ARRAY<STRING>
)
USING DELTA
PARTITIONED BY (DATE(created_at))
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- ClickZetta 等价写法
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT IDENTITY(1),           -- GENERATED ALWAYS AS IDENTITY → IDENTITY
    customer_id INT,
    amount DECIMAL(18,2),
    status STRING DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT current_timestamp(),
    meta STRUCT<city:STRING, zip:STRING>,
    tags ARRAY<STRING>
)
-- 不需要 USING DELTA（默认 Parquet）
PARTITIONED BY (days(created_at));   -- DATE() → days() 转换函数
-- TBLPROPERTIES → PROPERTIES
-- CDC 通过 TABLE STREAM 实现，不需要 enableChangeDataFeed
```

### 不支持的 DDL

```sql
-- ❌ USING DELTA / USING PARQUET（ClickZetta 默认 Parquet，不需要指定）
CREATE TABLE t (...) USING DELTA;
CREATE TABLE t (...) USING PARQUET;

-- ❌ TBLPROPERTIES（用 PROPERTIES）
CREATE TABLE t (...) TBLPROPERTIES ('key' = 'value');
-- ✅ ClickZetta
CREATE TABLE t (...) PROPERTIES ('data_lifecycle' = '30');

-- ❌ GENERATED ALWAYS AS IDENTITY（用 IDENTITY）
id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1)
-- ✅ ClickZetta
id BIGINT IDENTITY(1)

-- ❌ OPTIMIZE ... ZORDER BY（ClickZetta 有 OPTIMIZE 但无 ZORDER）
OPTIMIZE orders ZORDER BY (customer_id, created_at);
-- ✅ ClickZetta（小文件合并，无 ZORDER）
OPTIMIZE orders;

-- ❌ VACUUM（ClickZetta 自动管理存储）
VACUUM orders RETAIN 168 HOURS;
```

---

## ⚠️ 写入时类型转换（重要差异）

Databricks 允许字符串隐式转换，ClickZetta **不允许**：

```sql
-- ❌ Databricks 可以，ClickZetta 报错
INSERT INTO t VALUES ('2024-01-15', 'true', '123');

-- ✅ ClickZetta 必须显式转换
INSERT INTO t VALUES (DATE '2024-01-15', TRUE, CAST('123' AS INT));
```

详见 [migration-snowflake.md](migration-snowflake.md) 中的类型转换表（规则相同）。

---

## DML 差异

### MERGE INTO（WHEN NOT MATCHED BY SOURCE）

```sql
-- Databricks：支持 WHEN NOT MATCHED BY SOURCE
MERGE INTO target t USING source s ON t.id = s.id
WHEN MATCHED THEN UPDATE SET t.val = s.val
WHEN NOT MATCHED THEN INSERT (id, val) VALUES (s.id, s.val)
WHEN NOT MATCHED BY SOURCE THEN DELETE;  -- ❌ ClickZetta 不支持

-- ClickZetta 替代方案：两步操作
-- 步骤1：MERGE 处理匹配和新增
MERGE INTO target t USING source s ON t.id = s.id
WHEN MATCHED THEN UPDATE SET t.val = s.val
WHEN NOT MATCHED THEN INSERT (id, val) VALUES (s.id, s.val);
-- 步骤2：DELETE 不在 source 中的行
DELETE FROM target WHERE id NOT IN (SELECT id FROM source);
```

### APPLY CHANGES INTO（CDC）

```sql
-- Databricks：APPLY CHANGES INTO（DLT 专有）
APPLY CHANGES INTO target
FROM source
KEYS (id)
SEQUENCE BY ts
APPLY AS DELETE WHEN operation = 'DELETE';

-- ClickZetta：用 TABLE STREAM + MERGE 实现
CREATE TABLE STREAM source_stream ON TABLE source
    WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD');

MERGE INTO target t
USING source_stream s ON t.id = s.id
WHEN MATCHED AND s.__change_type = 'UPDATE_AFTER' THEN UPDATE SET t.val = s.val
WHEN MATCHED AND s.__change_type = 'DELETE' THEN DELETE
WHEN NOT MATCHED AND s.__change_type = 'INSERT' THEN INSERT (id, val) VALUES (s.id, s.val);
```

### 事务

```sql
-- ❌ ClickZetta 不支持事务语法
BEGIN;
COMMIT;
ROLLBACK;
```

---

## DQL 差异

### QUALIFY（窗口函数过滤）

```sql
-- 两者都支持 QUALIFY
SELECT * FROM orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) = 1;
```

### RECURSIVE CTE

```sql
-- Databricks：支持 WITH RECURSIVE
WITH RECURSIVE nums AS (
    SELECT 1 AS n
    UNION ALL
    SELECT n + 1 FROM nums WHERE n < 5
)
SELECT * FROM nums;

-- ❌ ClickZetta：不支持 WITH RECURSIVE（验证失败）
-- 替代方案：用 Python/ZettaPark 生成序列，或预建辅助表
```

### STRUCT 命名字段

```sql
-- Databricks：支持命名字段
SELECT STRUCT(1 AS id, 'Alice' AS name) AS person;

-- ClickZetta：用 named_struct 实现命名字段
SELECT named_struct('id', 1, 'name', 'Alice') AS person;  -- ✅ 推荐
SELECT STRUCT(1, 'Alice') AS person;  -- 位置参数写法，访问时用 person.col1, person.col2
```

---

## 分区差异

### 分区函数

```sql
-- Databricks：直接用列名
CREATE TABLE t (...) PARTITIONED BY (year, month);

-- ClickZetta：Iceberg 隐藏分区，用转换函数
CREATE TABLE t (...) PARTITIONED BY (years(created_at));  -- 按年
CREATE TABLE t (...) PARTITIONED BY (months(created_at)); -- 按月
CREATE TABLE t (...) PARTITIONED BY (days(created_at));   -- 按天
CREATE TABLE t (...) PARTITIONED BY (bucket(16, user_id)); -- 按 bucket
```

### 分区裁剪

```sql
-- ✅ ClickZetta 的 YEAR() 函数在 WHERE 中能触发分区裁剪（引擎自动转换）
SELECT * FROM t WHERE YEAR(dt) = 2024;  -- 实际会转换为范围过滤

-- ✅ 更推荐的写法（明确范围）
SELECT * FROM t WHERE dt >= DATE '2024-01-01' AND dt < DATE '2025-01-01';
```

---

## Delta Lake 特有功能对照

| Delta Lake 功能 | ClickZetta 对应 | 说明 |
|---|---|---|
| `OPTIMIZE ... ZORDER BY` | `OPTIMIZE table`（无 ZORDER） | 只做小文件合并 |
| `VACUUM` | 自动管理 | 不需要手动 VACUUM |
| `DESCRIBE HISTORY` | `DESC HISTORY table` | 相同功能 |
| `RESTORE TABLE ... VERSION AS OF` | `RESTORE TABLE ... TIMESTAMP AS OF` | 按时间戳恢复 |
| `Time Travel VERSION AS OF n` | `TIMESTAMP AS OF '...'` | ClickZetta 按时间戳，不按版本号 |
| `enableChangeDataFeed` | TABLE STREAM | 不同实现方式 |
| `MERGE ... WHEN NOT MATCHED BY SOURCE` | 不支持，需两步操作 | |
| `APPLY CHANGES INTO` | TABLE STREAM + MERGE | |
| `GENERATED ALWAYS AS IDENTITY` | `IDENTITY(seed)` | |
| `TBLPROPERTIES` | `PROPERTIES` | |
| `USING DELTA` | 不需要（默认 Parquet） | |

---

## 已验证的兼容性（Databricks 有，ClickZetta 也有）

- `SEMI JOIN` / `ANTI JOIN` ✅
- `LATERAL VIEW EXPLODE` / `POSEXPLODE` ✅
- `QUALIFY` ✅
- `MERGE INTO`（基本语法）✅
- `GROUPING SETS` / `ROLLUP` / `CUBE` ✅
- `WITH CTE`（非递归）✅
- `STRUCT` / `ARRAY` / `MAP` 类型 ✅
- `TRANSFORM` / `FILTER` / `AGGREGATE` 高阶函数 ✅
- `ARRAY_AGG` / `COLLECT_LIST` / `COLLECT_SET` ✅
- `REGEXP_EXTRACT` / `REGEXP_REPLACE` ✅
- `DATE_TRUNC` / `DATE_FORMAT` ✅
- `TRY_CAST` ✅
- `IDENTITY` 列 ✅
- `GENERATED ALWAYS AS (expr)` 生成列 ✅
- `DEFAULT` 默认值 ✅
- `OPTIMIZE`（小文件合并）✅
- `DESC HISTORY` ✅
- `RESTORE TABLE ... TIMESTAMP AS OF` ✅
- `UNDROP TABLE` ✅
