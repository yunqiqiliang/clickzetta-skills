# BulkloadStream 详细参考

> 适合：定时 ETL、本地文件导入、数据库迁移
> 不适合：主键表、5 分钟以内高频写入

## Maven 依赖

```xml
<!-- 最新版本见 https://central.sonatype.com/artifact/com.clickzetta/clickzetta-java -->
<dependency>
    <groupId>com.clickzetta</groupId>
    <artifactId>clickzetta-java</artifactId>
    <version>2.0.0</version>
</dependency>
```

最新版本见 [Maven Central](https://central.sonatype.com/artifact/com.clickzetta/clickzetta-java)

## 使用限制

- **不支持主键（pk）表写入**
- **不适合时间间隔小于 5 分钟的高频写入**
- 写入完成 `close()` 后数据才可见

## 完整示例：读取本地 CSV 写入 Lakehouse

### 建表

```sql
CREATE TABLE bulk_order_items (
    order_id            STRING,
    order_item_id       INT,
    product_id          STRING,
    seller_id           STRING,
    shipping_limit_date STRING,
    price               DOUBLE,
    freight_value       DOUBLE
);
```

### Java 代码（BulkloadFile 类）

```java
import com.clickzetta.client.BulkloadStream;
import com.clickzetta.client.ClickZettaClient;
import com.clickzetta.client.RowStream;
import com.clickzetta.client.StreamState;
import com.clickzetta.platform.client.api.Row;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.text.MessageFormat;

public class BulkloadFile {
    private static ClickZettaClient client;
    private static final String password = "";
    private static final String table = "bulk_order_items";
    private static final String workspace = "";
    private static final String schema = "public";
    private static final String vc = "default";
    private static final String user = "";
    static BulkloadStream bulkloadStream;

    public static void main(String[] args) throws Exception {
        initialize();
        File csvFile = new File("olist_order_items_dataset.csv");
        BufferedReader reader = new BufferedReader(new FileReader(csvFile));
        reader.readLine(); // 跳过 header 行

        String line;
        while ((line = reader.readLine()) != null) {
            String[] values = line.split(",");
            // 类型转换必须与建表 DDL 一致
            String orderId = values[0];
            int orderItemId = Integer.parseInt(values[1]);
            String productId = values[2];
            String sellerId = values[3];
            String shippingLimitDate = values[4];
            double price = Double.parseDouble(values[5]);
            double freightValue = Double.parseDouble(values[6]);

            Row row = bulkloadStream.createRow();
            // ⚠️ BulkloadStream 用列索引（从 0 开始），顺序与建表 DDL 一致
            row.setValue(0, orderId);
            row.setValue(1, orderItemId);
            row.setValue(2, productId);
            row.setValue(3, sellerId);
            row.setValue(4, shippingLimitDate);
            row.setValue(5, price);
            row.setValue(6, freightValue);
            // ⚠️ 必须调用 apply()，否则数据不发送到服务端
            bulkloadStream.apply(row);
        }

        reader.close();
        bulkloadStream.close();
        waitForBulkloadCompletion();
        client.close();
        System.out.println("Data inserted successfully!");
    }

    private static void initialize() throws Exception {
        // 推荐：显式参数方式（2.0.0+ 支持）
        client = ClickZettaClient.newBuilder()
            .service("cn-shanghai-alicloud.api.clickzetta.com")
            .instance("your_instance")
            .workspace(workspace)
            .schema(schema)
            .username(user)
            .password(password)
            .vcluster(vc)
            .build();
        bulkloadStream = client.newBulkloadStreamBuilder()
            .schema(schema)
            .table(table)
            .operate(RowStream.BulkLoadOperate.APPEND)
            .build();
    }

    private static void waitForBulkloadCompletion() throws InterruptedException {
        while (bulkloadStream.getState() == StreamState.RUNNING) {
            Thread.sleep(1000);
        }
        if (bulkloadStream.getState() == StreamState.FAILED) {
            throw new RuntimeException(bulkloadStream.getErrorMessage());
        }
    }
}
```

## 关键 API

| API | 说明 |
|---|---|
| `bulkloadStream.createRow()` | 创建行对象（无参数） |
| `row.setValue(int index, Object value)` | 按列索引设值（从 0 开始） |
| `bulkloadStream.apply(row)` | 发送行到服务端（必须调用） |
| `bulkloadStream.close()` | 关闭并触发提交 |
| `bulkloadStream.getState()` | 获取状态：RUNNING / SUCCEEDED / FAILED |
| `bulkloadStream.getErrorMessage()` | 获取失败原因 |

## 类型映射

| Java 类型 | Lakehouse 类型 |
|---|---|
| `Long` / `long` | BIGINT |
| `Integer` / `int` | INT |
| `Double` / `double` | DOUBLE |
| `String` | STRING / VARCHAR |
| `Boolean` | BOOLEAN |
| `java.sql.Timestamp` | TIMESTAMP |
| `java.sql.Date` | DATE |
| `BigDecimal` | DECIMAL |

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 数据写入后查不到 | 未调用 `apply()` 或未等待 RUNNING 结束 | 确认每行都调用 `apply()`，等待状态变为 SUCCEEDED |
| 主键表写入报错 | BulkloadStream 不支持主键表 | 改用 JDBC + MERGE 或 Flink igs-dynamic-table |
| 列值类型不匹配 | Java 类型与建表 DDL 不一致 | 写入前做类型转换（parseInt、parseDouble 等） |
| 连接失败 | URL 参数名错误 | BulkloadStream 用 `virtualcluster=`，不是 `vcluster=` |
