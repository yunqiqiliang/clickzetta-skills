---
name: clickzetta-overview
description: |
  ClickZetta Lakehouse 产品全貌：核心概念、对象模型、架构设计、Studio 功能介绍。
  覆盖：账户/实例/工作空间/Schema 对象层级，Workspace 与 Database/Catalog 的对应关系，
  VCluster 三种类型与 CRU 计费，Dynamic Table 增量刷新机制，Table Stream CDC，
  三层缓存体系，Pipe 持续导入，Synonym 跨 Schema 别名，权限体系（RBAC/ACL），
  与 Snowflake/Databricks 的关键差异对比，存算分离架构，
  品牌关系（ClickZetta = 云器 = Singdata）及各环境服务地址，
  Studio 六大模块（数据开发 IDE、任务调度、数据集成、数据目录、数据质量、运维监控）。
  当用户说"工作空间是什么"、"Schema 和 Database 什么关系"、"Catalog 是什么"、
  "VCluster 是什么"、"CRU 是什么"、"内部表和外部表区别"、"Lakehouse 架构"、
  "对象层级"、"权限体系"、"和 Snowflake 概念对比"、"和 Databricks 概念对比"、
  "存算分离"、"云器是什么"、"Singdata 是什么"、"ClickZetta 和云器什么关系"、
  "Studio 是什么"、"Studio 有哪些功能"、"任务调度怎么用"、"数据集成怎么用"、
  "数据目录"、"数据质量"、"运维监控"时触发。
  不适合：具体 SQL 语法（用 sql-syntax-guide）、具体元数据查询（用 metadata）、
  具体数据导入操作（用 pipeline skill）、具体权限操作（用 access-control）。
  Keywords: concepts, architecture, workspace, schema, VCluster, Studio, overview, object model
---

# ClickZetta Lakehouse 产品全貌

## 参考文档

| 文档 | 内容 |
|------|------|
| [references/object-model.md](references/object-model.md) | 对象层级、概念对比、独特设计详解 |
| [references/brands-and-endpoints.md](references/brands-and-endpoints.md) | 品牌关系、各环境服务地址 |
| [references/studio-modules.md](references/studio-modules.md) | Studio 六大模块详细功能 |

---

## 对象层级总览

```
账户 (Account)
└── 服务实例 (Instance)          ← 资源隔离单元
    └── 工作空间 (Workspace)      ← ≈ Snowflake Database / Databricks Catalog
        ├── Schema               ← 命名空间，权限边界
        │   ├── 内部表 / 外部表 / 视图 / 动态表 / 物化视图
        │   ├── Volume / Table Stream / Pipe / 索引 / Synonym
        │   └── 函数 / External Function
        ├── Share / Connection / External Catalog
        └── VCluster（计算集群）
```

---

## 核心概念速查

| 概念 | 说明 |
|------|------|
| CRU | 跨云统一算力单位，按 CRU×时 计费，集群停止不计费 |
| VCluster | 三种类型：通用型(GP)、分析型(AP)、同步型(INTEGRATION) |
| Dynamic Table | 声明式增量计算，基于 CBO 自适应增量/全量，最小 1 分钟刷新 |
| Table Stream | CDC 变更捕获对象，需先开启 change_tracking |
| Pipe | 持续导入对象（Kafka/OSS），每个 Pipe 对应独立 Volume |
| Synonym | 跨 Schema 别名，无需复制数据 |
| 三层缓存 | 结果缓存 + 元数据缓存 + 本地磁盘缓存（AP 支持 PRELOAD） |

---

## 与 Snowflake/Databricks 关键差异

| ClickZetta | Snowflake | Databricks | 差异点 |
|---|---|---|---|
| Workspace | Database | Catalog | 一个账户可多实例多云 |
| VCluster (3 类型) | Warehouse | SQL Warehouse | GP/AP/INTEGRATION 分离 |
| Studio（内置） | 需第三方 | 需第三方 | 内置调度/集成/质量/目录 |
| Dynamic Table (CBO) | Dynamic Table | Streaming Table | 基于 CBO 非流式 |
| Synonym | — | — | ClickZetta 特有 |

---

## Studio 六大模块

| 模块 | 核心能力 |
|------|---------|
| 数据开发 | Web IDE，支持 SQL/Python/Shell/JDBC/动态表/同步任务 |
| 任务调度 | Cron 调度 + DAG 编排 + 任务组 + 补数据 + 参数变量 |
| 数据集成 | 30+ 数据源无代码同步（离线/实时/CDC） |
| 数据目录 | 全局搜索、表详情、数据血缘、数据预览 |
| 数据质量 | 6 维度规则（完整性/唯一性/一致性/准确性/有效性/及时性） |
| 运维监控 | 任务实例运维 + 告警规则 + 飞书/企微通知 |

---

## 品牌关系

ClickZetta（技术品牌）= 云器（国内品牌）= Singdata（国际品牌）

详见 [references/brands-and-endpoints.md](references/brands-and-endpoints.md) 获取各环境服务地址。

---

## 存储架构

- 存算分离：VCluster 停止不产生计算费用
- 开放格式：内部表基于 Apache Iceberg
- 多云多地域：阿里云/腾讯云/AWS
- 私有存储（BYOS）：支持自有 OSS/S3/COS
