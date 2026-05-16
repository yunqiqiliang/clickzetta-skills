---
name: clickzetta-studio-task-manager
description: |
  管理 ClickZetta Lakehouse Studio 任务，覆盖任务类型说明（离线同步/多表离线同步/实时同步/
  多表实时同步/数据开发）、任务目录组织、任务类型区分、cz-cli task 命令族、
  调度配置、依赖管理和常见问题排查。实现"建管分离"工程规范：DDL 任务草稿化、ETL 任务调度化、
  Dynamic Table 自动刷新化。
  当用户说"创建 Studio 任务"、"任务目录"、"任务调度"、"cz-cli task"、"任务依赖"、
  "任务失败"、"任务状态"、"整库同步任务"、"ETL 任务编排"、"任务管理"、
  "建管分离"、"DDL 任务"、"调度 DAG"、"任务文件夹"、"Studio 任务"、
  "离线同步"、"实时同步"、"多表实时同步"、"数据开发任务"、"任务类型"、
  "选哪种同步"、"同步任务区别"时触发。
  Keywords: Studio task, task management, cz-cli task, scheduling, DAG, DDL draft, ETL pipeline, task folder, offline sync, realtime sync, CDC, task types
---

# ClickZetta Studio 任务管理

## 向导：明确操作意图

收到任务管理请求后，优先使用交互式问答工具（如 `question`）收集意图；若无此类工具，则用文字列出选项：

```
question({
  questions: [{
    question: "你想做什么？",
    options: [
      { label: "从零搭建新管道", description: "创建目录、DDL 任务、同步任务、ETL 任务" },
      { label: "管理现有任务", description: "查看状态、修改配置、配置依赖、重跑、补数" },
      { label: "排查任务问题", description: "失败诊断、依赖检查、日志分析 → 加载 clickzetta-pipeline-review" },
      { label: "规范检查", description: "检查现有任务是否符合建管分离规范" }
    ]
  }]
})
```

**如果用户已经明确说了要做什么，直接执行，不再询问。**

对于**从零搭建**，还需收集：业务域/项目名称、数据源类型、分层结构。

## 数据管道向导（从零搭建时使用）

完整流程：**需求理解 → 数据探索 → 技术选型 → 方案确认 → 执行**

---

### Step 0：需求输入

**优先询问用户是否有需求文档**（PRD、需求说明、数仓设计文档等）：

```
question({
  questions: [{
    question: "开始前，你有需求文档或背景说明吗？",
    options: [
      { label: "有，我来提供", description: "请粘贴文档内容或上传文件，我来提取关键信息" },
      { label: "没有，口头描述", description: "我来引导你回答几个关键问题" }
    ]
  }]
})
```

**如果有文档**：读取文档，自动提取业务场景、数据源、目标产出、时效性要求，跳到 Step 1。

**如果没有文档**，收集以下业务需求（优先使用交互式工具；若无，一次性文字列出）：

```
question({
  questions: [
    {
      question: "这个管道服务于什么业务场景？",
      options: [
        { label: "BI 报表 / 数据看板", description: "固定报表，指标体系明确，T+1 或小时级" },
        { label: "实时监控 / 运营看板", description: "分钟级延迟，关注实时指标" },
        { label: "数据科学 / 特征工程", description: "供模型训练或推理使用" },
        { label: "数据共享 / 对外输出", description: "提供给其他系统或团队使用" }
      ]
    },
    {
      question: "数据消费方是谁？",
      options: [
        { label: "BI 工具（Superset/Tableau 等）", description: "需要宽表或聚合表" },
        { label: "数据分析师（SQL 查询）", description: "需要清洗后的明细表" },
        { label: "下游系统 / API", description: "需要结构化输出" },
        { label: "数据科学家（Python/ZettaPark）", description: "需要特征表或原始明细" }
      ]
    },
    {
      question: "数据时效性要求？",
      options: [
        { label: "T+1（次日可用）", description: "每天凌晨跑批，早上数据就绪" },
        { label: "小时级", description: "每小时更新一次" },
        { label: "分钟级", description: "近实时，延迟 < 10 分钟" },
        { label: "秒级实时", description: "CDC 持续同步，秒级延迟" }
      ]
    }
  ]
})
```

还需口头确认（文字追问，不用菜单）：
- **核心指标口径**：如果涉及 GMV、活跃用户等业务指标，确认计算口径
- **项目/业务域名称**：用于任务目录和 Schema 命名（如 `ecommerce_dw`）

---

### Step 1：数据探索（AI 自主执行，不问用户）

收集到需求后，立即探查数据现状：

