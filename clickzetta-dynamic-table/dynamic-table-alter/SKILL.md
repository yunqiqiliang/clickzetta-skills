---
name: dynamic-table-alter
description: |
  修改 ClickZetta 动态表（Dynamic Table）的结构和属性。支持直接 ALTER 操作（suspend、resume、
  rename_column、set_comment、set_column_comment、set/unset properties）以及 CREATE OR REPLACE
  重建操作（修改调度周期、计算集群、加列、减列、改列类型、改 SQL 定义）。当用户说"修改动态表"、
  "动态表加列"、"改刷新间隔"、"暂停动态表"时触发。
---

# 动态表修改工作流

## 指令

### 步骤 1：确认动态表存在并获取当前定义
使用 `read_query` 执行 `SHOW CREATE TABLE schema_name.table_name` 获取动态表当前定义。
如果不确定是否为动态表，先用 `SHOW TABLES WHERE is_dynamic` 查看列表。

### 步骤 2：判断操作类型并选择执行方式

ClickZetta 动态表的修改操作分为两类：

**A. 直接 ALTER 操作**（6种，可直接执行）：

1. **suspend** — 暂停调度任务：
```sql
ALTER DYNAMIC TABLE dt_name SUSPEND;
```

2. **resume** — 启动调度任务：
```sql
ALTER DYNAMIC TABLE dt_name RESUME;
```

3. **set_comment** — 修改表注释：
```sql
ALTER DYNAMIC TABLE dt_name SET COMMENT 'comment';
```

4. **rename_column** — 修改列名：
```sql
ALTER DYNAMIC TABLE dt_name RENAME COLUMN old_name TO new_name;
```

5. **set_column_comment** — 修改列注释（注意用 CHANGE COLUMN）：
```sql
ALTER DYNAMIC TABLE dt_name CHANGE COLUMN column_name COMMENT 'comment';
```

6. **set/unset properties** — 修改表属性（目前为保留参数）：
```sql
-- 设置属性
ALTER DYNAMIC TABLE dt_name SET PROPERTIES('key' = 'value');
-- 删除属性
ALTER DYNAMIC TABLE dt_name UNSET PROPERTIES('key');
```

**B. CREATE OR REPLACE 操作**（6种，需要重建动态表）：

> ⚠️ **以下操作不支持 ALTER 语法**。`ALTER DYNAMIC TABLE ... SET REFRESH INTERVAL` 等语法不存在，会报语法错误。必须使用 `CREATE OR REPLACE DYNAMIC TABLE` 重建。

这些操作涉及 SQL 查询逻辑变化，无法通过 ALTER 直接完成：

7. **修改调度周期** — ❌ 不支持 `ALTER ... SET REFRESH INTERVAL`
8. **修改计算集群** — ❌ 不支持 `ALTER ... SET VCLUSTER`
9. **增加列**
10. **减列**
11. **修改列类型**
12. **修改 SQL 定义**

### 步骤 3：执行 CREATE OR REPLACE 重建（仅 B 类操作）

1. 用 `read_query` 执行 `SHOW CREATE TABLE schema_name.table_name` 获取原始 DDL
   > ⚠️ `SHOW CREATE TABLE` 不支持 LIMIT/WHERE 子句，直接执行即可
2. 解析出：列定义、REFRESH 子句、AS SELECT 子句、COMMENT 等
3. 根据操作修改对应部分
4. 用 `write_query` 执行重建 SQL

**关于全量刷新的触发**：
- 简单的删除列 / 添加列（添加的列只是从源表 SELECT 透传，不参与 JOIN key、GROUP key 等计算）→ **增量刷新**
- 涉及计算逻辑变化（修改 WHERE 条件、修改聚合逻辑、新增列参与计算等）→ **全量刷新**
- 兼容类型变更（如 INT → BIGINT）→ **增量刷新**

### 步骤 4：验证修改结果
使用 `DESC DYNAMIC TABLE dt_name` 确认修改生效。

---

## 示例

### 示例 1：修改调度周期

```sql
-- 原表
CREATE DYNAMIC TABLE dt_name
REFRESH INTERVAL 10 MINUTE vcluster DEFAULT
AS SELECT * FROM student02;

-- 修改后（改为 20 分钟）
CREATE OR REPLACE DYNAMIC TABLE dt_name
REFRESH INTERVAL 20 MINUTE vcluster DEFAULT
AS SELECT * FROM student02;
```

### 示例 2：修改计算集群

```sql
-- 原表
CREATE DYNAMIC TABLE dt_name
REFRESH INTERVAL 10 MINUTE vcluster DEFAULT
AS SELECT * FROM student02;

-- 修改后（改为 alter_vc 集群）
CREATE OR REPLACE DYNAMIC TABLE dt_name
REFRESH INTERVAL 10 MINUTE vcluster alter_vc
AS SELECT * FROM student02;
```

