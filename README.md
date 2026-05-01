# clickzetta-skills

[云器 Lakehouse](https://www.yunqi.tech) 的 Claude Code Skills 集合，帮助开发者在 AI 编程助手中更高效地使用 ClickZetta Lakehouse。

## Skills 总览

| 类别 | Skill | 说明 |
|---|---|---|
| 连接与基础 | [clickzetta-lakehouse-connect](./clickzetta-lakehouse-connect/) | Python SDK / ZettaPark / SQLAlchemy / JDBC 连接 |
| 连接与基础 | [clickzetta-concepts](./clickzetta-concepts/) | Lakehouse 核心概念：对象层级、Workspace/Schema/VCluster、权限体系 |
| 连接与基础 | [clickzetta-studio-overview](./clickzetta-studio-overview/) | Studio 一站式 Web IDE：任务开发/调度/数据集成/数据目录/数据质量/运维监控 |
| 连接与基础 | [clickzetta-manage-comments](./clickzetta-manage-comments/) | 管理表、字段、Schema 等对象的注释 |
| 数据导入同步 | [clickzetta-data-ingest-pipeline](./clickzetta-data-ingest-pipeline/) | 数据导入方案路由与决策 |
| 数据导入同步 | [clickzetta-batch-sync-pipeline](./clickzetta-batch-sync-pipeline/) | 离线批量同步（MySQL/PG 等 → Lakehouse） |
| 数据导入同步 | [clickzetta-cdc-sync-pipeline](./clickzetta-cdc-sync-pipeline/) | 多表实时 CDC 同步（整库镜像/分库分表） |
| 数据导入同步 | [clickzetta-realtime-sync-pipeline](./clickzetta-realtime-sync-pipeline/) | 单表实时同步（Kafka/MySQL/PG） |
| 数据导入同步 | [clickzetta-oss-ingest-pipeline](./clickzetta-oss-ingest-pipeline/) | 对象存储（OSS/S3/COS）数据导入管道 |
| 数据导入同步 | [clickzetta-kafka-ingest-pipeline](./clickzetta-kafka-ingest-pipeline/) | Kafka 数据接入管道（READ_KAFKA Pipe / 外部表） |
| 数据导入同步 | [clickzetta-file-import-pipeline](./clickzetta-file-import-pipeline/) | 本地文件 / URL 导入 |
| 数据导入同步 | [clickzetta-sql-pipeline-manager](./clickzetta-sql-pipeline-manager/) | SQL 管道对象（动态表/物化视图/Pipe/Stream） |
| 数据导入同步 | [clickzetta-table-stream-pipeline](./clickzetta-table-stream-pipeline/) | Table Stream CDC 变更捕获管道 |
| 计算集群 | [clickzetta-vcluster-manager](./clickzetta-vcluster-manager/) | VCluster 创建/启停/扩缩容/缓存管理 |
| 数据湖 | [clickzetta-volume-manager](./clickzetta-volume-manager/) | Volume 挂载、文件查询、导入导出 |
| 数据湖 | [clickzetta-external-catalog](./clickzetta-external-catalog/) | Hive/Iceberg/Databricks 联邦查询 |
| Python | [clickzetta-zettapark](./clickzetta-zettapark/) | ZettaPark DataFrame API 数据工程 |
| BI 工具 | [clickzetta-bi-connect](./clickzetta-bi-connect/) | Superset/Tableau/Metabase/DBeaver 连接 |
| 查询优化 | [clickzetta-query-optimizer](./clickzetta-query-optimizer/) | EXPLAIN/Result Cache/OPTIMIZE/Hints |
| 索引管理 | [clickzetta-index-manager](./clickzetta-index-manager/) | Bloom Filter/倒排/向量索引管理 |
| 访问控制 | [clickzetta-access-control](./clickzetta-access-control/) | 用户/角色/GRANT/REVOKE/动态脱敏 |
| 监控 | [clickzetta-monitoring](./clickzetta-monitoring/) | SHOW JOBS / information_schema 作业分析 |
| AI | [clickzetta-ai-vector-search](./clickzetta-ai-vector-search/) | VECTOR 类型、HNSW 索引、语义检索、RAG |
| AI | [clickzetta-external-function](./clickzetta-external-function/) | External Function / AI_COMPLETE / AI_EMBEDDING |
| 数据共享 | [clickzetta-data-sharing](./clickzetta-data-sharing/) | 跨账户/跨实例无复制数据分享 |
| 元数据查询 | [clickzetta-information-schema](./clickzetta-information-schema/) | INFORMATION_SCHEMA 元数据视图查询（表结构/作业历史/权限/Volume/费用分析） |
| 元数据查询 | [clickzetta-metadata-query](./clickzetta-metadata-query/) | SHOW/DESC 命令族 + load_history()：实时元数据查询（表/分区/历史/作业/权限） |
| 数据生命周期 | [clickzetta-data-lifecycle](./clickzetta-data-lifecycle/) | 数据 TTL 自动回收（data_lifecycle）和 Time Travel 保留周期管理 |
| SQL 语法参考 | [clickzetta-sql-syntax-guide](./clickzetta-sql-syntax-guide/) | SQL 语法完整参考 + Snowflake/Spark 差异对照 |
| 语义视图 | [clickzetta-semantic-view](./clickzetta-semantic-view/) | 语义视图（Semantic View）：逻辑表/维度/指标/过滤器定义与查询（邀测） |

---

## Skills 列表

### 连接与基础管理

#### [clickzetta-concepts](./clickzetta-concepts/)

介绍 ClickZetta Lakehouse 的核心概念和对象模型，帮助新用户快速建立正确的心智模型。覆盖：

- **对象层级** — 账户 → 实例 → 工作空间 → Schema → 数据对象的完整层级关系
- **Workspace vs Schema** — Workspace 等同于 Snowflake Database / Databricks Catalog；Schema 等同于传统 Database/Schema
- **与其他系统对比** — ClickZetta / Snowflake / Databricks / 传统数据库概念映射表
- **VCluster 三种类型** — 通用型（ETL）/ 分析型（BI 高并发）/ 同步型（数据集成），CRU 计费说明
- **数据对象类型** — 内部表/外部表/视图/动态表/物化视图/Volume/Stream/Pipe 的区别
- **权限体系** — RBAC/ACL 并存，实例角色 vs 工作空间角色，预置角色说明
- **存算分离架构** — 计算层/存储层/服务层/客户端层的分层架构

**触发词**：工作空间是什么、Schema 和 Database 什么关系、Catalog 是什么、实例和工作空间的区别、VCluster 是什么、CRU 是什么、内部表和外部表区别、Lakehouse 架构、对象层级、权限体系、和 Snowflake 概念对比、和 Databricks 概念对比、存算分离

**相关文档**：
[SCHEMA](https://www.yunqi.tech/documents/SCHEMA) ·
[计算集群](https://www.yunqi.tech/documents/virtual-cluster) ·
[访问控制概览](https://www.yunqi.tech/documents/access-control-general) ·
[角色](https://www.yunqi.tech/documents/roles) ·
[用户身份](https://www.yunqi.tech/documents/user-identification)

---

#### [clickzetta-studio-overview](./clickzetta-studio-overview/)

介绍 ClickZetta Lakehouse Studio 的核心功能，这是 ClickZetta 区别于 Snowflake/Databricks 的核心差异化能力——内置一站式 Web IDE，无需第三方工具即可完成全链路数据工程。覆盖：

- **六大模块** — 数据开发 IDE、任务调度编排、数据集成（30+ 数据源）、数据目录、数据质量、运维监控
- **任务类型** — SQL/Python/Shell/JDBC/动态表/离线同步/实时同步/多表 CDC
- **任务组 DAG** — 可视化拖拽编排，批量管理依赖关系，支持跨工作空间依赖
- **任务参数** — `${var}` 动态变量，`$[yyyy-MM-dd, -1d]` 时间表达式，任务组参数共享
- **数据目录** — 全局资产搜索，表详情（DDL/字段/预览/血缘/作业历史）
- **数据质量** — 6 维度规则（完整性/唯一性/一致性/准确性/有效性/及时性）
- **运维告警** — 飞书/企业微信 webhook，内置 + 自定义告警规则

**触发词**：Studio 是什么、Studio 怎么用、任务调度、DAG 编排、任务组、任务参数、数据目录、数据质量、运维监控、告警配置、补数据、任务依赖、Studio 和其他 Lakehouse 的区别

**相关文档**：
[Studio 快速导览](https://www.yunqi.tech/documents/LakehouseStudioTour) ·
[任务开发概念](https://www.yunqi.tech/documents/task_development) ·
[任务组](https://www.yunqi.tech/documents/task_group) ·
[任务参数](https://www.yunqi.tech/documents/task_param) ·
[数据目录](https://www.yunqi.tech/documents/data_catalog) ·
[数据质量](https://www.yunqi.tech/documents/DataQuality)

---

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

#### [clickzetta-kafka-ingest-pipeline](./clickzetta-kafka-ingest-pipeline/)

搭建 Kafka 数据接入管道，覆盖从连接验证到持续导入的端到端工作流：

- **READ_KAFKA Pipe**（推荐）— 使用 `READ_KAFKA` 函数直接消费 Kafka JSON/CSV/Avro 数据，支持复杂 SQL 转换和多层嵌套 JSON 解析
- **Kafka 外部表 + Table Stream Pipe** — 先落原始消息到外部表，再通过 Table Stream 增量消费，适合多下游消费场景
- **生产调优** — `BATCH_SIZE_PER_KAFKA_PARTITION`、`COPY_JOB_HINT` task 切分、VCluster 规格调整
- **延迟监控** — `pipe_latency`（offsetLag/timeLag）、`query_tag` 作业追踪、端到端延迟监控

包含 SASL 认证配置、消费位点管理（`RESET_KAFKA_GROUP_OFFSETS`）、Pipe 重建最佳实践。

**触发词**：Kafka 接入、Kafka 导入、Kafka Pipe、read_kafka、Kafka 数据管道、Kafka 外部表、Kafka 消费、消息队列导入、Kafka 到 Lakehouse、Kafka 持续导入、Kafka 延迟监控

**相关文档**：
[借助 read_kafka 函数持续导入](https://www.yunqi.tech/documents/pipe-kafka) ·
[借助 Kafka 外表 Table Stream 持续导入](https://www.yunqi.tech/documents/pipe-kafka-table-stream) ·
[最佳实践：使用 Pipe 高效接入 Kafka 数据](https://www.yunqi.tech/documents/pipe-kafka-bestpractice-1) ·
[Kafka 外部表](https://www.yunqi.tech/documents/kafka-external-table) ·
[read_kafka 函数](https://www.yunqi.tech/documents/read_kafka)

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

### 计算集群管理

#### [clickzetta-vcluster-manager](./clickzetta-vcluster-manager/)

管理 ClickZetta Lakehouse 计算集群（VCluster）的完整生命周期。覆盖三种集群类型：

- **通用型（GP）** — 离线 ETL、数据摄取，纵向弹性扩缩容（固定规格或 MIN/MAX 弹性规格）
- **分析型（AP）** — 高并发在线查询、BI 报表，横向弹性扩缩容（副本数 1-10，最大并发 1-32）
- **同步型（Integration）** — 数据集成同步任务，支持 0.25/0.5 CRU 小规格

包含集群创建、启动/停止、规格调整、预加载缓存（PRELOAD_TABLES）、查看状态等完整操作。

**触发词**：创建集群、计算集群、VCluster、启动集群、停止集群、调整集群规格、集群扩容、集群缩容、自动停止、自动启动、预加载缓存、PRELOAD、GP集群、AP集群、分析型集群、通用型集群

**相关文档**：
[计算集群概述](https://www.yunqi.tech/documents/virtual-cluster) ·
[CREATE VCLUSTER](https://www.yunqi.tech/documents/create_cluster) ·
[ALTER VCLUSTER](https://www.yunqi.tech/documents/alter-vcluster) ·
[DROP VCLUSTER](https://www.yunqi.tech/documents/drop-vcluster) ·
[SHOW VCLUSTERS](https://www.yunqi.tech/documents/show-vclusters) ·
[计算集群缓存](https://www.yunqi.tech/documents/vc_cache)

---

### AI 函数与外部函数

#### [clickzetta-external-function](./clickzetta-external-function/)

在 ClickZetta Lakehouse 中扩展 SQL 计算能力，调用 LLM、图像识别、自定义算法等外部服务。覆盖两条路径：

- **内置 AI 函数**（推荐）— `AI_COMPLETE`（调用 LLM 做文本摘要/情感分析）、`AI_EMBEDDING`（文本向量化），只需创建 API Connection
- **External Function（UDF）** — Python/Java 自定义函数，部署在阿里云FC/腾讯云SCF/AWS Lambda，支持 UDF/UDAF/UDTF

包含 Python UDF 代码结构、打包上传（支持 User Volume 无需 OSS）、CREATE API CONNECTION 配置。

**触发词**：外部函数、UDF、自定义函数、External Function、Remote Function、调用 LLM、AI_COMPLETE、AI_EMBEDDING、文本向量化、调用阿里云函数计算、Python UDF、Java UDF、CREATE EXTERNAL FUNCTION

**相关文档**：
[External Function 介绍](https://www.yunqi.tech/documents/RemoteFunctionintro) ·
[CREATE EXTERNAL FUNCTION](https://www.yunqi.tech/documents/CREATE_EXTERNATL_FUNCTION) ·
[CREATE API CONNECTION](https://www.yunqi.tech/documents/create-api-connection) ·
[Python3 开发指南](https://www.yunqi.tech/documents/RemoteFunctionDevGuidePython3) ·
[AI_COMPLETE](https://www.yunqi.tech/documents/AI_COMPLETE) ·
[AI_EMBEDDING](https://www.yunqi.tech/documents/AI_EMBEDDING)

---

### 数据分享

#### [clickzetta-data-sharing](./clickzetta-data-sharing/)

实现 ClickZetta Lakehouse 跨账户/跨实例的无复制、实时只读数据分享。覆盖提供方和消费方完整工作流：

- **提供方** — CREATE SHARE → GRANT TABLE/VIEW TO SHARE → ALTER SHARE ADD INSTANCE
- **消费方** — SHOW SHARES → DESC SHARE → CREATE SCHEMA FROM SHARE → 直接查询
- **管理操作** — REVOKE FROM SHARE、ALTER SHARE REMOVE INSTANCE、DROP SHARE

数据实时更新，消费方无需同步，无需为存储付费。

**触发词**：数据分享、数据共享、Share、跨账户共享、跨实例共享、CREATE SHARE、GRANT TO SHARE、CREATE SCHEMA FROM SHARE、无复制共享、分享数据给其他公司、接收共享数据

**相关文档**：
[数据分享概述](https://www.yunqi.tech/documents/datasharing) ·
[SHARE DDL](https://www.yunqi.tech/documents/share-ddl) ·
[GRANT TO SHARE](https://www.yunqi.tech/documents/grant-to-share) ·
[CREATE SCHEMA FROM SHARE](https://www.yunqi.tech/documents/create-schema-from-share) ·
[跨账号数据共享入门](https://www.yunqi.tech/documents/data_sharing_between_accounts_guide)

---

### BI 工具连接

#### [clickzetta-bi-connect](./clickzetta-bi-connect/)

将主流 BI 工具和数据库客户端连接到 ClickZetta Lakehouse。覆盖：

- **Apache Superset** — Docker 快速启动 + SQLAlchemy URL 配置
- **Tableau** — JDBC 驱动 + .taco 插件安装步骤
- **Metabase** — Docker 部署 + 专用驱动安装
- **DBeaver / DataGrip** — JDBC 驱动配置
- **JDBC / SQLAlchemy** — 连接字符串格式与地域代码速查

**触发词**：连接 Superset、Tableau 连接 Lakehouse、Metabase、DBeaver、DataGrip、BI 工具、JDBC 连接、SQLAlchemy 连接、帆软、FineBI、数据库客户端

**相关文档**：
[生态工具连接](https://www.yunqi.tech/documents/ecosystem-all) ·
[JDBC 驱动](https://www.yunqi.tech/documents/JDBC-Driver) ·
[SQLAlchemy](https://www.yunqi.tech/documents/sqlalchemy) ·
[Tableau 连接](https://www.yunqi.tech/documents/TableauConnectToLakehouse) ·
[Metabase](https://www.yunqi.tech/documents/metabase)

---

### AI 向量检索

#### [clickzetta-ai-vector-search](./clickzetta-ai-vector-search/)

在 ClickZetta Lakehouse 中实现向量存储、HNSW 向量索引和 ANN 近似最近邻检索，构建 RAG、语义搜索等 AI 应用。覆盖：

- **VECTOR 数据类型** — `VECTOR(FLOAT, 1024)` 定义，支持 float/tinyint 元素
- **向量索引** — HNSW 算法，支持 cosine/l2/hamming 距离函数
- **向量检索** — `cosine_distance`、`l2_distance` 等距离函数 + `ORDER BY LIMIT`
- **融合检索** — 向量 + 标量过滤 + 倒排索引全文检索同一张表
- **性能调优** — `cz.vector.index.search.ef` 参数，单独 VCluster 最佳实践

**触发词**：向量检索、向量索引、语义搜索、embedding 存储、RAG、ANN 搜索、HNSW、cosine_distance、l2_distance、VECTOR 类型、向量数据库、相似度搜索、向量+标量融合检索

**相关文档**：
[向量检索](https://www.yunqi.tech/documents/vector-search) ·
[VECTOR 类型](https://www.yunqi.tech/documents/vector-type) ·
[CREATE VECTOR INDEX](https://www.yunqi.tech/documents/create-vector-index) ·
[向量函数](https://www.yunqi.tech/documents/vector-funcitons) ·
[向量+标量融合检索实践](https://www.yunqi.tech/documents/PerformingVectorandScalarRetrievalinheSameTableinLakehouse)

---

### 访问控制与安全

#### [clickzetta-access-control](./clickzetta-access-control/)

管理 ClickZetta Lakehouse 的用户、角色和权限（RBAC），以及列级动态数据脱敏。覆盖：

- **用户管理** — CREATE/ALTER/DROP USER（将已有账户用户添加到工作空间）
- **角色管理** — 系统预置角色 + 自定义角色（CREATE/DROP ROLE，仅 SQL 支持）
- **权限授予与撤销** — GRANT/REVOKE 细粒度授权（表/Schema/VCluster/工作空间级）
- **动态数据脱敏** — 列级脱敏函数绑定（预览功能，需联系技术支持开通）

**触发词**：创建用户、添加用户、授权、GRANT、REVOKE、撤销权限、创建角色、角色管理、RBAC、权限管理、查看权限、数据脱敏、动态脱敏、列级安全

**相关文档**：
[访问控制概览](https://www.yunqi.tech/documents/access-control-general) ·
[CREATE USER](https://www.yunqi.tech/documents/CREAREUSER) ·
[角色](https://www.yunqi.tech/documents/roles) ·
[GRANT](https://www.yunqi.tech/documents/grant-user-privileges) ·
[REVOKE](https://www.yunqi.tech/documents/revoke-user-privileges) ·
[动态脱敏](https://www.yunqi.tech/documents/dynamic-mask)

---

### 查询优化

#### [clickzetta-query-optimizer](./clickzetta-query-optimizer/)

分析和优化 ClickZetta Lakehouse 查询性能。覆盖：

- **EXPLAIN** — 查看执行计划，识别性能瓶颈
- **SHOW JOBS** — 查看作业历史、运行状态、耗时统计
- **Result Cache** — 查询结果缓存配置与验证
- **OPTIMIZE** — 小文件合并、数据重组（仅通用型集群）
- **查询提示（Hints）** — MAPJOIN、Sort Key 等优化手段

**触发词**：查询慢、优化查询、执行计划、EXPLAIN、SHOW JOBS、查询缓存、Result Cache、小文件合并、OPTIMIZE、MAPJOIN、Sort Key

**相关文档**：
[EXPLAIN](https://www.yunqi.tech/documents/explain) ·
[SHOW JOBS](https://www.yunqi.tech/documents/show-jobs) ·
[OPTIMIZE](https://www.yunqi.tech/documents/optimize) ·
[查询结果缓存](https://www.yunqi.tech/documents/result-cache)

---

### 索引管理

#### [clickzetta-index-manager](./clickzetta-index-manager/)

管理 ClickZetta Lakehouse 表索引，加速查询性能。覆盖三种索引类型：

- **Bloom Filter 索引** — 等值过滤加速，适合高基数列（用户ID、订单号等）
- **倒排索引（Inverted Index）** — 全文检索、关键词搜索
- **向量索引（Vector Index）** — 基于 HNSW 算法的近似最近邻搜索，适合 AI 语义检索

包含 BUILD/DROP/SHOW/DESC INDEX 完整管理操作。

**触发词**：创建索引、Bloom Filter、倒排索引、向量索引、全文检索、向量搜索、ANN 搜索、HNSW、索引管理

**相关文档**：
[Bloom Filter 索引](https://www.yunqi.tech/documents/bloom-filter-index) ·
[倒排索引](https://www.yunqi.tech/documents/inverted-index) ·
[向量索引](https://www.yunqi.tech/documents/vector-index)

---

### Python 数据工程（ZettaPark）

#### [clickzetta-zettapark](./clickzetta-zettapark/)

使用 ZettaPark Python 库操作 ClickZetta Lakehouse 数据。ZettaPark 将 Python DataFrame 操作翻译为 SQL 在 Lakehouse 中分布式执行，提供类 pandas 的开发体验。覆盖：

- **Session 创建** — 连接参数配置、hints（超时/query_tag）、从 JSON 配置文件读取
- **DataFrame 构建** — `session.table()`、`session.sql()`、`create_dataframe()`
- **转换操作** — `filter`、`select`、`with_column`、`join`、`group_by + agg`、`sort`、`limit`
- **结果获取** — `show()`、`collect()`、`to_pandas()`、`count()`
- **写入数据** — `save_as_table(mode="overwrite/append")`
- **典型场景** — ETL 数据处理、特征工程、本地文件导入

**触发词**：ZettaPark、zettapark、DataFrame API、Python 操作 Lakehouse、save_as_table、session.table、session.sql、collect()、to_pandas、Python 数据工程、Python 写入 Lakehouse、clickzetta_zettapark_python

**相关文档**：
[ZettaPark 快速上手](https://www.yunqi.tech/documents/ZettaparkQuickStart) ·
[数据工程示例](https://www.yunqi.tech/documents/Zettapark_Data_Engineering_Demo) ·
[ZettaPark API 参考](https://www.yunqi.tech/documents/LakehousePythonZettapark) ·
[使用 ZettaPark 管理 Volume 文件](https://www.yunqi.tech/documents/ManagingFilesonDatalakeVolumewithZettapark)

---

### 联邦查询

#### [clickzetta-external-catalog](./clickzetta-external-catalog/)

通过 External Catalog 对 Hive、Iceberg、Databricks 等外部数据源执行只读联邦查询，无需迁移数据。覆盖：

- **三步创建流程** — 存储连接 → Catalog Connection → External Catalog
- **支持数据源** — Apache Hive（HMS）、Iceberg REST Catalog、Databricks Unity Catalog
- **联邦查询** — 三层命名空间语法（catalog.schema.table），支持外部表 JOIN 内部表

**触发词**：外部数据目录、External Catalog、联邦查询、Hive 联邦、访问 Hive 数据、Databricks 联邦、跨数据源查询、不迁移数据直接查询、Catalog Connection

**相关文档**：
[External Catalog 简介](https://www.yunqi.tech/documents/external-catalog-summary) ·
[CREATE EXTERNAL CATALOG](https://www.yunqi.tech/documents/create-external-catalog) ·
[CREATE CATALOG CONNECTION](https://www.yunqi.tech/documents/create-catalog-connection) ·
[SHOW CATALOGS](https://www.yunqi.tech/documents/show-catalog)

---

### 数据湖 Volume 管理

#### [clickzetta-volume-manager](./clickzetta-volume-manager/)

管理 ClickZetta Lakehouse Volume 对象，实现对象存储挂载、文件查询与数据导入导出。覆盖：

- **外部 Volume** — 挂载 OSS/COS/S3，支持目录自动刷新
- **User Volume** — PUT/GET/REMOVE 本地文件操作
- **SELECT FROM VOLUME** — 直接查询 CSV/Parquet/ORC/JSON 文件（无需建表）
- **COPY INTO** — Volume → 表（导入）和 表 → Volume（导出）

**触发词**：创建Volume、挂载OSS、挂载S3、挂载COS、Volume管理、查询OSS文件、上传文件到Volume、PUT文件、从Volume导入数据、导出到Volume、COPY INTO VOLUME、SELECT FROM VOLUME、User Volume

**相关文档**：
[数据湖 Volume 对象](https://www.yunqi.tech/documents/datalake_volume_object) ·
[内部 Volume](https://www.yunqi.tech/documents/internal_volume) ·
[OSS Volume 创建](https://www.yunqi.tech/documents/oss_volume_creation) ·
[SHOW VOLUMES](https://www.yunqi.tech/documents/show-volume)

---

### 作业监控

#### [clickzetta-monitoring](./clickzetta-monitoring/)

监控和分析 ClickZetta Lakehouse 作业运行状态、性能和资源使用情况。覆盖：

- **SHOW JOBS** — 实时查看作业状态、执行时间、集群分布
- **information_schema.job_history** — 历史作业分析（最近 7-90 天）
- **分析场景** — 集群负载、慢查询 TOP N、失败作业、缓存命中率、高峰期识别
- **query_tag** — 给作业打标，按来源过滤

**触发词**：查看作业、作业历史、SHOW JOBS、慢查询、查询性能、集群负载、作业失败、监控、job history、information_schema、缓存命中率、查询耗时

**相关文档**：
[SHOW JOBS](https://www.yunqi.tech/documents/show-jobs) ·
[作业历史](https://www.yunqi.tech/documents/web-job-history) ·
[information_schema 作业历史分析](https://www.yunqi.tech/documents/job_history_analysis_with_information_schema)

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

### 元数据查询

#### [clickzetta-information-schema](./clickzetta-information-schema/)

查询 ClickZetta Lakehouse INFORMATION_SCHEMA 元数据视图，获取表结构、字段信息、作业历史、用户权限等元数据。支持两个层级：

- **空间级**（`information_schema.*`）— 当前工作空间的元数据，需 workspace_admin 权限
- **实例级**（`SYS.information_schema.*`）— 所有工作空间的元数据，需 INSTANCE ADMIN 权限

覆盖 11 类视图：SCHEMAS、TABLES、COLUMNS、VIEWS、USERS、ROLES、JOB_HISTORY、MATERIALIZED_VIEW_REFRESH_HISTORY、AUTOMV_REFRESH_HISTORY、VOLUMES、CONNECTIONS，以及实例级专有的 WORKSPACES 和 OBJECT_PRIVILEGES。

包含常用查询模板：表结构探查、慢查询分析、CRU 消耗统计、物化视图刷新监控、Volume 列表、权限审计等。

**触发词**：查看表结构、查看字段信息、查看作业历史、查看 JOB 历史、查看慢查询、查看 CRU 消耗、查看用户列表、查看角色、查看权限、查看 Volume 列表、查看 Connection、查看物化视图刷新历史、元数据查询、information_schema、查看所有表、查看 Schema 列表、统计存储用量、查看删除的表

**相关文档**：
[实例级 INFORMATION_SCHEMA](https://www.yunqi.tech/documents/instance-information_schema) ·
[空间级 INFORMATION_SCHEMA](https://www.yunqi.tech/documents/weokspace-informationschema) ·
[视图字段详细说明](https://www.yunqi.tech/documents/worksapce-informaiton_schema-views) ·
[实例级视图字段说明](https://www.yunqi.tech/documents/instance-informaiton-schema)

---

### 数据生命周期管理

#### [clickzetta-data-lifecycle](./clickzetta-data-lifecycle/)

管理 ClickZetta Lakehouse 表的数据自动回收（TTL）和 Time Travel 历史版本保留周期。覆盖：

- **数据生命周期（TTL）** — `data_lifecycle` 属性，超过指定天数未更新的数据自动回收；`data_lifecycle_delete_meta='true'` 可同时删除表结构
- **Time Travel 保留周期** — `data_retention_days` 属性（0-90天），控制历史版本保留时长，支持时间点查询和数据恢复
- **查看配置** — `DESC EXTENDED`、`SHOW CREATE TABLE`、`information_schema.tables` 批量查询
- **分区表** — `SHOW PARTITIONS EXTENDED` 查看各分区 `last_modified_time`，分区独立计算到期
- **Time Travel** — `TIMESTAMP AS OF` 查询历史数据、`RESTORE TABLE` 恢复、`UNDROP TABLE` 恢复删除表

**触发词**：设置生命周期、数据自动清理、TTL、data_lifecycle、表数据过期、自动回收数据、设置数据保留、data_retention_days、Time Travel 保留周期、查看哪些表有生命周期、批量设置生命周期、数据生命周期管理

**相关文档**：
[数据生命周期管理](https://www.yunqi.tech/documents/data-lifecycle) ·
[Time Travel](https://www.yunqi.tech/documents/TIMETRAVEL) ·
[备份和恢复](https://www.yunqi.tech/documents/data-recover)

---

### SQL 语法参考

#### [clickzetta-sql-syntax-guide](./clickzetta-sql-syntax-guide/)

ClickZetta Lakehouse SQL 语法完整参考，以及与 Snowflake、Spark SQL 的深度差异对照。帮助从 Snowflake 或 Spark 迁移的用户快速找到正确语法，避免常见陷阱。覆盖：

- **迁移速查表** — 最常见的 15+ 个语法陷阱（TARGET_LAG、QUALIFY、VARIANT、METADATA$ACTION、CREATE OR REPLACE 等）
- **数据类型** — 完整类型列表及与 Snowflake/Spark 的映射关系
- **DDL** — 建表、分区、索引、修改表语法
- **DML** — INSERT/UPDATE/DELETE/MERGE INTO 语法与限制
- **查询语法** — SELECT EXCEPT、GROUP BY ALL、CTE、窗口函数、JSON 访问、LATERAL VIEW、STRUCT/ARRAY 操作
- **ClickZetta 特有对象** — VCLUSTER/DYNAMIC TABLE/TABLE STREAM/PIPE/VOLUME/SHARE/VECTOR 速查
- **函数速查** — 日期/字符串/条件/聚合函数完整对照

**触发词**：Snowflake 迁移、Spark SQL 迁移、语法差异、ClickZetta 怎么写、TARGET_LAG、QUALIFY、VARIANT、METADATA$ACTION、CREATE OR REPLACE、LISTAGG、IFF、DATEADD、FLATTEN、PIVOT、SQL 语法参考、数据类型、DATEDIFF

**相关文档**：
[查询语法](https://www.yunqi.tech/documents/query-syntax) ·
[CREATE TABLE](https://www.yunqi.tech/documents/create-table-ddl) ·
[MERGE INTO](https://www.yunqi.tech/documents/MERGE) ·
[窗口函数](https://www.yunqi.tech/documents/window-function-summary) ·
[Snowflake 迁移实践](https://www.yunqi.tech/documents/MigrateSnowflakeRealtimeETLPipelinetoClickzettaLakehouse)

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
