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
  Keywords: OSS, S3, COS, object storage, PIPE, COPY INTO, file ingestion
---

# 对象存储数据管道搭建工作流

## 向导：收集必要信息

开始搭建对象存储管道前，先收集以下信息（一次性问完）：

> 为了搭建对象存储导入管道，需要确认：
>
> **1. 云平台和存储信息**：
>    - 云平台：阿里云 OSS / AWS S3 / 腾讯云 COS？
>    - Bucket 名称和路径（如 `oss://my-bucket/data/`）
>    - 认证方式：AccessKey（access_id + access_key）还是 Role ARN？
>
> **2. 导入模式**（选一个）：
>    - A. 持续导入 — 新文件自动触发导入（PIPE 模式）
>    - B. 批量一次性导入 — 手动或定时执行 COPY INTO
>
> **3. 如果选持续导入，触发方式**：
>    - LIST_PURGE（定期扫描，通用，导入后删除源文件）
>    - EVENT_NOTIFICATION（消息通知，低延迟，仅支持 OSS/S3，需 Role ARN）
>
> **4. 文件格式**：CSV / JSON / Parquet / ORC？
>
> **5. 目标表**：写入 Lakehouse 的哪个 schema 和表名？

**如果用户已经提供了足够信息，直接进入工作流，不再重复询问。**

---

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
- **执行环境**：已安装 cz-cli（`pip install cz-cli`），并完成 `cz-cli configure` 配置

## 执行环境

所有 SQL 通过 `cz-cli sql` 执行：

```bash
cz-cli --version   # 确认 cz-cli 可用
cz-cli sql "SELECT 1" --sync   # 验证连接
```

若命令不存在，请先安装：`pip install cz-cli`，然后运行 `cz-cli configure`

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
- **Volume PIPE 不支持 Kafka 专用参数**：`BATCH_INTERVAL_IN_SECONDS`、`BATCH_SIZE_PER_KAFKA_PARTITION`、`MAX_SKIP_BATCH_COUNT_ON_ERROR` 仅适用于 Kafka PIPE
- **`COPY_JOB_HINT` 必须是合法 JSON 格式**，键值都要用双引号：`'{"IGNORE_TMP_FILE": "true"}'`，不能用 `KEY=VALUE` 格式

### 文件大小建议

- gzip 压缩文件：≈ 50MB
- CSV / PARQUET 未压缩文件：128MB ~ 256MB

## 工作流

### 模式 A：LIST_PURGE 扫描模式（通用）

#### 步骤 1：创建存储连接（Storage Connection）

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
-- 密钥方式（LIST_PURGE 模式支持）
CREATE STORAGE CONNECTION IF NOT EXISTS my_oss_connection
  TYPE OSS
  access_id = '<your_access_key_id>'
  access_key = '<your_access_key_secret>'
  ENDPOINT = 'oss-cn-hangzhou.aliyuncs.com';
```

> **参数说明**：
> - `access_id`：对应阿里云控制台的 **AccessKey ID**
> - `access_key`：对应阿里云控制台的 **AccessKey Secret**
> - 也可使用大写形式 `ACCESS_KEY_ID` / `ACCESS_KEY_SECRET`
> - ⚠️ `ACCESS_KEY` / `SECRET_KEY` 会报错（缺少 `_ID` / `_SECRET` 后缀）
>
> **提示**：如果使用 Role ARN 方式（EVENT_NOTIFICATION 模式必须），参见下方"模式 B"中的 Connection 创建语法。

#### 步骤 2：创建外部 Volume

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
CREATE EXTERNAL VOLUME IF NOT EXISTS pipe_volume
  LOCATION 'oss://my-bucket/data-path/'
  USING CONNECTION my_oss_connection
  DIRECTORY = (enable = true, auto_refresh = true)
  RECURSIVE = true
  COMMENT 'Volume for OSS PIPE ingestion';
```

> **关键参数**：
> - `RECURSIVE = true`：递归扫描子目录
> - `DIRECTORY = (enable = true, auto_refresh = true)`：自动刷新目录元数据
> - ⚠️ COMMENT 不带等号：`COMMENT 'text'`（不是 `COMMENT = 'text'`）

#### 步骤 3：验证 COPY INTO 可独立运行

