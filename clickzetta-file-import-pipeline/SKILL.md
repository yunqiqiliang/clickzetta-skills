---
name: clickzetta-file-import-pipeline
description: |
  从 URL、本地文件或 Volume 路径将数据导入到 ClickZetta 表中，覆盖文件下载、格式推断、
  表创建、COPY INTO 导入、结果验证的完整流程。当用户说"导入数据"、"从 URL 加载"、
  "上传 CSV 到表"、"文件导入"、"COPY INTO"时触发。包含 ClickZetta USER VOLUME 机制、
  COPY INTO 语法、格式推断规则、写入模式语义等平台特有知识。
  Keywords: file import, URL, CSV, JSON, Parquet, COPY INTO, Volume
---

# URL/文件数据导入工作流

## 指令

### 步骤 1：获取源文件并上传到 Volume
根据数据来源选择对应方式：
- **HTTP/HTTPS URL**：需要先用外部工具下载到本地，然后用 `PUT` 命令上传到 User Volume
- **本地文件**：执行 SQL `PUT '/local/path/file.csv' TO USER VOLUME` 上传
- **Volume 路径**：文件已在 Volume 上，跳过此步骤
- **外部 Volume（OSS/S3/COS）**：文件已在外部 Volume，直接使用
- 记录上传后的 Volume 名称和文件名，后续步骤需要

> ⚠️ **注意**：文件上传操作参考 `clickzetta-volume-manager` skill。

### 步骤 2：推断文件格式
根据文件扩展名推断格式（ClickZetta COPY INTO 支持的格式）：
- `.csv`, `.tsv`, `.txt` → CSV 格式
- `.json`, `.jsonl`, `.ndjson` → JSON 格式
- `.parquet`, `.pq` → PARQUET 格式
- `.orc` → ORC 格式
- `.bson` → BSON 格式
如果扩展名不明确，执行 `SELECT FROM VOLUME ... USING format` 预览文件内容来确认格式和 schema。

### 步骤 3：确认或创建目标表
根据写入模式处理目标表：
- **create 模式**：表必须不存在。执行 `SELECT FROM VOLUME ... LIMIT 5` 推断 schema，然后执行 `CREATE TABLE` 创建表
- **append 模式**：表必须已存在。用 `DESC TABLE <table_name>` 确认表存在并检查列兼容性
- **overwrite 模式**：表存在则先清空。执行 `TRUNCATE TABLE table_name`，再执行 COPY INTO（⚠️ 不支持 `COPY OVERWRITE INTO` 语法）

### 步骤 4：执行 COPY INTO 导入数据
执行 COPY INTO 语句。核心语法：

```sql
COPY INTO target_table
FROM VOLUME volume_name
USING format_type
OPTIONS('option_name' = 'value')
FILES('filename');
```

对于 USER VOLUME（通过 PUT 命令上传的文件）：
```sql
COPY INTO target_table
FROM USER VOLUME
USING CSV
OPTIONS('header' = 'true')
FILES('uploaded_filename');
```

CSV 格式可附加 OPTIONS：
```sql
COPY INTO target_table
FROM VOLUME vol
USING CSV
OPTIONS('header' = 'true', 'sep' = ',', 'quote' = '"', 'nullValue' = '')
FILES('data.csv');
```

⚠️ **语法顺序要求**：`OPTIONS` 必须在 `FILES` 之前，否则报错 `Syntax error - missing EQ at '('`

overwrite 模式（⚠️ 不支持 `COPY OVERWRITE INTO`）：
```sql
-- 正确方式：先 TRUNCATE 再 COPY
TRUNCATE TABLE target_table;
COPY INTO target_table FROM VOLUME vol USING CSV FILES('data.csv');
```

### 步骤 5：验证导入结果
执行验证查询：
```sql
SELECT COUNT(*) as row_count FROM target_table;
SELECT * FROM target_table LIMIT 5;
```
确认行数符合预期，数据内容正确。

## 示例

