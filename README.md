# clickzetta-skills

[云器 Lakehouse](https://www.yunqi.tech) 的 Claude Code Skills 集合，帮助开发者在 AI 编程助手中更高效地使用 ClickZetta Lakehouse。

## Skills 列表

### 连接与基础管理

#### [clickzetta-lakehouse-connect](./clickzetta-lakehouse-connect/)

连接 ClickZetta Lakehouse 的完整指南。支持四种连接方式：

- **Python SDK** (`clickzetta-connector-python`) — 执行 SQL、自动化脚本
- **ZettaPark Session** — DataFrame API、数据工程
- **SQLAlchemy** — ORM、Web 应用、BI 工具（Superset）
- **JDBC** — Java 应用、DBeaver

自动从本地配置文件读取连接参数，覆盖国内版（`clickzetta.com`）和国际版（`singdata.com`）多区域。

**触发词**：ClickZetta、云器、Lakehouse 连接、ZettaPark、JDBC 连接、连接数据库、执行 SQL 查询

**相关文档**：
[如何连接到 Lakehouse](https://www.yunqi.tech/documents/tutorial_connect_to_lakehouse) ·
[Python SDK](https://www.yunqi.tech/documents/python-sdk-summary) ·
[ZettaPark 快速上手](https://www.yunqi.tech/documents/ZettaparkQuickStart) ·
[SQLAlchemy](https://www.yunqi.tech/documents/sqlalchemy) ·
[JDBC 驱动](https://www.yunqi.tech/documents/JDBC-Driver) ·
[云服务和地域](https://www.yunqi.tech/documents/Supported_Cloud_Platforms) ·
[相关下载](https://www.yunqi.tech/documents/Lakehouse-client-repository)

---

#### [clickzetta-manage-comments](./clickzetta-manage-comments/)

管理 ClickZetta Lakehouse 各类对象的注释（COMMENT）。支持增加、修改、删除注释，覆盖对象类型：

- Schema、普通表、外部表、字段
- 动态表（Dynamic Table）、物化视图（Materialized View）
- VCluster（计算集群）、Workspace（工作空间）

包含 ClickZetta 特有语法（与标准 SQL `COMMENT ON` 不同）及单引号转义处理。

**触发词**：加注释、改注释、删注释、补注释、加 comment、补充元数据、字段描述、表说明

**相关文档**：
[ALTER TABLE](https://www.yunqi.tech/documents/ALTERTABLE) ·
[ALTER SCHEMA](https://www.yunqi.tech/documents/ALTER-SCHEMA) ·
[ALTER DYNAMIC TABLE](https://www.yunqi.tech/documents/alter-dynamic-table) ·
[ALTER MATERIALIZED VIEW](https://www.yunqi.tech/documents/alter-materialzied-view) ·
[修改工作空间](https://www.yunqi.tech/documents/alter-worksapce)

---

### 数据导入与同步

#### [clickzetta-data-ingest-pipeline](./clickzetta-data-ingest-pipeline/)

Lakehouse 数据导入总览与路由入口。根据用户的数据源类型、实时性要求、数据量等条件，推荐最合适的数据导入方式，并引导到对应的专项 Skill。覆盖：

- **决策矩阵** — Kafka / 对象存储 / 关系型数据库 / 本地文件 / SDK 等数据源的导入方案选择
- **路由引导** — 自动匹配到 batch-sync、cdc-sync、realtime-sync、oss-ingest、file-import 等专项 Skill
- **简单场景直接执行** — SQL INSERT、单次 COPY INTO、Java SDK / ZettaPark 导入指引

**触发词**：导入数据到 Lakehouse、数据入仓、数据入湖、怎么把数据导进来、数据采集、数据加载、ingest data、load data

**相关文档**：
[数据导入概述](https://www.yunqi.tech/documents/data-ingest-overview) ·
[Java SDK 批量写入](https://www.yunqi.tech/documents/comprehensive_guide_to_ingesting_javasdk_buckload_realtime) ·
[ZettaPark save_as_table](https://www.yunqi.tech/documents/comprehensive_guide_to_ingesting_zettapark_save_as_table)

---

#### [clickzetta-batch-sync-pipeline](./clickzetta-batch-sync-pipeline/)

创建和管理离线同步（批量同步）任务，支持单表和多表两种模式：

- **单表离线同步**（task_type=10）— 源表 → 目标表周期性同步，精细控制单表
- **多表离线同步**（task_type=291）— 整库镜像、多表镜像、分库分表合并，支持 Schema Evolution 和自动建表
- **调度部署** — Cron 表达式配置、Sync VCluster 分配、任务提交与运维

支持 MySQL、PostgreSQL、SQL Server、Aurora、PolarDB 等数据源。

**触发词**：离线同步、批量同步、batch sync、数据库同步到 Lakehouse、整库迁移、多表同步、定期同步、分库分表合并

**相关文档**：
[离线同步概述](https://www.yunqi.tech/documents/offline-sync-summary) ·
[多表离线同步](https://www.yunqi.tech/documents/multi-table-offline-sync)

---

#### [clickzetta-cdc-sync-pipeline](./clickzetta-cdc-sync-pipeline/)

创建和管理多表实时同步任务（CDC），将 MySQL / PostgreSQL 数据库整库或多表实时同步到 Lakehouse：

- **三种同步模式** — 整库镜像、多表镜像、多表合并（分库分表合并）
- **全量 + 增量** — 基于 Binlog（MySQL）或 WALs（PostgreSQL），秒级端到端时效性
- **完整运维体系** — 补全量、加表、数据修复、优先同步、监控告警（5 种告警规则 + IM webhook）

包含源端数据库准备（参数配置 + 权限）、详细故障排除（Binlog 位点过期、server-id 冲突等）。

**触发词**：多表实时同步、整库同步、整库镜像、CDC 整库、多表 CDC、分库分表合并、MySQL 整库同步到 Lakehouse、Binlog 位点过期、补充全量同步

**相关文档**：
[多表实时同步概述](https://www.yunqi.tech/documents/multi-table-realtime-sync) ·
[MySQL CDC 配置](https://www.yunqi.tech/documents/mysql-cdc-config) ·
[PostgreSQL CDC 配置](https://www.yunqi.tech/documents/postgresql-cdc-config)

---

#### [clickzetta-realtime-sync-pipeline](./clickzetta-realtime-sync-pipeline/)

创建和管理单表实时同步任务，将外部数据源实时同步到 Lakehouse：

- **多数据源支持** — Kafka（支持 JSON 消息 JSONPath 解析）、MySQL、PostgreSQL、SQL Server 等
- **持续运行** — 流式任务，提交即运行，无需配置调度策略
- **Sync VCluster** — 自动分配同步专用计算集群

**触发词**：Studio 实时同步、realtime sync、单表 CDC 同步、Kafka 实时同步到 Lakehouse、MySQL 单表实时同步

**相关文档**：
[实时同步概述](https://www.yunqi.tech/documents/realtime-sync-summary) ·
[Kafka 实时同步](https://www.yunqi.tech/documents/kafka-realtime-sync)

---

#### [clickzetta-oss-ingest-pipeline](./clickzetta-oss-ingest-pipeline/)

搭建对象存储（OSS/S3/COS）数据导入管道，覆盖持续导入和批量导入两大场景：

- **PIPE 持续导入** — LIST_PURGE 扫描模式（通用）和 EVENT_NOTIFICATION 消息通知模式（低延迟，仅阿里云 OSS + AWS S3）
- **批量导入** — Volume + INSERT INTO（支持过滤转换）和 Volume + COPY INTO（简洁语法）
- **完整管道搭建** — Storage Connection → External Volume → PIPE/COPY INTO，含监控与运维

**触发词**：对象存储导入、OSS 数据管道、S3 数据导入、PIPE 持续导入、文件自动加载、COS 导入、批量导入 OSS、Volume 导入

**相关文档**：
[使用 Pipe 持续导入对象存储数据](https://www.yunqi.tech/documents/pipe-storage-object) ·
[External Volume](https://www.yunqi.tech/documents/external-volume) ·
[Storage Connection](https://www.yunqi.tech/documents/storage-connection) ·
[COPY INTO](https://www.yunqi.tech/documents/copy-into)

---

#### [clickzetta-file-import-pipeline](./clickzetta-file-import-pipeline/)

从 URL、本地文件或 Volume 路径将数据导入到 ClickZetta 表中，覆盖完整流程：

- **文件获取** — HTTP/HTTPS URL 下载、本地文件上传到 Volume
- **格式推断** — 自动识别 CSV/JSON/Parquet/ORC/BSON 格式，支持 preview 预览
- **三种写入模式** — create（新建表）、append（追加）、overwrite（覆盖）

包含 USER VOLUME 机制、COPY INTO / COPY OVERWRITE INTO 语法、CSV OPTIONS 配置等。

**触发词**：导入数据、从 URL 加载、上传 CSV 到表、文件导入、COPY INTO

**相关文档**：
[COPY INTO](https://www.yunqi.tech/documents/copy-into) ·
[User Volume](https://www.yunqi.tech/documents/user-volume) ·
[文件格式参考](https://www.yunqi.tech/documents/file-format)

---

#### [clickzetta-sql-pipeline-manager](./clickzetta-sql-pipeline-manager/)

通过 SQL 命令管理 ClickZetta Lakehouse 数据管道对象的完整生命周期。纯 SQL 操作，不涉及 Studio 图形化界面。覆盖四类对象：

- **Dynamic Table（动态表）** — CREATE / ALTER（暂停/恢复）/ DROP / SHOW / 刷新历史，支持增量计算和多层级联
- **Materialized View（物化视图）** — CREATE / REFRESH / ALTER / DROP，适合固定聚合加速 BI 查询
- **Table Stream（表流）** — CREATE / DROP / SHOW，捕获 INSERT/UPDATE/DELETE 变更，构建 CDC 管道
- **Pipe** — 从 Kafka 或对象存储（OSS/S3/COS）持续自动导入数据

内置决策树帮助选择合适的管道对象，包含 Kafka→动态表、CDC UPSERT、多层 ETL、Medallion Architecture（Bronze/Silver/Gold）等典型场景示例。

**触发词**：创建动态表、物化视图、Pipe、表流、增量计算、实时 ETL、数据管道、CDC 变更捕获、接入 Kafka、从对象存储持续导入、修改刷新频率、刷新历史、Medallion 架构、Bronze Silver Gold、湖仓分层

**相关文档**：
[增量计算概述](https://www.yunqi.tech/documents/streaming_data_pipeline_overview) ·
[CREATE DYNAMIC TABLE](https://www.yunqi.tech/documents/create-dynamic-table) ·
[CREATE MATERIALIZED VIEW](https://www.yunqi.tech/documents/CREATEMATERIALIZEDVIEW) ·
[CREATE TABLE STREAM](https://www.yunqi.tech/documents/create-table-stream) ·
[PIPE 导入语法](https://www.yunqi.tech/documents/pipe-syntax) ·
[Dynamic Table 实时 ETL 教程](https://www.yunqi.tech/documents/tutorials-streaming-data-pipeline-with_dynamic-table)

---

#### [clickzetta-table-stream-pipeline](./clickzetta-table-stream-pipeline/)

搭建和管理 Table Stream 变更数据捕获管道，覆盖端到端工作流：

- **两种模式** — STANDARD（捕获 INSERT/UPDATE/DELETE）和 APPEND_ONLY（仅捕获 INSERT）
- **完整消费流程** — 变更跟踪开启 → Stream 创建 → 数据预览 → MERGE 幂等消费 → offset 管理
- **元数据字段** — `__change_type`、`__commit_version`、`__commit_timestamp`

包含 offset 管理机制、幂等消费最佳实践、性能优化要点。

**触发词**：创建 Table Stream、Table Stream CDC、Table Stream 管道、Table Stream 增量消费、Stream 消费

**相关文档**：
[CREATE TABLE STREAM](https://www.yunqi.tech/documents/create-table-stream) ·
[增量计算概述](https://www.yunqi.tech/documents/streaming_data_pipeline_overview)

---

### 数据恢复

#### [clickzetta-data-recovery](./clickzetta-data-recovery/)

ClickZetta Lakehouse 数据恢复与历史查询。覆盖完整数据恢复工作流：

- **Time Travel** — 查询任意历史时间点的数据（`TIMESTAMP AS OF`）
- **UNDROP TABLE** — 恢复被误删的表、动态表、物化视图
- **RESTORE TABLE** — 将表回滚到历史版本
- **DESC HISTORY / SHOW TABLES HISTORY** — 查看表的变更记录与删除记录
- **数据保留周期** — 配置 `data_retention_days`（默认 1 天，最长 90 天）

**触发词**：恢复误删的表、回滚数据、时间旅行查询、UNDROP、RESTORE TABLE、数据保留周期

**相关文档**：
[备份和恢复](https://www.yunqi.tech/documents/data-recover) ·
[TIME TRAVEL](https://www.yunqi.tech/documents/TIMETRAVEL) ·
[RESTORE TABLE](https://www.yunqi.tech/documents/restore) ·
[UNDROP TABLE](https://www.yunqi.tech/documents/UNDROP-TABLE) ·
[SHOW TABLES HISTORY](https://www.yunqi.tech/documents/show-tables-history)

---

## 安装

将对应 skill 目录复制到你的项目或全局 skills 目录，Claude Code 会自动识别并加载。

```bash
git clone https://github.com/yunqiqiliang/clickzetta-skills.git
```

## 相关资源

- [云器 Lakehouse 文档](https://www.yunqi.tech/documents/Overview)
- [LLM 全量文档索引](https://yunqi.tech/llms-full.txt) — 适合 AI 助手直接消费的完整文档，涵盖所有 SQL 命令、SDK、连接方式等
- [Lakehouse MCP Server](https://www.yunqi.tech/documents/LakehouseMCPServer) — 通过 MCP 协议将 Lakehouse 能力暴露给 Claude 等 AI 助手
- [AI 生态集成](https://www.yunqi.tech/documents/AI_eco) — Dify、LangChain、N8N 等集成方案
