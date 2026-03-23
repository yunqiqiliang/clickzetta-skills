# Table Stream（表流）SQL 参考

> **⚠️ ClickZetta 特有语法**
> - 创建语法是 `CREATE TABLE STREAM`（不是 `CREATE STREAM`）
> - `_change_type` 字段值：`insert` / `update_preimage` / `update_postimage` / `delete`
> - UPDATE 产生两条记录：`update_preimage`（更新前）和 `update_postimage`（更新后）
> - 通常只需要 `update_postimage`（更新后的值）

Table Stream 捕获源表的变更数据（INSERT / UPDATE / DELETE），是构建 CDC 管道的核心对象。通常与 Dynamic Table 或 SQL 任务配合消费变更数据。

## CREATE TABLE STREAM

```sql
CREATE [ OR REPLACE ] TABLE STREAM [ IF NOT EXISTS ] <stream_name>
  ON { TABLE | DYNAMIC TABLE | MATERIALIZED VIEW | EXTERNAL TABLE } <source_name>
  [ MODE = { STANDARD | APPEND_ONLY } ]
  [ COMMENT = '<comment>' ];
```

**关键参数：**
- `MODE = STANDARD`（默认）：捕获 INSERT、UPDATE、DELETE 所有变更，每行附带 `_change_type` 字段（`insert` / `update_preimage` / `update_postimage` / `delete`）
- `MODE = APPEND_ONLY`：只捕获 INSERT，性能更好，适合仅追加写入的源表

**示例：**
```sql
-- 在普通表上创建标准流（捕获所有变更）
CREATE TABLE STREAM orders_stream ON TABLE ods.orders;

-- 在动态表上创建仅追加流
CREATE TABLE STREAM events_stream
  ON DYNAMIC TABLE dw.events
  MODE = APPEND_ONLY
  COMMENT '事件流，仅追加';

-- 在物化视图上创建流
CREATE TABLE STREAM mv_stream ON MATERIALIZED VIEW dw.mv_product_stats;
```

## 消费 Table Stream

Table Stream 是一次性消费的：**每次 SELECT 后，已读取的数据会被标记为已消费**，下次 SELECT 只返回新增变更。

```sql
-- 查看当前未消费的变更数据
SELECT * FROM orders_stream;

-- 变更数据包含的系统字段
-- _change_type: insert | update_preimage | update_postimage | delete
-- _change_timestamp: 变更发生时间

-- 典型用法：将变更数据 MERGE 到目标表
MERGE INTO dw.orders_dim AS target
USING (
  SELECT * FROM orders_stream WHERE _change_type IN ('insert', 'update_postimage')
) AS src
ON target.order_id = src.order_id
WHEN MATCHED THEN UPDATE SET target.status = src.status, target.amount = src.amount
WHEN NOT MATCHED THEN INSERT (order_id, status, amount) VALUES (src.order_id, src.status, src.amount);

-- 配合 Dynamic Table 自动消费（推荐）
CREATE OR REPLACE DYNAMIC TABLE dw.orders_processed
  TARGET_LAG = '1 minutes'
  VCLUSTER = default_ap
AS
SELECT order_id, status, amount, _change_type, _change_timestamp
FROM orders_stream
WHERE _change_type IN ('insert', 'update_postimage');
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
- `STANDARD` 模式下 UPDATE 会产生两条记录：`update_preimage`（更新前）和 `update_postimage`（更新后）
- 推荐用 Dynamic Table 消费 Stream，避免手动管理消费状态

## 参考文档

- [CREATE TABLE STREAM](https://www.yunqi.tech/documents/create-table-stream)
- [DESC TABLE STREAM](https://www.yunqi.tech/documents/desc-table-stream)
- [SHOW TABLE STREAMS](https://www.yunqi.tech/documents/show-table-streams)
- [DROP TABLE STREAM](https://www.yunqi.tech/documents/drop-table-stream)
- [TABLE STREAM 简介](https://www.yunqi.tech/documents/tablestream_summary)
- [Table Stream 变化数据捕获](https://www.yunqi.tech/documents/table_stream)
- [Table Stream 最佳实践](https://www.yunqi.tech/documents/lakehouse-table-stream-best-practices)
