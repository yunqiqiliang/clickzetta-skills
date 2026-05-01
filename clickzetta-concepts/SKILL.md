---
name: clickzetta-concepts
description: |
  介绍 ClickZetta Lakehouse 的核心概念、对象模型和独特设计，帮助用户建立正确认知。
  覆盖：账户/实例/工作空间/Schema 层级，Workspace 与 Database/Catalog 的对应关系，
  VCluster 三种类型与 CRU 计费，Dynamic Table 增量刷新机制，Table Stream CDC，
  三层缓存体系，Pipe 持续导入，Synonym 跨 Schema 别名，权限体系（RBAC/ACL），
  以及与 Snowflake/Databricks 的关键差异对比。
  当用户说"工作空间是什么"、"Schema 和 Database 什么关系"、"Catalog 是什么"、
  "实例和工作空间的区别"、"VCluster 是什么"、"CRU 是什么"、"内部表和外部表区别"、
  "动态表和物化视图区别"、"Table Stream 是什么"、"Pipe 是什么"、"同义词是什么"、
  "Lakehouse 架构"、"对象层级"、"权限体系"、"和 Snowflake 概念对比"、
  "和 Databricks 概念对比"、"存算分离"、"CBO 增量计算"时触发。
---

# ClickZetta Lakehouse 核心概念

阅读 [references/object-model.md](references/object-model.md) 了解完整对象层级和差异对比。

---

## 对象层级总览

```
账户 (Account)
└── 服务实例 (Instance)          ← 对应一个云区域部署，资源隔离单元
    └── 工作空间 (Workspace)      ← 业务隔离单元，≈ Snowflake Database / Databricks Catalog
        ├── Schema               ← 命名空间，≈ 传统 Database / Snowflake Schema
        │   ├── 内部表 (Managed Table)   — Iceberg · ACID · Time Travel
        │   ├── 外部表 (External Table)  — Delta/Hudi/Kafka · 只读
        │   ├── 视图 / 动态表 / 物化视图
        │   ├── Volume            — User/Table/External(OSS/S3/COS)
        │   ├── Table Stream      — CDC 变更捕获（ClickZetta 特有）
        │   ├── Pipe              — 持续导入（Kafka/OSS）
        │   ├── 函数 / External Function
        │   ├── 索引（BloomFilter/倒排/向量）
        │   └── 同义词 (Synonym)  — 跨 Schema 别名（ClickZetta 特有）
        ├── Share                 — 跨账户零拷贝共享
        ├── Connection            — Storage/API 连接
        └── External Catalog      — Hive/Iceberg/Databricks 联邦查询
```

---

## 与其他系统的概念对比

| ClickZetta | Snowflake | Databricks | 传统数据库 | 关键差异 |
|---|---|---|---|---|
| 服务实例 (Instance) | Account | Workspace | 数据库服务器 | ClickZetta 一个账户可多实例多云 |
| 工作空间 (Workspace) | Database | Catalog | Database | 连接时必须指定 |
| Schema | Schema | Schema/Database | Schema | 权限边界，支持 EXTERNAL 类型 |
| VCluster | Warehouse | SQL Warehouse | — | 三种类型，CRU 细粒度计费 |
| Dynamic Table | Dynamic Table | Streaming Table | — | 基于 CBO 的增量刷新，非流式 |
| Table Stream | Stream | — | — | 需先开启 change_tracking |
| Pipe | Pipe | Auto Loader | — | 每个 Pipe 对应独立 Volume |
| Volume | Stage | External Location | — | 三种子类型：User/Table/External |
| Share | Share | Delta Sharing | — | 跨实例零拷贝，消费方无存储费 |
| Synonym | — | — | Synonym | 支持跨 Schema 别名 |
| CRU | Credit | DBU | — | 跨云统一算力单位 |

---

## ClickZetta 独特概念详解

### 1. CRU（Compute Resource Unit）— 跨云统一算力单位

CRU 是 ClickZetta 对 IaaS 计算资源的抽象，**在不同云平台、不同 CPU 架构下提供一致的算力**。

- 计费单位：CRU × 时（集群运行时间）
- 集群停止时不计费，自动停止最小 15 秒
- 旧规格代码（XS/S/M/L/XL）已迁移为数字（1/2/4/8/16 CRU）

