# 索引管理命令参考

> 来源：https://www.yunqi.tech/documents/build-inverted-index、DROP-INDEX、SHOW-INDEX、DESC-INDEX

---

## BUILD INDEX（为存量数据构建索引）

支持向量索引和倒排索引，**不支持 Bloom Filter**。

```sql
-- 全表构建
BUILD INDEX index_name ON [schema.]table_name;

-- 指定分区构建（支持 =, !=, >, >=, <, <=）
BUILD INDEX index_name ON table_name
WHERE partition_col1 = '2024-01-01' AND partition_col2 = 'us';
```

说明：
- `BUILD INDEX` 是**同步任务**，执行过程消耗计算资源
- 大分区表建议**按分区逐批**构建，避免单次消耗过多资源
- 进度可通过 Job Profile 查看

---

## DROP INDEX（删除索引）

```sql
DROP INDEX [IF EXISTS] index_name;
```

注意：删除索引**不会立即释放存储空间**，后续新增数据不再构建该索引数据。

---

## SHOW INDEX（列出表的所有索引）

```sql
SHOW INDEX [IN|FROM] [schema.]table_name [LIMIT num];
```

示例：
```sql
SHOW INDEX FROM orders;
SHOW INDEX FROM my_schema.orders;
```

---

## DESC INDEX（查看索引详情）

```sql
DESC INDEX [EXTENDED] index_name;
```

- 基础模式：显示名称、创建时间、类型、所属表、列名
- `EXTENDED`：额外显示索引大小（倒排索引支持，Bloom Filter 暂不支持）

示例输出：
```
+--------------------------+--------------------------+
|        info_name         |        info_value        |
+--------------------------+--------------------------+
| name                     | order_year_index         |
| creator                  | my_user                  |
| created_time             | 2024-12-27 10:51:58.977  |
| index_type               | inverted                 |
| table_name               | t                        |
| table_column             | order_year               |
| total_index_size         | 296                      |
+--------------------------+--------------------------+
```
