---
name: clickzetta-oss-ingest-pipeline
description: |
  搭建 ClickZetta 对象存储（OSS/S3/COS）数据导入管道，覆盖持续导入（PIPE）和批量一次性导入
  两大场景。持续导入支持 LIST_PURGE 扫描模式和 EVENT_NOTIFICATION 消息通知模式；批量导入支持
  Volume + INSERT INTO 和 Volume + COPY INTO 两种方式。当用户说"对象存储导入"、"OSS 数据管道"、
  "S3 数据导入"、"PIPE 持续导入"、"文件自动加载"、"存储桶数据同步"、"COS 导入"、
  "批量导入 OSS"、"从 OSS 加载数据"、"Volume 导入"时触发。
  包含 PIPE 持续导入（两种 INGEST_MODE）、批量导入（Volume + COPY/INSERT）、Connection/Volume 创建、
  监控管理等 ClickZetta 特有逻辑。
---

# 对象存储数据管道搭建工作流

## 适用场景

- 从对象存储（阿里云 OSS / AWS S3 / 腾讯云 COS）持续自动导入数据到 Lakehouse（PIPE 模式）
- 从对象存储批量一次性导入数据到 Lakehouse（Volume + COPY/INSERT 模式）
- 需要微批处理方式加载新增文件，实现近实时数据同步
- 需要选择扫描模式（LIST_PURGE）或消息通知模式（EVENT_NOTIFICATION）
- 需要对导入数据进行过滤转换（WHERE 条件、指定文件）
- 关键词：OSS PIPE、S3 导入、对象存储管道、文件自动加载、PIPE 持续导入、COS 数据同步、批量导入、Volume 导入

## 前置依赖

- ClickZetta Lakehouse 账户，具备创建 PIPE、表、存储连接、Volume 等权限
- 对象存储桶可达（Endpoint、AccessKey 或 Role ARN）
- clickzetta-studio-mcp 工具可用（`LH_execute_query`、`LH_show_object_list` 等）

## 核心概念

### INGEST_MODE 选择指引

| 模式 | 触发方式 | 适用场景 | 云平台支持 | 授权方式 |
|------|---------|---------|-----------|---------|
| `LIST_PURGE` | 定期扫描目录 | 通用场景，导入后删除源文件 | 所有云平台 | 密钥 或 Role ARN |
| `EVENT_NOTIFICATION` | 消息服务通知 | 低延迟场景，文件上传即触发 | 仅阿里云 OSS + AWS S3 | 仅 Role ARN |

### 关键限制

- 每个 PIPE 需对应独立的 Volume，不可复用
- 不支持修改 COPY 语句逻辑，需删除 PIPE 重新创建
- PIPE 中的 COPY 语句不支持 `files` / `regexp` / `subdirectory` 参数
- 数据加载无法保证严格有序
- `load_history` 去重记录保留 7 天
- 修改 `COPY_JOB_HINT` 会覆盖所有已有 hints，需一次性设置全部参数

### 文件大小建议

- gzip 压缩文件：≈ 50MB
- CSV / PARQUET 未压缩文件：128MB ~ 256MB

## 工作流

### 模式 A：LIST_PURGE 扫描模式（通用）

#### 步骤 1：创建存储连接（Storage Connection）

```sql
-- 使用 LH_execute_query 执行
-- 密钥方式（LIST_PURGE 模式支持）
CREATE STORAGE CONNECTION IF NOT EXISTS my_oss_connection
  TYPE OSS
  ENDPOINT = 'oss-cn-hangzhou.aliyuncs.com'
  ACCESS_KEY = '<your_access_key>'
  SECRET_KEY = '<your_secret_key>'
  COMMENT = 'OSS connection for data pipeline';
```

> **提示**：如果使用 Role ARN 方式（EVENT_NOTIFICATION 模式必须），参见下方"模式 B"中的 Connection 创建语法。

#### 步骤 2：创建外部 Volume

```sql
-- 使用 LH_execute_query 执行
CREATE EXTERNAL VOLUME IF NOT EXISTS pipe_volume
  STORAGE_CONNECTION = my_oss_connection
  LOCATION = 'oss://my-bucket/data-path/'
  COMMENT = 'Volume for OSS PIPE ingestion';
```

> **关键参数**：
> - 如需递归扫描子目录：添加 `recursive = true`
> - 如需自动刷新目录元数据：添加 `directory = (enable = true, auto_refresh = true)`

