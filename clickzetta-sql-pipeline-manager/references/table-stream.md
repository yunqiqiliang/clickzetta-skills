# Table Stream（表流）SQL 参考

> **⚠️ ClickZetta 特有语法**
> - 创建语法是 `CREATE TABLE STREAM`，参数放在 `WITH PROPERTIES (...)` 里
> - 元数据字段是 `__change_type`（双下划线），值：`INSERT` / `UPDATE_BEFORE` / `UPDATE_AFTER` / `DELETE`
> - UPDATE 产生两条记录：`UPDATE_BEFORE`（更新前）和 `UPDATE_AFTER`（更新后）
> - 通常只需要 `UPDATE_AFTER` 和 `INSERT`，忽略 `UPDATE_BEFORE`

Table Stream 捕获源表的变更数据（INSERT / UPDATE / DELETE），是构建 CDC 管道的核心对象。通常与 Dynamic Table 或 SQL 任务配合消费变更数据。

## CREATE TABLE STREAM

```sql
CREATE [ OR REPLACE ] TABLE STREAM [ IF NOT EXISTS ] <stream_name>
  ON TABLE <source_name>
  [ TIMESTAMP AS OF <timestamp_expr> ]
  [ COMMENT = '<comment>' ]
  WITH PROPERTIES (
    'TABLE_STREAM_MODE' = 'STANDARD | APPEND_ONLY',
    'SHOW_INITIAL_ROWS' = 'TRUE | FALSE'
  );
```

**关键参数：**
- `TABLE_STREAM_MODE = STANDARD`（默认）：捕获 INSERT、UPDATE、DELETE 所有变更，每行附带 `__change_type` 字段（`INSERT` / `UPDATE_BEFORE` / `UPDATE_AFTER` / `DELETE`）
- `TABLE_STREAM_MODE = APPEND_ONLY`：只捕获 INSERT，性能更好，适合仅追加写入的源表
- `SHOW_INITIAL_ROWS = TRUE`：首次消费返回建 Stream 时表中已有行；`FALSE`（默认）仅返回建 Stream 后的新变更
- `TIMESTAMP AS OF`：指定 Stream 从哪个时间点开始捕获变更

**示例：**
```sql
-- 在普通表上创建标准流（捕获所有变更，需先开启 change_tracking）
ALTER TABLE ods.orders SET PROPERTIES ('change_tracking' = 'true');

CREATE TABLE STREAM orders_stream
  ON TABLE ods.orders
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD');

-- 仅追加流
CREATE TABLE STREAM events_stream
  ON TABLE dw.events
  COMMENT = '事件流，仅追加'
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'APPEND_ONLY');

-- 从指定时间点开始捕获
CREATE TABLE STREAM orders_stream_from_ts
  ON TABLE ods.orders
  TIMESTAMP AS OF '2024-01-01 00:00:00'
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD', 'SHOW_INITIAL_ROWS' = 'TRUE');
```

## 消费 Table Stream

Table Stream 是一次性消费的：**每次 SELECT 后，已读取的数据会被标记为已消费**，下次 SELECT 只返回新增变更。

```sql
-- 查看当前未消费的变更数据
SELECT * FROM orders_stream;

-- 变更数据包含的系统字段
-- __change_type: INSERT | UPDATE_BEFORE | UPDATE_AFTER | DELETE
-- __commit_version: 变更版本号
-- __commit_timestamp: 变更发生时间

-- 典型用法：将变更数据 MERGE 到目标表（忽略 UPDATE_BEFORE）
MERGE INTO dw.orders_dim AS target
USING (
  SELECT * FROM orders_stream
  WHERE __change_type IN ('INSERT', 'UPDATE_AFTER', 'DELETE')
) AS src
ON target.order_id = src.order_id
WHEN MATCHED AND src.__change_type = 'DELETE' THEN DELETE
WHEN MATCHED AND src.__change_type = 'UPDATE_AFTER' THEN UPDATE SET target.status = src.status, target.amount = src.amount
WHEN NOT MATCHED AND src.__change_type = 'INSERT' THEN INSERT (order_id, status, amount) VALUES (src.order_id, src.status, src.amount);

-- 配合 Dynamic Table 自动消费（推荐）
CREATE OR REPLACE DYNAMIC TABLE dw.orders_processed
  TARGET_LAG = '1 minutes'
  VCLUSTER = default_ap
AS
SELECT order_id, status, amount, __change_type, __commit_timestamp
FROM orders_stream
WHERE __change_type IN ('INSERT', 'UPDATE_AFTER');
```

## DROP TABLE STREAM

```sql
DROP TABLE STREAM [ IF EXISTS ] <stream_name>;
```

## SHOW / DESC

```sql
-- 列出当前 schema 下所有 Table Stream
SHOW TABLE STREAMS;

-- 列出指定 schema 下的 Table Stream
SHOW TABLE STREAMS IN <schema_name>;

-- 按名称过滤
SHOW TABLE STREAMS LIKE 'orders%';

-- 查看 Table Stream 详情（源表、模式、创建时间）
DESC TABLE STREAM <stream_name>;
```

## 注意事项

- Stream 数据**只能消费一次**，SELECT 后即标记为已读
- 若长时间不消费，超出源表的 `data_retention_days` 后数据会丢失
- `STANDARD` 模式下 UPDATE 会产生两条记录：`UPDATE_BEFORE`（更新前）和 `UPDATE_AFTER`（更新后）
- 消费时通常过滤 `__change_type IN ('INSERT', 'UPDATE_AFTER', 'DELETE')`，忽略 `UPDATE_BEFORE`

## 参考文档

- [CREATE TABLE STREAM](https://www.yunqi.tech/documents/create-table-stream)
- [DESC TABLE STREAM](https://www.yunqi.tech/documents/desc-table-stream)
- [SHOW TABLE STREAMS](https://www.yunqi.tech/documents/show-table-streams)
- [DROP TABLE STREAM](https://www.yunqi.tech/documents/drop-table-stream)
- [TABLE STREAM 简介](https://www.yunqi.tech/documents/tablestream_summary)
- [Table Stream 变化数据捕获](https://www.yunqi.tech/documents/table_stream)
- [Table Stream 最佳实践](https://www.yunqi.tech/documents/lakehouse-table-stream-best-practices)
