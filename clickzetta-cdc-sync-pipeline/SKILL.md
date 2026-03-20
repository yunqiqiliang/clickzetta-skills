---
name: clickzetta-cdc-sync-pipeline
description: |
  创建和管理 ClickZetta Lakehouse 多表实时同步任务（CDC），将 MySQL / PostgreSQL 数据库整库或多表实时同步到 Lakehouse。
  支持三种同步模式：整库镜像、多表镜像、多表合并（分库分表合并）。
  基于 Binlog（MySQL）或 WALs（PostgreSQL）实现秒级端到端时效性，包含全量 + 增量两阶段同步。
  当用户说"多表实时同步"、"整库同步"、"整库镜像"、"CDC 整库"、"多表 CDC"、"分库分表合并"、
  "多表合并同步"、"MySQL 整库同步到 Lakehouse"、"PostgreSQL 整库同步"、"multi-table realtime sync"、
  "database migration"、"全量+增量同步"、"同步运维"、"同步 SOP"、"同步告警配置"、
  "Binlog 位点过期"、"server-id 冲突"、"补充全量同步"、"新增同步表"时触发。
  包含源端数据库准备（参数配置+权限）、三种同步模式选择、任务创建部署、运维 SOP（补全量/加表/数据修复）、
  监控告警配置（5 种告警规则+IM webhook）、详细故障排除等 ClickZetta Studio 特有逻辑。
---

# 多表实时同步 Pipeline 工作流

## 适用场景

- 将 MySQL / PostgreSQL 数据库整库或多表实时同步到 Lakehouse（CDC 变更捕获）
- 整库镜像：以数据库为粒度，自动适配新增表
- 多表镜像：以表粒度选择，支持自动感知字段变更
- 多表合并：将分库分表数据合并写入同一张目标表
- 全量 + 增量两阶段同步，秒级端到端时效性
- 关键词：多表实时同步、整库同步、CDC、分库分表合并、database migration

## 与其他同步方式的区别

| 维度 | 多表实时同步（本 Skill） | 单表实时同步 | 离线同步 |
|------|------------------------|------------|---------|
| 任务类型 ID | `281`（多表实时同步） | `28` | `10` / `291` |
| 同步粒度 | 整库/多表/分库分表合并 | 单表/单 Topic | 单表/多表 |
| 运行模式 | 持续运行（流式 CDC） | 持续运行（流式） | 周期调度（批量） |
| 数据源 | MySQL / PostgreSQL | Kafka/MySQL/PG/SQLServer | 多种 |
| 调度策略 | 无需配置，提交即运行 | 无需配置 | 需配置 Cron |
| 适用 Skill | `clickzetta-cdc-sync-pipeline` | `clickzetta-realtime-sync-pipeline` | `clickzetta-batch-sync-pipeline` |

## 支持的数据源

### 来源端

| 数据源类型 | 增量读取模式 | 数据库版本 | ds_type |
|-----------|------------|-----------|---------|
| MySQL 类（含 Aurora MySQL、PolarDB MySQL） | Binlog | 5.6+、8.x | 5, 39, 19 |
| PostgreSQL 类（含 Aurora PG、PolarDB PG） | WALs 日志 | 14+ | 7, 40, 48 |
| SQL Server | CDC | - | 8 |
| TiDB | - | - | 17 |

### 目标端

| 数据源 | ds_type |
|--------|---------|
| Lakehouse | 1 |
| Kafka | 2 |

## 前置依赖

- ClickZetta Lakehouse Studio 账户，具备创建同步任务权限
- 源端数据源已在 Studio 中配置，且账号具备 CDC 所需权限
- Sync VCluster 可用（多表实时同步任务 task_type=281 必须使用 Sync VCluster）
- clickzetta-studio-mcp 工具可用（`create_task`、`save_cdc_realtime_task`、`publish_task`、`list_data_sources`、`LH_show_object_list` 等）

## 源端数据库准备

### MySQL 参数要求

在源端 MySQL 数据库上确认以下参数：

| 参数 | 要求值 | 查询方法 |
|------|--------|---------|
| `log_bin` | ON | `SHOW GLOBAL VARIABLES LIKE 'log_bin'` |
| `binlog_format` | ROW | `SHOW GLOBAL VARIABLES LIKE 'binlog_format'` |
| `binlog_row_image` | FULL | `SHOW GLOBAL VARIABLES LIKE 'binlog_row_image'` |
| `binlog_expire_logs_seconds` | ≥86400（建议） | - |