在创建 PIPE 之前，先用 COPY INTO 验证数据能正常加载：

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
COPY INTO my_schema.target_table
FROM VOLUME pipe_volume
USING CSV OPTIONS ('header' = 'true', 'delimiter' = ',') PURGE=true;
```

> **重要**：
> - PIPE 中的 COPY 语句不支持 `files`、`regexp`、`subdirectory` 参数。确保此处验证时也不使用这些参数。
> - OPTIONS 放在 PURGE=true **之前**：`USING CSV OPTIONS (...) PURGE=true`

#### 步骤 4：创建 PIPE（LIST_PURGE 模式）

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
CREATE PIPE IF NOT EXISTS my_oss_pipe
  INGEST_MODE = 'LIST_PURGE'
  VIRTUAL_CLUSTER = 'my_vc'
  COMMENT 'OSS data pipeline - scan mode'
AS
COPY INTO my_schema.target_table
FROM VOLUME pipe_volume
USING CSV OPTIONS ('header' = 'true') PURGE=true;
```

> **⚠️ 语法关键点**：
> - `PURGE=true` 放在最后：`USING <format> [OPTIONS (...)] PURGE=true`
> - OPTIONS 在 PURGE=true **之前**（如果需要的话）
> - 也可以不带 OPTIONS：`USING CSV PURGE=true`（推荐简洁写法）
> - COMMENT 不带等号：`COMMENT 'text'`
> - 大写 `PURGE`，小写 `true`，中间用 `=` 连接，无空格
> - **LIST_PURGE 模式必须设置** `PURGE=true`，加载成功后删除源文件（避免重复导入）
> - 即使不想删除源文件，LIST_PURGE 模式也需要此参数，否则会重复导入同一文件
> - `VIRTUAL_CLUSTER`：指定执行 PIPE 任务的虚拟集群
>
> **错误写法**（会报语法错误）：
> ```sql
> -- ❌ 不要把 purge 放在 OPTIONS 里
> OPTIONS ('header' = 'true', 'purge' = 'true')
> -- ❌ OPTIONS 不能在 PURGE 之后
> USING CSV PURGE=true OPTIONS ('header' = 'true')
> -- ❌ 不要用小写或加引号
> 'purge'='true'
> ```

#### 步骤 5：验证 PIPE 状态

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
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
-- 通过 cz-cli sql "<SQL>" --sync 执行
CREATE STORAGE CONNECTION IF NOT EXISTS my_oss_role_connection
  TYPE OSS
  ENDPOINT = 'oss-cn-hangzhou.aliyuncs.com'
  ROLE_ARN = 'acs:ram::1234567890:role/clickzetta-oss-role'
  REGION = 'cn-hangzhou';
```

#### 步骤 2：创建外部 Volume

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
CREATE EXTERNAL VOLUME IF NOT EXISTS pipe_event_volume
  LOCATION 'oss://my-bucket/data-path/'
  USING CONNECTION my_oss_role_connection
  DIRECTORY = (enable = true, auto_refresh = true)
  RECURSIVE = true;
```

#### 步骤 3：创建 PIPE（EVENT_NOTIFICATION 模式）

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
CREATE PIPE IF NOT EXISTS my_oss_event_pipe
  INGEST_MODE = 'EVENT_NOTIFICATION'
  VIRTUAL_CLUSTER = 'my_vc'
  ALICLOUD_MNS_QUEUE = 'my-mns-queue-name'
  COMMENT 'OSS data pipeline - event notification mode'
AS
COPY INTO my_schema.target_table
FROM VOLUME pipe_event_volume
USING CSV;
```

> **参数说明**：
> - `INGEST_MODE = 'EVENT_NOTIFICATION'`：通过消息通知触发加载
> - `ALICLOUD_MNS_QUEUE`：阿里云 MNS 队列名称（AWS 使用 `AWS_SQS_QUEUE`）
> - 此模式下不需要 `PURGE=true`，因为是事件驱动而非扫描
> - COMMENT 不带等号：`COMMENT 'text'`

---

### 模式 C：批量导入（一次性 Volume + COPY/INSERT）

> 适用于一次性或定期批量加载对象存储中的文件，无需创建 PIPE。支持阿里云 OSS、腾讯云 COS 和 AWS S3。
> 推荐使用 GENERAL PURPOSE 类型的虚拟集群执行批量加载。

#### 使用限制

- 不支持跨云导入（源存储与 Lakehouse 环境需在同一云平台）
- 同地域建议使用内网 Endpoint（如 `oss-cn-shanghai-internal.aliyuncs.com`）以提升速度和稳定性

#### 步骤 1：创建目标表

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
CREATE TABLE IF NOT EXISTS my_schema.target_table (
  id STRING,
  name STRING,
  amount DECIMAL(10,2),
  created_date STRING
);
```

