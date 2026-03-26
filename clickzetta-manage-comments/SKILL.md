---
name: clickzetta-manage-comments
description: >
  管理 ClickZetta Lakehouse 各类对象的注释（COMMENT），包括增加、修改、删除注释。
  支持对象：Schema、普通表、外部表、字段、动态表（Dynamic Table）、物化视图（Materialized View）、
  VCluster、Workspace。
  当用户说"加注释"、"改注释"、"删注释"、"补注释"、"更新注释"、"清除注释"、
  "加 comment"、"补充元数据"、"给表/字段/schema/动态表/物化视图/计算集群/工作空间 加描述/改描述/删描述"、
  "COMMENT 相关操作"、"更新字段说明"时触发。
  包含 ClickZetta 特有的注释语法（与标准 SQL 不同），以及各对象类型的语法差异和单引号转义处理。
  务必在用户提到 ClickZetta 注释、元数据补充、字段描述、表说明等场景时使用此 skill。
---

# ClickZetta 注释管理

ClickZetta 的注释语法与标准 SQL（`COMMENT ON ...`）不同，使用错误语法会直接报错。
本 skill 固化了各类对象的增、改、删正确语法。

> 增加和修改注释使用完全相同的语法（覆盖写入即可），删除注释通过设置空字符串 `''` 实现，不支持 `NULL`。

---

## 各对象注释语法

### 1. Schema

```sql
-- 增加 / 修改
ALTER SCHEMA <schema_name> SET COMMENT '<comment>';

-- 删除
ALTER SCHEMA <schema_name> SET COMMENT '';
```

### 2. 普通表 / 外部表（External Table）

两者语法完全相同，统一用 `ALTER TABLE`：

```sql
-- 表注释：增加 / 修改
ALTER TABLE <schema_name>.<table_name> SET COMMENT '<comment>';

-- 表注释：删除
ALTER TABLE <schema_name>.<table_name> SET COMMENT '';

-- 字段注释：增加 / 修改
ALTER TABLE <schema_name>.<table_name> CHANGE COLUMN <col_name> COMMENT '<comment>';

-- 字段注释：删除
ALTER TABLE <schema_name>.<table_name> CHANGE COLUMN <col_name> COMMENT '';
```

> 字段注释**不能**用 `ALTER COLUMN ... COMMENT`，必须用 `CHANGE COLUMN`。

### 3. 动态表（Dynamic Table）

动态表有专属的 `ALTER DYNAMIC TABLE` 语法：

```sql
-- 表注释：增加 / 修改
ALTER DYNAMIC TABLE <dt_name> SET COMMENT '<comment>';

-- 表注释：删除
ALTER DYNAMIC TABLE <dt_name> SET COMMENT '';

-- 字段注释：增加 / 修改
ALTER DYNAMIC TABLE <dt_name> CHANGE COLUMN <col_name> COMMENT '<comment>';

-- 字段注释：删除
ALTER DYNAMIC TABLE <dt_name> CHANGE COLUMN <col_name> COMMENT '';
```

### 4. 物化视图（Materialized View）

注意：物化视图的注释修改用的是 `ALTER TABLE`，不是 `ALTER MATERIALIZED VIEW`：

```sql
-- 表注释：增加 / 修改
ALTER TABLE <mv_name> SET COMMENT '<comment>';

-- 表注释：删除
ALTER TABLE <mv_name> SET COMMENT '';

-- 字段注释：增加 / 修改
ALTER TABLE <mv_name> CHANGE COLUMN <col_name> COMMENT '<comment>';

-- 字段注释：删除
ALTER TABLE <mv_name> CHANGE COLUMN <col_name> COMMENT '';
```

### 5. VCluster（计算集群）

```sql
-- 增加 / 修改
ALTER VCLUSTER <vc_name> SET COMMENT '<comment>';

-- 删除
ALTER VCLUSTER <vc_name> SET COMMENT '';
```

### 6. Workspace（工作空间）

```sql
-- 增加 / 修改
ALTER WORKSPACE <ws_name> SET COMMENT '<comment>';

-- 删除
ALTER WORKSPACE <ws_name> SET COMMENT '';
```

---

## 不支持 ALTER COMMENT 的对象