MySQL 权限要求（建议用 root 执行）：
- 元数据读取：`SELECT` on information_schema + 目标库表
- Binlog 同步：`REPLICATION SLAVE`, `REPLICATION CLIENT`
- 全量同步：`SELECT` on 目标表

### PostgreSQL 参数要求

以下参数修改后需重启 PostgreSQL Server：

| 参数 | 要求值 | 说明 |
|------|--------|------|
| `wal_level` | logical | 支持逻辑解码 |
| `max_replication_slots` | ≥10 | 允许创建的 slot 数量 |
| `max_wal_senders` | ≥10 | 最多同时运行的 WAL sender 进程数 |

PostgreSQL 权限要求（建议用管理员账号执行）：
- 元数据读取：`SELECT` on information_schema
- WAL 日志同步：`REPLICATION` 权限
- 全量同步：`SELECT` on 目标表
- 创建 publication：`CREATE` 权限

> **PostgreSQL 特别注意**：需要配置 replication slot，不同任务不要复用同一个 slot。任务启动时如 slot 被占用会启动失败。

## 工作流

### 步骤 1：确认 Sync VCluster 可用

```
使用 LH_show_object_list（object_type='VCLUSTERS'）查看可用虚拟集群。
筛选 vcluster_type 包含 SYNC 的集群。
如无可用 Sync VCluster，提示用户先创建后再继续。
```

### 步骤 2：查找源端数据源

```
使用 list_data_sources 查看已配置的数据源。
按类型过滤：
- MySQL: ds_type=5
- PostgreSQL: ds_type=7
记录源端 datasource_id 和 datasource_type。
```

### 步骤 3：探查源端数据结构

```
使用 list_namespaces 查看源端数据库列表。
使用 list_metadata_objects 查看库下的表列表。
确认需要同步的范围（整库 / 指定表 / 分库分表）。
```

### 步骤 4：选择同步模式

根据用户需求选择三种模式之一：

| 模式 | pipeline_type | 适用场景 |
|------|--------------|---------|
| 整库镜像 | 3 | 同步整个数据库所有表，自动适配新增表 |
| 多表镜像 | 1 | 选定指定表同步，支持自动感知字段变更 |
| 多表合并 | 2 | 分库分表数据合并写入同一张目标表 |

### 步骤 5：创建多表实时同步任务

```
使用 create_task 创建任务：
- task_type: 281（多表实时同步）
- task_name: 自定义名称（如 "cdc_sync_mysql_orders_db"）
- data_folder_id: 目标文件夹 ID（通过 list_folders 获取）

记录返回的 task_id（即 data_file_id）。
```

### 步骤 6：配置同步内容

```
使用 save_cdc_realtime_task 配置同步：
- data_file_id: 步骤 5 返回的 task_id
- pipeline_type: 步骤 4 选择的模式（1=多表镜像, 2=多表合并, 3=整库镜像）
- source_datasource_list: [{"datasourceId": <id>, "datasourceType": <type>}]
- sync_object_list:
  - 整库镜像：[{"schemaName": "<数据库名>"}]（仅指定库名）
  - 多表镜像：[{"schemaName": "<库名>", "tableName": "<表名>"}, ...]
  - 多表合并：通过正则或文件批量配置
- target_datasource: {"datasourceId": <lakehouse_id>, "datasourceType": 1}
- sync_mode: 1（全量+增量，推荐）或 2（仅增量）
- save_mode: 2（追加，推荐新任务使用）
```

> **sync_mode 说明**：
> - `1`（全量+增量）：先全量同步历史数据，再启动增量 CDC，推荐首次使用
> - `2`（仅增量）：仅从当前位点开始捕获变更，适合已有历史数据的场景

### 步骤 7：提交部署

```
使用 publish_task 提交任务：
- task_id: 任务 ID
- task_version: 当前版本号（通过 get_task_detail 获取）

提交后任务不会自动启动，需要手动启动。
```

> **重要**：多表实时同步任务是持续运行的流式任务，不需要配置调度策略（不要调用 save_task_configuration）。提交后在 Studio UI 中手动启动。

### 步骤 8：启动任务

在 Studio UI 中启动任务，选择启动方式：

