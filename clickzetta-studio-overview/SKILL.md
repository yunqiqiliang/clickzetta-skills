---
name: clickzetta-studio-overview
description: |
  ClickZetta Lakehouse Studio 功能全貌概览。Studio 是内置于 Lakehouse 的一站式
  Web IDE，集数据开发、任务调度、数据集成、数据目录、数据质量、运维监控六大模块于一体，
  是 ClickZetta 区别于 Snowflake/Databricks 的核心差异化能力（后两者需第三方工具）。
  覆盖：六大模块定位与边界、任务类型（SQL/Python/Shell/JDBC/同步/动态表）、
  任务组 DAG 编排、任务参数（${var} 和 $[时间表达式]）、调度配置、
  数据目录（Data Catalog）、数据质量规则六大维度、运维监控告警。
  当用户说"Studio 是什么"、"Studio 有哪些功能"、"Studio 和其他 Lakehouse 的区别"、
  "任务调度怎么配"、"DAG 编排"、"任务组"、"任务参数"、"${} 参数怎么用"、
  "数据目录"、"数据质量"、"运维监控"、"告警配置"、"补数据"、"任务依赖"时触发。
---

# ClickZetta Lakehouse Studio 功能概览

阅读 [references/studio-modules.md](references/studio-modules.md) 了解各模块详细说明。

---

## Studio 是什么

Studio 是 ClickZetta Lakehouse **内置的一站式 Web IDE**，无需安装任何客户端，直接在浏览器中完成从数据接入、开发、调度到运维的全链路操作。

**这是 ClickZetta 与 Snowflake、Databricks 等产品的核心差异之一**：

| 能力 | ClickZetta Studio | Snowflake | Databricks |
|---|---|---|---|
| Web SQL 开发 | ✅ 内置 | ✅ Snowsight | ✅ Notebooks |
| 可视化数据集成（无代码同步） | ✅ 内置 30+ 数据源 | ❌ 需第三方 | ❌ 需第三方 |
| 任务调度 + DAG 编排 | ✅ 内置 | ❌ 需第三方 | ❌ 需第三方 |
| 数据目录（Data Catalog） | ✅ 内置 | 部分 | 部分 |
| 数据质量规则 | ✅ 内置 6 维度 | ❌ 需第三方 | ❌ 需第三方 |
| 运维监控 + 告警 | ✅ 内置 | 部分 | 部分 |

---

## Studio 六大模块

### 1. 数据开发（IDE）

Web 在线 IDE，支持多种任务类型：

| 任务类型 | 说明 | 使用集群 |
|---|---|---|
| SQL 任务 | 编写 DDL/DML，支持自动补全、结果可视化 | GP 或 AP |
| Python 任务 | SQLAlchemy / ZettaPark 脚本，支持安装依赖 | 不使用 VCluster |
| Shell 任务 | Shell 脚本，支持调用外部命令 | 不使用 VCluster |
| JDBC 任务 | 连接 MySQL/Hive/ClickHouse 等执行 SQL | 不使用 VCluster |
| 动态表任务 | 向导式创建 Dynamic Table，配置刷新周期 | GP 或 AP |
| 数据同步任务 | 无代码配置离线/实时/CDC 同步 | 同步型 VCluster |

### 2. 任务调度与编排

- **周期调度**：Cron 表达式，支持分钟/小时/天/月级别
- **任务依赖**：上下游依赖，支持跨工作空间依赖
- **任务组（DAG）**：可视化拖拽编排，批量管理一组任务
- **补数据**：对历史周期重新触发执行
- **任务参数**：动态变量替换，支持时间表达式

### 3. 数据集成（同步任务）

内置 30+ 数据源，无代码配置数据同步：

- **离线同步**：全量/增量，支持整库迁移、Schema Evolution
- **实时同步**（单表）：Kafka、MySQL、PostgreSQL 实时写入
- **多表实时 CDC**：整库镜像、分库分表合并，基于 Binlog/WAL

### 4. 数据目录（Data Catalog）

- 全局数据资产搜索（按名称、描述、负责人）
- 表详情：DDL、字段、数据预览（100行）、数据血缘、作业历史
- 可视化创建 Schema/表（内置 DDL 模板）

### 5. 数据质量

6 大维度质量规则：完整性、唯一性、一致性、准确性、有效性、及时性。

- 支持定时触发、调度任务触发、手动触发
- 质量规则大盘：覆盖表数、校验通过率、高质量表

### 6. 运维监控与告警

- 任务实例运维：启停、重跑、批量操作
- 内置告警规则：周期任务失败、数据质量失败等
- 自定义告警规则
- 告警通知：飞书/企业微信 webhook

---

## 任务参数详解

任务参数是 Studio 调度的核心能力，实现代码与配置分离。

### 参数格式

```sql
-- 在 SQL 中使用参数（格式：${参数名}）
SELECT * FROM orders
WHERE city = '${city}'
  AND dt = '${yesterday}';
```

### 参数赋值方式

| 赋值类型 | 示例 | 说明 |
|---|---|---|
| 常量 | `Shanghai` | 固定值 |
| 系统内置时间函数 | `$[yyyy-MM-dd, -1d]` | 昨天日期 |
| 系统内置时间函数 | `$[yyyy-MM-dd HH:mm:ss]` | 当前时间 |
| 系统内置时间函数 | `$[yyyyMM, -1M]` | 上月 |
| 系统内置参数 | `sys_plan_datetime` | 任务计划执行时间 |

```sql
-- 示例：每天处理前一天数据
SELECT date, SUM(amount)
FROM sales
WHERE dt = '${yesterday}'   -- 赋值：$[yyyy-MM-dd, -1d]
GROUP BY date;
```

### 参数作用域

- **任务参数**：仅当前任务有效
- **任务组参数**：任务组内所有任务共享，任务组提交后生效

---

## 任务组（DAG）编排

任务组是 Studio 的核心调度能力，用于管理有依赖关系的一批任务。

```
任务组（Task Group）
├── 节点 A：离线同步（MySQL → Lakehouse）
├── 节点 B：SQL 任务（ODS 清洗）  依赖 A
├── 节点 C：SQL 任务（DWD 加工）  依赖 B
└── 节点 D：SQL 任务（DWS 聚合）  依赖 C
```

**关键限制：**
- 任务组内仅支持周期任务，不支持实时任务
- 一个任务节点只能归属于一个任务组
- 任务组参数需提交后才对任务节点生效
- 跨工作空间依赖支持，但下游链路复制不包含其他空间节点

---

## 数据目录（Data Catalog）核心功能

```sql
-- 数据目录中的表详情页提供：
-- 1. DDL 语句（一键复制）
-- 2. 字段信息（名称/类型/描述/主键标识）
-- 3. 数据预览（100行，需 SELECT 权限 + 指定 VCluster）
-- 4. 数据血缘（上下游表关系）
-- 5. 作业历史（该表相关的查询记录）
-- 6. 上传（本地文件直接上传到表）
```

---

## 与其他系统的对比

**为什么 Studio 是差异化能力？**

Snowflake 和 Databricks 的数据集成、调度、数据质量通常需要对接 Fivetran、dbt、Airflow、Great Expectations 等第三方工具，形成复杂的技术栈。

ClickZetta Studio 将这些能力**内置在平台中**，统一的权限体系、统一的监控告警、统一的数据血缘，降低了运维复杂度，特别适合中小团队和希望减少工具链复杂度的企业。