#### 步骤 3：验证 COPY INTO 可独立运行

在创建 PIPE 之前，先用 COPY INTO 验证数据能正常加载：

```sql
-- 使用 LH_execute_query 执行
COPY INTO my_schema.target_table
FROM VOLUME pipe_volume
USING CSV
OPTIONS (
  'header' = 'true',
  'delimiter' = ','
);
```

> **重要**：PIPE 中的 COPY 语句不支持 `files`、`regexp`、`subdirectory` 参数。确保此处验证时也不使用这些参数。

#### 步骤 4：创建 PIPE（LIST_PURGE 模式）

```sql
-- 使用 LH_execute_query 执行
CREATE PIPE IF NOT EXISTS my_oss_pipe
  INGEST_MODE = 'LIST_PURGE'
  VIRTUAL_CLUSTER = 'my_vc'
  COMMENT = 'OSS data pipeline - scan mode'
AS
COPY INTO my_schema.target_table
FROM VOLUME pipe_volume
USING CSV
OPTIONS (
  'header' = 'true',
  'delimiter' = ',',
  'purge' = 'true'
);
```

> **参数说明**：
> - `INGEST_MODE = 'LIST_PURGE'`：定期扫描 Volume 目录，发现新文件即加载
> - `purge = true`：**LIST_PURGE 模式必须设置**，加载成功后删除源文件（避免重复导入）。即使不想删除源文件，LIST_PURGE 模式也需要此参数，否则会重复导入同一文件
> - `VIRTUAL_CLUSTER`：指定执行 PIPE 任务的虚拟集群

#### 步骤 5：验证 PIPE 状态

```sql
-- 使用 LH_execute_query 执行
DESC PIPE EXTENDED my_oss_pipe;
```

确认 `pipe_execution_paused = false`（PIPE 已启动运行）。

---

### 模式 B：EVENT_NOTIFICATION 消息通知模式（低延迟）

> 仅支持阿里云 OSS + AWS S3。文件上传到桶后，通过消息服务（MNS/SQS）通知 Lakehouse 立即加载。

#### 前置准备（阿里云 OSS 示例）

1. **开通阿里云 MNS 消息服务**：在阿里云控制台开通消息服务 MNS
2. **配置 OSS 事件通知**：在 OSS 桶 → 事件通知 → 创建规则，事件类型选择 `ObjectCreated`，目标选择 MNS 队列
3. **授权 OSS 读取权限**：创建 RAM 角色，授予 `oss:GetObject`、`oss:ListBucket` 权限，记录 Role ARN
4. **授权 MNS 到 Lakehouse**：将 Lakehouse 服务账号添加到 MNS 队列的授权策略中

#### 步骤 1：创建存储连接（Role ARN 方式）

```sql
-- 使用 LH_execute_query 执行
CREATE STORAGE CONNECTION IF NOT EXISTS my_oss_role_connection
  TYPE OSS
  ENDPOINT = 'oss-cn-hangzhou.aliyuncs.com'
  ROLE_ARN = 'acs:ram::1234567890:role/clickzetta-oss-role'
  REGION = 'cn-hangzhou'
  COMMENT = 'OSS connection via Role ARN for event notification mode';
```

#### 步骤 2：创建外部 Volume

```sql
-- 使用 LH_execute_query 执行
CREATE EXTERNAL VOLUME IF NOT EXISTS pipe_event_volume
  STORAGE_CONNECTION = my_oss_role_connection
  LOCATION = 'oss://my-bucket/data-path/';
```

#### 步骤 3：创建 PIPE（EVENT_NOTIFICATION 模式）

```sql
-- 使用 LH_execute_query 执行
CREATE PIPE IF NOT EXISTS my_oss_event_pipe
  INGEST_MODE = 'EVENT_NOTIFICATION'
  VIRTUAL_CLUSTER = 'my_vc'
  ALICLOUD_MNS_QUEUE = 'my-mns-queue-name'
  COMMENT = 'OSS data pipeline - event notification mode'
AS
COPY INTO my_schema.target_table
FROM VOLUME pipe_event_volume
USING CSV
OPTIONS (
  'header' = 'true',
  'delimiter' = ','
);
```

> **参数说明**：
> - `INGEST_MODE = 'EVENT_NOTIFICATION'`：通过消息通知触发加载
> - `ALICLOUD_MNS_QUEUE`：阿里云 MNS 队列名称（AWS 使用 `AWS_SQS_QUEUE`）
> - 此模式下不需要 `purge = true`，因为是事件驱动而非扫描