```sql
-- 查看相关 schema 和表
SHOW SCHEMAS;
SHOW TABLES IN <相关schema>;

-- 查表大小和行数
SELECT table_schema, table_name,
       ROUND(bytes/1024.0/1024/1024, 2) AS size_gb, row_count
FROM information_schema.tables
WHERE table_type = 'MANAGED_TABLE'
ORDER BY bytes DESC NULLS LAST LIMIT 20;

-- 抽样了解字段含义
SELECT * FROM <schema>.<table> LIMIT 5;
```

同时用 `cz-cli datasource list` 查看已配置的外部数据源。

---

### Step 2：技术选型（选数据源类型和接入方式）

基于需求和数据探索结果，用交互式工具收集技术选型：

**选数据源类型：**
```
question({ questions: [{ question: "数据来自哪里？", options: [
  { label: "外部数据库", description: "MySQL / PostgreSQL / SQL Server / Oracle 等" },
  { label: "Kafka 消息队列", description: "Kafka Topic → Lakehouse" },
  { label: "对象存储", description: "OSS / S3 / COS 文件导入" },
  { label: "Lakehouse 内部 ETL 分层", description: "ODS→DWD→DWS/ADS，SQL 任务 + Dynamic Table" },
  { label: "端到端完整管道", description: "数据接入 + 分层建模 + 聚合" },
  { label: "不确定，先探索数据", description: "先看现有数据再给方案建议" }
]}]})
```

**追问（仅部分选项需要）：**

选了"外部数据库"：
```
question({ questions: [{ question: "同步时效性？", options: [
  { label: "实时同步（秒级）", description: "CDC，基于 Binlog/WALs，持续运行" },
  { label: "离线批量（小时/天级）", description: "周期性全量同步，配置 Cron" }
]}]})
```

选了"对象存储"：
```
question({ questions: [{ question: "接入方式？", options: [
  { label: "SQL Pipe（持续自动导入）", description: "LIST_PURGE 或 EVENT_NOTIFICATION 模式" },
  { label: "Studio 离线同步任务", description: "周期性批量导入，配置 Cron" }
]}]})
```

选了"Kafka"：
```
question({ questions: [{ question: "接入方式？", options: [
  { label: "SQL Pipe（READ_KAFKA）", description: "纯 SQL，灵活，推荐工程师使用" },
  { label: "Studio 实时同步任务", description: "图形化配置，支持 JSONPath 计算列" }
]}]})
```

---

### Step 3：方案确认（必须执行，不得跳过）

综合需求和技术选型，向用户呈现完整方案摘要，请求确认：

```
question({
  questions: [{
    question: "确认以下方案后开始构建：\n业务场景：<场景>\n数据源：<数据源名称>\n同步方式：<离线/实时/SQL Pipe>\n分层结构：<ODS/DWD/DWS 或 Bronze/Silver/Gold>\n目标 Schema：<schema>\n调度：<Cron 或持续运行>\n是否开始？",
    options: [
      { label: "确认，开始构建", description: "加载对应 skill，开始创建任务" },
      { label: "需要调整", description: "重新收集信息" }
    ]
  }]
})
```

用户确认后，按路由表加载对应 skill：

**路由表**

| 数据源 | 时效性/方式 | 加载 skill |
|---|---|---|
| 外部数据库 | 实时单表 CDC | `clickzetta-realtime-sync-pipeline` |
| 外部数据库 | 实时多表/整库 CDC | `clickzetta-cdc-sync-pipeline` |
| 外部数据库 | 离线批量 | `clickzetta-batch-sync-pipeline` |
| Kafka | SQL Pipe | `clickzetta-kafka-ingest-pipeline` |
| Kafka | Studio 实时同步 | `clickzetta-realtime-sync-pipeline` |
| 对象存储 | SQL Pipe | `clickzetta-oss-ingest-pipeline` |
| 对象存储 | Studio 离线同步 | `clickzetta-batch-sync-pipeline` |
| Lakehouse 内部 ETL 分层 | — | `clickzetta-sql-pipeline-manager` |
| 端到端完整管道 / 不确定 | — | `clickzetta-dw-modeling` |

> 实时 CDC 单表 vs 多表：用户说"整库"或"多张表"→ `cdc-sync-pipeline`；"一张表"→ `realtime-sync-pipeline`；不确定时追问。

---

## Studio 任务类型说明

Studio 提供四大类任务，选错类型是最常见的工程错误：

### 离线同步（单表）
将单张源表周期性全量同步到 Lakehouse。

- **适用场景**：单表定期覆盖更新、数据时效性要求不高（按天/小时批量）、资源优化（不需要实时）
- **运行模式**：周期调度（需配置 Cron），每次全量覆盖或追加
- **数据源**：MySQL、PostgreSQL、SQL Server 等关系型数据库
- **对应 skill**：`clickzetta-batch-sync-pipeline`（单表模式）

