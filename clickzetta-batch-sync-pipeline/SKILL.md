---
name: clickzetta-batch-sync-pipeline
description: |
  创建和管理 ClickZetta Lakehouse 离线同步（批量同步）任务，支持单表离线同步和多表离线同步两种模式。
  单表模式适合简单的源→目标表同步；多表模式支持整库镜像、多表镜像、多表合并三种同步方式。
  当用户说"离线同步"、"批量同步"、"batch sync"、"数据库同步到 Lakehouse"、"整库迁移"、
  "多表同步"、"定期同步"、"周期性数据同步"、"分库分表合并"、"离线数据迁移"时触发。
  包含单表/多表离线同步任务创建、数据源配置、字段映射、同步规则、调度部署、任务运维等
  ClickZetta Studio 特有逻辑。
---

# 离线同步（批量同步）Pipeline 工作流

## 适用场景

- 将外部数据库（MySQL / PostgreSQL / SQL Server 等）的数据定期同步到 Lakehouse
- 单表离线同步：简单的源表 → 目标表周期性同步
- 多表离线同步：整库迁移、多表批量同步、分库分表合并
- 数据时效性要求不高，按天/小时等周期批量更新
- 需要通过 Studio 调度系统进行周期性自动执行
- 关键词：离线同步、批量同步、整库迁移、多表同步、定期同步、batch sync

## 前置依赖

- ClickZetta Lakehouse Studio 账户，具备创建同步任务、目标表的权限
- 源端数据源已在 Studio 中配置（具备 SELECT 权限）
- 目标端 Lakehouse 数据源可用（具备 CREATE、INSERT 权限）
- clickzetta-studio-mcp 工具可用（`create_task`、`save_integration_task`、`save_task_configuration`、`publish_task`、`list_data_sources` 等）

## 模式选择指引

| 维度 | 单表离线同步 | 多表离线同步 |
|------|------------|------------|
| 任务类型 ID | `10`（离线同步） | `291`（多表离线同步） |
| 同步粒度 | 单张源表 → 单张目标表 | 整库 / 多表 → 多张目标表 |
| 适用场景 | 简单同步、精细控制单表 | 整库迁移、批量同步、分库分表合并 |
| 字段映射 | 手动拖拽调整 | 自动识别 + 批量配置 |
| Schema Evolution | 不支持 | 支持（新增字段自动适配） |
| 自动建表 | 需手动创建目标表或快速创建 | 目标表不存在时自动创建 |
| 写入模式 | 由数据源决定 | overwrite / upsert 可选 |

## 多表离线同步支持的数据源

**来源端**：MySQL、PostgreSQL、SQL Server、Aurora MySQL、Aurora PostgreSQL、PolarDB MySQL、PolarDB PostgreSQL

**目标端**：Lakehouse

## 工作流

### 模式 A：单表离线同步

#### 步骤 1：查找可用数据源

```
使用 list_data_sources 查看已配置的数据源列表。
如需按类型过滤，指定 ds_type 参数（5=MySQL, 7=PostgreSQL, 8=SQL Server）。
记录源端 datasource_name 和目标端 datasource_name。
```

#### 步骤 2：创建离线同步任务

```
使用 create_task 创建任务：
- task_type: 10（离线同步）
- task_name: 自定义任务名称
- data_folder_id: 目标文件夹 ID（可通过 list_folders 获取）
```

#### 步骤 3：配置同步内容

```
使用 save_integration_task 配置同步：
- task_id: 步骤 2 返回的任务 ID
- source_datasource_name: 源端数据源名称
- source_schema: 源端数据库/Schema
- source_table: 源端表名
- source_ds_type: 源端类型（5=MySQL, 7=PostgreSQL, 8=SQL Server 等）
- sink_datasource_name: 目标 Lakehouse 数据源名称
- sink_schema: 目标 Schema（默认 public）
- sink_table: 目标表名（可选，默认与源表同名）
- sink_ds_type: 1（Lakehouse）
```

> **说明**：系统会自动获取源表和目标表的元数据，生成字段映射。如目标表不存在，会自动创建。

#### 步骤 4：配置调度并部署