| 启动方式 | 说明 | 适用场景 |
|---------|------|---------|
| 无状态启动 | 完整同步所有数据（全量→增量） | 首次启动 |
| 从上次保存状态恢复 | 从停止位点断点续传 | 停止后重启 |
| 自定义起始位置 | MySQL: 指定 binlog 文件/时间；PG: 指定 LSN | 数据回刷 |

全量同步阶段可配置最大并发数，控制对源端数据库的压力。

### 步骤 9：运维监控

```
任务启动后经历三个阶段：初始化 → 全量同步 → 增量同步。

监控指标：
- 读取数据 / 写入数据（记录数）
- 平均读取速率 / 平均写入速率
- Failover 次数
- 单表级别：最新读取位置、最新更新时间、数据延迟

单表运维操作：
- 优先执行：提高全量同步优先级
- 取消运行 / 强制停止：停止单表同步
- 重新同步：对该表重新全量+增量
- 补数同步：按条件过滤部分数据重新全量同步
- 查看异常：查看 Schema Evolution 异常等
```

## 三种同步模式详解

### 整库镜像

- 以数据库为粒度配置，只选库不选表
- 自动适配库中新增表
- 适合需要完整镜像整个数据库的场景

### 多表镜像

- 以表粒度选择需要同步的表
- 支持自动感知字段个数的新增和删除
- 支持批量配置（上传配置文件）
- PostgreSQL 需要配置 replication slot（decoderbufs 或 pgoutput 插件）

### 多表合并

- 将分库分表数据合并写入同一张目标表
- 使用"虚拟表"作为中间承接：新建虚拟表时，基于数据源/Schema/Table 名称给定筛选条件，将匹配的源端表定义为写入同一张虚拟表
- 两种配置方式：
  - 基于规则：正则匹配筛选表（如以 `abc` 开头的所有表）
  - 基于文件：上传配置文件批量指定
- 扩展字段功能：可在目标表中额外新增字段记录来源信息（server/database/schema/table 名称）
- 分库分表主键冲突解决：开启扩展字段并将其设为联合主键，避免不同分库分表中主键相同记录的写入冲突
- 异构字段合并：当分库分表字段结构不完全一致时，系统自动校验并提示差异，可选择异构字段合并功能处理

## 高阶参数

在任务「参数」区域可设定以下高阶参数（默认不建议调整，调整前请联系技术支持）：

| 参数 | 含义 | 默认值 | 调优建议 |
|------|------|--------|---------|
| `step1.taskmanager.memory.process.size` | 增量同步进程总内存 | 1600m | 全量数据特别大时可调至 4000m |
| `step2.taskmanager.memory.process.size` | 全量同步进程总内存 | 2000m | - |
| `step1.taskmanager.memory.task.off-heap.size` | 增量同步堆外内存 | 256m | 全量数据特别大时可调至 500M |
| `lh.table.cz.common.output.file.max.size` | 全量同步单文件切分大小 | 33554432 | - |
| `pod.limit.memory` | 提交客户端内存上限 | 1Gi | - |

## 停止与下线

### 停止任务

- 停止会自动保存增量同步位点
- 全量阶段停止：重启后未完成的表会重新全量同步
- 增量阶段停止：重启后从停止位点继续
- 恢复方式：点击"启动"，选择"从上次保存状态恢复"即可断点续传
- 如需回溯数据：选择"自定义起始位置"，指定 binlog 文件/位点（MySQL）或 LSN（PostgreSQL），确保指定位点未过期

### 下线任务（高危）

- 不保存同步位点，再次上线需重新同步
- 不清理已同步到目标端的数据，不删除目标表
- 重新同步不会重建表：全量覆盖写入（insert overwrite），增量 merge into 更新
- 仅在以下情况使用：任务确定不再需要、任务状态异常需修复

## 运维 SOP

### 后续补充全量同步

首次启动未选择全量同步，后续需要补充全量数据的 3 种方案：

| 方案 | 操作 | 影响 |
|------|------|------|
| 方案一：单表重新同步 | 对指定表执行"重新同步" | 源端数据同步到临时表，insert overwrite 写入目标表，不影响查询 |
| 方案二：单表补数同步 | 对指定表执行"补数同步"，过滤条件设为 `where 1=1` | 按条件从源端拉取数据到临时表，delete + merge into 写入目标表 |
| 方案三：下线重上线 | 停止→下线→上线→启动（选择全量同步） | 清空位点信息，重新全量+增量同步，不删除目标表 |

### 新增同步表

