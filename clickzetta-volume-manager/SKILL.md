---
name: clickzetta-volume-manager
description: |
  管理 ClickZetta Lakehouse Volume 对象，实现对象存储（OSS/COS/S3）的挂载、
  文件查询与数据导入导出。覆盖外部 Volume 创建（OSS/COS/S3）、内部 User Volume
  文件操作（PUT/GET/REMOVE）、SELECT FROM VOLUME 直接查询文件、
  COPY INTO TABLE 导入、COPY INTO VOLUME 导出等完整工作流。
  当用户说"创建Volume"、"挂载OSS"、"挂载S3"、"挂载COS"、"Volume管理"、
  "查询OSS文件"、"查询S3文件"、"上传文件到Volume"、"PUT文件"、"GET文件"、
  "从Volume导入数据"、"导出到Volume"、"COPY INTO VOLUME"、"SELECT FROM VOLUME"、
  "User Volume"、"数据湖文件"、"数据导出"、"导出数据"、"导出CSV"、"导出Parquet"、
  "COPY OVERWRITE INTO"时触发。
---

# ClickZetta Volume 管理

阅读 [references/volume-ddl.md](references/volume-ddl.md) 了解完整语法。

## Volume 类型

| 类型 | 说明 | 典型用途 |
|---|---|---|
| 外部 Volume | 挂载 OSS/COS/S3 路径 | 访问已有对象存储数据 |
| User Volume | 用户专属内部存储 | 临时文件上传、本地文件导入 |
| Table Volume | 表关联内部存储 | 表数据文件管理 |

---

## 创建外部 Volume

前提：先创建 STORAGE CONNECTION（对象存储认证配置）

> ⚠️ **跨云限制**：Storage Connection 必须与 Lakehouse 实例在同一云厂商。阿里云实例不能创建 COS/S3 Connection，腾讯云实例不能创建 OSS Connection。

> ⚠️ **阿里云 OSS 参数名易混淆**：`ACCESS_ID` 对应阿里云控制台的 **AccessKey ID**；`ACCESS_KEY` 对应 **AccessKey Secret**（不是 secret_key）。

```sql
-- 阿里云 OSS
CREATE STORAGE CONNECTION IF NOT EXISTS my_oss_conn
  TYPE OSS
  ACCESS_ID = 'LTAIxxxxxxxxxxxx'       -- 对应 AccessKey ID
  ACCESS_KEY = 'T8Gexxxxxxmtxxxxxx'    -- 对应 AccessKey Secret（注意：不是 secret_key）
  ENDPOINT = 'oss-cn-hangzhou-internal.aliyuncs.com';

-- 腾讯云 COS
CREATE STORAGE CONNECTION IF NOT EXISTS my_cos_conn
  TYPE COS
  ACCESS_KEY = '<access_key>'
  SECRET_KEY = '<secret_key>'
  REGION = 'ap-shanghai'
  APP_ID = '1310000503';

-- AWS S3
CREATE STORAGE CONNECTION IF NOT EXISTS my_s3_conn
  TYPE S3
  ACCESS_KEY = '<access_key>'
  SECRET_KEY = '<secret_key>'
  REGION = 'us-east-1';
```

```sql
-- 挂载阿里云 OSS
CREATE EXTERNAL VOLUME my_oss_volume
  LOCATION 'oss://my-bucket/data-path/'
  USING CONNECTION my_oss_conn
  DIRECTORY = (ENABLE = TRUE, AUTO_REFRESH = TRUE)
  RECURSIVE = TRUE;

-- 挂载腾讯云 COS
CREATE EXTERNAL VOLUME my_cos_volume
  LOCATION 'cos://my-bucket/data-path/'
  USING CONNECTION my_cos_conn
  DIRECTORY = (ENABLE = TRUE)
  RECURSIVE = TRUE;

-- 挂载 AWS S3
CREATE EXTERNAL VOLUME my_s3_volume
  LOCATION 's3://my-bucket/data-path/'
  USING CONNECTION my_s3_conn
  DIRECTORY = (ENABLE = TRUE)
  RECURSIVE = TRUE;
```

---

## 查看 Volume

