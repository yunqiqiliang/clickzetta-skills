# Volume 管理参考

> 来源：https://www.yunqi.tech/documents/datalake_volume_object 等

## Volume 类型

| 类型 | 说明 |
|---|---|
| 外部 Volume（External Volume） | 挂载 OSS/COS/S3 等对象存储路径 |
| 内部 Volume（Internal Volume） | 系统托管存储，含 User Volume、Table Volume、命名 Volume |

---

## CREATE EXTERNAL VOLUME

```sql
-- OSS
CREATE EXTERNAL VOLUME my_oss_volume
  LOCATION 'oss://<bucket>/<path>'
  USING CONNECTION my_oss_conn
  DIRECTORY = (ENABLE = TRUE, AUTO_REFRESH = TRUE)
  RECURSIVE = TRUE;

-- COS
CREATE EXTERNAL VOLUME my_cos_volume
  LOCATION 'cos://<bucket>/<path>'
  USING CONNECTION my_cos_conn
  DIRECTORY = (ENABLE = TRUE)
  RECURSIVE = TRUE;

-- S3
CREATE EXTERNAL VOLUME my_s3_volume
  LOCATION 's3://<bucket>/<path>'
  USING CONNECTION my_s3_conn
  DIRECTORY = (ENABLE = TRUE)
  RECURSIVE = TRUE;
```

参数说明：
- `LOCATION`：对象存储路径
- `USING CONNECTION`：已创建的 STORAGE CONNECTION 名称
- `DIRECTORY`：目录功能配置，`ENABLE=TRUE` 开启目录索引，`AUTO_REFRESH=TRUE` 自动刷新
- `RECURSIVE`：是否递归扫描子目录

---

## ALTER VOLUME

```sql
-- 刷新目录元数据
ALTER VOLUME my_oss_volume REFRESH;
```

---

## DROP VOLUME

```sql
DROP VOLUME IF EXISTS my_oss_volume;
```

---

## SHOW / DESC VOLUME

```sql
-- 列出所有 Volume
SHOW VOLUMES;

-- 按条件过滤
SHOW VOLUMES WHERE external = true;
SHOW VOLUMES WHERE volume_name = 'my_oss_volume';
SHOW VOLUMES WHERE connection = 'my_oss_conn';

-- 查看 Volume 详情
DESC VOLUME my_oss_volume;

-- 查看 Volume 目录下的文件
SHOW VOLUME DIRECTORY my_oss_volume;
```

---

## 查看目录元数据（DIRECTORY 函数）

```sql
-- 查看 Volume 目录元数据（需先 ALTER VOLUME REFRESH）
SELECT * FROM DIRECTORY(VOLUME my_oss_volume);
```

---

## User Volume 操作

```sql
-- 查看 User Volume 文件列表
SHOW USER VOLUME DIRECTORY;

-- 上传文件到 User Volume 根目录
PUT '/local/path/file.csv' TO USER VOLUME;

-- 上传并指定目标路径
PUT '/local/path/file.csv' TO USER VOLUME FILE 'subdir/file.csv';

-- 通配符上传多个文件
PUT '/local/path/images/*' TO USER VOLUME SUBDIRECTORY 'images/';

-- 下载文件
GET USER VOLUME FILE 'subdir/file.csv' TO '/local/output/';

-- 删除文件
REMOVE USER VOLUME FILE 'subdir/file.csv';

-- 删除目录下所有文件
REMOVE USER VOLUME SUBDIRECTORY '/';
```

---

## 从 Volume 查询数据（SELECT FROM VOLUME）

```sql
-- 查询 CSV 文件
SELECT * FROM VOLUME my_oss_volume
USING CSV
OPTIONS('header' = 'true', 'sep' = ',')
SUBDIRECTORY 'data/'
LIMIT 100;

-- 查询 Parquet 文件
SELECT * FROM VOLUME my_oss_volume
USING PARQUET
FILES('part-00001.parquet', 'part-00002.parquet');

-- 正则匹配文件
SELECT * FROM VOLUME my_oss_volume
USING PARQUET
REGEXP '.*2024-0[1-3].parquet';

-- 查询 User Volume 文件
SELECT * FROM USER VOLUME
USING CSV
OPTIONS('header' = 'true')
FILES('data.csv')
LIMIT 10;
```

支持格式：`CSV`、`PARQUET`、`ORC`、`JSON`、`BSON`

CSV OPTIONS 常用参数：
- `header`：是否有表头，默认 `false`
- `sep`：列分隔符，默认 `,`
- `compression`：压缩格式（gzip/zstd/zlib）
- `multiLine`：是否支持多行字段，默认 `false`

---

## COPY INTO TABLE（从 Volume 导入）

```sql
COPY INTO my_table
FROM VOLUME my_oss_volume
USING CSV
OPTIONS('header' = 'true')
SUBDIRECTORY 'data/';
```

## COPY INTO VOLUME（导出到 Volume）

```sql
-- 导出表到 Volume
COPY INTO VOLUME my_oss_volume
SUBDIRECTORY 'export/'
FROM my_table
USING CSV
OPTIONS('header' = 'true');

-- 导出查询结果
COPY INTO VOLUME my_oss_volume
SUBDIRECTORY 'export/'
FROM (SELECT * FROM orders WHERE year = 2024)
USING PARQUET;
```
