# Bloom Filter 索引参考

> 来源：https://www.yunqi.tech/documents/CREATE-BLOOMFILTER-INDEX

## 适用场景

高基数列（如 ID、邮箱、手机号）的**等值查询**加速。通过跳过不含目标值的数据文件，减少 I/O。

不支持的列类型：INTERVAL、STRUCT、MAP、ARRAY。

## 建表时创建

```sql
CREATE TABLE orders (
    order_id INT,
    customer_id INT,
    amount DOUBLE,
    INDEX order_id_idx (order_id) BLOOMFILTER COMMENT 'bloom filter on order_id',
    INDEX customer_id_idx (customer_id) BLOOMFILTER
) USING parquet;
```

## 已有表添加

```sql
CREATE BLOOMFILTER INDEX [IF NOT EXISTS] index_name
ON TABLE [schema.]table_name(column_name)
[COMMENT 'comment']
[PROPERTIES ('key' = 'value')];
```

### ngram 分词器（用于字符串模糊匹配）

```sql
CREATE BLOOMFILTER INDEX idx_ngram
ON TABLE demo(col_name)
PROPERTIES ('analyzer' = 'ngram', 'n' = '3');
```

`n` 为 ngram 长度，例如 n=4 时 "Lakehouse" 被索引为 "Lake"、"akeh"、"keho"...

## 注意事项

- **只对新写入数据生效**，旧数据不生效
- 旧数据需要生效：执行 `INSERT OVERWRITE table SELECT * FROM table` 重写数据
- 一张表可以创建多个 Bloom Filter 索引
- 目前只支持**单列索引**

## 示例（完整流程）

```sql
-- 建表时指定
CREATE TABLE t (
    order_id INT,
    customer_id INT,
    INDEX order_id_index (order_id) BLOOMFILTER COMMENT 'BLOOMFILTER'
);

-- 查看索引
SHOW INDEX FROM t;

-- 查看索引详情
DESC INDEX order_id_index;

-- 删除索引
DROP INDEX order_id_index;
```