### 示例 3：增加列

```sql
-- 原表
CREATE DYNAMIC TABLE change_table (i, j)
AS SELECT * FROM dy_base_a;

-- 添加一列 col（涉及计算逻辑，下次刷新会全量刷新）
CREATE OR REPLACE DYNAMIC TABLE change_table (i, j, col)
AS SELECT i, j, j * 1 FROM dy_base_a;

REFRESH DYNAMIC TABLE change_table;
```

### 示例 4：减列

```sql
-- 原表有 i, j 两列
CREATE DYNAMIC TABLE change_table (i, j)
AS SELECT * FROM dy_base_a;

-- 减列（简单透传，增量刷新）
CREATE OR REPLACE DYNAMIC TABLE change_table (i)
AS SELECT i FROM dy_base_a;
```

### 示例 5：修改 SQL 定义

```sql
-- 修改 WHERE 过滤条件（全量刷新）
CREATE OR REPLACE DYNAMIC TABLE change_table (i, j)
AS SELECT * FROM dy_base_a WHERE i > 3;

REFRESH DYNAMIC TABLE change_table;
```

### 示例 6：修改列类型

```sql
-- INT → BIGINT（兼容类型，增量刷新）
CREATE OR REPLACE DYNAMIC TABLE change_table (i, j)
AS SELECT CAST(i AS BIGINT), j FROM dy_base_a;

REFRESH DYNAMIC TABLE change_table;
```

---

## 平台特有知识

- **CHANGE COLUMN 语法**：设置列注释用 `CHANGE COLUMN col COMMENT 'xxx'`，不是 `ALTER COLUMN`
- **RENAME COLUMN 语法**：`RENAME COLUMN old TO new`
- **DML 限制**：动态表默认不支持 UPDATE/DELETE/MERGE（因隐藏列 MV__KEY），如需 DML 须先执行 `SET cz.sql.dt.allow.dml = true;`
- **REFRESH 格式**：`REFRESH INTERVAL <N> MINUTE vcluster <name>`，支持 SECOND/MINUTE/HOUR/DAY
- **CREATE OR REPLACE 风险**：涉及计算逻辑变化时会触发全量刷新，大表可能耗时较长
- **schema 前缀**：所有 ALTER/CREATE 语句中表名应包含 schema 前缀
- **列定义可省略类型**：`CREATE DYNAMIC TABLE dt (i, j) AS SELECT ...` 类型由 SELECT 推断
- **DROP 语法**：必须用 `DROP DYNAMIC TABLE dt_name`，不能用 `DROP TABLE dt_name`（会报错）
- **UNDROP 语法**：必须用 `UNDROP TABLE dt_name`，不能用 `UNDROP DYNAMIC TABLE dt_name`
- **DESC 语法**：动态表用 `DESC TABLE dt_name`，不要写 `DESC DYNAMIC TABLE dt_name EXTENDED`（EXTENDED 不支持）

## 故障排除

| 错误 | 原因 | 解决方案 |
|---|---|---|
| ALTER 报 "Syntax error at or near 'REFRESH'" | `ALTER ... SET REFRESH INTERVAL` 语法不存在 | 使用 `CREATE OR REPLACE DYNAMIC TABLE ... REFRESH INTERVAL ...` 重建 |
| ALTER 报 "unsupported operation" | 尝试对动态表执行 B 类操作的 ALTER 语法 | 使用 CREATE OR REPLACE 重建 |
| `DROP TABLE dt_name` 报错 | 动态表必须用 `DROP DYNAMIC TABLE` | 改为 `DROP DYNAMIC TABLE dt_name` |
| `UNDROP DYNAMIC TABLE` 报错 | UNDROP 不支持 DYNAMIC TABLE 关键字 | 改为 `UNDROP TABLE dt_name` |
| `DESC DYNAMIC TABLE ... EXTENDED` 报错 | 不支持 EXTENDED 参数 | 改为 `DESC TABLE dt_name`（不加 EXTENDED） |
| UPDATE/DELETE 报 "MV__KEY" 相关错误 | 动态表有隐藏列 MV__KEY，默认禁止 DML | 先执行 `SET cz.sql.dt.allow.dml = true;` |
| CREATE OR REPLACE 后数据为空 | AS SELECT 子句引用的源表或列不正确 | 先用 `read_query` 验证 SELECT 子句 |
| CREATE OR REPLACE 后全量刷新 | 新增列参与了计算逻辑（JOIN key、GROUP key 等） | 预期行为，等待全量刷新完成 |
