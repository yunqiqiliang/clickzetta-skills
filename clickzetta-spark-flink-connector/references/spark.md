# Spark Connector 详细参考

## Maven 依赖

```xml
<dependencies>
    <dependency>
        <groupId>org.apache.spark</groupId>
        <artifactId>spark-sql_2.12</artifactId>
        <version>3.4.0</version>
        <scope>provided</scope>
    </dependency>
    <dependency>
        <groupId>com.clickzetta</groupId>
        <artifactId>spark-clickzetta</artifactId>
        <version>1.0.0</version>
    </dependency>
</dependencies>
```

> ⚠️ `spark-clickzetta` JAR 需从 ClickZetta 官方下载，不在 Maven Central。联系 ClickZetta 支持获取。

## 连接参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `endpoint` | ✅ | 如 `your_instance.cn-shanghai-alicloud.api.clickzetta.com` |
| `username` | ✅ | 用户名 |
| `password` | ✅ | 密码 |
| `workspace` | ✅ | 工作空间 |
| `virtualCluster` | ✅ | 虚拟集群，默认 `default_ap` |
| `schema` | ✅ | Schema 名称 |
| `table` | ✅ | 目标表名 |

## 完整 Scala 示例

```scala
import org.apache.spark.sql.SparkSession

object SparkToLakehouse {
  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("SparkToLakehouse")
      .getOrCreate()

    val endpoint = sys.env("CZ_ENDPOINT")
    val username = sys.env("CZ_USERNAME")
    val password = sys.env("CZ_PASSWORD")
    val workspace = sys.env("CZ_WORKSPACE")

    // 读取
    val df = spark.read.format("clickzetta")
      .option("endpoint", endpoint)
      .option("username", username)
      .option("password", password)
      .option("workspace", workspace)
      .option("virtualCluster", "default_ap")
      .option("schema", "silver")
      .option("table", "orders_cleaned")
      .load()

    // 转换
    import org.apache.spark.sql.functions._
    val result = df
      .filter(col("amount") > 0)
      .groupBy("region")
      .agg(sum("amount").as("total_revenue"), count("*").as("order_count"))

    // 写入（必须写全部字段，不支持主键表）
    result.write.format("clickzetta")
      .option("endpoint", endpoint)
      .option("username", username)
      .option("password", password)
      .option("workspace", workspace)
      .option("virtualCluster", "default_ap")
      .option("schema", "gold")
      .option("table", "region_summary")
      .mode("append")
      .save()

    spark.stop()
  }
}
```

## Python（PySpark）示例

```python
from pyspark.sql import SparkSession
import os

spark = SparkSession.builder.appName("PySparkToLakehouse").getOrCreate()

options = {
    "endpoint": os.environ["CZ_ENDPOINT"],
    "username": os.environ["CZ_USERNAME"],
    "password": os.environ["CZ_PASSWORD"],
    "workspace": os.environ["CZ_WORKSPACE"],
    "virtualCluster": "default_ap",
    "schema": "public",
    "table": "orders",
}

# 读取
df = spark.read.format("clickzetta").options(**options).load()
df.show(5)

# 写入
df.write.format("clickzetta").options(**options).mode("append").save()
```

## 类型映射

| Spark 类型 | Lakehouse 类型 |
|---|---|
| BooleanType | BOOLEAN |
| IntegerType | INT32 |
| LongType | INT64 |
| FloatType | FLOAT32 |
| DoubleType | FLOAT64 |
| StringType | STRING |
| TimestampType | TIMESTAMP |
| DateType | DATE |
| ArrayType | ARRAY |
| MapType | MAP |
| StructType | STRUCT |

## 限制

- **不支持主键表写入**：目标表不能有主键，否则报错
- **必须写全部字段**：DataFrame schema 必须与目标表完全匹配，不支持部分字段写入
- **仅支持 append 模式**：不支持 overwrite（会报错）
