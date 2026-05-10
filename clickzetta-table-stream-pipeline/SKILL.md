---
name: clickzetta-table-stream-pipeline
description: |
  搭建和管理 ClickZetta Table Stream 变更数据捕获管道，覆盖从源表配置、Stream 创建、
  数据消费到增量 ETL 的端到端工作流。当用户说"创建 Table Stream"、"Table Stream CDC"、
  "Table Stream 管道"、"Table Stream 增量消费"、"Stream 消费"时触发。
  包含变更跟踪开启、模式选择、offset 管理、元数据字段使用、幂等消费等 ClickZetta 特有逻辑。
  Keywords: table stream, CDC, change capture, incremental ETL, stream
---

# Table Stream 变更数据捕获工作流

## 指令

### 步骤 1：开启源表变更跟踪（必需前置）
使用 `write_query` 开启源表的 change_tracking：
```sql
ALTER TABLE <source_table> SET PROPERTIES ('change_tracking' = 'true');
```
- 这是强制性前置步骤，不执行则 Stream 无法正确捕获变更
- 使用 `read_query` 验证属性是否生效：
```sql
SHOW CREATE TABLE <source_table>;
```

### 步骤 2：创建 Table Stream
使用 `write_query` 创建 Stream：
```sql
CREATE [ OR REPLACE ] TABLE STREAM <stream_name>
  ON TABLE <source_table>
  [ TIMESTAMP AS OF '<timestamp>' ]
  [ COMMENT '<描述>' ]
  WITH PROPERTIES (
    'TABLE_STREAM_MODE' = 'STANDARD | APPEND_ONLY',
    'SHOW_INITIAL_ROWS' = 'TRUE | FALSE'
  );
```
关键参数选择：
- **STANDARD 模式**：捕获 INSERT/UPDATE/DELETE，反映表当前状态（delta 变化） → 适用于数据同步、增量 ETL
  - delta 变化指两个事务时间点之间的净变化。例如：先 INSERT 再 DELETE 同一行 → delta 为空；先 INSERT 再 UPDATE → delta 为一条新行（最终状态）
- **APPEND_ONLY 模式**：仅捕获 INSERT，保留所有历史插入记录 → 适用于审计、历史记录保留
  - 即使后续 DELETE 了某行，APPEND_ONLY 模式仍保留该行的 INSERT 记录
- **SHOW_INITIAL_ROWS = TRUE**：首次消费返回建 Stream 时表中已有行
- **SHOW_INITIAL_ROWS = FALSE**（默认）：首次消费仅返回建 Stream 后的新变更
- 可选：指定起始时间点
```sql
-- TIMESTAMP AS OF 用于指定 Stream 的起始读取位点
-- 注意：此功能在某些场景下可能不稳定，建议优先使用默认行为（从创建时刻开始）
CREATE TABLE STREAM <stream_name>
  ON TABLE <source_table>
  TIMESTAMP AS OF '<timestamp>'
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD');
```

### 步骤 3：准备目标表
使用 `write_query` 或 `create_table` 创建与源表结构兼容的目标表：
- 目标表列定义需包含源表的业务列
- 建议额外添加元数据列（如 sync_version、sync_timestamp）用于追踪

### 步骤 4：查询 Stream 数据（预览，不移动 offset）
使用 `read_query` 预览 Stream 中的变更数据：
```sql
SELECT *, __change_type, __commit_version, __commit_timestamp
FROM <stream_name>;
```
- 仅 SELECT 不会移动 offset
- 元数据字段：`__change_type`（值：`INSERT` / `UPDATE_BEFORE` / `UPDATE_AFTER` / `DELETE`）、`__commit_version`、`__commit_timestamp`
- **UPDATE 处理要点**：UPDATE 操作产生两条记录：
  - `UPDATE_BEFORE`：更新前的旧值（通常在消费时忽略）
  - `UPDATE_AFTER`：更新后的新值（用于写入目标表）
  - 消费时务必过滤 `__change_type`，避免将 `UPDATE_BEFORE` 旧值误写入目标表

### 步骤 5：消费 Stream 数据（移动 offset）
使用 `write_query` 执行 DML 操作消费数据：

#### 方式 A：全量消费（INSERT INTO）
```sql
INSERT INTO <target_table>
SELECT <columns> FROM <stream_name>;
```

#### 方式 B：幂等消费（MERGE，推荐）
```sql
MERGE INTO <target_table> t
USING (SELECT * FROM <stream_name> WHERE __change_type != 'UPDATE_BEFORE') s
ON t.<pk_column> = s.<pk_column>
WHEN MATCHED AND s.__change_type = 'DELETE' THEN DELETE
WHEN MATCHED AND s.__change_type IN ('INSERT', 'UPDATE_AFTER') THEN UPDATE SET t.col1 = s.col1, t.col2 = s.col2
WHEN NOT MATCHED AND s.__change_type = 'INSERT' THEN INSERT (<columns>) VALUES (s.<columns>);
```
- DML 操作（INSERT/UPDATE/MERGE）会移动 offset
- ⚠️ 即使使用 WHERE 条件过滤，**所有数据的 offset 仍会移动**（不仅是匹配的行）
- 推荐使用 MERGE 实现幂等性，避免重复消费导致数据重复
- 在 USING 子查询中过滤掉 `UPDATE_BEFORE`，避免旧值干扰 MERGE 逻辑
- ⚠️ **MERGE 语法顺序要求**：多个 `WHEN MATCHED` 子句时，**DELETE 必须在 UPDATE 之前**，否则报错