```sql
-- 列出所有 Volume
SHOW VOLUMES;

-- 过滤外部 Volume（SHOW VOLUMES 不支持 WHERE 过滤，使用 information_schema）
SELECT volume_name, volume_type, volume_region, volume_creator
FROM information_schema.volumes
WHERE volume_type = 'EXTERNAL';

-- 查看详情
DESC VOLUME my_oss_volume;

-- 查看目录下的文件
SHOW VOLUME DIRECTORY my_oss_volume;

-- 刷新目录元数据后查询
ALTER VOLUME my_oss_volume REFRESH;
SELECT * FROM DIRECTORY(VOLUME my_oss_volume);
```

---

## 直接查询 Volume 中的文件

```sql
-- 查询 CSV 文件（自动推断 schema）
SELECT * FROM VOLUME my_oss_volume
USING CSV
OPTIONS('header' = 'true', 'sep' = ',')
SUBDIRECTORY 'orders/2024/'
LIMIT 100;

-- 查询 Parquet 文件
SELECT * FROM VOLUME my_oss_volume
USING PARQUET
REGEXP '.*2024-0[1-6].parquet';

-- 查询 User Volume 文件
SELECT * FROM USER VOLUME
USING CSV
OPTIONS('header' = 'true')
FILES('upload.csv');
```

---

## User Volume 文件操作

```sql
-- 查看文件列表
SHOW USER VOLUME DIRECTORY;

-- 上传本地文件
PUT '/local/path/data.csv' TO USER VOLUME;
PUT '/local/path/data.csv' TO USER VOLUME FILE 'subdir/data.csv';

-- 下载文件
GET USER VOLUME FILE 'subdir/data.csv' TO '/local/output/';

-- 删除文件
REMOVE USER VOLUME FILE 'subdir/data.csv';
```

---

## 数据导入导出

### 从 Volume 导入到表

```sql
-- CSV 导入
COPY INTO my_table
FROM VOLUME my_oss_volume
USING CSV
OPTIONS('header' = 'true')
SUBDIRECTORY 'data/';

-- 指定文件导入
COPY INTO my_table
FROM VOLUME my_oss_volume
USING PARQUET
FILES('data_2024.parquet');

-- 正则匹配文件导入
COPY INTO my_table
FROM VOLUME my_oss_volume
USING PARQUET
REGEXP '.*2024-0[1-6].parquet';

-- 覆盖写入（清空表后导入）
COPY OVERWRITE INTO my_table
FROM VOLUME my_oss_volume
USING CSV
OPTIONS('header' = 'true');
```

### 导出表到 Volume

```sql
-- 导出整张表为 Parquet
COPY INTO VOLUME my_oss_volume
SUBDIRECTORY 'export/'
FROM my_table
USING PARQUET;

-- 导出查询结果为 CSV
COPY INTO VOLUME my_oss_volume
SUBDIRECTORY 'export/2024/'
FROM (SELECT * FROM orders WHERE year = 2024)
USING CSV
OPTIONS('header' = 'true');

-- 导出为 JSON 格式
COPY INTO VOLUME my_oss_volume
SUBDIRECTORY 'export/json/'
FROM (SELECT * FROM orders LIMIT 1000)
USING JSON;

-- 导出到 User Volume
COPY INTO USER VOLUME
SUBDIRECTORY 'my_export/'
FROM my_table
USING CSV
OPTIONS('header' = 'true');
```

### 导出到本地（GET 命令）

```sql
-- 从 Volume 下载文件到本地
GET VOLUME my_oss_volume FILE 'export/data.csv' TO '/local/output/';

-- 从 User Volume 下载
GET USER VOLUME FILE 'my_export/data.csv' TO '/local/output/';
```

### 通过 Studio 导出

在 Lakehouse Studio 中：
- 执行 SQL 查询后，点击结果区域的「导出」按钮，可导出为 CSV 或 Excel 文件
- 支持导出最多 10 万行查询结果

---

## 删除 Volume

```sql
DROP VOLUME IF EXISTS my_oss_volume;
```

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| SHOW VOLUME DIRECTORY 无文件 | 目录未刷新 | 执行 `ALTER VOLUME name REFRESH` |
| SELECT FROM VOLUME 报错 | 格式不匹配 | 确认 USING 后的格式与实际文件格式一致 |
| PUT 命令失败 | 本地路径不存在 | 确认本地文件路径正确 |
| COPY INTO 报错 | 权限不足 | 检查 STORAGE CONNECTION 的访问密钥权限 |
