---
name: clickzetta-studio-task-manager
description: |
  管理 ClickZetta Lakehouse Studio 任务，覆盖任务目录组织、任务类型区分、cz-cli task 命令族、
  调度配置、依赖管理和常见问题排查。实现"建管分离"工程规范：DDL 任务草稿化、ETL 任务调度化、
  Dynamic Table 自动刷新化。
  当用户说"创建 Studio 任务"、"任务目录"、"任务调度"、"cz-cli task"、"任务依赖"、
  "任务失败"、"任务状态"、"整库同步任务"、"ETL 任务编排"、"任务管理"、
  "建管分离"、"DDL 任务"、"调度 DAG"、"任务文件夹"、"Studio 任务"时触发。
  Keywords: Studio task, task management, cz-cli task, scheduling, DAG, DDL draft, ETL pipeline, task folder
---

# ClickZetta Studio 任务管理

## 向导：明确操作意图

收到任务管理请求后，先判断用户意图，选择对应工作流：

> 你想做什么？
>
> **A. 从零搭建新管道的任务体系**（创建目录、DDL 任务、同步任务、ETL 任务）
> **B. 管理现有任务**（查看状态、修改配置、配置依赖、重跑、补数据）
> **C. 排查任务问题**（失败诊断、依赖检查、日志分析）→ 加载 `clickzetta-pipeline-review` skill，它提供完整的五阶段诊断流程
> **D. 规范检查**（检查现有任务是否符合建管分离规范）

**如果用户已经明确说了要做什么（如"帮我创建一个 ETL 任务"、"查看任务 xxx 的运行日志"），直接执行，不再询问。**

对于 **A（从零搭建）**，还需要确认：
- 业务域/项目名称（用于任务目录命名，如 `ecommerce_dw`）
- 数据源类型（MySQL/PG/Kafka/OSS 等）
- 分层结构（ODS/DWD/DWS/ADS 还是 Bronze/Silver/Gold）

---

## 核心原则：建管分离

**不同类型的任务，调度策略完全不同。** 混淆任务类型是最常见的工程错误。

| 任务类型 | 典型内容 | 调度配置 | 状态 |
|---|---|---|---|
| **DDL 建表任务** | CREATE TABLE / CREATE SCHEMA | ❌ 禁止 Cron，禁止依赖 | DRAFT |
| **数据同步任务** | MySQL→ODS 整库/单表同步 | ✅ 配置 Cron | PUBLISHED |
| **ETL 转换任务** | ODS→DWD 清洗 SQL | ✅ 配置 Cron + 依赖上游同步 | PUBLISHED |
| **数据质量任务** | 行数检查、NULL 率验证 | ✅ 配置 Cron + 依赖 ETL | PUBLISHED |
| **DWS/ADS 聚合层** | 指标汇总、报表宽表 | ❌ 使用 Dynamic Table，不建任务 | — |

> ⚠️ **DDL 任务绝对不能配 Cron**：建表语句重复执行会引发 `SCHEDULE_TASK_HAD_CHILDREN_NODES_EXCEPTION` 等调度冲突。DDL 任务执行完成后立即降级为 DRAFT。

> ⚠️ **DWS/ADS 层不要建调度任务**：Dynamic Table 系统自动刷新，额外建任务是冗余计算，浪费资源。

---

## 任务目录组织规范

每个数仓项目在 Studio 中创建独立任务目录，统一管理所有任务资产：

```
<业务域>_dw/                              ← 项目任务目录（如 shenyu_gateway_dw、ecommerce_dw）
├── 00_sync_<source>_to_ods               ← 数据同步（Cron，最早执行）
├── 01_ddl_ods                            ← ODS 建表（DRAFT，不调度，手动执行一次）
├── 02_ddl_dwd                            ← DWD 建表（DRAFT，不调度，手动执行一次）
├── 03_ddl_dws_ads                        ← DWS/ADS 动态表建表（DRAFT，不调度）
├── 04_transform_ods_to_dwd               ← ODS→DWD 清洗（Cron，依赖 00）
└── 05_dqc_check                          ← 数据质量检查（Cron，依赖 04，可选）
```

> DWS/ADS 层由 Dynamic Table 自动刷新，**无需创建任务**。

---

## cz-cli task 命令族

### 任务目录管理

```bash
# 创建任务目录
cz-cli task folder create <folder_name>

# 列出所有任务目录
cz-cli task folder list
```

### 任务查询

```bash
# 列出所有任务
cz-cli task list

# 按目录过滤
cz-cli task list --folder <folder_name>

# 查看任务详情
cz-cli task get <task_id>

# 查看任务状态
cz-cli task status <task_id>
```

### 任务执行

```bash
# 手动触发任务运行
cz-cli task run <task_id>

# 查看任务运行日志
cz-cli task logs <task_id>

# 查看最近一次运行实例
cz-cli task instances <task_id> --limit 5
```

### 任务创建

```bash
# 创建 SQL 任务（ETL/DDL）
cz-cli task create \
  --name "04_transform_ods_to_dwd" \
  --type SQL \
  --folder <folder_name> \
  --vcluster default \
  --sql-file ./transform.sql

# 创建数据同步任务（单表）
cz-cli task create \
  --name "00_sync_mysql_to_ods" \
  --type SINGLE_DI \
  --folder <folder_name>
```