### 步骤 6：验证消费状态
使用 `read_query` 确认消费完成：
```sql
SELECT COUNT(*) FROM <stream_name>;
```
- 消费成功后 COUNT 应为 0 或仅包含新变更
- 记录最后消费的 `__commit_version` 用于故障恢复

## Offset 移动规则

| 操作 | 是否移动 offset | 说明 |
|------|----------------|------|
| `SELECT * FROM stream` | ❌ 不移动 | 仅预览，可反复查询 |
| `INSERT INTO target SELECT ... FROM stream` | ✅ 移动 | 消费数据 |
| `MERGE INTO target USING stream ...` | ✅ 移动 | 消费数据（推荐） |
| `UPDATE target SET ... FROM stream` | ✅ 移动 | 消费数据 |
| `DELETE FROM target USING stream` | ✅ 移动 | 消费数据 |
| 带 WHERE 的 DML | ✅ 全部移动 | 即使 WHERE 过滤了部分行，所有行的 offset 都会移动 |

> ⚠️ **关键注意**：offset 移动是全量的。一旦执行 DML 消费 Stream，所有变更记录的 offset 都会前进，无法部分消费。如果 DML 执行失败（如目标表不存在），offset 不会移动。

## 模式选择速查

| 需求 | 推荐模式 |
|------|---------|
| 数据同步（保持目标与源一致） | STANDARD |
| 增量 ETL 流程 | STANDARD |
| 审计所有插入记录 | APPEND_ONLY |
| 历史记录保留 | APPEND_ONLY |

## 性能优化要点

- 只 SELECT 必要列，避免 `SELECT *`
- 定期消费 Stream，避免数据累积
- 高变更率表：更频繁消费；低变更率表：降低频率
- 大型 Stream 可按主键范围拆分并行处理
- 在源表上设置适当的数据保留期

## 示例

### 示例 1：订单表实时同步
```
1. write_query("ALTER TABLE orders SET PROPERTIES ('change_tracking' = 'true')")
2. write_query("CREATE TABLE STREAM orders_stream ON TABLE orders WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD', 'SHOW_INITIAL_ROWS' = 'FALSE')")
3. write_query("CREATE TABLE orders_sync LIKE orders")  -- 或手动建表
4. read_query("SELECT *, __commit_version, __commit_timestamp FROM orders_stream")  -- 预览
5. write_query("MERGE INTO orders_sync t USING orders_stream s ON t.order_id = s.order_id WHEN MATCHED THEN UPDATE SET t.status = s.status, t.amount = s.amount WHEN NOT MATCHED THEN INSERT (order_id, status, amount) VALUES (s.order_id, s.status, s.amount)")
6. read_query("SELECT COUNT(*) FROM orders_stream")  -- 验证 offset 已移动
```

### 示例 2：用户行为审计（保留全部插入历史）
```
1. write_query("ALTER TABLE user_actions SET PROPERTIES ('change_tracking' = 'true')")
2. write_query("CREATE TABLE STREAM user_actions_audit_stream ON TABLE user_actions WITH PROPERTIES ('TABLE_STREAM_MODE' = 'APPEND_ONLY', 'SHOW_INITIAL_ROWS' = 'TRUE')")
3. read_query("SELECT *, __commit_version, __commit_timestamp FROM user_actions_audit_stream")
4. write_query("INSERT INTO user_actions_audit SELECT *, __commit_version AS audit_version, __commit_timestamp AS audit_time FROM user_actions_audit_stream")
```

## 故障排除

Stream 不捕获变更：
原因：源表未开启 change_tracking
解决方案：执行 `ALTER TABLE <table> SET PROPERTIES ('change_tracking' = 'true')`，确认 DML 在 Stream 创建后执行

无法区分变更类型：
原因：未在 MERGE/INSERT 中过滤 `__change_type`，导致 `UPDATE_BEFORE` 旧值也被写入目标表
解决方案：MERGE 时过滤 `__change_type IN ('UPDATE_AFTER', 'DELETE')`，忽略 `UPDATE_BEFORE` 记录

消费后 offset 未移动：
原因：仅使用 SELECT 查询，未执行 DML
解决方案：必须通过 INSERT INTO / MERGE INTO / UPDATE 等 DML 操作消费数据

重复消费导致目标表数据重复：
原因：使用 INSERT INTO 而非 MERGE，或消费逻辑非幂等
解决方案：改用 MERGE 语句；记录最后消费的 `__commit_version` 和 `__commit_timestamp` 用于断点恢复

COMMENT 语法错误：
原因：使用了 `COMMENT = '...'`（带等号）而非 `COMMENT '...'`
解决方案：正确语法为 `COMMENT '注释内容'`，不带等号