### 示例 1：从 URL 导入 CSV 到新表
```sql
-- 1. 下载 URL 文件到本地，然后上传到 User Volume
PUT '/tmp/data.csv' TO USER VOLUME;

-- 2. 预览文件内容推断 schema
SELECT * FROM USER VOLUME USING CSV OPTIONS('header' = 'true') FILES('data.csv') LIMIT 5;
-- 推断出列：id INT, name STRING, value DOUBLE

-- 3. 创建目标表
CREATE TABLE imported_data (id INT, name STRING, value DOUBLE);

-- 4. 执行 COPY INTO 导入（注意：OPTIONS 必须在 FILES 之前）
COPY INTO imported_data FROM USER VOLUME USING CSV OPTIONS('header' = 'true') FILES('data.csv');

-- 5. 验证导入结果
SELECT COUNT(*) FROM imported_data;
```

### 示例 2：追加 Parquet 数据到已有表
```sql
-- 1. 上传本地文件到 User Volume
PUT '/local/new_batch.parquet' TO USER VOLUME;

-- 2. 确认目标表存在
DESC TABLE existing_table;

-- 3. 执行 COPY INTO 导入（Parquet 格式通常不需要 OPTIONS）
COPY INTO existing_table FROM USER VOLUME USING PARQUET FILES('new_batch.parquet');

-- 4. 验证导入结果
SELECT COUNT(*) FROM existing_table;
```

### 示例 3：从外部 Volume（OSS）导入
```sql
-- 1. 查看 Volume 中的文件列表
SHOW VOLUME DIRECTORY my_oss_volume;

-- 2. 预览文件内容
SELECT * FROM VOLUME my_oss_volume USING CSV OPTIONS('header' = 'true') FILES('data.csv') LIMIT 5;

-- 3. 创建目标表并导入（注意：OPTIONS 必须在 FILES 之前）
CREATE TABLE imported_data (col1 INT, col2 STRING);
COPY INTO imported_data FROM VOLUME my_oss_volume USING CSV OPTIONS('header' = 'true') FILES('data.csv');
```

## 故障排除

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| COPY INTO 报 "table not found" | create 模式下表未创建，或 append 模式下表名拼写错误 | 先用 `SHOW TABLES` 确认表是否存在 |
| COPY INTO 报 "file not found" | FILES 中的文件名与 Volume 上的实际文件名不匹配 | 执行 `SHOW VOLUME DIRECTORY vol_name` 或 `SHOW USER VOLUME DIRECTORY` 确认文件名，注意大小写敏感 |
| COPY INTO 报语法错误 "missing EQ at '('" | OPTIONS 放在了 FILES 之后 | 调整顺序，确保 `OPTIONS` 在 `FILES` 之前：`USING CSV OPTIONS(...) FILES(...)` |
| CSV 导入列数不匹配 | CSV 文件有 header 行但未指定 `OPTIONS('header'='true')`，导致 header 被当作数据行 | 添加 `OPTIONS('header' = 'true')`，或检查 CSV 分隔符是否正确（sep 参数） |
| COPY INTO 报 "schema mismatch" | 文件中的数据类型与目标表列定义不兼容 | 执行 `SELECT FROM VOLUME ... USING format LIMIT 5` 预览实际数据，调整表定义或使用列映射 |
| overwrite 模式数据未清空 | 使用了 `COPY OVERWRITE INTO` 语法（不支持） | overwrite 模式应先用 `TRUNCATE TABLE` 清空表，再执行 `COPY INTO` |
| SELECT FROM VOLUME 报错 | 格式不匹配或多格式文件混合 | 确认 USING 后的格式与实际文件格式一致；使用 `FILES()` 指定文件或 `SUBDIRECTORY` 指定子目录 |
| PUT 命令失败 | 本地文件路径不存在 | 确认本地文件路径正确，文件存在 |

---

## 依赖的 Skills

| 操作 | 需要加载的 Skill |
|------|-----------------|
| 文件上传/下载/删除 | `clickzetta-volume-manager` |
| 查询 Volume 文件内容 | `clickzetta-volume-manager` |
| COPY INTO 导入 | 本 Skill |