### 多表离线同步
将多张源表或整库周期性批量同步到 Lakehouse。

- **适用场景**：
  - 整库迁移（批量同步所有表，减少逐表配置工作量）
  - 分库分表合并（多个分库分表合并到统一目标表）
  - 定期数据校准（周期性全量同步确保目标端与源端一致）
- **运行模式**：周期调度（需配置 Cron），支持整库镜像、多表镜像、多表合并三种模式
- **数据源**：MySQL、PostgreSQL、SQL Server 等
- **对应 skill**：`clickzetta-batch-sync-pipeline`（多表模式）

### 实时同步（单表）
将单张 Kafka Topic 数据持续实时同步到 Lakehouse。

- **适用场景**：Kafka 消息流实时入湖、秒级/分钟级延迟要求、单 Topic 精细化同步
- **运行模式**：持续运行（无需配置 Cron，提交即运行）
- **数据源**：**仅支持 Kafka**（JSON 消息解析，支持 JSONPath 计算列）
- **对应 skill**：`clickzetta-realtime-sync-pipeline`

### 多表实时同步（CDC）
将 MySQL / PostgreSQL 整库或多表通过 CDC 实时同步到 Lakehouse，包含全量 + 增量两阶段。

- **适用场景**：数据库整库实时镜像、秒级端到端时效性、分库分表实时合并
- **运行模式**：持续运行（无需配置 Cron，提交即运行）
- **数据源**：

| 类型 | 增量读取模式 | 支持版本 |
|---|---|---|
| MySQL 类（含 Aurora MySQL、PolarDB MySQL） | Binlog | 5.6 及以上、8.x |
| PostgreSQL 类（含 Aurora PG、PolarDB PG） | WALs 日志 | 14 及以上 |

- **对应 skill**：`clickzetta-cdc-sync-pipeline`

### 数据开发任务（SQL / Python / Shell）
在 Studio 中编写和调度数据处理逻辑，是数仓 ETL 的核心载体。

- **SQL 任务**：ODS→DWD 清洗转换、数据质量检查、临时数据修复
- **Python 任务**：自定义数据处理脚本、调用外部 API、机器学习推理
- **Shell 任务**：系统命令、文件操作、调用外部工具
- **运行模式**：周期调度（配置 Cron）或手动触发
- **对应 skill**：`clickzetta-studio-task-manager`（本 skill）

### 四类任务对比速查

| 任务类型 | 数据源 | 同步粒度 | 运行模式 | 时效性 |
|---|---|---|---|---|
| 离线同步 | 关系型数据库 | 单表 | 周期调度 | 小时/天级 |
| 多表离线同步 | 关系型数据库 | 多表/整库 | 周期调度 | 小时/天级 |
| 实时同步 | **仅 Kafka** | 单 Topic | 持续运行 | 秒/分钟级 |
| 多表实时同步 | MySQL / PostgreSQL | 多表/整库 | 持续运行 | 秒级 |
| 数据开发 | 任意（SQL/Python/Shell） | 自定义逻辑 | 周期调度或手动 | 取决于调度频率 |

---

## 核心原则：建管分离

**不同类型的任务，调度策略完全不同。** 混淆任务类型是最常见的工程错误。

| 任务类型 | 典型内容 | Studio 任务类型 | 调度配置 | 状态 |
|---|---|---|---|---|
| **DDL 建表任务** | CREATE TABLE / CREATE SCHEMA | SQL 任务 | ❌ 禁止 Cron，禁止依赖 | DRAFT |
| **数据同步任务** | 外部数据源（关系型数据库/对象存储）→ ODS | **SINGLE_DI / MULTI_DI / REALTIME**（不是 SQL 任务） | ✅ 配置 Cron（离线）或持续运行（实时） | PUBLISHED |
| **ETL 转换任务** | ODS→DWD 清洗 SQL（Lakehouse 内部） | SQL 任务 | ✅ 配置 Cron + 依赖上游同步 | PUBLISHED |
| **数据质量任务** | 行数检查、NULL 率验证 | SQL 任务 | ✅ 配置 Cron + 依赖 ETL | PUBLISHED |
| **DWS/ADS 聚合层** | 指标汇总、报表宽表 | ❌ 使用 Dynamic Table，不建任务 | — | — |

**数据同步任务支持的数据源：**
- 离线同步（SINGLE_DI/MULTI_DI）：MySQL、PostgreSQL、Oracle、SQL Server 等关系型数据库，以及 OSS/COS/S3 对象存储
- 实时同步单表（REALTIME）：Kafka
- 多表实时同步 CDC：MySQL（Binlog，5.6+/8.x）、PostgreSQL（WALs，14+）

