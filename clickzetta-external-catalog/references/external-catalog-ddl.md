# External Catalog 参考

> 来源：https://www.yunqi.tech/documents/external-catalog-summary 等

> ⚠️ External Catalog 当前处于公开预览阶段。目前只有 instance admin 角色可以查询 Catalog。

## 概述

External Catalog 映射外部数据系统（Hive、Iceberg、Databricks）的数据库，使 Lakehouse 可对其执行**只读**联邦查询。

**支持的数据源**：
- Apache Hive（通过 Hive Metastore）
- Iceberg REST Catalog（如 Snowflake OpenCatalog）
- Databricks Unity Catalog

---

## 创建流程（以 Hive 为例）

### 步骤 1：创建存储连接

```sql
-- OSS
CREATE STORAGE CONNECTION IF NOT EXISTS catalog_storage_oss
  TYPE OSS
  ACCESS_ID = 'LTAIxxxxxxxxxxxx'
  ACCESS_KEY = 'T8Gexxxxxxmtxxxxxx'
  ENDPOINT = 'oss-cn-hangzhou-internal.aliyuncs.com';

-- COS
CREATE STORAGE CONNECTION IF NOT EXISTS catalog_storage_cos
  TYPE COS
  ACCESS_KEY = '<access_key>'
  SECRET_KEY = '<secret_key>'
  REGION = 'ap-shanghai'
  APP_ID = '1310000503';

-- S3
CREATE STORAGE CONNECTION IF NOT EXISTS catalog_storage_s3
  TYPE S3
  ACCESS_KEY = '<access_key>'
  SECRET_KEY = '<secret_key>'
  REGION = 'us-east-1';
```

### 步骤 2：创建 Catalog Connection

```sql
-- Hive Metastore
CREATE CATALOG CONNECTION IF NOT EXISTS catalog_api_connection
  TYPE hms
  hive_metastore_uris = 'host:9083'
  storage_connection = 'catalog_storage_oss';
```

参数说明：
- `type`：连接类型，目前支持 `hms`（Hive Metastore Service）
- `hive_metastore_uris`：HMS 服务地址，格式 `host:port`，端口通常为 9083
- `storage_connection`：已创建的存储连接名称

### 步骤 3：创建 External Catalog

```sql
CREATE EXTERNAL CATALOG my_external_catalog
  CONNECTION catalog_api_connection;
```

---

## 查看 Catalog

```sql
-- 列出所有 Catalog
SHOW CATALOGS;

-- 查看 Catalog 详情
DESC CATALOG my_external_catalog;
DESC CATALOG EXTENDED my_external_catalog;
```

---

## 查看 Catalog 下的对象

```sql
-- 查看 Schema 列表
SHOW SCHEMAS IN my_external_catalog;

-- 查看 Schema 列表（含类型：managed/external）
SHOW SCHEMAS EXTENDED IN my_external_catalog;

-- 查看表列表
SHOW TABLES IN my_external_catalog.my_schema;

-- 查看表结构
DESC TABLE my_external_catalog.my_schema.my_table;
```

---

## 查询外部数据

```sql
-- 三层命名空间语法（必须）
SELECT * FROM my_external_catalog.my_schema.my_table;

-- 联邦查询（外部表 JOIN 内部表）
SELECT e.*, i.region
FROM my_external_catalog.hive_schema.orders e
JOIN public.dim_region i ON e.region_id = i.id;
```

⚠️ 查询 External Catalog 下的表**必须**使用三层结构语法（catalog.schema.table），不支持 `USE` 切换 catalog。

---

## 删除 Catalog

```sql
DROP CATALOG IF EXISTS my_external_catalog;
```

---

## 注意事项

- External Catalog 为**只读**，不支持写入操作
- HMS 所在服务器网络需与 Lakehouse 打通（可通过 PrivateLink 实现）
- 目前只有 `instance_admin` 角色可以创建和查询 External Catalog
- Databricks Unity Catalog 要求与 Lakehouse 在同一云平台（如同在 AWS 上）
