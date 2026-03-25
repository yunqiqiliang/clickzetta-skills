# OPTIMIZE 命令参考

> 来源：https://www.yunqi.tech/documents/OPTIMIZE 和 https://www.yunqi.tech/documents/small_file_optimization

## 语法

```sql
OPTIMIZE table_name
[WHERE predicate]
[OPTIONS('key' = 'value')]
```

## 参数说明

- `table_name`：格式为 `[schema_name.]table_name`
- `WHERE predicate`：（可选）分区过滤条件，必须包含完整分区列匹配
  - 格式：`partition_column = 'value'` 或 `dt='2023-01-01' AND region='us'`
- `OPTIONS`：（可选）控制执行模式

## 执行模式

### 异步模式（默认）

立即返回 Job ID，后台执行，不阻塞当前连接。

```sql
-- 默认异步
OPTIMIZE my_schema.orders;

-- 显式指定异步
OPTIMIZE my_schema.orders OPTIONS('cz.sql.optimize.table.async' = 'true');
```

### 同步模式

阻塞直到完成，适合开发测试和小表优化。

```sql
OPTIMIZE my_schema.orders OPTIONS('cz.sql.optimize.table.async' = 'false');
```

## 核心功能

- **小文件合并**：将多个小文件整合为大文件，减少文件元数据开销
- **删除标记清理**：清理 UPDATE/DELETE 产生的删除标记，回收存储空间
- **数据重组**：重新整理数据布局，提升查询性能

## 注意事项

- **只能在通用型计算集群（GENERAL PURPOSE VIRTUAL CLUSTER）运行**，分析型集群不生效
- 后台默认会不定时自动执行文件合并，手动 OPTIMIZE 用于精细控制

## DML 写入时自动触发小文件合并

```sql
-- 在 DML 执行时同时触发小文件合并
SET cz.sql.compaction.after.commit = true;
INSERT INTO my_table VALUES (...);
```

## 查看分区文件数量

```sql
SHOW PARTITIONS EXTENDED table_name;
```