---

### 模式 C：批量导入（一次性 Volume + COPY/INSERT）

> 适用于一次性或定期批量加载对象存储中的文件，无需创建 PIPE。支持阿里云 OSS、腾讯云 COS 和 AWS S3。
> 推荐使用 GENERAL PURPOSE 类型的虚拟集群执行批量加载。

#### 使用限制

- 不支持跨云导入（源存储与 Lakehouse 环境需在同一云平台）
- 同地域建议使用内网 Endpoint（如 `oss-cn-shanghai-internal.aliyuncs.com`）以提升速度和稳定性

#### 步骤 1：创建目标表

```sql
-- 使用 LH_execute_query 执行
CREATE TABLE IF NOT EXISTS my_schema.target_table (
  id STRING,
  name STRING,
  amount DECIMAL(10,2),
  created_date STRING
);
```

#### 步骤 2：创建存储连接（access_id/access_key 语法）

```sql
-- 使用 LH_execute_query 执行
-- 批量导入场景使用 access_id / access_key 语法
CREATE STORAGE CONNECTION IF NOT EXISTS my_batch_conn
  TYPE OSS
  ENDPOINT = 'oss-cn-shanghai-internal.aliyuncs.com'
  access_id = '<your_access_id>'
  access_key = '<your_access_key>'
  COMMENTS = 'OSS batch import connection';
```

> **注意**：批量导入场景中 Connection 参数使用 `access_id` / `access_key`（小写），与 PIPE 模式中的 `ACCESS_KEY` / `SECRET_KEY` 写法不同，两种写法均可使用。

#### 步骤 3：创建外部 Volume（启用目录自动刷新）

```sql
-- 使用 LH_execute_query 执行
CREATE EXTERNAL VOLUME IF NOT EXISTS my_batch_volume
  LOCATION 'oss://my-bucket/data-path/'
  USING CONNECTION my_batch_conn
  DIRECTORY = (enable=true, auto_refresh=true);
```

> **关键参数**：
> - `LOCATION`：对象存储路径，格式为 `oss://bucket/path/`
> - `USING CONNECTION`：引用已创建的存储连接
> - `DIRECTORY = (enable=true, auto_refresh=true)`：启用目录元数据并自动刷新，便于查询 Volume 中的文件列表
>
> **注意**：批量导入 Volume 使用 `LOCATION ... USING CONNECTION ...` 语法；PIPE 模式 Volume 使用 `STORAGE_CONNECTION = ... LOCATION = ...` 语法。两种语法均有效，适用于不同场景，不可混用。

#### 步骤 4a：INSERT INTO 从 Volume 导入（支持过滤转换）

```sql
-- 使用 LH_execute_query 执行
INSERT INTO my_schema.target_table
SELECT * FROM VOLUME my_batch_volume (
  id STRING,
  name STRING,
  amount DECIMAL(10,2),
  created_date STRING
) USING CSV OPTIONS ('header'='true', 'sep'=',')
FILES ('data_file_01.csv')
WHERE amount > 0;
```

> **参数说明**：
> - `VOLUME my_batch_volume (...)`：指定 Volume 及列定义（Schema-on-Read）
> - `USING CSV OPTIONS (...)`：指定文件格式和解析选项
> - `FILES ('file1.csv', 'file2.csv')`：指定要加载的文件名（可选，不指定则加载全部）
> - `WHERE ...`：对数据进行过滤转换（可选）
> - INSERT INTO 方式支持 `FILES` 和 `WHERE` 参数，适合需要精细控制的场景

#### 步骤 4b：COPY INTO 从 Volume 导入（简洁语法）

```sql
-- 使用 LH_execute_query 执行
COPY INTO my_schema.target_table
FROM VOLUME my_batch_volume (
  id STRING,
  name STRING,
  amount DECIMAL(10,2),
  created_date STRING
) USING CSV OPTIONS ('header'='true', 'sep'=',');
```

> **INSERT INTO vs COPY INTO 选择**：
> - `INSERT INTO`：支持 `FILES()` 指定文件、`WHERE` 过滤转换，适合精细控制
> - `COPY INTO`：语法更简洁，适合全量加载
> - 两者都支持 Schema-on-Read（在 FROM VOLUME 中定义列）

#### 步骤 5：验证导入结果