```sql
-- 创建 4 CRU 通用型集群
CREATE VCLUSTER my_gp TYPE GENERAL SIZE 4;

-- 创建分析型集群（弹性 1-4 副本，每副本 8 CRU）
CREATE VCLUSTER my_ap TYPE ANALYTICS SIZE 8 MIN_INSTANCE 1 MAX_INSTANCE 4;
```

### 2. VCluster 三种类型 — 不同场景不同集群

| 类型 | 弹性方式 | 规格步长 | 适用场景 | 特殊能力 |
|---|---|---|---|---|
| 通用型 (GENERAL) | 纵向（规格扩缩） | 1 CRU | ETL、批量导入、Ad-Hoc | 自动小文件合并（Dynamic Table 推荐） |
| 分析型 (ANALYTICS) | 横向（副本 1-10） | 2^n CRU | 高并发 BI、在线查询 | 本地缓存 PRELOAD_TABLES |
| 同步型 (INTEGRATION) | — | 0.25 CRU | 数据集成、CDC 同步 | 最小 0.25 CRU 小规格 |

**关键差异**：Dynamic Table 必须用通用型（GP），分析型（AP）不支持小文件合并，会导致文件碎片化。

### 3. Dynamic Table — 声明式增量计算（非流式）

Dynamic Table 是 ClickZetta 的核心特色之一，**通过 SQL 声明加工逻辑，系统自动判断增量/全量计算策略**。

与 Snowflake Dynamic Table 的关键差异：
- ClickZetta 基于 **CBO（Cost-Based Optimizer）** 自适应选择增量/全量算法
- `CREATE OR REPLACE` 保留数据和权限（Snowflake 会清空数据）
- 最小刷新间隔 **1 分钟**（非秒级流式）
- 建议用 **GP 集群**（AP 集群不支持小文件合并）

```sql
-- 声明式增量计算，系统自动处理增量逻辑
CREATE OR REPLACE DYNAMIC TABLE dws_order_daily
  REFRESH interval 5 MINUTE
  VCLUSTER default_gp
AS
SELECT date_trunc('day', order_time) AS dt,
       SUM(amount) AS total_amount,
       COUNT(*) AS order_cnt
FROM ods_orders
GROUP BY 1;

-- 手动触发刷新
REFRESH DYNAMIC TABLE dws_order_daily;
```

### 4. Table Stream — CDC 变更捕获对象

Table Stream 是 SQL 对象，记录表的 DML 变更（INSERT/UPDATE/DELETE），**消费后自动推进 offset**。

与 Snowflake Stream 的关键差异：
- **必须先开启 `change_tracking`**（Snowflake 不需要）
- 实时写入数据需等待 **1 分钟**后才可被 Stream 读取
- 支持在 Table、Dynamic Table、Materialized View、Kafka 外部表上创建

```sql
-- 第一步：开启变更跟踪（必须）
ALTER TABLE orders SET PROPERTIES ('change_tracking' = 'true');

-- 第二步：创建 Stream
CREATE TABLE STREAM orders_stream
  ON TABLE orders
  WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD', 'SHOW_INITIAL_ROWS' = 'FALSE');

-- 消费 Stream（DML 操作后 offset 自动推进）
INSERT INTO orders_summary
SELECT __change_type, order_id, amount
FROM orders_stream
WHERE __change_type = 'INSERT';
```

Stream 元数据字段：
- `__change_type`：INSERT / UPDATE_BEFORE / UPDATE_AFTER / DELETE
- `__commit_version`：提交版本号
- `__commit_timestamp`：提交时间戳

### 5. Pipe — 持续导入对象

Pipe 是 SQL 对象，持续自动将数据从 Kafka 或对象存储导入到表中。

**ClickZetta 特有限制**：每个 Pipe 必须对应独立的 Volume，不可复用。

```sql
-- OSS 持续导入（LIST_PURGE 扫描模式）
CREATE PIPE oss_orders_pipe
  VIRTUAL_CLUSTER = 'default_gp'
  INGEST_MODE = 'LIST_PURGE'
AS COPY INTO orders
   FROM VOLUME my_oss_volume
   USING CSV OPTIONS('header'='true');

-- Kafka 持续导入
CREATE PIPE kafka_events_pipe
  VIRTUAL_CLUSTER = 'default_gp'
  BATCH_INTERVAL_IN_SECONDS = '60'
  BATCH_SIZE_PER_KAFKA_PARTITION = '500000'
AS COPY INTO events
   FROM (SELECT * FROM READ_KAFKA(...));
```

### 6. 三层缓存体系

