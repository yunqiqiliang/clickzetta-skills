---
name: clickzetta-index-manager
description: |
  管理 ClickZetta Lakehouse 的三类索引：Bloom Filter 索引（等值查询加速）、
  倒排索引（全文检索）、向量索引（语义相似度搜索）。覆盖创建、构建存量数据、
  删除、查看等完整生命周期，以及索引类型选择指南。
  当用户说"创建索引"、"加索引"、"Bloom Filter"、"布隆过滤器"、"倒排索引"、
  "全文检索"、"向量索引"、"向量搜索"、"相似度搜索"、"BUILD INDEX"、
  "DROP INDEX"、"SHOW INDEX"、"查询加速"、"索引优化"时触发。
  Keywords: index, bloom filter, inverted index, vector index, full-text search
---

# ClickZetta 索引管理

## 索引类型选择

| 需求 | 推荐索引 | 参考文件 |
|---|---|---|
| 高基数列等值查询（ID、邮箱、手机号） | Bloom Filter | [references/bloomfilter-index.md](references/bloomfilter-index.md) |
| 文本关键词搜索、全文检索 | 倒排索引 | [references/inverted-index.md](references/inverted-index.md) |
| 向量相似度搜索、语义检索、RAG | 向量索引 | [references/vector-index.md](references/vector-index.md) |
| 存量数据补建索引、删除、查看 | — | [references/index-management.md](references/index-management.md) |

## ⚠️ 关键注意事项

- **所有索引只对新写入数据生效**，旧数据需用 `BUILD INDEX` 补建（Bloom Filter 除外，不支持 BUILD INDEX）
- Bloom Filter 旧数据生效方法：`INSERT OVERWRITE table SELECT * FROM table`（重写数据）
- `BUILD INDEX` 是同步任务，大表建议按分区逐批执行
- **索引必须与表在同一 Schema 中**，跨 Schema 创建索引会报错（`index and table must in the same schema`）

---

## 步骤 1：选择索引类型并创建

### Bloom Filter（等值查询加速）

阅读 [references/bloomfilter-index.md](references/bloomfilter-index.md)

```sql
-- 建表时指定
CREATE TABLE orders (
    order_id INT,
    INDEX order_id_idx (order_id) BLOOMFILTER
);

-- 已有表添加
CREATE BLOOMFILTER INDEX idx_name
ON TABLE my_schema.orders(order_id)
COMMENT '订单ID布隆过滤器';
```

### 倒排索引（全文检索）

阅读 [references/inverted-index.md](references/inverted-index.md)

```sql
-- 数值/日期列（不需要 PROPERTIES）
CREATE INVERTED INDEX id_idx ON TABLE t(order_id);

-- 字符串列（必须指定分词器，否则报错）
-- ⚠️ 字符串列不指定 analyzer 会创建失败
CREATE INVERTED INDEX title_idx
ON TABLE articles(title)
PROPERTIES('analyzer'='chinese');   -- 中文内容用 chinese

-- 其他分词器选项：
-- 'keyword'  → 不分词，整列作为一个词（适合精确匹配：状态码、标签）
-- 'english'  → 英文分词
-- 'unicode'  → 通用 Unicode 分词（中英混合）
-- 'chinese'  → 中文分词（默认推荐）

-- 查询
SELECT * FROM articles WHERE match_any(title, '关键词', 'analyzer'='chinese');
```

### 向量索引（相似度搜索）

阅读 [references/vector-index.md](references/vector-index.md)

```sql
CREATE VECTOR INDEX vec_idx
ON TABLE embeddings(vec)
PROPERTIES(
    "scalar.type" = "f32",
    "distance.function" = "cosine_distance"
);
```

---

## 步骤 2：为存量数据构建索引

阅读 [references/index-management.md](references/index-management.md)

```sql
-- 全表构建（倒排索引和向量索引支持，Bloom Filter 不支持）
BUILD INDEX index_name ON my_schema.table_name;

-- 按分区构建（大表推荐）
BUILD INDEX index_name ON table_name WHERE dt = '2024-01-01';
```

---

## 步骤 3：查看和管理索引

```sql
-- 列出表的所有索引
SHOW INDEX FROM my_schema.orders;

-- 查看索引详情
DESC INDEX index_name;
DESC INDEX EXTENDED index_name;  -- 含索引大小

-- 删除索引
DROP INDEX IF EXISTS index_name;
```

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 加了索引但查询没变快 | 旧数据未建索引 | 执行 `BUILD INDEX`（倒排/向量）或重写数据（Bloom Filter） |
| BUILD INDEX 执行很慢 | 数据量大 | 按分区逐批执行 `BUILD INDEX ... WHERE partition=...` |
| 倒排索引字符串列报错 | 未指定分词器（字符串列必须指定） | 添加 `PROPERTIES('analyzer'='chinese')` 或其他分词器 |
| 向量索引查询结果不准 | ef.construction 太小 | 调大 `ef.construction`（默认 128，可调至 200-500） |

---

## 参考文档

- [CREATE BLOOMFILTER INDEX](https://www.yunqi.tech/documents/CREATE-BLOOMFILTER-INDEX)
- [CREATE INVERTED INDEX](https://www.yunqi.tech/documents/create-inverted-index)
- [CREATE VECTOR INDEX](https://www.yunqi.tech/documents/create-vector-index)
- [BUILD INDEX](https://www.yunqi.tech/documents/build-inverted-index)
- [DROP INDEX](https://www.yunqi.tech/documents/DROP-INDEX)
- [SHOW INDEX](https://www.yunqi.tech/documents/SHOW-INDEX)
- [DESC INDEX](https://www.yunqi.tech/documents/DESC-INDEX)