#### 步骤 2：创建存储连接（access_id/access_key 语法）

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
CREATE STORAGE CONNECTION IF NOT EXISTS my_batch_conn
  TYPE OSS
  ENDPOINT = 'oss-cn-shanghai-internal.aliyuncs.com'
  access_id = '<your_access_key_id>'
  access_key = '<your_access_key_secret>';
```

> **Connection 参数命名**：
> - 小写形式：`access_id` / `access_key`（推荐）
> - 大写形式：`ACCESS_KEY_ID` / `ACCESS_KEY_SECRET`（也可以）
> - ⚠️ `ACCESS_KEY` / `SECRET_KEY` 会报错（缺少后缀）

#### 步骤 3：创建外部 Volume（启用目录自动刷新）

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
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
> **Volume 创建语法统一说明**：
> - ✅ 推荐语法：`LOCATION '...' USING CONNECTION conn_name`（官方文档标准写法）
> - ⚠️ 旧语法：`STORAGE_CONNECTION = conn_name LOCATION = '...'`（部分旧文档中出现，仍可使用）
> - 两种语法功能等价，建议统一使用 `LOCATION ... USING CONNECTION` 形式

#### 步骤 4a：INSERT INTO 从 Volume 导入（支持过滤转换）

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
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
-- 通过 cz-cli sql "<SQL>" --sync 执行
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
> - ⚠️ **load_history 差异**：只有 `COPY INTO` 会记录到 `load_history`，`INSERT INTO ... FROM VOLUME` 不会记录。如需去重保护，请使用 `COPY INTO`

#### 步骤 5：验证导入结果

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
SELECT COUNT(*) AS total_rows FROM my_schema.target_table;
SELECT * FROM my_schema.target_table LIMIT 10;
```

---

## 监控与运维

### 查看 PIPE 详细状态

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
DESC PIPE EXTENDED my_oss_pipe;
```

关键字段：
- `pipe_execution_paused`：是否暂停
- `ingest_mode`：导入模式
- `virtual_cluster`：执行集群
- `definition`：COPY 语句定义

### 查看加载历史

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
SELECT * FROM load_history('my_schema.target_table')
ORDER BY last_load_time DESC
LIMIT 20;
```

> `load_history` 去重记录保留 7 天。

### 通过 query_tag 过滤 PIPE 作业

PIPE 执行的作业会自动打上 `query_tag`，格式为：`pipe.<workspace_name>.<schema_name>.<pipe_name>`

```sql
-- 通过 cz-cli sql "<SQL>" --sync 执行
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
-- 必须是合法 JSON 格式，键值都要用双引号
ALTER PIPE my_oss_pipe SET COPY_JOB_HINT = '{"max_file_count":"100","force":"false"}';
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
| LIST_PURGE 模式文件未被删除 | 确认 `PURGE=true` 已设置（紧跟 `USING <format>` 之后）；检查 Connection 的 AccessKey 是否有删除权限 |
| `PURGE=true` 语法错误 | OPTIONS 必须在 PURGE 之前：`USING CSV OPTIONS (...) PURGE=true`。不要写成 `USING CSV PURGE=true OPTIONS(...)` |
| EVENT_NOTIFICATION 模式无触发 | 1. 检查 MNS/SQS 队列是否收到消息 2. 确认 OSS 事件通知规则配置正确 3. 检查 Role ARN 授权 |
| 重复加载数据 | `load_history` 去重记录仅保留 7 天，超过 7 天的同名文件会被重新加载 |
| COPY_JOB_HINT 修改后部分参数丢失 | `SET COPY_JOB_HINT` 会覆盖所有已有 hints，需在一次 ALTER 中设置全部参数 |
| INSERT INTO FROM VOLUME 后 load_history 无记录 | 正常行为：只有 `COPY INTO` 会记录到 load_history，`INSERT INTO` 不会 |
| COPY INTO 报格式错误 | Volume 中有多种格式文件，使用 `FILES('xxx.json')` 指定文件 |

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
- Connection 参数使用 `access_id`/`access_key`（小写）或 `ACCESS_KEY_ID`/`ACCESS_KEY_SECRET`（大写），不要用 `ACCESS_KEY`/`SECRET_KEY`
- ⚠️ `INSERT INTO ... FROM VOLUME` 不会记录到 `load_history`，只有 `COPY INTO` 会记录
- ⚠️ Volume 中有多种格式文件时，不指定 `FILES()` 的 COPY INTO 会尝试读取所有文件，可能因格式不匹配而失败。建议使用 `FILES('xxx.json')` 指定文件或 `SUBDIRECTORY` 指定子目录
- 上传文件到 OSS 后，`SHOW VOLUME DIRECTORY` 可能需要先执行 `ALTER VOLUME name REFRESH` 刷新目录元数据

---

## cz-cli 执行路径

### 模式 A：LIST_PURGE 扫描模式（cz-cli 版）

```bash
# 步骤 1：创建存储连接
cz-cli agent run "创建 OSS Storage Connection，名称 <my_oss_connection>，endpoint <oss-cn-hangzhou.aliyuncs.com>，access_key <key>，secret_key <secret>" \
  --format a2a --dangerously-skip-permissions

