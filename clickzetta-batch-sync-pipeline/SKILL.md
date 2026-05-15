---
name: clickzetta-batch-sync-pipeline
description: |
  创建和管理 ClickZetta Lakehouse 离线同步（批量同步）任务，支持单表离线同步和多表离线同步两种模式。
  单表模式适合简单的源→目标表同步；多表模式支持整库镜像、多表镜像、多表合并三种同步方式。
  当用户说"离线同步"、"批量同步"、"batch sync"、"数据库同步到 Lakehouse"、"整库迁移"、
  "多表同步"、"定期同步"、"周期性数据同步"、"分库分表合并"、"离线数据迁移"时触发。
  包含单表/多表离线同步任务创建、数据源配置、字段映射、同步规则、调度部署、任务运维等
  ClickZetta Studio 特有逻辑。
  Keywords: batch sync, offline sync, full load, mirror, multi-table sync
---

# 离线同步（批量同步）Pipeline 工作流

## 向导：收集必要信息

开始创建同步任务前，先收集以下信息（一次性问完）：

> 为了创建离线同步任务，需要确认：
>
> **1. 数据源**：源端数据库类型和名称是什么？（如 MySQL `aliyun_mysql`）
> **2. 同步范围**：
>    - 单表（指定表名）
>    - 多表镜像（整库或指定多张表）
>    - 分库分表合并（多张源表合并到一张目标表）
> **3. 目标**：同步到 Lakehouse 的哪个 schema？（如 `ods`）
> **4. 调度频率**：每天几点执行？（如每天凌晨 02:00）
> **5. 写入模式**：全量覆盖（OVERWRITE）还是增量追加（APPEND）？

**如果用户已经提供了足够信息，直接进入工作流，不再重复询问。**

---

## 前置依赖

- ClickZetta Lakehouse Studio 账户，具备创建同步任务、目标表的权限
- 源端数据源已在 Studio 中配置（具备 SELECT 权限）
- 目标端 Lakehouse 数据源可用（具备 CREATE、INSERT 权限）
- 已安装 cz-cli 并完成 profile 配置（`cz-cli profile status` 验证连接）

---

## 适用场景

- 将外部数据库（MySQL / PostgreSQL / SQL Server 等）的数据定期同步到 Lakehouse
- 单表离线同步：简单的源表 → 目标表周期性同步
- 多表离线同步：整库迁移、多表批量同步、分库分表合并
- 数据时效性要求不高，按天/小时等周期批量更新

---

## 模式选择

| 维度 | 单表离线同步 | 多表离线同步 |
|------|------------|------------|
| 任务类型 ID | `1`（DI/INTEGRATION） | `291`（MULTI_DI） |
| 同步粒度 | 单张源表 → 单张目标表 | 整库 / 多表 → 多张目标表 |
| 适用场景 | 简单同步、精细控制单表 | 整库迁移、批量同步、分库分表合并 |
| Schema Evolution | 不支持 | 支持（新增字段自动适配） |
| 自动建表 | 需手动创建或快速创建 | 目标表不存在时自动创建 |
| 写入模式 | 由数据源决定 | overwrite / upsert 可选 |

> **重要**：这两种任务类型均为 UI_ONLY 类型，脚本内容必须在 Studio Web UI 中配置。
> cz-cli 负责任务创建、调度配置、发布和运维；数据源选择、字段映射等内容配置在 Studio UI 完成。

---

## 工作流

> **重要**：离线同步任务的**内容配置**（来源表选择、字段映射、同步规则等）必须在 Studio Web UI 中完成。
> cz-cli 负责任务创建、调度配置、发布和运维；数据源选择、字段映射等内容配置在 Studio UI 完成。

### 步骤 1：用 cz-cli 创建任务

```bash
# 单表离线同步（task_type=1，即 DI/INTEGRATION）
cz-cli task create "sync_orders_daily" --type DI --folder <folder_name>

# 多表离线同步（task_type=291，即 MULTI_DI）
cz-cli task create "sync_ecommerce_db" --type MULTI_DI --folder <folder_name>
```

命令返回 `task_id` 和 `studio_url`，在 `studio_url` 中完成数据源配置。

### 步骤 2：在 Studio UI 中配置同步内容

打开步骤 1 返回的 `studio_url`，在 Studio 中完成：

**来源数据配置**
- 选择源端数据源类型和连接（支持的数据源类型以 Studio UI 中显示为准，可通过 `cz-cli datasource list` 查看已配置的数据源）
- 单表：指定 schema 和表名
- 多表：选择整库 / 勾选多表 / 配置合并规则

**目标设置**
- 选择目标 Lakehouse 数据源和 workspace
- 配置目标 schema 和表名
- 多表模式可配置命名规则（支持 `{SOURCE_DATABASE}`、`{SOURCE_TABLE}` 变量）

