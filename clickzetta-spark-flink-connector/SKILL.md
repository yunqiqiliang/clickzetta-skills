---
name: clickzetta-spark-flink-connector
description: |
  使用 Spark Connector 或 Flink Write Connector 将数据写入 ClickZetta Lakehouse。
  覆盖 Spark DataFrame 读写配置（Maven 依赖、连接参数、read/write 代码）、
  Flink Table API 写入（CDC 模式 igs-dynamic-table、仅追加模式 igs-dynamic-table-append-only）、
  checkpoint 配置、buffer/flush 调优，以及主键表限制等关键约束。
  当用户说"Spark Connector"、"Flink Connector"、"Spark 写入 Lakehouse"、
  "Flink 写入 Lakehouse"、"spark-clickzetta"、"igs-flink-connector"、
  "Spark DataFrame 写入"、"Flink CDC 写入"、"Flink sink"、
  "spark.read.format clickzetta"时触发。
---

# ClickZetta Spark & Flink Connector

阅读 [references/spark.md](references/spark.md) 了解 Spark Connector，[references/flink.md](references/flink.md) 了解 Flink Write Connector。

---

## 关键约束（必读）

| 约束 | Spark Connector | Flink Connector |
|---|---|---|
| 主键表写入 | ❌ 不支持 | ✅ 支持（igs-dynamic-table 模式） |
| 部分字段写入 | ❌ 必须写全部字段 | ✅ 支持 |
| CDC（UPDATE/DELETE） | ❌ 仅 append | ✅ igs-dynamic-table 模式支持 |
| Spark 版本 | 3.4.0+ | — |
| Flink 版本 | — | 1.15.2+ |

---

## Spark Connector 快速示例

```scala
// 写入
df.write.format("clickzetta")
  .option("endpoint", "your_instance.cn-shanghai-alicloud.api.clickzetta.com")
  .option("username", sys.env("CZ_USERNAME"))
  .option("password", sys.env("CZ_PASSWORD"))
  .option("workspace", "your_workspace")
  .option("virtualCluster", "default_ap")
  .option("schema", "public")
  .option("table", "orders")
  .mode("append")
  .save()

// 读取
val df = spark.read.format("clickzetta")
  .option("endpoint", "your_instance.cn-shanghai-alicloud.api.clickzetta.com")
  .option("username", sys.env("CZ_USERNAME"))
  .option("password", sys.env("CZ_PASSWORD"))
  .option("workspace", "your_workspace")
  .option("virtualCluster", "default_ap")
  .option("schema", "public")
  .option("table", "orders")
  .load()
```

---

## Flink Connector 快速示例

```sql
-- CDC 模式（支持 INSERT/UPDATE/DELETE，目标表需有主键）
CREATE TABLE lakehouse_sink (
    order_id   INT,
    status     STRING,
    amount     DOUBLE,
    PRIMARY KEY (order_id) NOT ENFORCED
) WITH (
    'connector'       = 'igs-dynamic-table',
    'curl'            = 'jdbc:clickzetta://your_instance.cn-shanghai-alicloud.api.clickzetta.com/default?username=user&password=***&schema=public',
    'schema-name'     = 'public',
    'table-name'      = 'orders',
    'sink.parallelism' = '1',
    'properties'      = 'authentication:true'
);

INSERT INTO lakehouse_sink SELECT order_id, status, amount FROM source_table;
```

---

## 选择指南

| 场景 | 推荐方案 |
|---|---|
| Spark ETL 批量写入（无主键表） | Spark Connector |
| Flink 实时流写入（无主键表） | Flink igs-dynamic-table-append-only |
| Flink CDC 同步（有主键表，含 UPDATE/DELETE） | Flink igs-dynamic-table |
| 高频实时写入（Java 应用） | Java SDK RealtimeStream |
