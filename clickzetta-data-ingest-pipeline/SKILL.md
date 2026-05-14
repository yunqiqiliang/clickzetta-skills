---
name: clickzetta-data-ingest-pipeline
description: |
  ClickZetta Lakehouse 数据导入总览与路由。根据用户的数据源类型、实时性要求、数据量等条件，
  推荐最合适的数据导入方式，并引导到对应的专项 Skill 或直接执行简单导入操作。
  当用户说"导入数据到 Lakehouse"、"数据入仓"、"数据入湖"、"怎么把数据导进来"、
  "数据采集"、"数据加载"、"ingest data"、"load data"、"数据导入方案选择"时触发。
  Keywords: data ingestion, import, routing, pipeline selection, data source
---

# Lakehouse 数据导入总览与路由

根据用户的数据源、实时性需求、数据规模等条件，推荐最合适的数据导入方式，
并路由到对应的专项 Pipeline Skill 或直接执行简单导入操作。

## 适用场景

- 用户想把数据导入 ClickZetta Lakehouse，但不确定用哪种方式
- 用户描述了数据源（Kafka、MySQL、OSS、文件等），需要推荐导入方案
- 用户需要了解各种导入方式的适用场景和差异
- 关键词：数据导入、数据入仓、数据入湖、数据采集、数据加载、pipeline 选择

## 前置依赖

- ClickZetta Lakehouse 账户，具备创建工作空间、Schema、表、PIPE、任务等权限
- **执行环境（满足其一即可，优先使用 cz-cli）**：
  - **cz-cli 路径**：已安装 cz-cli（`pip install cz-cli`），并完成 `cz-cli configure` 配置
  - **MCP 路径**：clickzetta-studio-mcp 或 clickzetta-mcp-server 工具可用（`LH_execute_query`、`create_task`、`save_integration_task` 等）

## 环境探测（执行前必读）

在开始任何操作前，先判断当前执行环境：

**第一步：检测 cz-cli 是否可用**
```bash
cz-cli --version
```
- 若命令存在 → **走 cz-cli 路径**（见本文档末尾"cz-cli 替代路径"章节，以及各专项 Skill 的 cz-cli 替代路径）
- 若命令不存在 → 继续检测 MCP

**第二步：检测 MCP 是否可用（仅在 cz-cli 不可用时）**

尝试调用 `LH_execute_query` 工具执行一条简单 SQL（如 `SELECT 1`）。
- 若工具存在于 tool list → **走 MCP 路径**（本文档默认路径）
- 若工具不存在 → 停止执行，提示用户：
  > "当前环境既无 cz-cli 也无 MCP 工具，请安装其中之一后重试。
  > cz-cli 安装：`pip install cz-cli`，然后运行 `cz-cli configure`
  > MCP 安装：参考 clickzetta-studio-mcp 或 clickzetta-mcp-server 配置文档"

## 数据导入方式决策树

### 步骤 1：确认数据源类型和需求

向用户收集以下信息：

1. **数据源类型**：Kafka / 对象存储(OSS/S3/COS) / 关系型数据库(MySQL/PostgreSQL/SQL Server) / 本地文件 / URL/Web 文件 / Java SDK / ZettaPark
2. **实时性要求**：实时（秒级延迟）/ 准实时（分钟级）/ 离线批量（小时/天级）
3. **同步范围**：单表 / 多表 / 整库
4. **是否需要持续同步**：一次性导入 / 持续增量同步
5. **是否需要 CDC（变更数据捕获）**：是 / 否

### 步骤 2：根据决策矩阵推荐方案

| 数据源 | 实时性 | 同步范围 | 推荐方式 | 对应 Skill |
|--------|--------|---------|---------|-----------|
| Kafka | 实时/准实时 | 单 topic | Kafka PIPE 持续导入（SQL） | `clickzetta-kafka-ingest-pipeline` |
| Kafka | 实时 | 多 topic | Studio 实时同步 | `clickzetta-realtime-sync-pipeline` |
| 对象存储 (OSS/S3/COS) | 准实时/批量 | 文件持续到达 | PIPE 持续导入 | `clickzetta-oss-ingest-pipeline` |
| 对象存储 | 一次性 | 批量文件 | COPY INTO 命令 | `clickzetta-file-import-pipeline`（COPY INTO 部分） |
| MySQL/PostgreSQL/SQL Server | 实时 CDC | 单表 | Studio 实时同步 | `clickzetta-realtime-sync-pipeline` |
| MySQL/PostgreSQL/SQL Server | 实时 CDC | 多表/整库 | Studio 多表实时同步 | `clickzetta-cdc-sync-pipeline` |
| MySQL/PostgreSQL/SQL Server | 离线批量 | 单表 | Studio 离线同步 | `clickzetta-batch-sync-pipeline` |
| MySQL/PostgreSQL/SQL Server | 离线批量 | 多表 | Studio 多表离线同步 | `clickzetta-batch-sync-pipeline` |
| 本地文件 / URL | 一次性 | 单文件/多文件 | URL 下载 + COPY INTO | `clickzetta-file-import-pipeline` |
| 流式增量计算 | 准实时 | 表变更驱动 | Dynamic Table + Stream | `clickzetta-incremental-compute-pipeline` |
| Java 应用 | 实时/批量 | 程序写入 | Java SDK | （见下方 SDK 导入指引） |
| Python/ZettaPark | 批量 | DataFrame | ZettaPark save_as_table | （见下方 SDK 导入指引） |

