# 向量索引参考

> 来源：https://www.yunqi.tech/documents/create-vector-index

## 适用场景

语义相似度搜索、RAG 检索、推荐系统。基于 HNSW 算法。

## 建表时创建

```sql
CREATE TABLE embeddings (
    id INT,
    vec VECTOR(FLOAT, 512),
    INDEX vec_idx (vec) USING VECTOR PROPERTIES(
        "scalar.type" = "f32",
        "distance.function" = "l2_distance"
    )
);
```

## 已有表添加

```sql
CREATE VECTOR INDEX [IF NOT EXISTS] index_name
ON TABLE [schema.]table_name(column_name)
PROPERTIES(
    "property1" = "value1",
    ...
);
```

## PROPERTIES 参数说明

| 参数 | 可选值 | 默认值 | 说明 |
|---|---|---|---|
| `distance.function` | `l2_distance`, `cosine_distance`, `jaccard_distance`, `hamming_distance` | `cosine_distance` | 距离函数 |
| `scalar.type` | `f32`, `f16`, `i8`, `b1` | `f32` | 向量元素类型 |
| `m` | 建议不超过 1000 | `16` | HNSW 最大邻居数 |
| `ef.construction` | 建议不超过 5000 | `128` | HNSW 构建时候选集大小 |
| `reuse.vector.column` | `true`, `false` | `false` | 复用 vector column 数据节省存储 |
| `compress.codec` | `uncompressed`, `zstd`, `lz4` | `uncompressed` | 压缩算法（复用 column 时不生效） |
| `compress.level` | `fastest`, `default`, `best` | `default` | 压缩级别 |

## 向量列类型与索引元素类型对应

| 索引元素类型（scalar.type） | 支持的向量列类型 |
|---|---|
| `f32` | int, float |
| `f16` | int, float |
| `i8` | tinyint, int, float |
| `b1` | tinyint, int, float（按位建索引需设 `conversion.rule=as_bits`） |

## 注意事项

- **只对新写入数据生效**，旧数据需用 `BUILD INDEX` 命令补建

## 完整示例

```sql
-- 建表时创建向量索引
CREATE TABLE test_vector (
    vec VECTOR(FLOAT, 4),
    id INT,
    INDEX vec_idx (vec) USING VECTOR PROPERTIES(
        "scalar.type" = "f32",
        "distance.function" = "l2_distance"
    )
);

-- 已有表添加向量索引
CREATE VECTOR INDEX vec_idx
ON TABLE public.test_vector(vec)
PROPERTIES(
    "scalar.type" = "f32",
    "distance.function" = "cosine_distance"
);

-- 对存量数据构建索引
BUILD INDEX vec_idx ON public.test_vector;
```
