---
name: clickzetta-external-catalog
description: |
  配置和使用 ClickZetta Lakehouse External Catalog，实现对 Hive、Iceberg、Databricks 等
  外部数据源的联邦查询（只读）。覆盖完整创建流程：存储连接 → Catalog Connection →
  External Catalog，以及 SHOW/DESC/查询外部表等操作。
  当用户说"外部数据目录"、"External Catalog"、"联邦查询"、"Hive 联邦"、
  "访问 Hive 数据"、"Databricks 联邦"、"Iceberg 联邦"、"跨数据源查询"、
  "不迁移数据直接查询"、"Catalog Connection"时触发。
---

# ClickZetta External Catalog

> ⚠️ 创建 External Catalog 需要 `instance_admin` 角色。查询权限可通过 GRANT 授予其他用户。

阅读 [references/external-catalog-ddl.md](references/external-catalog-ddl.md) 了解完整语法。

## 概述

External Catalog 让 Lakehouse 可以**不迁移数据**，直接对外部数据系统（Hive、Iceberg、Databricks）执行只读联邦查询。

**支持数据源**：Apache Hive · Iceberg REST Catalog · Databricks Unity Catalog

---

## 创建流程（三步）

### 步骤 1：创建存储连接

```sql
-- 阿里云 OSS
CREATE STORAGE CONNECTION IF NOT EXISTS catalog_storage_oss
  TYPE OSS
  ACCESS_ID = 'LTAIxxxxxxxxxxxx'
  ACCESS_KEY = 'T8Gexxxxxxmtxxxxxx'
  ENDPOINT = 'oss-cn-hangzhou-internal.aliyuncs.com';
```

### 步骤 2：创建 Catalog Connection

```sql
CREATE CATALOG CONNECTION IF NOT EXISTS hive_catalog_conn
  TYPE hms
  hive_metastore_uris = 'hms-host:9083'
  storage_connection = 'catalog_storage_oss';
```

### 步骤 3：创建 External Catalog

```sql
CREATE EXTERNAL CATALOG my_hive_catalog
  CONNECTION hive_catalog_conn;
```

---

## 验证连通性

```sql
-- 查看 Schema 列表（验证连通）
SHOW SCHEMAS IN my_hive_catalog;

-- 查看表列表
SHOW TABLES IN my_hive_catalog.my_schema;

-- 查询数据
SELECT * FROM my_hive_catalog.my_schema.my_table LIMIT 10;
```

---

## 查看与管理

```sql
-- 列出所有 Catalog
SHOW CATALOGS;

-- 查看 Catalog 详情
DESC CATALOG my_hive_catalog;

-- 查看表结构
DESC TABLE my_hive_catalog.my_schema.my_table;

-- 删除 Catalog
DROP CATALOG IF EXISTS my_hive_catalog;
```

---

## 联邦查询示例

```sql
-- 外部 Hive 表 JOIN 内部 Lakehouse 表
SELECT h.order_id, h.amount, d.region_name
FROM my_hive_catalog.sales.orders h
JOIN public.dim_region d ON h.region_id = d.id
WHERE h.order_date >= '2024-01-01';
```

⚠️ 必须使用三层命名空间语法：`catalog.schema.table`

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 无法连接 HMS | 网络未打通 | 通过 PrivateLink 打通 Lakehouse 与 HMS 服务器网络 |
| 权限不足 | 非 instance_admin | 联系管理员授予 instance_admin 角色 |
| 查询报错找不到表 | 未使用三层语法 | 使用 `catalog.schema.table` 格式 |
| Databricks 连接失败 | 不在同一云平台 | 确保 Databricks 存储与 Lakehouse 在同一云平台 |