以下对象**只能在 CREATE 时**通过 `COMMENT` 参数指定注释，创建后无法通过 ALTER 修改：

| 对象 | 说明 |
|---|---|
| VIEW（普通视图） | 无 `ALTER VIEW SET COMMENT` 语法；可用 `CREATE OR REPLACE VIEW ... COMMENT '...' AS ...` 更新注释，无需 DROP |
| FUNCTION / PROCEDURE | 只能在 CREATE 时指定，无 ALTER 修改注释的语法 |
| VOLUME | 无 ALTER VOLUME SET COMMENT 语法 |
| PIPE | 无 ALTER PIPE SET COMMENT 语法 |
| TABLE STREAM | 无 ALTER STREAM SET COMMENT 语法 |
| USER | `ALTER USER` 只支持 `DEFAULT_VCLUSTER` / `DEFAULT_SCHEMA`，不支持 COMMENT |
| ROLE | 只能在 `CREATE ROLE ... COMMENT '...'` 时设置 |

如果用户需要修改这些对象的注释：
- **VIEW**：使用 `CREATE OR REPLACE VIEW view_name COMMENT '新注释' AS <原查询>` 直接替换，无需 DROP
- **其他对象**：需要 DROP 后重新 CREATE（注意评估影响）

---

## 常见错误语法（不要使用）

| 错误写法 | 正确写法 |
|---|---|
| `COMMENT ON TABLE t IS '...'` | `ALTER TABLE t SET COMMENT '...'` |
| `COMMENT ON SCHEMA s IS '...'` | `ALTER SCHEMA s SET COMMENT '...'` |
| `ALTER TABLE t ALTER COLUMN c COMMENT '...'` | `ALTER TABLE t CHANGE COLUMN c COMMENT '...'` |
| `ALTER TABLE t SET COMMENT NULL` | `ALTER TABLE t SET COMMENT ''`（删除用空字符串）|
| `ALTER MATERIALIZED VIEW mv SET COMMENT '...'` | `ALTER TABLE mv SET COMMENT '...'`（物化视图用 ALTER TABLE）|

---

## 单引号转义

注释内容中如果含有单引号（如 `it's`），需要用两个单引号转义：

```sql
ALTER TABLE t SET COMMENT 'it''s a player table';
```

Python 中统一处理：

```python
comment = comment.replace("'", "''")
sql = f"ALTER TABLE {schema}.{table} SET COMMENT '{comment}'"
```

---

## 批量操作示例

```python
import clickzetta

conn = clickzetta.connect(...)
cursor = conn.cursor()

# 批量修改表注释
table_comments = {
    "players": "玩家基础信息表 | Steam player profiles",
    "games":   "游戏基础信息表 | Game metadata",
}
for table, comment in table_comments.items():
    c = comment.replace("'", "''")
    cursor.execute(f"ALTER TABLE my_schema.{table} SET COMMENT '{c}'")

# 批量修改字段注释
col_comments = [
    ("players", "playerid", "玩家唯一标识符 | Unique player ID"),
    ("players", "country",  "玩家所在国家 | Player country"),
]
for table, col, comment in col_comments:
    c = comment.replace("'", "''")
    cursor.execute(f"ALTER TABLE my_schema.{table} CHANGE COLUMN {col} COMMENT '{c}'")

# 动态表注释
cursor.execute("ALTER DYNAMIC TABLE my_schema.dt_orders SET COMMENT '订单动态表'")

# VCluster 注释
cursor.execute("ALTER VCLUSTER default SET COMMENT '默认通用计算集群'")

cursor.close()
conn.close()
```

---

## 验证注释是否生效

```sql
DESCRIBE SCHEMA <schema_name>;
DESCRIBE TABLE <schema_name>.<table_name>;
DESCRIBE DYNAMIC TABLE <schema_name>.<dt_name>;
```

---

## 操作流程

1. 确认目标对象类型（schema / 普通表 / 外部表 / 动态表 / 物化视图 / VCluster / Workspace）
2. 如果是不支持 ALTER COMMENT 的对象（VIEW、FUNCTION 等），告知用户只能 DROP + CREATE
3. 对注释内容中的单引号做转义
4. 执行对应 SQL
5. 用 `DESCRIBE` 验证结果
