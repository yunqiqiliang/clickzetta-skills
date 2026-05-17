# clickzetta-skills

[ClickZetta Lakehouse / 云器 Lakehouse](https://www.yunqi.tech) 的 AI Agent Skills 集合，适用于 Codex、Claude Code、czcode 以及其他支持 Skills 机制的 AI 编程助手。

这些 skills 将 ClickZetta 的 SQL 语法、Studio 任务、数据同步、动态表、权限、运维、SDK、BI 集成等经验沉淀为可复用的工作流，帮助 AI 助手在具体场景中自动选择正确文档、命令、SQL 和排查路径。

## Skills 总览

当前仓库包含 37 个顶层 `clickzetta-*` skills：

| 类别 | Skill | 适用场景 |
|---|---|---|
| 基础与连接 | [clickzetta-overview](./clickzetta-overview/) | ClickZetta 产品全貌、对象模型、架构、Studio 模块、品牌与服务地址 |
| 基础与连接 | [clickzetta-lakehouse-connect](./clickzetta-lakehouse-connect/) | Python SDK、ZettaPark、SQLAlchemy、JDBC 等连接配置 |
| 基础与连接 | [clickzetta-sql-syntax-guide](./clickzetta-sql-syntax-guide/) | SQL 语法参考、函数、数据类型、Snowflake/Databricks/Spark 迁移差异 |
| 基础与连接 | [clickzetta-metadata](./clickzetta-metadata/) | SHOW/DESC 命令族、INFORMATION_SCHEMA 元数据、费用和用量统计 |
| 基础与连接 | [clickzetta-manage-comments](./clickzetta-manage-comments/) | Schema、表、字段、动态表、物化视图、VCluster、Workspace 注释管理 |
| 数据导入与管道 | [clickzetta-data-ingest-pipeline](./clickzetta-data-ingest-pipeline/) | 数据导入方案路由，根据数据源、实时性、范围选择最佳导入方式 |
| 数据导入与管道 | [clickzetta-file-import-pipeline](./clickzetta-file-import-pipeline/) | URL、本地文件、Volume 文件导入，格式推断、建表、COPY INTO |
| 数据导入与管道 | [clickzetta-oss-ingest-pipeline](./clickzetta-oss-ingest-pipeline/) | OSS/S3/COS 对象存储批量导入或 PIPE 持续导入 |
| 数据导入与管道 | [clickzetta-kafka-ingest-pipeline](./clickzetta-kafka-ingest-pipeline/) | Kafka 到 Lakehouse 的 READ_KAFKA Pipe 或外部表接入 |
| 数据导入与管道 | [clickzetta-batch-sync-pipeline](./clickzetta-batch-sync-pipeline/) | Studio 离线同步，支持单表、多表、整库镜像、分库分表合并 |
| 数据导入与管道 | [clickzetta-realtime-sync-pipeline](./clickzetta-realtime-sync-pipeline/) | Studio 单表实时同步，支持 Kafka、MySQL、PostgreSQL 等来源 |
| 数据导入与管道 | [clickzetta-cdc-sync-pipeline](./clickzetta-cdc-sync-pipeline/) | 多表实时 CDC，同步 MySQL/PostgreSQL 整库或多表到 Lakehouse |
| 数据导入与管道 | [clickzetta-sql-pipeline-manager](./clickzetta-sql-pipeline-manager/) | SQL 管道对象管理：Dynamic Table、Materialized View、Table Stream、Pipe |
| 数据导入与管道 | [clickzetta-table-stream-pipeline](./clickzetta-table-stream-pipeline/) | Table Stream 变更捕获、offset 管理、增量 ETL 消费 |
| 数据导入与管道 | [clickzetta-studio-task-manager](./clickzetta-studio-task-manager/) | Studio 任务类型、目录、调度、依赖、cz-cli task 命令族和建管分离规范 |
| 数据导入与管道 | [clickzetta-pipeline-review](./clickzetta-pipeline-review/) | 数据管道 Review、任务/表/运行记录发现、问题诊断与修复建议 |
| 建模与计算 | [clickzetta-dw-modeling](./clickzetta-dw-modeling/) | 数仓建模、ODS/DWD/DWS/ADS、Medallion 架构、DDL 与管道设计 |
| 建模与计算 | [clickzetta-dynamic-table](./clickzetta-dynamic-table/) | Dynamic Table 创建、增量刷新、ALTER、性能优化和最佳实践 |
| 建模与计算 | [clickzetta-query-optimizer](./clickzetta-query-optimizer/) | 慢查询、EXPLAIN、Result Cache、OPTIMIZE、Hints、Sort Key 调优 |
| 建模与计算 | [clickzetta-index-manager](./clickzetta-index-manager/) | Bloom Filter、倒排索引、向量索引创建、构建、删除、查看 |
| 建模与计算 | [clickzetta-data-science](./clickzetta-data-science/) | 数据科学工作流：Jupyter、EDA、特征工程、采样、推理、向量检索 |
| 建模与计算 | [clickzetta-semantic-view](./clickzetta-semantic-view/) | Semantic View 语义层、逻辑表、维度、指标、过滤器和查询 |
| SDK 与外部集成 | [clickzetta-app-python-sdk](./clickzetta-app-python-sdk/) | Python 应用 SDK：connector、BulkLoad、IGS 实时写入、SQLAlchemy |
| SDK 与外部集成 | [clickzetta-zettapark](./clickzetta-zettapark/) | ZettaPark DataFrame API、Session、表读写、文件操作、SQL 执行 |
| SDK 与外部集成 | [clickzetta-java-sdk](./clickzetta-java-sdk/) | Java SDK BulkloadStream 批量写入、RealtimeStream Kafka 实时写入 |
| SDK 与外部集成 | [clickzetta-spark-flink-connector](./clickzetta-spark-flink-connector/) | Spark Connector 读写、Flink CDC/append-only 写入 |
| SDK 与外部集成 | [clickzetta-bi-connect](./clickzetta-bi-connect/) | Superset、Tableau、Metabase、DBeaver、DataGrip、FineBI、PowerBI 连接 |
| SDK 与外部集成 | [clickzetta-external-function](./clickzetta-external-function/) | External Function、Python/Java UDF、AI_COMPLETE、AI_EMBEDDING |
| SDK 与外部集成 | [clickzetta-external-catalog](./clickzetta-external-catalog/) | Hive、Iceberg、Databricks、Snowflake Open Catalog 联邦查询 |
| 运维与治理 | [clickzetta-access-control](./clickzetta-access-control/) | 用户、角色、GRANT/REVOKE、动态脱敏、网络策略 |
| 运维与治理 | [clickzetta-vcluster-manager](./clickzetta-vcluster-manager/) | VCluster 创建、启停、扩缩容、自动挂起、缓存预加载 |
| 运维与治理 | [clickzetta-volume-manager](./clickzetta-volume-manager/) | Volume 创建、OSS/COS/S3 挂载、PUT/GET、文件查询、导入导出 |
| 运维与治理 | [clickzetta-monitoring](./clickzetta-monitoring/) | SHOW JOBS、job_history、慢查询、失败作业、集群负载、缓存命中率 |
| 运维与治理 | [clickzetta-dba-guide](./clickzetta-dba-guide/) | DBA 运维：集群、作业、恢复、存储优化、Schema/对象、成本分析 |
| 运维与治理 | [clickzetta-data-retention](./clickzetta-data-retention/) | TTL 生命周期、Time Travel、UNDROP、RESTORE、历史版本查询 |
| 运维与治理 | [clickzetta-data-sharing](./clickzetta-data-sharing/) | Share 跨账户/跨实例零复制数据共享 |
| 运维与治理 | [clickzetta-table-lineage](./clickzetta-table-lineage/) | 基于 job_history 的表血缘和成本可视化 |

## 路由建议

如果你不确定应该使用哪个 skill，优先从这些入口开始：

| 用户意图 | 推荐入口 |
|---|---|
| 了解 ClickZetta、Workspace/Schema/VCluster、Studio 能力 | `clickzetta-overview` |
| 配置连接、写 Python/JDBC/SQLAlchemy/ZettaPark 连接代码 | `clickzetta-lakehouse-connect` |
| 不确定如何把数据导入 Lakehouse | `clickzetta-data-ingest-pipeline` |
| 从文件、URL、对象存储或 Kafka 导入数据 | `clickzetta-file-import-pipeline` / `clickzetta-oss-ingest-pipeline` / `clickzetta-kafka-ingest-pipeline` |
| 做离线同步、实时同步、多表 CDC | `clickzetta-batch-sync-pipeline` / `clickzetta-realtime-sync-pipeline` / `clickzetta-cdc-sync-pipeline` |
| 管理 Studio 任务、调度、依赖、补数、任务目录 | `clickzetta-studio-task-manager` |
| 设计数据管道、动态表、流式增量 ETL | `clickzetta-sql-pipeline-manager` / `clickzetta-dynamic-table` / `clickzetta-table-stream-pipeline` |
| 诊断管道质量、任务失败、链路缺陷 | `clickzetta-pipeline-review` |
| 写 SQL、迁移 SQL、查函数或语法差异 | `clickzetta-sql-syntax-guide` |
| 查询元数据、表结构、作业历史、成本归因 | `clickzetta-metadata` / `clickzetta-monitoring` |
| 查询慢、作业慢、小文件、缓存、执行计划 | `clickzetta-query-optimizer` |
| 用户、角色、授权、脱敏、网络策略 | `clickzetta-access-control` |
| 集群、Volume、DBA 运维、恢复、生命周期 | `clickzetta-vcluster-manager` / `clickzetta-volume-manager` / `clickzetta-dba-guide` / `clickzetta-data-retention` |
| Python、Java、Spark、Flink、BI 工具集成 | `clickzetta-app-python-sdk` / `clickzetta-java-sdk` / `clickzetta-spark-flink-connector` / `clickzetta-bi-connect` |

## Skill 结构

每个 skill 目录通常包含：

```text
clickzetta-xxx/
├── SKILL.md              # 触发条件、工作流、关键语法和执行步骤
├── references/           # 细分参考文档、SQL 片段、API 说明或模板
├── eval_cases.jsonl      # 评测样例，用于验证 skill 是否能被正确触发和执行
└── evals/                # 可选，结构化评测数据
```

少数 skill 还包含子 skill 或最佳实践文档，例如 `clickzetta-dynamic-table/dt-creator/`、`clickzetta-dynamic-table/dynamic-table-alter/` 和 `clickzetta-dynamic-table/best-practices/`。

## 使用方式

将本仓库中的 skill 目录放到 AI 编程助手可识别的 skills 路径下，或在支持插件/技能仓库的环境中直接加载本仓库。使用时直接描述你的 ClickZetta 任务即可，例如：

```text
帮我把 OSS 上的 CSV 持续导入到 public.orders
```

```text
这个动态表刷新很慢，帮我看执行计划并给出优化建议
```

```text
给 analyst 用户授予 ods schema 下所有表的只读权限
```

AI 助手会根据 `SKILL.md` 中的 `description`、触发词和工作流选择对应 skill，并按其中的步骤读取必要参考文档。

## 维护说明

- 新增 skill 时，在根目录创建 `clickzetta-<name>/SKILL.md`，并在本 README 的总览表中补充条目。
- 每个 `SKILL.md` 必须包含 front matter：`name`、`description`，并尽量提供清晰的触发词和关键词。
- 复杂语法、长 SQL、SDK 样例和故障排查细节应放入 `references/`，`SKILL.md` 只保留路由和关键工作流。
- 涉及可验证行为的 skill 建议维护 `eval_cases.jsonl`，便于持续评测。
- 归档或废弃 skill 不应继续出现在本 README 的总览表中。

## 测试与评测

仓库包含 `tests/` 目录和各 skill 下的 `eval_cases.jsonl`。更新 skill 或 README 后，建议至少运行静态契约测试，确保 skill 元信息、路径和评测样例保持一致：

```bash
pytest tests/test_static_skill_contract.py
```

更多测试说明见 [tests/README.md](./tests/README.md)。