1. 编辑任务，添加需要新增的表，保存
2. 提交任务发布
3. 在运维中心停止任务，再启动任务
4. 重启后自动同步新增表数据（如设定全量同步则执行全量，否则仅增量）
5. 不影响存量表的同步进度

### 分库分表加减数据源/Schema/Table

- 在任务开发界面直接编辑
- 保存→提交→重启任务后生效
- 新增对象如设定全量同步会自动执行全量
- 不影响存量表同步进度

### 优先同步重要表

- 全量同步阶段，对重要表使用"优先执行"操作
- 在资源队列中插队，优先处理该表的全量同步

### 暂停/恢复单表增量同步

- 暂停：对单表执行"停止增量同步"，暂停该表变更消息消费
- 恢复：执行"恢复增量同步"，为保证数据连续性会从源端重新拉取一次全量数据
- 适用场景：源端突发大流量时，暂停不重要表为重要表让出处理资源

### 单表数据修复

| 操作 | 说明 | 写入方式 |
|------|------|---------|
| 重新同步 | 重新同步源端表全量数据 | 同步到临时表 → insert overwrite 写入目标表 |
| 补数同步 | 按过滤条件从源端拉取部分/全部数据 | 同步到临时表 → delete 目标表相关数据 → merge into 写入 |

## 监控告警配置

### 推荐告警规则

建议配置以下 5 种告警规则，全方位监控任务健康度：

| 告警类型 | 监控事项 | 说明 |
|---------|---------|------|
| 任务 Failover | 多表实时同步作业 failover | 监控任务运行稳定性 |
| 任务停止 | 多表实时同步任务运行失败 | 任务异常停止告警 |
| 单表异常 | 多表实时同步任务目标表变更失败 | Schema Evolution 失败、单字段超 10M 限制等 |
| 端到端延迟 | 多表实时同步延迟 | 数据从源端到目标端的时间间隔 |
| 读取位点延迟 | 多表实时同步读取点位延迟 | 读取位点与源端最新位点的差距 |

每种告警可额外增加过滤属性（工作空间、任务名称等），不增加过滤则默认监控实例下所有多表实时任务。

### IM 告警机器人配置

1. 在飞书/企业微信中配置群机器人，获取 webhook 地址
2. 在产品中新增 webhook 配置，渠道选择飞书/企业微信，填写 webhook 地址
3. 在通知策略中启用 webhook
4. 在监控规则中选择启用了 webhook 的通知策略

## 示例

### 示例 1：MySQL 整库实时同步到 Lakehouse

用户说："把 MySQL 的 ecommerce 数据库整库实时同步到 Lakehouse"

操作：
1. 源端准备：确认 MySQL 已开启 Binlog（`binlog_format=ROW`），创建同步账号并授权 REPLICATION SLAVE、SELECT
2. `list_data_sources` 找到 MySQL 数据源（ds_type=5）和 Lakehouse 数据源
3. `create_task(task_type=281, task_name="realtime_sync_ecommerce")` → 获取 studio_url
4. 在 Studio UI 中：选择整库镜像 → 选择 ecommerce 数据库 → 配置目标 workspace → sync_mode 选全量+增量
5. `publish_task(...)` 提交，任务立即开始全量初始化，完成后自动切换增量 CDC

### 示例 2：分库分表合并同步

用户说："我有 order_0、order_1、order_2 三张分表，要合并同步到一张 orders 表"

操作：
1. `create_task(task_type=281, task_name="sync_sharding_orders")`
2. 在 Studio UI 中：选择多表合并 → 选择 order_0/order_1/order_2 → 目标表设为 orders → 配置扩展字段（如 `__source_table__`）区分来源
3. `publish_task(...)` 提交

## 故障排除

### 快速排查表

| 问题 | 排查方向 |
|------|---------|
| 任务创建失败 | 检查是否有可用 Sync VCluster |
| 源端连接失败 | 检查数据源配置、网络可达性、账号权限 |
| Binlog 读取失败 | 确认 MySQL `log_bin=ON`、`binlog_format=ROW`、`binlog_row_image=FULL` |
| WAL 读取失败 | 确认 PostgreSQL `wal_level=logical`，slot 未被其他任务占用 |
| Slot 启动冲突 | 不同任务不要复用同一个 slot，检查是否有其他运行中任务占用 |
| 全量同步慢 | 调整最大并发数，检查源端数据库负载，调大内存参数 |
| 增量延迟增大 | 检查 Sync VCluster 资源、源端数据量是否突增 |
| Schema Evolution 异常 | 通过"查看异常"操作查看详情，注意不支持变更字段类型 |
| 分库分表主键冲突 | 开启扩展字段并设为联合主键 |

