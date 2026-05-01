---
name: clickzetta-concepts
description: |
  介绍 ClickZetta Lakehouse 的核心概念和对象模型，帮助用户理解平台架构。
  覆盖：账户/实例/工作空间/Schema 的层级关系，Workspace 与 Database/Catalog 的对应关系，
  VCluster 计算集群类型，内部表/外部表/视图/动态表等数据对象，权限体系（RBAC/ACL），
  存算分离架构，以及各概念与 Snowflake/Databricks 的对比映射。
  当用户说"工作空间是什么"、"Schema 和 Database 什么关系"、"Catalog 是什么"、
  "实例和工作空间的区别"、"VCluster 是什么"、"CRU 是什么"、"内部表和外部表区别"、
  "Lakehouse 架构"、"对象层级"、"权限体系"、"和 Snowflake 概念对比"、
  "和 Databricks 概念对比"、"存算分离"时触发。
---

# ClickZetta Lakehouse 核心概念

阅读 [references/object-model.md](references/object-model.md) 了解完整对象层级。

---

## 对象层级总览

```
账户 (Account)
└── 服务实例 (Instance)
    └── 工作空间 (Workspace)  ← 相当于其他系统的 "Database" 或 "Catalog"
        ├── Schema             ← 命名空间，相当于其他系统的 "Schema" 或 "Database"
        │   ├── 内部表 / 外部表 / 视图 / 动态表 / 物化视图
        │   ├── Volume（文件存储）
        │   ├── Stream / Pipe
        │   ├── 函数 / External Function
        │   └── 索引 / 同义词
        ├── Share（跨账户数据共享）
        ├── Connection（存储/API 连接）
        └── External Catalog（联邦查询）
```

---

## 核心概念详解

### 账户（Account）

全局唯一身份，对应一个企业或团队。支持 SSO（SAML 2.0 / OIDC）和 MFA（Google Authenticator）。账户下可创建多个服务实例。

### 服务实例（Instance）

资源隔离单元，对应一个云区域的部署（如阿里云上海、腾讯云北京）。一个账户可在多个云/地域创建多个实例。实例级权限由 `instance_admin` 角色管理。

### 工作空间（Workspace）

**业务隔离单元**，是日常操作的主要边界。

- 连接时必须指定 workspace（等同于 Snowflake 的 Database，或 Databricks 的 Catalog）
- 每个 workspace 有独立的用户角色、VCluster、任务调度
- SQL 三层命名：`workspace_name.schema_name.table_name`
- 通过 `USE SCHEMA` 切换默认 Schema，无需每次写全路径

### Schema（数据库）

**命名空间**，用于组织数据对象（等同于传统数据库的 "Database" 或 "Schema"）。

- 一个 Workspace 下可有多个 Schema
- Schema 是权限边界：可对 Schema 级别授权
- 类型：`MANAGED`（内部托管）/ `EXTERNAL`（外部数据湖）
- 常用命令：`CREATE SCHEMA`、`USE SCHEMA`、`SHOW SCHEMAS`、`DROP SCHEMA`

### 与其他系统的概念对比

| ClickZetta | Snowflake | Databricks | 传统数据库 |
|---|---|---|---|
| 服务实例 (Instance) | Account | Workspace | 数据库服务器 |
| 工作空间 (Workspace) | Database | Catalog | Database |
| Schema | Schema | Schema / Database | Schema |
| 表 (Table) | Table | Table | Table |
| VCluster | Warehouse | Cluster / SQL Warehouse | — |
| Dynamic Table | Dynamic Table | Streaming Table | — |
| Volume | Stage | External Location | — |
| Share | Share | Delta Sharing | — |

---

## 计算集群（VCluster）

VCluster 是执行 SQL 查询和 ETL 的计算资源，按 **CRU（Compute Resource Unit）** 计费。

| 类型 | 适用场景 | 弹性方式 | 规格范围 |
|---|---|---|---|
| 通用型（GENERAL） | ETL、批量导入、Ad-Hoc 查询 | 纵向弹性（1-256 CRU） | 1 CRU 步长 |
| 分析型（ANALYTICS） | 高并发 BI、在线查询 | 横向弹性（1-10 副本） | 2^n CRU 步长 |
| 同步型（INTEGRATION） | Studio 数据集成、CDC 同步 | — | 0.25 CRU 起 |

**关键特性：**
- 自动停止（最小 15 秒无作业即停止）/ 自动启动
- 按 CRU·时 计费，停止时不计费
- 分析型支持本地缓存（PRELOAD_TABLES）
- Dynamic Table 建议用通用型（自动小文件合并，分析型不支持）

---

## 数据对象类型

### 内部表（Managed Table）

- 基于 Apache Iceberg 格式，存储在平台托管的对象存储
- 支持 ACID 事务（INSERT/UPDATE/DELETE/MERGE）
- 支持 Time Travel（`TIMESTAMP AS OF`）
- 支持分区、分桶、主键约束、索引（BloomFilter/倒排/向量）

### 外部表（External Table）

- 数据存储在外部（OSS/S3/COS 或 Kafka），表结构在 Lakehouse 中定义
- 支持 Delta Lake、Apache Hudi、Kafka 实时表
- 只读联邦查询（不支持 DML）

### 视图（View）

- 虚拟视图，每次查询时执行底层 SQL
- 不存储数据，不支持 Time Travel

### 动态表（Dynamic Table）

- 声明式增量计算，通过 SQL 定义加工逻辑，系统自动增量刷新
- 替代传统 ETL 调度，支持多层级联（ODS→DWD→DWS）
- 最小刷新间隔 1 分钟

### 物化视图（Materialized View）

- 预计算并存储查询结果，加速 BI 查询
- 支持手动或定时全量刷新
- 支持查询改写（Preview 功能）

---

## 权限体系

### 两种授权模式（并存）

- **RBAC**（推荐）：权限 → 角色 → 用户，便于批量管理
- **ACL**：权限直接授予用户，适合简单场景

### 角色层级

```
实例角色（Instance Role）
├── instance_admin    — 管理所有工作空间、用户、External Catalog
└── instance_user     — 默认角色，无任何数据权限

工作空间角色（Workspace Role）
├── workspace_admin   — 管理空间内所有对象和用户
├── workspace_dev     — 读写权限 + 任务管理
├── workspace_analyst — 只读权限
└── 自定义角色         — 通过 SQL 创建（仅工作空间级）
```

**注意**：实例角色与工作空间角色互不影响；无超级用户概念，所有操作必须明确授权。

---

## 存储层架构

- **存算分离**：计算（VCluster）和存储（OSS/S3/COS）独立扩展
- **开放格式**：内部表基于 Apache Iceberg，可被 Spark/Trino 等直接读取
- **多云部署**：阿里云（cn-shanghai）、腾讯云（ap-shanghai/beijing/guangzhou）、AWS（ap-southeast-1/cn-north-1）
- **私有存储（BYOS）**：支持使用自己的对象存储账号

---

## SQL 命名规范

```sql
-- 三层全路径（跨 workspace 查询时使用）
SELECT * FROM workspace_name.schema_name.table_name;

-- 切换默认 Schema 后可省略前缀
USE SCHEMA my_schema;
SELECT * FROM my_table;

-- 查看当前 workspace 下所有 Schema
SHOW SCHEMAS;

-- 查看 Schema 下所有表
SHOW TABLES IN my_schema;
```