# 步骤 2：创建外部 Volume
cz-cli agent run "创建外部 Volume，名称 <pipe_volume>，使用 Connection <my_oss_connection>，路径 oss://<bucket>/<data-path>/" \
  --format a2a --dangerously-skip-permissions

# 步骤 3：验证 COPY INTO 可独立运行
cz-cli agent run "用 COPY INTO 从 Volume <pipe_volume> 加载数据到表 <schema>.<table>，文件格式 CSV，有 header，验证数据能正常加载" \
  --format a2a --dangerously-skip-permissions

# 步骤 4：创建 LIST_PURGE 模式 PIPE
cz-cli agent run "创建 PIPE <my_oss_pipe>，INGEST_MODE 为 LIST_PURGE，使用 VCluster <my_vc>，从 Volume <pipe_volume> 以 CSV 格式（有 header，purge=true）持续导入数据到表 <schema>.<table>" \
  --format a2a --dangerously-skip-permissions

# 步骤 5：验证 PIPE 状态
cz-cli agent run "查看 PIPE <my_oss_pipe> 的详细状态，确认 pipe_execution_paused 为 false" \
  --format a2a --dangerously-skip-permissions
```

---

### 模式 B：EVENT_NOTIFICATION 消息通知模式（cz-cli 版）

```bash
# 步骤 1：创建 Role ARN 方式的存储连接
cz-cli agent run "创建 OSS Storage Connection，名称 <my_oss_role_connection>，endpoint <oss-cn-hangzhou.aliyuncs.com>，使用 Role ARN <acs:ram::xxx:role/clickzetta-oss-role>，region cn-hangzhou" \
  --format a2a --dangerously-skip-permissions

# 步骤 2：创建外部 Volume
cz-cli agent run "创建外部 Volume，名称 <pipe_event_volume>，使用 Connection <my_oss_role_connection>，路径 oss://<bucket>/<data-path>/" \
  --format a2a --dangerously-skip-permissions

# 步骤 3：创建 EVENT_NOTIFICATION 模式 PIPE
cz-cli agent run "创建 PIPE <my_oss_event_pipe>，INGEST_MODE 为 EVENT_NOTIFICATION，使用 VCluster <my_vc>，ALICLOUD_MNS_QUEUE 为 <my-mns-queue-name>，从 Volume <pipe_event_volume> 以 CSV 格式持续导入数据到表 <schema>.<table>" \
  --format a2a --dangerously-skip-permissions
```

---

### 模式 C：批量导入（cz-cli 版）

```bash
# 步骤 1：创建目标表
cz-cli agent run "在 schema <my_schema> 下创建表 <target_table>，字段：id STRING, name STRING, amount DECIMAL(10,2), created_date STRING" \
  --format a2a --dangerously-skip-permissions

# 步骤 2-3：创建存储连接和 Volume
cz-cli agent run "创建 OSS Storage Connection <my_batch_conn>，endpoint <oss-cn-shanghai-internal.aliyuncs.com>，access_id <id>，access_key <key>；然后创建外部 Volume <my_batch_volume>，路径 oss://<bucket>/<data-path>/，启用目录自动刷新" \
  --format a2a --dangerously-skip-permissions

# 步骤 4：从 Volume 导入数据
cz-cli agent run "从 Volume <my_batch_volume> 以 CSV 格式（有 header）将数据导入表 <my_schema>.<target_table>" \
  --format a2a --dangerously-skip-permissions

# 步骤 5：验证导入结果
cz-cli agent run "查询表 <my_schema>.<target_table> 的总行数和前 10 条数据，验证导入结果" \
  --format a2a --dangerously-skip-permissions
```

---

### 监控与运维（cz-cli 版）

```bash
# 查看 PIPE 状态
cz-cli agent run "查看 PIPE <my_oss_pipe> 的详细状态和加载历史" \
  --format a2a --dangerously-skip-permissions

# 暂停/恢复 PIPE
cz-cli agent run "暂停 PIPE <my_oss_pipe>" \
  --format a2a --dangerously-skip-permissions

cz-cli agent run "恢复 PIPE <my_oss_pipe>" \
  --format a2a --dangerously-skip-permissions
```
