# 向量检索参考

> 来源：https://www.yunqi.tech/documents/vector-search 等

## VECTOR 数据类型

```sql
-- 语法
vector(scalar_type, dimension)
vector(dimension)  -- 默认 float 类型

-- 示例
CREATE TABLE embeddings (
    id       INT,
    content  STRING,
    vec      VECTOR(FLOAT, 1024),   -- 1024 维 float 向量
    vec_bin  VECTOR(TINYINT, 128)   -- 128 维 tinyint 向量（二值化）
);
```

支持的元素类型：`FLOAT`（f32）、`TINYINT`（i8/b1）

---

## 创建向量索引

```sql
-- 建表时内联创建
CREATE TABLE doc_embeddings (
    id      INT,
    content STRING,
    vec     VECTOR(FLOAT, 1024),
    INDEX vec_idx (vec) USING VECTOR PROPERTIES (
        "distance.function" = "cosine_distance",
        "scalar.type"       = "f32",
        "m"                 = "16",
        "ef.construction"   = "128"
    )
);

-- 在已有表上添加向量索引
ALTER TABLE doc_embeddings ADD INDEX vec_idx (vec) USING VECTOR PROPERTIES (
    "distance.function" = "cosine_distance",
    "scalar.type"       = "f32"
);

-- 为存量数据构建索引
BUILD INDEX vec_idx ON doc_embeddings;
```

### 关键参数

| 参数 | 可选值 | 默认值 | 说明 |
|---|---|---|---|
| distance.function | l2_distance, cosine_distance, jaccard_distance, hamming_distance | cosine_distance | 距离函数 |
| scalar.type | f32, f16, i8, b1 | f32 | 索引元素类型 |
| m | 建议 ≤ 1000 | 16 | HNSW 最大邻居数 |
| ef.construction | 建议 ≤ 5000 | 128 | 构建时候选集大小 |
| compress.codec | uncompressed/zstd/lz4 | uncompressed | 压缩算法 |

---

## 插入向量数据

```sql
-- 直接插入
INSERT INTO doc_embeddings (id, content, vec) VALUES
    (1, 'hello world', vector(0.1, 0.2, 0.3, ...)),
    (2, 'foo bar',     vector(0.4, 0.5, 0.6, ...));

-- 从字符串转换
INSERT INTO doc_embeddings (id, vec)
SELECT id, CAST('[0.1, 0.2, 0.3]' AS VECTOR(3))
FROM source_table;

-- 从 ARRAY 列转换（外部系统写入场景）
INSERT OVERWRITE doc_embeddings
SELECT id, content, CAST(vec_array AS VECTOR(FLOAT, 1024))
FROM staging_table;
```

---

## 向量检索

```sql
-- 调整探索因子（精度 vs 速度权衡）
SET cz.vector.index.search.ef = 64;

-- L2 距离检索（欧几里得距离，越小越相似）
SELECT id, content, l2_distance(vec, vector(0.1, 0.2, 0.3, ...)) AS dist
FROM doc_embeddings
ORDER BY dist
LIMIT 10;

-- 余弦距离检索（越小越相似）
SELECT id, content, cosine_distance(vec, CAST('[0.1,0.2,0.3]' AS VECTOR(3))) AS dist
FROM doc_embeddings
ORDER BY dist
LIMIT 10;

-- 带过滤条件的向量检索（向量 + 标量融合）
SELECT id, content, cosine_distance(vec, :query_vec) AS dist
FROM doc_embeddings
WHERE category = 'tech'
  AND cosine_distance(vec, :query_vec) < 0.3
ORDER BY dist
LIMIT 10;
```

---

## 距离函数速查

| 函数 | 适用场景 | 说明 |
|---|---|---|
| `l2_distance(v1, v2)` | 通用语义检索 | 欧几里得距离，越小越相似 |
| `cosine_distance(v1, v2)` | 文本语义检索 | 余弦距离，越小越相似 |
| `dot_product(v1, v2)` | 归一化向量 | 点积，越大越相似 |
| `hamming_distance(v1, v2)` | 二值向量 | 汉明距离，越小越相似 |
| `jaccard_distance(v1, v2)` | 集合相似度 | 雅卡德距离 |
| `binary_quantize(v)` | 向量压缩 | 将 float 向量二值化 |

---

## 向量 + 倒排索引融合检索

```sql
-- 建表：同时支持向量索引和倒排索引
CREATE TABLE hybrid_search (
    id      INT,
    content STRING,
    vec     VECTOR(FLOAT, 1024),
    INDEX content_inv_idx (content) USING INVERTED,
    INDEX vec_idx (vec) USING VECTOR PROPERTIES (
        "distance.function" = "cosine_distance"
    )
);

-- 融合检索：先用倒排过滤，再用向量排序
SELECT id, content, cosine_distance(vec, :query_vec) AS dist
FROM hybrid_search
WHERE content LIKE '%关键词%'
ORDER BY dist
LIMIT 10;
```

---

## 注意事项

- 向量类型不支持 `ORDER BY` 或 `GROUP BY`（只能对距离函数结果排序）
- 向量索引性能与内存/磁盘缓存直接相关，建议**单独占用 VCluster**
- 外部系统写入时不能直接写 VECTOR 类型，需先写 ARRAY 再 CAST 转换
- `ef` 值越大，检索精度越高但延迟越大；建议从 64 开始调优