### 增量同步失败

#### Binlog 位点过期

- 现象：报错 `The connector is trying to read binlog starting at ... but this is no longer available on the server`
- 原因：指定的 binlog 文件已被 MySQL 定期回收清理，或任务停止时间过长导致位点过期
- 解决：
  1. 在源端执行 `SHOW MASTER STATUS` 查询当前最新 binlog 文件和位点
  2. 使用最新的 file 和 position 重启同步任务（选择"自定义起始位置"）
  3. 如需补回丢失数据，对相应表执行"重新同步"

#### Server-id 冲突

- 现象：报错 `A slave with the same server_uuid/server_id as this slave has connected to the master`
- 原因：任务分配的 server-id（范围 5400-6400）与同一数据库上的其他同步工具/任务冲突
- 解决：检查同一数据库实例下是否有其他同步任务或工具正在同步 binlog，重启同步任务

#### 数据源时区配置错误

- 现象：报错 `The MySQL server has a timezone offset ... which does not match the configured timezone`
- 原因：数据源中配置的时区（默认 Asia/Shanghai）与数据库实际时区不一致
- 解决：确认数据库配置的时区，修改数据源中的时区配置

#### Binlog 事件 size 超限

- 现象：报错 `log event entry exceeded max_allowed_packet`
- 原因：数据库 `max_allowed_packet` 小于 Binlog 中某个事件的 size，或 binlog 文件损坏
- 解决：
  1. 联系 DBA 调大 `max_allowed_packet`（上限 1G），生效后重新同步
  2. 如调整后仍失败（binlog 可能损坏），重启任务选择更新的位点跳过问题位点
  3. 对可能缺少数据的表执行"重新同步"补全

### 全量同步失败

#### PK 长度超限

- 现象：报错 `Encoded key size 191 exceeds max size 128`
- 原因：源表主键字段总长度超过 128 字节，或多表合并场景中扩展字段联合主键过长
- 解决：在同步任务配置中增加参数调大 PK 长度限制

### 同步任务 Failover

#### 与 Lakehouse Ingestion Service 断连

- 现象：Failover 详情中包含 `Async commit for instance ... failed. rpcProxy call hit final failed after max retry reached`
- 原因：通常发生在 Lakehouse 服务端升级期间，连接中断
- 解决：
  1. 服务升级完成后任务通常自动恢复
  2. 如持续 Failover，手动重启任务
  3. 如仍无法恢复，检查 Lakehouse Ingestion Service 健康状态

#### Binlog 事件反序列化失败

- 现象：Failover 详情中包含 `Failed to deserialize data of EventHeaderV4`
- 原因：源端 binlog 突发大量事件（大量更新/批量删除），写入端反压导致读取端停止消费，binlog client 连接超时中断
- 解决：
  1. 短时间流量增长：任务通常在有限 Failover 次数内自动恢复
  2. 持续出现：调大 MySQL 参数 `slave_net_timeout` 和 `thread_pool_idle_timeout`
  3. 临时调整（重启失效）：`SET GLOBAL slave_net_timeout = 120; SET GLOBAL thread_pool_idle_timeout = 120;`
  4. 永久调整：修改 MySQL 配置文件

### 表进入黑名单

#### Schema Evolution 失败

- 现象：表状态自动变为停止同步，提示 `pk column different`、`pk column type mismatch`、`invalid modify column`
- 原因：源端表结构发生 Lakehouse 不支持的变更（PK 字段列表变更、PK 字段类型变更、字段类型不兼容修改）
- 解决：
  1. 检查源端表结构，修改为正确的结构
  2. 对停止同步的表执行"重新同步"，全量同步完成后增量数据会继续同步

## 已知局限

- Schema Evolution 暂不支持变更字段类型、不支持自动新增表
- 仅支持带主键（PK）字段的表，非 PK 表不支持同步
- 源端不同库表中若存在主键相同的数据，同步结果会异常
- 无特别必要不要手动创建/修改/删除目标表（系统自动管理目标表结构）
- MySQL 不支持的字段类型：`year`（取值不对应）
- PostgreSQL 不支持的字段类型：`varbit`、`bytea`、`TIMETZ`、`interval`、`NAME`（取值不对应），`NUMERIC`、`decimal`（精度不对应，目标端精度更高）
