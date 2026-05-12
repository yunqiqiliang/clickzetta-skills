# 倒排索引参考

> 来源：https://www.yunqi.tech/documents/create-inverted-index

## 适用场景

文本搜索、关键词匹配。支持数值、日期、字符串列。字符串列必须指定分词器。

## 分词器选择

| 分词器 | 适用场景 | 说明 |
|---|---|---|
| `keyword` | 精确匹配 | 不分词，整个字符串作为一个词根 |
| `english` | 英文文本 | 识别连续 ASCII 字母和数字，转小写 |
| `chinese` | 中英文混合 | 识别中文和英文，过滤标点，英文转小写 |
| `unicode` | 多语言 | 基于 Unicode 文本分割算法，支持多语言 |

数值和日期类型**不需要**指定 PROPERTIES。

## 建表时创建

```sql
CREATE TABLE articles (
    id INT,
    title STRING,
    content STRING,
    INDEX id_idx (id) INVERTED,
    INDEX title_idx (title) INVERTED PROPERTIES('analyzer'='chinese'),
    INDEX content_idx (content) INVERTED PROPERTIES('analyzer'='english')
);
```

## 已有表添加

```sql
CREATE INVERTED INDEX [IF NOT EXISTS] index_name
ON TABLE [schema.]table_name(column_name)
[COMMENT 'comment']
[PROPERTIES('analyzer'='english|chinese|keyword|unicode')];
```

## 注意事项

- **只对新写入数据生效**，旧数据需用 `BUILD INDEX` 命令补建
- 只支持**单列索引**

## 查询语法

```sql
-- 匹配任意词（OR）
SELECT * FROM articles WHERE match_any(content, 'keyword1 keyword2');

-- 匹配所有词（AND）
SELECT * FROM articles WHERE match_all(content, 'keyword1 keyword2');
```

## 完整示例

```sql
-- 建表
CREATE TABLE t (
    order_id INT,
    order_year STRING,
    INDEX order_id_index (order_id) INVERTED COMMENT 'INVERTED'
);

-- 给已有列添加索引
CREATE INVERTED INDEX order_year_index
ON TABLE public.t(order_year)
PROPERTIES('analyzer'='chinese');

-- 对存量数据构建索引
BUILD INDEX order_year_index ON public.t;

-- 查询
SELECT * FROM t WHERE match_all(order_year, '2023');

-- 查看索引详情
DESC INDEX EXTENDED order_year_index;
```