> ⚠️ **整库同步任务（MULTI_DI）的能力边界**：`cz-cli` 可以创建任务框架，但源端/目标端字段映射配置**必须在 Studio UI 中手动完成**。推荐 SOP：
> 1. `cz-cli task create --type MULTI_DI` 创建任务框架
> 2. 复制输出的任务链接，在浏览器中打开
> 3. 在 Studio UI 中配置源端数据库、目标端 Schema、字段映射
> 4. 点击发布运行

---

## 调度配置最佳实践

### Cron 表达式参考

```
# 每天 02:00 执行（数据同步）
0 2 * * *

# 每天 02:30 执行（ETL 转换，同步完成后 30 分钟）
30 2 * * *

# 每天 03:00 执行（数据质量检查）
0 3 * * *

# 每小时执行
0 * * * *
```

### 依赖配置原则

```
正确的依赖链：
00_sync（Cron 02:00）
    ↓ 依赖
04_transform（Cron 02:30）
    ↓ 依赖
05_dqc（Cron 03:00）

错误的依赖：
❌ DDL 任务（01/02/03）不应出现在依赖链中
❌ Dynamic Table 不应出现在依赖链中
```

---

## 数据同步任务类型选择

| 场景 | 任务类型 | 说明 |
|---|---|---|
| MySQL/PG 单表同步到 Lakehouse | `SINGLE_DI` | 简单，CLI 可完全配置 |
| MySQL/PG 整库同步（多表镜像） | `MULTI_DI` | CLI 创建框架，UI 配置映射 |
| Kafka 实时接入 | `REALTIME_SYNC` | 持续运行，无需 Cron |
| 文件批量导入（OSS/S3） | SQL 任务（COPY INTO） | 用 SQL 任务执行 COPY INTO |

---

## 常见问题排查

| 问题 | 原因 | 解决方案 |
|---|---|---|
| `SCHEDULE_TASK_HAD_CHILDREN_NODES_EXCEPTION` | DDL 任务被配置了 Cron 或依赖 | 清除 DDL 任务的调度配置，降级为 DRAFT |
| 任务发布失败，提示循环依赖 | 任务 A 依赖 B，B 又依赖 A | 检查依赖链，去除环形依赖 |
| 同步任务一直失败，无明确报错 | 字段类型不兼容（如 MySQL BIT(1) vs Lakehouse BOOLEAN） | 检查字段类型映射，参考下方类型映射表 |
| 整库同步任务创建后无法运行 | MULTI_DI 任务缺少字段映射配置 | 进入 Studio UI 配置源端/目标端映射后重新发布 |
| ETL 任务未按时触发 | 上游同步任务失败，依赖未满足 | 先修复上游同步任务，再手动触发 ETL |
| DWS 层数据未更新 | 误建了调度任务但 Dynamic Table 未刷新 | 删除冗余调度任务，确认 Dynamic Table 状态为 RUNNING |
| 任务运行成功但数据为空 | SQL 逻辑问题（如 LEFT JOIN 过滤条件位置错误） | 检查 SQL，LEFT JOIN 右表过滤条件必须在 ON 子句 |

### MySQL → Lakehouse 字段类型映射（同步任务常见踩坑）

| MySQL 类型 | ❌ 不要用 | ✅ ODS 层用 | DWD 层转换 |
|---|---|---|---|
| `BIT(1)` | `BOOLEAN` | `TINYINT` | `CAST(col AS BOOLEAN)` |
| `DATETIME` | `DATETIME` | `TIMESTAMP` | 直接用 |
| `ENUM('a','b')` | `ENUM` | `STRING` | 直接用 |
| `TEXT` / `LONGTEXT` | `TEXT` | `STRING` | 直接用 |
| `DECIMAL(p,s)` | `FLOAT` | `DECIMAL(p,s)` | 直接用 |
| `TINYINT(1)` | `BOOLEAN` | `TINYINT` | `CAST(col AS BOOLEAN)` |

> **ODS 层原则：宽泛类型优先**，同步成功后在 DWD 层做精确类型转换，避免同步阶段因类型不兼容失败。

---

## 完整工程化 SOP

### 新项目启动流程

```
1. 创建任务目录
   cz-cli task folder create <业务域>_dw

2. 创建 DDL 任务（DRAFT，不配调度）
   - 01_ddl_ods：建 ODS 层表
   - 02_ddl_dwd：建 DWD 层表
   - 03_ddl_dws_ads：建 DWS/ADS Dynamic Table（含首次 REFRESH）

3. 手动执行 DDL 任务（一次性）
   cz-cli task run <ddl_task_id>

4. 创建数据同步任务（配 Cron）
   - 00_sync：整库或单表同步到 ODS
   - MULTI_DI 类型需进 UI 配置映射

5. 创建 ETL 转换任务（配 Cron + 依赖 00）
   - 04_transform：ODS→DWD 清洗 SQL

6. 可选：创建数据质量任务（配 Cron + 依赖 04）
   - 05_dqc：行数检查、NULL 率验证

7. 验证全链路
   - 手动触发 00_sync，观察同步结果
   - 手动触发 04_transform，验证 DWD 行数
   - 检查 Dynamic Table 刷新历史
```

### 交付验证 Checklist

- [ ] 各层行数与预期一致
- [ ] Dynamic Table 使用的 VCluster 存在且 `status = RUNNING`（`SHOW VCLUSTERS`）
- [ ] Dynamic Table 刷新历史显示 SUCCESS
- [ ] 关键字段 NULL 率在可接受范围
- [ ] LEFT JOIN 结果行数 ≥ 左表行数
- [ ] 所有 DDL 任务为 DRAFT 状态
- [ ] DWS/ADS 层无冗余调度任务
- [ ] 调度 DAG 无循环依赖
