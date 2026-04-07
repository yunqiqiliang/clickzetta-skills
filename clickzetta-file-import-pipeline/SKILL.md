---
name: clickzetta-file-import-pipeline
description: |
  从 URL、本地文件或 Volume 路径将数据导入到 ClickZetta 表中，覆盖文件下载、格式推断、
  表创建、COPY INTO 导入、结果验证的完整流程。当用户说"导入数据"、"从 URL 加载"、
  "上传 CSV 到表"、"文件导入"、"COPY INTO"时触发。包含 ClickZetta USER VOLUME 机制、
  COPY INTO 语法、格式推断规则、写入模式语义等平台特有知识。
---

# URL/文件数据导入工作流

## 指令

### 步骤 1：获取源文件并上传到 Volume
根据数据来源选择对应方式：
- HTTP/HTTPS URL：使用 `put_file_to_volume` 的 source_path 参数直接传入 URL，工具会自动下载并上传
- 本地文件：使用 `put_file_to_volume` 指定 source_path 为本地路径
- Volume 路径（`volume://vol_name/path`）：文件已在 Volume 上，跳过此步骤
- 记录上传后的 Volume 名称和文件名，后续步骤需要

### 步骤 2：推断文件格式
根据文件扩展名推断格式（ClickZetta COPY INTO 支持的格式）：
- `.csv`, `.tsv`, `.txt` → CSV 格式
- `.json`, `.jsonl`, `.ndjson` → JSON 格式
- `.parquet`, `.pq` → PARQUET 格式
- `.orc` → ORC 格式
- `.bson` → BSON 格式
如果扩展名不明确，使用 `preview_volume_data` 预览文件内容来确认格式和 schema。

### 步骤 3：确认或创建目标表
根据写入模式处理目标表：
- **create 模式**：表必须不存在。使用 `preview_volume_data` 推断 schema，然后用 `create_table` 创建表
- **append 模式**：表必须已存在。用 `desc_object`(object_type='TABLE') 确认表存在并检查列兼容性
- **overwrite 模式**：表存在则先清空。用 `write_query` 执行 `TRUNCATE TABLE table_name`，再执行 COPY INTO

### 步骤 4：执行 COPY INTO 导入数据
使用 `write_query` 执行 COPY INTO 语句。核心语法：

```sql
COPY INTO target_table
FROM VOLUME volume_name
USING format_type
FILES('filename');
```

对于 USER VOLUME（通过 put_file_to_volume 上传的文件）：
```sql
COPY INTO target_table
FROM USER VOLUME
USING CSV
FILES('uploaded_filename');
```

CSV 格式可附加 OPTIONS：
```sql
COPY INTO target_table
FROM VOLUME vol USING CSV
FILES('data.csv')
OPTIONS('header'='true', 'sep'=',', 'quote'='"', 'nullValue'='');
```

overwrite 模式使用 COPY OVERWRITE：
```sql
COPY OVERWRITE INTO target_table
FROM VOLUME vol USING CSV FILES('data.csv');
```

### 步骤 5：验证导入结果
使用 `read_query` 执行验证查询：
```sql
SELECT COUNT(*) as row_count FROM target_table;
SELECT * FROM target_table LIMIT 5;
```
确认行数符合预期，数据内容正确。

## 示例

### 示例 1：从 URL 导入 CSV 到新表
```
1. put_file_to_volume(source_path='https://example.com/data.csv', target_volume='my_vol')
2. preview_volume_data(source_volume='my_vol', files='data.csv', format='CSV', limit='5')
   → 推断出列: id INT, name STRING, value DOUBLE
3. create_table(table_name='imported_data', columns='id INT, name STRING, value DOUBLE')
4. write_query(query="COPY INTO imported_data FROM VOLUME my_vol USING CSV FILES('data.csv') OPTIONS('header'='true')")
5. read_query(query="SELECT COUNT(*) FROM imported_data")
```

### 示例 2：追加 Parquet 数据到已有表
```
1. put_file_to_volume(source_path='/local/new_batch.parquet', target_volume='data_vol')
2. desc_object(object_name='existing_table', object_type='TABLE')  → 确认表存在
3. write_query(query="COPY INTO existing_table FROM VOLUME data_vol USING PARQUET FILES('new_batch.parquet')")
4. read_query(query="SELECT COUNT(*) FROM existing_table")
```

## 故障排除

错误：COPY INTO 报 "table not found"
原因：create 模式下表未创建，或 append 模式下表名拼写错误
解决方案：先用 `show_object_list`(object_type='TABLES') 确认表是否存在

错误：COPY INTO 报 "file not found"
原因：FILES 中的文件名与 Volume 上的实际文件名不匹配
解决方案：用 `list_files_on_volume` 确认文件名，注意大小写敏感

错误：CSV 导入列数不匹配
原因：CSV 文件有 header 行但未指定 OPTIONS(header='true')，导致 header 被当作数据行
解决方案：添加 OPTIONS(header='true')，或检查 CSV 分隔符是否正确（sep 参数）

错误：COPY INTO 报 "schema mismatch"
原因：文件中的数据类型与目标表列定义不兼容
解决方案：用 `preview_volume_data` 预览实际数据，调整表定义或使用列映射

错误：overwrite 模式数据未清空
原因：使用了普通 COPY INTO 而非 COPY OVERWRITE INTO
解决方案：overwrite 模式必须使用 `COPY OVERWRITE INTO` 语法