```
使用 save_task_configuration 配置调度：
- task_id: 任务 ID
- cron_express: Cron 表达式（如 '0 0 2 * * ? *' 表示每天凌晨 2 点）
- schedule_start_time: 调度开始时间（如 '02:00'）

注意：离线同步任务（task_type=10）需要 Sync VCluster。
工具会自动检查并分配可用的 Sync VCluster。如无可用 Sync VCluster，需先创建。
```

#### 步骤 5：提交任务

```
使用 publish_task 提交任务到调度系统：
- task_id: 任务 ID
- task_version: 当前版本号（通过 get_task_detail 获取）
```

#### 步骤 6：验证与监控

```
使用 get_task_detail 查看任务详情和状态。
使用 list_task_run 查看任务执行记录。
如执行失败，使用 list_executions + get_execution_log 查看日志排查问题。
```

---

### 模式 B：多表离线同步

#### 三种同步方式

| 方式 | 说明 | 适用场景 |
|------|------|---------|
| 整库镜像 | 同步源端整个数据库的所有表 | 整库迁移 |
| 多表镜像 | 选择多张表分别同步，保持表结构独立 | 按需选择部分表 |
| 多表合并 | 多个源表合并到一张或多张目标表 | 分库分表合并 |

#### 步骤 1：创建多表离线同步任务

```
使用 create_task 创建任务：
- task_type: 291（多表离线同步）
- task_name: 自定义任务名称
- data_folder_id: 目标文件夹 ID
```

#### 步骤 2：在 Studio UI 中配置同步

> **重要**：多表离线同步的详细配置（来源数据选择、目标设置、映射关系、同步规则等）
> 目前需要在 Studio Web UI 中完成。create_task 返回的 studio_url 可直接打开配置页面。

配置要点：

**来源数据配置**
- 选择源端数据源类型和数据源连接
- 根据同步方式选择：整库 / 勾选多表 / 配置合并规则

**目标设置**
- 选择目标 Lakehouse 数据源和 workspace
- 配置命名空间规则：镜像来源 / 指定选择 / 自定义（支持 `{SOURCE_DATABASE}` 变量）
- 配置目标表命名规则：镜像来源 / 自定义（支持 `{SOURCE_DATABASE}`、`{SOURCE_SCHEMA}`、`{SOURCE_TABLE}` 变量）
- 可选：配置分区（分区字段 + 分区值表达式）

**同步规则**
- Schema Evolution：源端删除字段 → 写入 Null；源端新增字段 → 自动适配；源端删除表 → 忽略
- 分组策略：智能分组（自动）或 静态分组（指定单组表数量，默认 4）
- 并发控制：单分组源端最大连接数（默认 4）、并发执行分组数（默认 2）
- 写入模式：非主键表 → overwrite；主键表 → overwrite 或 upsert

#### 步骤 3：调试运行

在 Studio UI 中点击「运行」按钮进行调试，验证数据源连接和配置是否正确。
在「运行历史」中查看运行详情。

#### 步骤 4：配置调度

```
使用 save_task_configuration 配置调度：
- task_id: 任务 ID
- cron_express: Cron 表达式
- schedule_start_time: 调度开始时间

同样需要 Sync VCluster（task_type=291 属于离线同步类型）。
```

#### 步骤 5：提交任务

```
使用 publish_task 提交任务：
- task_id: 任务 ID
- task_version: 当前版本号
```

#### 步骤 6：任务运维

```
多表离线同步任务在「任务运维」→「周期任务」中管理。

查看任务详情：get_task_detail
查看执行记录：list_task_run
查看执行日志：list_executions + get_execution_log

Studio UI 中可查看：
- 任务详情 Tab：上下游 DAG、配置信息
- 任务实例 Tab：实例列表、每张表的读取/写入行数和同步速率
- 同步对象 Tab：所有源表和目标表的映射关系
- 操作日志 Tab：运维操作审计
```

---

## 任务运维操作

### 常用操作

| 操作 | 说明 |
|------|------|
| 暂停/恢复 | 暂停或恢复周期调度 |
| 下线 | 停止任务并从调度系统移除，回退到未提交状态 |
| 下线（含下游） | 将当前任务及下游任务一并下线（有下游依赖时不允许单独下线） |
| 补数据 | 对历史周期进行数据补录 |
| 编辑 | 跳转到开发界面修改配置 |