**其他数据访问方式（不是数据同步任务）：**
- Kafka/OSS/S3/COS → 也可以用 SQL Pipe（`READ_KAFKA`/Volume Pipe），与 Studio 同步任务都合法，根据场景选择
- Hive/Databricks/Snowflake Open Catalog → External Catalog 联邦只读查询，不做数据同步

> ⚠️ **DDL 任务绝对不能配 Cron**：建表语句重复执行会引发 `SCHEDULE_TASK_HAD_CHILDREN_NODES_EXCEPTION` 等调度冲突。DDL 任务执行完成后立即降级为 DRAFT。

> ⚠️ **DWS/ADS 层不要建调度任务**：Dynamic Table 系统自动刷新，额外建任务是冗余计算，浪费资源。

> ⚠️ **严禁用 SQL 任务替代数据同步任务**：不能用 SQL 任务写 `SELECT FROM EXTERNAL` 模拟同步（语法不支持），也不能用 JDBC 任务（JDBC 只能在外部数据库执行 SQL，不支持将数据同步到 Lakehouse）。

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

### 代码资产化原则

**数据管道开发 / 数仓建模场景下，所有 SQL 代码都应保存为 Studio 任务，作为可管理的代码资产。**

- 任务是代码的载体，不只是调度配置
- 即使是一次性执行的 DDL，也应保存为 DRAFT 任务，方便查阅、复用和多环境迁移
- 不需要保存为任务的场景：SELECT 查询、临时修复 SQL、一次性验证查询

### 新项目启动流程

```
1. 创建任务目录
   cz-cli task folder create <业务域>_dw

2. 生成各层 DDL，逐层保存为独立 DRAFT 任务（不配 Cron，不配依赖）
   cz-cli task save-content 01_ddl_ods --content "<ods_ddl_sql>"
   cz-cli task save-content 02_ddl_dwd --content "<dwd_ddl_sql>"
   cz-cli task save-content 03_ddl_dws_ads --content "<dws_ads_ddl_sql>"

3. 手动执行 DDL 任务（一次性）
   cz-cli task run <ddl_task_id>

4. 创建数据同步任务（配 Cron）
   - 00_sync：整库或单表同步到 ODS
   - MULTI_DI 类型需进 UI 配置映射

5. 生成 ETL 转换 SQL，保存为调度任务（配 Cron + 依赖 00）
   cz-cli task save-content 04_transform_ods_to_dwd --content "<etl_sql>"
   cz-cli task save-cron 04_transform_ods_to_dwd --cron '0 30 2 * * ? *'
   cz-cli task deploy 04_transform_ods_to_dwd

6. 可选：生成数据质量 SQL，保存为任务（配 Cron + 依赖 04）
   cz-cli task save-content 05_dqc_check --content "<dqc_sql>"
   cz-cli task save-cron 05_dqc_check --cron '0 0 3 * * ? *'
   cz-cli task deploy 05_dqc_check

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
- [ ] **ETL 任务依赖链完整**（`cz-cli task deps <task>` 验证，`task_dependencies` 不为空）
- [ ] 关键表和字段已加注释（加载 `clickzetta-manage-comments`）

---

## 多环境管理（dev → prod）

企业通常有 dev/staging/prod 多套环境。管道在 dev 验证通过后，迁移到 prod 的 SOP：

### 迁移步骤

```bash
# 1. 导出 dev 环境的任务配置
cz-cli task list --folder <业务域>_dw > task_list.txt
cz-cli task content <task_id> > task_<name>.json  # 逐个导出

# 2. 替换环境相关配置（数据源名称、Schema 前缀、VCluster 名称）
# dev 数据源：aliyun_mysql_dev  →  prod 数据源：aliyun_mysql_prod
# dev schema：ecommerce_ods_dev  →  prod schema：ecommerce_ods

# 3. 在 prod 环境创建任务目录
cz-cli task folder create <业务域>_dw

# 4. 逐层创建任务（先 DDL，再同步，再 ETL）
cz-cli task save-content <task_name> --content "<替换后的SQL>"
cz-cli task save-cron <task_name> --cron '<cron>'
cz-cli task deploy <task_name>

# 5. 验证 prod 环境任务依赖
cz-cli task deps <task_name>
```

### 注意事项

- **数据源名称**：dev/prod 通常是不同的数据源配置，迁移时必须替换
- **Schema 命名**：建议 dev 用 `<业务域>_dev` 后缀，prod 不加后缀，便于区分
- **VCluster**：prod 环境的集群名称可能与 dev 不同，`SHOW VCLUSTERS` 确认
- **Dynamic Table**：prod 环境重建后立即执行 `REFRESH DYNAMIC TABLE` 重置基准时间
- **调度时间**：dev 可以用短间隔测试，prod 按业务需求设置正式 Cron
