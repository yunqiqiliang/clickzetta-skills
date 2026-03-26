---
name: clickzetta-ai-vector-search
description: |
  在 ClickZetta Lakehouse 中实现向量存储、向量索引（HNSW）和向量检索，
  构建 RAG、语义搜索、图像检索等 AI 应用。覆盖 VECTOR 数据类型定义、
  向量索引创建（cosine/l2/hamming 距离）、向量数据插入与转换、
  ANN 近似最近邻检索、向量+倒排索引融合检索等完整工作流。
  当用户说"向量检索"、"向量索引"、"语义搜索"、"embedding 存储"、
  "RAG"、"ANN 搜索"、"HNSW"、"cosine_distance"、"l2_distance"、
  "VECTOR 类型"、"向量数据库"、"相似度搜索"、"向量 + 标量融合检索"、
  "文本向量化"时触发。
---

# ClickZetta 向量检索

Lakehouse 原生支持 VECTOR 数据类型和 HNSW 向量索引，无需独立向量数据库即可在同一张表中实现向量检索、全文检索和标量过滤的融合查询。

阅读 [references/vector-search.md](references/vector-search.md) 了解完整语法。

---

## 快速开始

### 1. 建表（含向量索引）

```sql
CREATE TABLE doc_embeddings (
    id      INT,
    content STRING,
    vec     VECTOR(FLOAT, 1024),
    INDEX vec_idx (vec) USING VECTOR PROPERTIES (
        "distance.function" = "cosine_distance",
        "scalar.type"       = "f32"
    )
);
```

### 2. 插入向量数据

```sql
-- 直接插入
INSERT INTO doc_embeddings VALUES
    (1, '云器 Lakehouse 产品介绍', vector(0.12, 0.34, ...));

-- 从字符串转换（适合 API 返回的 JSON 格式）
INSERT INTO doc_embeddings (id, content, vec)
SELECT id, content, CAST(embedding_str AS VECTOR(1024))
FROM staging_table;
```

### 3. 向量检索

```sql
-- 设置探索因子（精度 vs 速度）
SET cz.vector.index.search.ef = 64;

-- 余弦距离 Top-10 相似文档
SELECT id, content, cosine_distance(vec, CAST('[0.12, 0.34, ...]' AS VECTOR(1024))) AS dist
FROM doc_embeddings
ORDER BY dist
LIMIT 10;
```

---

## 向量 + 标量融合检索（RAG 场景）

```sql
-- 先用标量过滤缩小范围，再用向量排序
SELECT id, content, cosine_distance(vec, :query_embedding) AS dist
FROM doc_embeddings
WHERE category = 'product'
  AND created_at >= '2024-01-01'
ORDER BY dist
LIMIT 5;
```

---

## 向量 + 全文检索融合

```sql
-- 建表：同时支持向量索引和倒排索引
CREATE TABLE hybrid_docs (
    id      INT,
    title   STRING,
    body    STRING,
    vec     VECTOR(FLOAT, 1024),
    INDEX body_inv_idx (body) USING INVERTED,
    INDEX vec_idx (vec) USING VECTOR PROPERTIES (
        "distance.function" = "cosine_distance"
    )
);

-- 融合检索：关键词过滤 + 向量排序
SELECT id, title, cosine_distance(vec, :query_vec) AS dist
FROM hybrid_docs
WHERE body LIKE '%向量检索%'
ORDER BY dist
LIMIT 10;
```

---

## 外部系统写入向量（ARRAY → VECTOR 转换）

外部系统（Python SDK、Kafka 等）不能直接写 VECTOR 类型，需先写 ARRAY 再转换：

```sql
-- 暂存表（ARRAY 类型）
CREATE TABLE staging (id INT, vec_array ARRAY<FLOAT>);

-- 转换写入目标表
INSERT INTO doc_embeddings (id, vec)
SELECT id, CAST(vec_array AS VECTOR(FLOAT, 1024))
FROM staging;
```

---

## 距离函数速查

| 函数 | 适用场景 |
|---|---|
| `cosine_distance(v1, v2)` | 文本语义检索（最常用） |
| `l2_distance(v1, v2)` | 图像/通用向量检索 |
| `dot_product(v1, v2)` | 归一化向量的相似度 |
| `hamming_distance(v1, v2)` | 二值向量（高效压缩） |
| `binary_quantize(v)` | 将 float 向量压缩为二值向量 |

---

## 性能调优

```sql
-- 调整探索因子（默认 64，越大精度越高但越慢）
SET cz.vector.index.search.ef = 128;

-- 验证向量索引是否生效
EXPLAIN SELECT id, cosine_distance(vec, vector(0.1, 0.2)) AS dist
FROM doc_embeddings ORDER BY dist LIMIT 10;
-- 查看执行计划中是否有 vector_index_search_type 字样
```

**最佳实践：**
- 向量检索建议**单独占用 VCluster**，避免与其他查询争抢缓存
- 大批量写入后执行 `BUILD INDEX vec_idx ON table_name` 为存量数据构建索引
- 外部系统写入时先写 ARRAY，再批量 CAST 转换，避免频繁小文件

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 向量索引未生效 | 存量数据未构建索引 | 执行 `BUILD INDEX idx ON table` |
| 检索精度低 | ef 值太小 | 增大 `cz.vector.index.search.ef` |
| 外部写入报错 | 不支持直接写 VECTOR | 先写 ARRAY，再 CAST 转换 |
| 向量检索慢 | 与其他查询共用 VCluster | 为向量检索单独分配 VCluster |