### 步骤 3：路由到专项 Skill 或直接执行

根据推荐方案，执行以下路由逻辑：

**有对应专项 Skill 的场景** → 告知用户推荐方案，引导使用对应 Skill：
- `clickzetta-kafka-ingest-pipeline`：Kafka PIPE 管道搭建
- `clickzetta-oss-ingest-pipeline`：对象存储 PIPE 管道搭建
- `clickzetta-batch-sync-pipeline`：Studio 离线同步任务
- `clickzetta-realtime-sync-pipeline`：Studio 实时同步任务
- `clickzetta-cdc-sync-pipeline`：Studio 多表实时同步（CDC）
- `clickzetta-incremental-compute-pipeline`：Dynamic Table + Stream 增量计算管道
- `clickzetta-file-import-pipeline`：URL/文件下载导入
- `clickzetta-table-stream-pipeline`：Table Stream 变更数据捕获

**无专项 Skill 的简单场景** → 直接执行：

#### SQL INSERT 导入（小数据量）
```sql
-- 使用 LH_execute_query 执行
INSERT INTO schema_name.table_name (col1, col2, col3)
VALUES ('val1', 'val2', 'val3');
```

#### COPY INTO 快速导入（从 Volume）
```sql
-- 1. 确认 Volume 中有文件
SHOW VOLUME DIRECTORY volume_name;

-- 2. 执行 COPY INTO
COPY INTO schema_name.table_name
FROM VOLUME volume_name
USING CSV
OPTIONS('header' = 'true');
```

#### Java SDK 导入指引
提供 Java SDK 的关键配置信息：
- Maven 依赖坐标
- 连接配置（endpoint、workspace、schema、vcluster）
- 批量写入 API：`BulkloadWriter`
- 实时写入 API：`RealtimeWriter`
- 建议用户参考官方文档：`comprehensive_guide_to_ingesting_javasdk_buckload_realtime`

#### ZettaPark (Python) 导入指引
- `INSERT` 方式：`session.sql("INSERT INTO ...")`
- `save_as_table` 方式：`df.write.save_as_table("table_name")`
- 建议用户参考官方文档：`comprehensive_guide_to_ingesting_zettapark_save_as_table`

## 异构数据源类型映射（ODS 层建表必读）

从关系型数据库（MySQL/PostgreSQL 等）同步数据时，ODS 层建表的字段类型选择直接影响同步成功率。

**核心原则：ODS 层使用宽泛类型，DWD 层再做精确转换。**

### MySQL → Lakehouse 类型映射

| MySQL 类型 | ❌ ODS 层不要用 | ✅ ODS 层用 | DWD 层转换 |
|---|---|---|---|
| `BIT(1)` | `BOOLEAN` | `TINYINT` | `CAST(col AS BOOLEAN)` |
| `TINYINT(1)` | `BOOLEAN` | `TINYINT` | `CAST(col AS BOOLEAN)` |
| `DATETIME` | `DATETIME` | `TIMESTAMP` | 直接用 |
| `ENUM('a','b')` | `ENUM` | `STRING` | 直接用 |
| `TEXT` / `LONGTEXT` / `MEDIUMTEXT` | `TEXT` | `STRING` | 直接用 |
| `DECIMAL(p,s)` | `FLOAT` / `DOUBLE` | `DECIMAL(p,s)` | 直接用 |
| `JSON` | `JSON` | `STRING` | `parse_json(col)['field']` |
| `SET('a','b')` | `SET` | `STRING` | 直接用 |

> ⚠️ **最常见踩坑**：`BIT(1)` 映射为 `BOOLEAN` 会导致同步任务失败。ODS 层改为 `TINYINT`，同步成功后在 DWD 层用 `CAST(col AS BOOLEAN)` 转换。

### PostgreSQL → Lakehouse 类型映射

| PostgreSQL 类型 | ❌ ODS 层不要用 | ✅ ODS 层用 |
|---|---|---|
| `BOOLEAN` | `BOOLEAN` | `TINYINT` |
| `SERIAL` / `BIGSERIAL` | `SERIAL` | `BIGINT` |
| `JSONB` / `JSON` | `JSON` | `STRING` |
| `ARRAY` | `ARRAY` | `STRING`（JSON 序列化） |
| `UUID` | `UUID` | `STRING` |
| `NUMERIC(p,s)` | `FLOAT` | `DECIMAL(p,s)` |