```sql
-- 使用 LH_execute_query 执行
SELECT COUNT(*) AS total_rows FROM my_schema.target_table;
SELECT * FROM my_schema.target_table LIMIT 10;
```

---

## 监控与运维

### 查看 PIPE 详细状态

```sql
-- 使用 LH_execute_query 执行
DESC PIPE EXTENDED my_oss_pipe;
```

关键字段：
- `pipe_execution_paused`：是否暂停
- `ingest_mode`：导入模式
- `virtual_cluster`：执行集群
- `definition`：COPY 语句定义

### 查看加载历史

```sql
-- 使用 LH_execute_query 执行
SELECT * FROM TABLE(load_history('my_schema.target_table'))
ORDER BY last_load_time DESC
LIMIT 20;
```

> `load_history` 去重记录保留 7 天。

### 通过 query_tag 过滤 PIPE 作业

PIPE 执行的作业会自动打上 `query_tag`，格式为：`pipe.<workspace_name>.<schema_name>.<pipe_name>`

```sql
-- 使用 LH_execute_query 执行
-- 在 JOBS 列表中过滤 PIPE 相关作业
SHOW JOBS WHERE query_tag = 'pipe.my_workspace.my_schema.my_oss_pipe';
```

---

## PIPE 管理操作

### 暂停 / 恢复 PIPE

```sql
-- 暂停 PIPE
ALTER PIPE my_oss_pipe SET PIPE_EXECUTION_PAUSED = true;

-- 恢复 PIPE
ALTER PIPE my_oss_pipe SET PIPE_EXECUTION_PAUSED = false;
```

### 修改 PIPE 属性

```sql
-- 修改虚拟集群
ALTER PIPE my_oss_pipe SET VIRTUAL_CLUSTER = 'new_vc';

-- 修改 COPY_JOB_HINT（注意：会覆盖所有已有 hints，需一次性设置全部参数）
ALTER PIPE my_oss_pipe SET COPY_JOB_HINT = (
  'max_file_count' = '100',
  'force' = 'false'
);
```

> **限制**：每次 ALTER PIPE 只能修改一个属性。不支持修改 COPY 语句逻辑，需删除 PIPE 重新创建。

### 删除 PIPE

```sql
DROP PIPE IF EXISTS my_oss_pipe;
```

---

## 故障排除

| 问题 | 排查方向 |
|------|---------|
| PIPE 创建后无数据加载 | 1. `DESC PIPE EXTENDED` 检查是否暂停 2. 确认 Volume 路径下有新文件 3. 检查 COPY INTO 是否能独立运行 |
| LIST_PURGE 模式文件未被删除 | 确认 `purge = true` 已设置；检查 Connection 的 AccessKey 是否有删除权限 |
| EVENT_NOTIFICATION 模式无触发 | 1. 检查 MNS/SQS 队列是否收到消息 2. 确认 OSS 事件通知规则配置正确 3. 检查 Role ARN 授权 |
| 重复加载数据 | `load_history` 去重记录仅保留 7 天，超过 7 天的同名文件会被重新加载 |
| COPY_JOB_HINT 修改后部分参数丢失 | `SET COPY_JOB_HINT` 会覆盖所有已有 hints，需在一次 ALTER 中设置全部参数 |

## 注意事项

### PIPE 持续导入（模式 A / B）

- 每个 PIPE 需对应独立的 Volume，不可多个 PIPE 共用同一 Volume
- PIPE 中的 COPY 语句不支持 `files` / `regexp` / `subdirectory` 参数
- 数据加载无法保证严格有序（多文件并行加载）
- 推荐文件大小：gzip 压缩 ≈ 50MB，CSV/Parquet 未压缩 128MB ~ 256MB
- `load_history` 去重记录保留 7 天，超期后同名文件可能被重复加载
- 修改 COPY 逻辑需删除 PIPE 重新创建，ALTER PIPE 不支持修改 COPY 语句

### 批量导入（模式 C）

- Volume 支持阿里云 OSS、腾讯云 COS 和 AWS S3
- 不支持跨云导入（源存储与 Lakehouse 环境需在同一云平台）
- 同地域建议使用内网 Endpoint 以提升传输速度和稳定性
- 推荐使用 GENERAL PURPOSE 类型虚拟集群执行批量加载任务
- INSERT INTO 方式支持 `FILES()` 和 `WHERE` 参数，COPY INTO 不支持
- Connection 参数 `access_id`/`access_key` 和 `ACCESS_KEY`/`SECRET_KEY` 两种写法均可使用
