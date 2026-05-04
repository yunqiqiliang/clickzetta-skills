---
name: clickzetta-realtime-sync-pipeline
description: |
  创建和管理 ClickZetta Lakehouse 实时同步任务（单表），将外部数据源的数据实时同步到 Lakehouse。
  支持 Kafka、MySQL、PostgreSQL 等数据源作为来源端，Lakehouse 作为目标端。
  实时同步任务为持续运行的流式任务，无需配置调度策略，提交后即持续运行。
  当用户说"Studio 实时同步"、"realtime sync"、"单表 CDC 同步"、"实时数据同步"、"Kafka 实时同步到 Lakehouse"、
  "MySQL 单表实时同步"、"单表实时同步"、"实时数据迁移"时触发。
  包含实时同步任务创建、数据源配置、字段映射（含 JSONPath 计算列）、部署运维等
  ClickZetta Studio 特有逻辑。
  Keywords: real-time sync, single table, Kafka source, MySQL source, streaming
---

# 实时同步（单表）Pipeline 工作流

## 适用场景

- 将外部数据源的数据实时同步到 Lakehouse（低延迟、持续运行）
- Kafka Topic → Lakehouse 表（支持 JSON 消息解析）
- MySQL / PostgreSQL / SQL Server 等数据库 → Lakehouse 表（CDC 变更捕获）
- 数据时效性要求高，需要秒级或分钟级延迟
- 单张源表/Topic 到单张目标表的实时同步
- 关键词：实时同步、CDC、流式同步、realtime sync、Kafka 实时同步

## 与其他同步方式的区别

| 维度 | 实时同步（本 Skill） | 离线同步 | 多表实时同步 |
|------|---------------------|---------|------------|
| 任务类型 ID | `28`（实时同步） | `10` / `291` | `281` |
| 同步粒度 | 单表/单 Topic | 单表/多表 | 整库/多表 |
| 运行模式 | 持续运行（流式） | 周期调度（批量） | 持续运行（流式） |
| 调度策略 | 无需配置，提交即运行 | 需配置 Cron 表达式 | 无需配置，提交即运行 |
| 延迟 | 秒级~分钟级 | 取决于调度周期 | 秒级~分钟级 |
| 适用 Skill | `clickzetta-realtime-sync-pipeline` | `clickzetta-batch-sync-pipeline` | `clickzetta-cdc-sync-pipeline` |

## 前置依赖

- ClickZetta Lakehouse Studio 账户，具备创建同步任务、目标表的权限
- 源端数据源已在 Studio 中配置（Kafka / MySQL / PostgreSQL / SQL Server 等）
- 目标端 Lakehouse 数据源可用
- Sync VCluster 可用（实时同步任务 task_type=28 需要 Sync VCluster）
- clickzetta-studio-mcp 工具可用（`create_task`、`save_integration_task`、`publish_task`、`list_data_sources`、`LH_show_object_list` 等）

## 工作流

### 步骤 1：确认 Sync VCluster 可用

```
使用 LH_show_object_list（object_type='VCLUSTERS'）查看可用虚拟集群。
筛选 vcluster_type 包含 SYNC 的集群。
如无可用 Sync VCluster，需先创建后再继续。
```

### 步骤 2：查找可用数据源

```
使用 list_data_sources 查看已配置的数据源列表。
按类型过滤：
- Kafka: ds_type=2
- MySQL: ds_type=5
- PostgreSQL: ds_type=7
- SQL Server: ds_type=8
记录源端 datasource_name 和目标端 Lakehouse datasource_name。
```

### 步骤 3：探查源端数据结构（可选）

```
使用 list_namespaces 查看源端数据源的命名空间（数据库/Schema）。
使用 list_metadata_objects 查看命名空间下的表/Topic 列表。
使用 get_metadata_detail 查看具体表/Topic 的字段结构。
```

### 步骤 4：创建实时同步任务

```
使用 create_task 创建任务：
- task_type: 28（实时同步）
- task_name: 自定义任务名称（建议包含源和目标信息，如 "rt_sync_kafka_orders"）
- data_folder_id: 目标文件夹 ID（可通过 list_folders 获取）

记录返回的 task_id 和 studio_url。
```

### 步骤 5：配置同步内容