ClickZetta 有三种独立缓存，理解它们对性能调优至关重要：

| 缓存类型 | 作用范围 | 适用集群 | 说明 |
|---|---|---|---|
| 查询结果缓存 (Result Cache) | 工作空间共享 | GP + AP | 相同 SQL 直接返回缓存结果 |
| 元数据缓存 (Metadata Cache) | 工作空间共享 | GP + AP | 表结构、分区信息缓存 |
| 本地磁盘缓存 (Local Disk Cache) | 集群本地节点 | GP + AP | 热数据文件缓存，集群停止后释放 |

**主动缓存**（仅 AP 集群）：集群启动时自动预加载指定表的最新数据。

```sql
-- 设置 AP 集群预加载表（集群启动时自动缓存）
ALTER VCLUSTER my_ap SET PRELOAD_TABLES = "sales.orders,sales.products";

-- 查看缓存状态
SHOW PRELOAD CACHED STATUS;
SHOW EXTENDED PRELOAD CACHED STATUS;
```

### 7. Synonym（同义词）— 跨 Schema 别名

Synonym 是 ClickZetta 特有的对象类型，为表/Stream/动态表/物化视图/Volume/函数创建跨 Schema 别名，**无需复制数据**。

```sql
-- 在 schema_b 中为 schema_a 的表创建别名
CREATE SYNONYM schema_b.orders_alias FOR schema_a.orders;

-- 直接查询别名（数据实时与原表一致）
SELECT * FROM schema_b.orders_alias;

-- Volume 同义词（必须加 VOLUME 关键字）
CREATE VOLUME SYNONYM my_schema.vol_alias FOR data_schema.raw_volume;

-- 函数同义词（必须加 FUNCTION 关键字）
CREATE FUNCTION SYNONYM my_schema.fn_alias FOR data_schema.my_function;
```

### 8. Sort Key 智能推荐（Auto Index）

ClickZetta 会自动分析查询历史，推荐最优排序列（Sort Key），通过 `information_schema.sortkey_candidates` 查看。

```sql
-- 开启自动分析（每天收集，分析最近 150 分钟的作业）
ALTER WORKSPACE quick_start SET PROPERTIES ('auto_index' = 'day');

-- 查看推荐结果
SELECT table_name, col, statement, ratio
FROM information_schema.sortkey_candidates
ORDER BY ratio DESC;

-- 应用推荐（执行 statement 列中的 SQL）
ALTER TABLE sales.orders SET PROPERTIES ("hint.sort.columns" = "order_date");
```

---

## 核心概念详解

### 工作空间（Workspace）

**业务隔离单元**，是日常操作的主要边界。

- 连接时必须指定（等同于 Snowflake Database / Databricks Catalog）
- 每个 Workspace 有独立的：用户角色、VCluster、任务调度、INFORMATION_SCHEMA
- SQL 三层命名：`workspace_name.schema_name.table_name`
- 通过 `USE SCHEMA` 切换默认 Schema

### Schema

**命名空间**，是权限授予的边界。

- 类型：`MANAGED`（平台托管存储）/ `EXTERNAL`（外部数据湖路径）
- 一个 Workspace 下可有多个 Schema
- 可对整个 Schema 批量授权：`GRANT SELECT ON ALL TABLES IN SCHEMA my_schema TO ROLE ...`

### 权限体系关键点

- **无超级用户**：所有操作必须明确授权，无法绕过权限检查
- **实例角色与工作空间角色互不影响**：`instance_admin` 不能直接操作工作空间数据
- **自定义角色仅工作空间级**：不支持实例级自定义角色，且只能通过 SQL 创建
- **新用户默认无权限**：加入实例后获得 `instance_user` 角色，需显式授予工作空间角色才能操作数据

```sql
-- 新用户加入后必须授予工作空间角色
GRANT ROLE workspace_analyst TO USER new_user;

-- 创建自定义角色（仅 SQL，不支持 Web 端）
CREATE ROLE data_engineer;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA dw TO ROLE data_engineer;
GRANT ROLE data_engineer TO USER alice;
```

---

## 存储架构关键点

- **存算分离**：VCluster 停止时不产生计算费用，存储按 GiB 独立计费
- **开放格式**：内部表基于 Apache Iceberg，可被 Spark/Trino 直接读取
- **多云多地域**：阿里云上海、腾讯云上海/北京/广州、AWS 北京
- **私有存储（BYOS）**：支持使用自己的 OSS/S3/COS 账号存储数据