### 实例操作（多表离线同步）

| 操作 | 说明 |
|------|------|
| 重跑（全部对象） | 重新同步所有表 |
| 重跑（仅失败对象） | 只重跑同步失败的表 |
| 置成功/置失败 | 手动设置实例最终状态 |
| 取消运行 | 强制终止正在运行的实例 |
| 单表重新同步 | 在同步对象 Tab 中对单张表重新同步 |
| 单表强制停止 | 终止单张表的同步 |

---

## 示例

### 示例 1：MySQL 单表每日同步

用户说："把 MySQL 的 orders 表每天凌晨 2 点同步到 Lakehouse"

操作：
1. `list_data_sources` 找到 MySQL 数据源名称（如 `mysql_prod`）和 Lakehouse 数据源名称
2. `create_task(task_type=10, task_name="sync_orders_daily")`
3. `save_integration_task(source_datasource_name="mysql_prod", source_table="orders", sink_schema="public", sink_table="orders")`
4. `save_task_configuration(cron_express="0 0 2 * * ? *", schedule_start_time="02:00")`
5. `publish_task(task_id=..., task_version=...)`

### 示例 2：MySQL 整库迁移到 Lakehouse

用户说："把 MySQL 的 ecommerce 数据库整库同步到 Lakehouse"

操作：
1. `create_task(task_type=291, task_name="sync_ecommerce_db")` → 获取 studio_url
2. 在 Studio UI 中：选择整库镜像 → 选择 ecommerce 数据库 → 配置目标 workspace → 写入模式选 upsert（主键表）
3. 点击「运行」调试验证
4. `save_task_configuration(cron_express="0 0 1 * * ? *")` 配置每日凌晨 1 点调度
5. `publish_task(...)` 提交

## 故障排除

| 问题 | 排查方向 |
|------|---------|
| 任务创建失败 | 检查是否有可用的 Sync VCluster（`LH_show_object_list` 查看 VCLUSTERS） |
| 源端连接失败 | 检查数据源配置中的连接信息、网络可达性、账号权限 |
| 字段映射失败 | 检查源表和目标表的字段类型兼容性 |
| 同步速度慢 | 调整并发数（最大 10）和同步速率；检查源端数据库负载 |
| Schema Evolution 失败 | 不支持修改主键字段；字段类型仅支持同类型扩展（int8→int16→int32→int64）；不支持跨类型转换 |
| 多表同步部分表失败 | 在实例详情的「同步对象」Tab 查看各表状态；可对失败表单独重跑 |
| upsert 模式数据不一致 | 确认目标表有正确的主键定义；检查源端数据是否有主键冲突 |

## 注意事项

### 权限要求

- 源端：数据源配置的账号需具备 SELECT 权限（读取元数据和表数据）
- 目标端：任务负责人需具备 CREATE 和 INSERT 权限

### 性能考虑

- 合理配置并发度，避免对源端数据库造成过大压力
- 首次执行需初始化所有同步对象，可能耗时较长
- 单个多表同步任务的表数量控制在合理范围，过多表影响执行效率
- 选择源端数据库压力较小的时间窗口执行调度

### 数据一致性

- overwrite 模式：每次执行完全刷新目标表数据
- upsert 模式：基于主键进行增量更新
- 两次同步间隔期间的数据变化会在下次同步时体现

### Schema Evolution 限制（多表离线同步）

- 不支持修改主键字段（Lakehouse 主键表限制）
- 字段类型修改仅支持同类型扩展（int8 → int16 → int32 → int64）
- 不支持跨类型转换（如 int → double）
- 建议在源端 Schema 相对稳定时启用

### Sync VCluster 要求

- 离线同步任务（task_type=10 和 291）必须使用 Sync VCluster
- 创建/调度任务前需确认有可用的 Sync VCluster
- 可通过 `LH_show_object_list`（object_type='VCLUSTERS'）查看，筛选 vcluster_type 包含 SYNC 的集群