## 数据入仓 vs 数据入湖| 维度 | 数据入仓 | 数据入湖 |
|------|---------|---------|
| 目标 | Lakehouse 托管表 | 用户 Volume（对象存储） |
| 格式 | 自动转为内部列式格式 | 保持原始文件格式 |
| 查询性能 | 高（列式存储 + 索引） | 较低（需扫描原始文件） |
| 适用场景 | 分析查询、BI 报表、数据仓库 | 数据暂存、原始数据归档、跨系统共享 |
| 常用方式 | Studio 同步、PIPE、COPY INTO、SDK | PUT 文件、Python 脚本上传 |

## 示例

### 示例 1：用户不确定导入方式

用户说："我有一个 MySQL 数据库，想把里面的订单表实时同步到 Lakehouse"

路由逻辑：
1. 数据源：MySQL（关系型数据库）
2. 实时性：实时
3. 同步范围：单表
4. 需要 CDC：是（实时同步意味着需要捕获变更）
→ 推荐：Studio 实时同步
→ 路由到 `clickzetta-realtime-sync-pipeline` Skill

### 示例 2：多种数据源混合场景

用户说："我们有 Kafka 的用户行为日志，还有 MySQL 的业务数据，都要导入 Lakehouse"

路由逻辑：
1. Kafka 用户行为日志 → `clickzetta-kafka-ingest-pipeline`（PIPE 持续导入）
2. MySQL 业务数据 → 确认实时性需求：
   - 实时 → `clickzetta-realtime-sync-pipeline` 或 `clickzetta-cdc-sync-pipeline`
   - 离线 → `clickzetta-batch-sync-pipeline`
→ 分别引导到对应 Skill

### 示例 3：简单的一次性文件导入

用户说："我有一个 CSV 文件要导入"

路由逻辑：
1. 数据源：本地文件
2. 一次性导入
→ 路由到 `clickzetta-file-import-pipeline` Skill（支持文件上传 + COPY INTO）

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 用户无法确定数据源类型 | 询问数据当前存储位置（哪个系统/服务），帮助判断 |
| 用户需求跨多种导入方式 | 拆分为多个独立的导入任务，分别路由到对应 Skill |
| 推荐的 Skill 尚未创建 | 提供该导入方式的基本步骤和关键 SQL/API，引导用户参考官方文档 |
| 用户的云环境不支持某种连接 | 使用 `LH_show_object_list`（object_type=CONNECTIONS）检查可用连接类型，推荐替代方案 |
| 数据量极大（TB 级） | 建议分批导入，优先使用 PIPE 或 Studio 同步任务（支持断点续传） |

## 注意事项

- 本 Skill 是路由入口，不直接执行复杂的 pipeline 搭建，而是引导到专项 Skill
- 对于简单场景（SQL INSERT、单次 COPY INTO），可以直接在本 Skill 中完成
- 推荐方案时需考虑用户的云环境（阿里云/腾讯云/AWS），不同环境支持的连接类型可能不同
- 使用 `LH_show_object_list`（object_type=VCLUSTERS）确认可用的虚拟集群，同步任务需要 SYNC 类型的 VCluster
- 数据入仓是最常见的场景，数据入湖主要用于原始数据暂存或跨系统共享

---

## cz-cli 替代路径

> 仅在 cz-cli 可用且 MCP 不可用时使用本节。
> 本 Skill 是路由入口，cz-cli 路径的核心逻辑在各专项 Skill 的"cz-cli 替代路径"章节中。

### 路由说明

当 MCP 不可用时，各专项 Skill 均已提供 cz-cli 替代路径：

| 数据源 | 推荐方式 | 对应 Skill 的 cz-cli 路径 |
|--------|---------|--------------------------|
| Kafka | PIPE 持续导入 | `clickzetta-kafka-ingest-pipeline` → cz-cli 替代路径 |
| 对象存储 (OSS/S3/COS) | PIPE 持续导入 | `clickzetta-oss-ingest-pipeline` → cz-cli 替代路径 |
| MySQL/PostgreSQL/SQL Server（实时单表） | Studio 实时同步 | `clickzetta-realtime-sync-pipeline` → cz-cli 替代路径 |
| MySQL/PostgreSQL/SQL Server（实时多表/整库） | Studio 多表实时同步 | `clickzetta-cdc-sync-pipeline` → cz-cli 替代路径 |
| MySQL/PostgreSQL/SQL Server（离线批量） | Studio 离线同步 | `clickzetta-batch-sync-pipeline` → cz-cli 替代路径 |

### 简单场景直接执行（cz-cli 版）

对于无需专项 Skill 的简单场景，可直接用 cz-cli agent 完成：

```bash
# SQL INSERT 导入（小数据量）
cz-cli agent run "向表 <schema_name>.<table_name> 插入数据：<col1>=<val1>, <col2>=<val2>" \
  --format a2a --dangerously-skip-permissions

# COPY INTO 快速导入（从 Volume）
cz-cli agent run "从 Volume <volume_name> 以 CSV 格式（有 header）将数据导入表 <schema_name>.<table_name>" \
  --format a2a --dangerously-skip-permissions
```