```
使用 save_integration_task 配置同步：
- task_id: 步骤 4 返回的任务 ID
- source_datasource_name: 源端数据源名称
- source_schema: 源端数据库/Schema（Kafka 场景为 Topic 所在命名空间）
- source_table: 源端表名或 Kafka Topic 名称
- source_ds_type: 源端类型（2=Kafka, 5=MySQL, 7=PostgreSQL, 8=SQL Server）
- sink_datasource_name: 目标 Lakehouse 数据源名称
- sink_schema: 目标 Schema（默认 public）
- sink_table: 目标表名（可选，默认与源表同名）
- sink_ds_type: 1（Lakehouse）
```

> **说明**：系统会自动获取源端和目标端的元数据，生成字段映射。如目标表不存在，会自动创建。

### 步骤 6：Kafka JSON 消息解析（Kafka 数据源专用）

如果 Kafka Topic 的消息格式为 JSON，可在 Studio UI 中通过新增计算列解析嵌套字段：

- 使用 JSONPath 规则解析 value 字段中的内容
- 示例：`$.id` 提取顶层 id 字段，`$.data.code` 提取嵌套字段
- 默认使用 Kafka Topic 内置字段（key、value、timestamp、partition、offset）进行映射
- 计算列配置需在 Studio UI 中完成（通过 studio_url 打开）

### 步骤 7：提交部署

```
实时同步任务不需要配置调度策略（无需调用 save_task_configuration）。
直接使用 publish_task 提交任务：
- task_id: 任务 ID
- task_version: 当前版本号（通过 get_task_detail 获取）

提交后任务即开始持续运行。
```

> **重要**：实时同步任务不支持开发状态下的测试运行，提交即为正式部署。

### 步骤 8：运维监控

```
提交后在运维中心管理实时同步任务：

查看任务状态：get_task_detail
查看运行记录：list_task_run（注意实时任务为持续运行，不同于离线任务的周期实例）

Studio UI 中可进行：
- 启动/停止任务
- 查看同步延迟和吞吐量
- 查看错误日志
```

---

## 支持的数据源

### 来源端

| 数据源 | ds_type | 说明 |
|--------|---------|------|
| Kafka | 2 | 支持 JSON 消息解析（JSONPath 计算列） |
| MySQL | 5 | CDC 变更捕获 |
| PostgreSQL | 7 | CDC 变更捕获 |
| SQL Server | 8 | CDC 变更捕获 |
| Aurora MySQL | 39 | CDC 变更捕获 |
| Aurora PostgreSQL | 40 | CDC 变更捕获 |
| PolarDB MySQL | 19 | CDC 变更捕获 |
| PolarDB PostgreSQL | 48 | CDC 变更捕获 |

### 目标端

| 数据源 | ds_type |
|--------|---------|
| Lakehouse | 1 |

## 故障排除

| 问题 | 排查方向 |
|------|---------|
| 任务创建失败 | 检查是否有可用的 Sync VCluster（`LH_show_object_list` 查看 VCLUSTERS，筛选 SYNC 类型） |
| 源端连接失败 | 检查数据源配置中的连接信息、网络可达性、账号权限 |
| Kafka 消费无数据 | 检查 Topic 名称是否正确、消费位点设置、Kafka 集群连通性 |
| JSON 解析失败 | 检查 JSONPath 表达式是否正确、消息格式是否为合法 JSON |
| 同步延迟增大 | 检查 Sync VCluster 资源是否充足、源端数据量是否突增 |
| 目标表写入失败 | 检查目标表是否存在、字段类型是否兼容、权限是否充足 |
| 任务异常停止 | 查看执行日志（`list_executions` + `get_execution_log`）排查具体错误 |

## 注意事项

### 运行模式

- 实时同步任务为持续运行的流式任务，提交后即开始运行，无需配置调度
- 不支持开发状态下的测试运行
- 停止后需手动重新启动

### Sync VCluster 要求

- 实时同步任务（task_type=28）必须使用 Sync VCluster
- 创建任务前需确认有可用的 Sync VCluster
- 可通过 `LH_show_object_list`（object_type='VCLUSTERS'）查看，筛选 vcluster_type 包含 SYNC 的集群

### Kafka 数据源特殊说明

- 支持指定消费起始位点（earliest / latest / 指定 offset）
- JSON 消息可通过 JSONPath 计算列解析嵌套字段
- 默认字段包括：key、value、timestamp、partition、offset

### 与多表实时同步的选择

- 单表实时同步（本 Skill）：适合单张表/Topic 的精细化同步
- 多表实时同步（`clickzetta-cdc-sync-pipeline`）：适合整库 CDC、多表批量实时同步
- 如需同步整个数据库的所有表，建议使用多表实时同步
