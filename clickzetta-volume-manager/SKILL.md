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
  Keywords: Volume, OSS, COS, S3, mount, file query, COPY INTO, external storage
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

> ⚠️ **阿里云 OSS 参数名**：
> - 必须使用小写 `access_id` / `access_key`
> - `access_id`：对应阿里云控制台的 **AccessKey ID**
> - `access_key`：对应阿里云控制台的 **AccessKey Secret**
> - ⚠️ 大写 `ACCESS_KEY` / `SECRET_KEY` 会报错

```sql
-- 阿里云 OSS
CREATE STORAGE CONNECTION IF NOT EXISTS my_oss_conn
  TYPE OSS
  access_id = 'LTAIxxxxxxxxxxxx'
  access_key = 'T8Gexxxxxxmtxxxxxx'
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

-- 刷新目录元数据后查询（上传新文件后可能需要手动刷新）
ALTER VOLUME my_oss_volume REFRESH;
SELECT * FROM DIRECTORY(VOLUME my_oss_volume);
```

> ⚠️ **目录刷新注意**：上传文件到对象存储后，`SHOW VOLUME DIRECTORY` 可能不会立即显示新文件。
> 如果启用了 `AUTO_REFRESH = TRUE`，系统会定期自动刷新；否则需要手动执行 `ALTER VOLUME name REFRESH`。

---

## 直接查询 Volume 中的文件

> ⚠️ **语法限制**：ClickZetta 不支持 `@volume_name` 简写（Snowflake Stage 语法），必须使用 `FROM VOLUME name USING format` 完整语法。
> ⚠️ **多格式文件处理**：如果 Volume 中包含多种格式的文件（如 .csv 和 .json 混合），不指定 `FILES()` 或 `SUBDIRECTORY` 时会尝试读取所有文件，可能因格式不匹配而报错。建议使用 `FILES('xxx.csv')` 指定文件或 `SUBDIRECTORY 'csv_data/'` 指定子目录。
> ⚠️ **JSON 嵌套字段访问**：使用 `data['key']` 语法（不是 Snowflake 的 `data:key` 语法）。

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

-- 查询指定文件（推荐，避免多格式冲突）
SELECT * FROM VOLUME my_oss_volume
USING JSON
FILES('user_events.json');

-- 查询 JSON 嵌套字段
SELECT
  data['event_id'] AS event_id,
  data['properties']['device'] AS device
FROM VOLUME my_oss_volume
USING JSON
FILES('events.json');

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
-- 导出整张表为 Parquet（到 External Volume）
COPY INTO VOLUME my_oss_volume
SUBDIRECTORY 'export/'
FROM TABLE my_table
FILE_FORMAT = (TYPE = PARQUET);

-- 导出查询结果为 CSV（带压缩）
COPY INTO VOLUME my_oss_volume
SUBDIRECTORY 'export/2024/'
FROM (SELECT * FROM orders WHERE year = 2024)
FILE_FORMAT = (TYPE = CSV COMPRESSION = 'GZIP');

-- 导出到 User Volume
COPY INTO USER VOLUME
SUBDIRECTORY 'my_export/'
FROM TABLE my_table
FILE_FORMAT = (TYPE = CSV);

-- 导出到 Table Volume
COPY INTO TABLE VOLUME my_table
SUBDIRECTORY 'backup/'
FROM TABLE my_table
FILE_FORMAT = (TYPE = PARQUET);
```

> ⚠️ `COPY INTO VOLUME` 导出使用 `FILE_FORMAT = (TYPE = CSV/PARQUET)`，不是 `USING CSV`。
> `USING` 关键字仅用于 `SELECT FROM VOLUME` 查询文件。

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
| SELECT FROM VOLUME 报错 | 格式不匹配 | 确认 USING 后的格式与实际文件格式一致；使用 `FILES()` 指定文件 |
| COPY INTO 读取多格式文件失败 | Volume 中有混合格式文件 | 使用 `FILES('xxx.csv')` 指定文件或 `SUBDIRECTORY` 指定子目录 |
| PUT 命令失败 | 本地路径不存在 | 确认本地文件路径正确 |
| COPY INTO 报错 | 权限不足 | 检查 STORAGE CONNECTION 的访问密钥权限 |
| `@volume` 语法报错 | ClickZetta 不支持 | 使用 `FROM VOLUME name USING format` 完整语法 |
| `data:key` 语法报错 | Snowflake JSON 语法不适用 | 使用 `data['key']` 语法访问 JSON 嵌套字段 |
| `METADATA$FILENAME` 报错 | ClickZetta 不支持此元数据字段 | 使用字符串字面量或在 INSERT 时手动添加文件路径列 |

---

## Snowflake 迁移对照

| Snowflake 语法 | ClickZetta 等价语法 | 说明 |
|---|---|---|
| `@my_stage` | `VOLUME my_volume` | Stage → Volume |
| `SELECT * FROM @stage/path` | `SELECT * FROM VOLUME vol USING CSV SUBDIRECTORY 'path/'` | 必须指定 USING 格式 |
| `data:key::STRING` | `data['key']` | JSON 字段访问 |
| `data:nested.key` | `data['nested']['key']` | 嵌套 JSON 访问 |
| `METADATA$FILENAME` | 不支持 | 需手动添加文件路径列 |
| `METADATA$FILE_ROW_NUMBER` | 不支持 | 无等价功能 |
| `FILE_FORMAT = (TYPE = CSV)` | `USING CSV OPTIONS(...)` | 导入时用 USING，导出时用 FILE_FORMAT |
| `COPY INTO table FROM @stage` | `COPY INTO table FROM VOLUME vol USING format` | 导入语法 |
| `COPY INTO @stage FROM table` | `COPY INTO VOLUME vol SUBDIRECTORY '/' FROM TABLE t FILE_FORMAT=(...)` | 导出语法 |