**同步规则（多表模式）**
- Schema Evolution：源端新增字段自动适配；删除字段写入 Null
- 写入模式：非主键表 → overwrite；主键表 → overwrite 或 upsert

### 步骤 3：在 Studio UI 中调试运行

点击「运行」按钮进行调试，验证数据源连接和配置是否正确。

### 步骤 4：用 cz-cli 配置调度和发布

```bash
# 配置调度（具体参数见 --help）
cz-cli task save-cron <task_name> --help

# 发布任务
cz-cli task deploy <task_name> -y
```

> 离线同步任务（task_type=1 和 291）必须使用 Sync VCluster，不能使用通用型或分析型 VCluster。

### 步骤 5：验证与监控

```bash
cz-cli runs list --task <task_name>      # 查看运行记录
cz-cli runs detail <run_id>              # 查看运行详情
cz-cli attempts log <run_id>             # 查看执行日志
cz-cli runs refill <task_name> --help    # 补数据（--help 查看参数）
```

---

## 任务运维操作

| 操作 | cz-cli 命令 | 说明 |
|------|------------|------|
| 下线 | `cz-cli task undeploy <task> -y` | 停止任务并从调度系统移除（不可逆） |
| 补数据 | `cz-cli runs refill <task> --from D --to D -y` | 对历史周期进行数据补录 |
| 查看依赖 | `cz-cli runs deps <task>` | 查看已发布的上下游依赖 |
| 查看运行 | `cz-cli runs list --task <task>` | 查看运行实例列表 |

多表离线同步任务在 Studio「任务运维」→「周期任务」中管理，可查看：
- 任务实例 Tab：每张表的读取/写入行数和同步速率
- 同步对象 Tab：所有源表和目标表的映射关系

---

## 交付验收 Checklist

同步任务发布运行后，**必须逐项验证**：

```sql
-- 1. 行数比对：目标表行数与源端一致
SELECT COUNT(*) FROM <ods_schema>.<table>;
-- 与源端 MySQL/PG 执行 SELECT COUNT(*) FROM <table> 对比

-- 2. 关键字段非空率
SELECT
  COUNT(*) AS total,
  COUNT(key_field) AS non_null,
  ROUND(COUNT(key_field) * 100.0 / COUNT(*), 2) AS non_null_pct
FROM <ods_schema>.<table>;
```

**验收标准：**
- [ ] 目标表行数与源端一致
- [ ] 关键字段非空率符合预期
- [ ] 同步任务最近运行状态为 SUCCESS
- [ ] 字段类型映射正确（重点检查 BIT/ENUM/TEXT 等异构类型）
- [ ] 调度 Cron 配置正确，下次执行时间符合预期

---

## 故障排除

| 问题 | 排查方向 |
|------|---------|
| 任务创建失败 | 确认账号有创建任务权限；检查文件夹 ID 是否存在 |
| 源端连接失败 | 检查数据源配置中的连接信息、网络可达性、账号权限 |
| 字段映射失败 | 检查源表和目标表的字段类型兼容性 |
| 同步速度慢 | 调整并发数（最大 10）和同步速率；检查源端数据库负载 |
| Schema Evolution 失败 | 不支持修改主键字段；字段类型仅支持同类型扩展（int8→int16→int32→int64） |
| 多表同步部分表失败 | 在实例详情的「同步对象」Tab 查看各表状态；可对失败表单独重跑 |
| upsert 模式数据不一致 | 确认目标表有正确的主键定义；检查源端数据是否有主键冲突 |
| VCluster 类型错误 | 离线同步必须使用 Sync VCluster，通过 `SHOW VCLUSTERS` 确认类型 |

---

## 注意事项

**权限要求**
- 源端：数据源配置的账号需具备 SELECT 权限
- 目标端：任务负责人需具备 CREATE 和 INSERT 权限

**性能考虑**
- 合理配置并发度，避免对源端数据库造成过大压力
- 首次执行需初始化所有同步对象，可能耗时较长
- 选择源端数据库压力较小的时间窗口执行调度

**Schema Evolution 限制（多表离线同步）**
- 不支持修改主键字段（Lakehouse 主键表限制）
- 字段类型修改仅支持同类型扩展（int8 → int16 → int32 → int64）
- 不支持跨类型转换（如 int → double）

**支持的数据源**
- 来源端：关系型数据库（MySQL、PostgreSQL、SQL Server 等）及其云变体（Aurora、PolarDB 等），具体支持列表以 Studio UI 中显示为准，可通过 `cz-cli datasource list` 查看已配置的数据源
- 目标端：Lakehouse

