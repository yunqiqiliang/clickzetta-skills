# ClickZetta Lakehouse 对象模型完整参考

> 来源：官方产品文档 yunqi.tech
> 参考：clickzetta-lakehouse-architecture.html

---

## ClickZetta 独特概念速查

| 概念 | 独特之处 | 常见误区 |
|---|---|---|
| CRU | 跨云统一算力单位，旧规格 XS/S/M/L 已迁移为数字 1/2/4/8 | 不是 Snowflake Credit，不是 DBU |
| VCluster 三类型 | GP/AP/Integration 各有适用场景，Dynamic Table 必须用 GP | AP 集群不支持小文件合并 |
| Dynamic Table | CBO 自适应增量/全量，`OR REPLACE` 保留数据 | 最小 1 分钟，非秒级流式 |
| Table Stream | 需先 `ALTER TABLE SET PROPERTIES ('change_tracking'='true')` | 实时写入数据需等 1 分钟才可读 |
| Pipe | 每个 Pipe 对应独立 Volume，不可复用 | 不是 Snowflake Snowpipe，无自动触发 |
| Synonym | 支持跨 Schema 别名，VOLUME/FUNCTION 类型需显式声明关键字 | 不是视图，不复制数据 |
| 权限体系 | 无超级用户；实例角色与工作空间角色互不影响 | instance_admin 不能直接操作工作空间数据 |
| Workspace | 连接时必须指定，≈ Snowflake Database | 不是 Databricks Workspace（那个是实例级） |
| Schema TYPE | MANAGED（内部托管）/ EXTERNAL（外部数据湖） | EXTERNAL Schema 不支持 DML |

---

## 完整对象层级

```
账户 (Account)
│  全局唯一 · SSO/MFA · 实名认证
│
└── 服务实例 (Instance)
    │  资源隔离 · 多云多地域 · Instance Role
    │
    └── 工作空间 (Workspace)
        │  业务隔离 · Workspace Role · VCluster 绑定 · 任务调度
        │
        ├── Schema（数据库/命名空间）
        │   │  MANAGED / EXTERNAL 类型
        │   │
        │   ├── 内部表 (Managed Table)     — Iceberg · ACID · Time Travel · 索引
        │   ├── 外部表 (External Table)    — Delta/Hudi/Kafka · 只读
        │   ├── 视图 (View)               — 虚拟 · 无存储
        │   ├── 动态表 (Dynamic Table)    — 声明式增量刷新
        │   ├── 物化视图 (Materialized View) — 预计算 · 定时刷新
        │   ├── Volume                    — User/Table/External(OSS/S3/COS)
        │   ├── Table Stream              — CDC 变更捕获
        │   ├── Pipe                      — Kafka/OSS 持续导入
        │   ├── 函数 / External Function  — SQL UDF / Python / Java
        │   ├── 索引                      — BloomFilter / Inverted / Vector(HNSW)
        │   └── 同义词 (Synonym)          — 跨 Schema 别名
        │
        ├── Share                         — 跨账户零拷贝数据共享
        ├── Connection                    — Storage(OSS/COS/S3) / API(云函数)
        └── External Catalog              — Hive HMS / Iceberg REST / Databricks Unity
```

---

## 工作空间（Workspace）详解

### 核心定位

Workspace 是 ClickZetta 中**业务隔离的最小单元**，也是连接时必须指定的对象。

- 等同于 Snowflake 的 **Database**，或 Databricks 的 **Catalog**
- 每个 Workspace 有独立的：用户角色、VCluster、任务调度、INFORMATION_SCHEMA
- 连接参数中的 `workspace` 字段即指定此对象

### 管理命令

```sql
-- 查看所有工作空间（需 instance_admin）
SHOW WORKSPACES;

-- 查看工作空间详情
DESC WORKSPACE my_workspace;

-- 修改注释
ALTER WORKSPACE my_workspace SET COMMENT '生产环境';

-- 查看属性
SHOW PROPERTIES IN WORKSPACE my_workspace;
```

### DESC WORKSPACE 输出字段

| 字段 | 说明 |
|---|---|
| name | 工作空间名称 |
| creator | 创建者 |
| created_time | 创建时间 |
| last_modified_time | 最后修改时间 |
| comment | 注释 |

---

## Schema 详解

### 核心定位

Schema 是 ClickZetta 中的**命名空间**，用于组织数据对象。

- 等同于传统数据库的 **Database** 或 **Schema**（注意：不同系统叫法不同）
- 是权限授予的边界（可对整个 Schema 授权）
- 类型：`MANAGED`（平台托管存储）/ `EXTERNAL`（外部数据湖路径）

### 管理命令

```sql
-- 创建 Schema
CREATE SCHEMA my_schema;

-- 创建外部 Schema（指向外部数据湖）
CREATE EXTERNAL SCHEMA ext_schema LOCATION 'oss://bucket/path/';

-- 切换默认 Schema
USE SCHEMA my_schema;

-- 查看所有 Schema
SHOW SCHEMAS;

-- 查看 Schema 详情
DESC SCHEMA my_schema;

-- 修改 Schema
ALTER SCHEMA my_schema RENAME TO new_schema;
ALTER SCHEMA my_schema SET COMMENT '数据仓库层';

-- 删除 Schema（需先删除其中的对象）
DROP SCHEMA my_schema;
DROP SCHEMA IF EXISTS my_schema CASCADE;  -- 级联删除所有对象
```

---

## VCluster（计算集群）详解

### 三种类型对比

| 属性 | 通用型 (GENERAL) | 分析型 (ANALYTICS) | 同步型 (INTEGRATION) |
|---|---|---|---|
| 适用场景 | ETL、批量导入、Ad-Hoc | 高并发 BI、在线查询 | 数据集成、CDC 同步 |
| 弹性方式 | 纵向（规格扩缩） | 横向（副本数 1-10） | — |
| 最小规格 | 1 CRU | 1 CRU | 0.25 CRU |
| 最大规格 | 256 CRU | 256 CRU | 256 CRU |
| 规格步长 | 1 CRU | 2^n CRU | 0.25 CRU |
| 本地缓存 | 不支持 | 支持（PRELOAD） | 不支持 |
| 小文件合并 | 支持（Dynamic Table 推荐） | 不支持 | — |

### 任务类型与集群对应

| 任务类型 | 推荐集群 |
|---|---|
| SQL ETL / 批量导入 | 通用型 |
| Ad-Hoc 查询 / BI | 分析型 |
| Dynamic Table（低频大量） | 通用型 |
| Dynamic Table（高频小量） | 分析型 |
| 离线同步 / 实时同步 / CDC | 同步型 |
| Python / Shell / JDBC 任务 | 不使用 VCluster |

### 管理命令

```sql
-- 创建通用型集群
CREATE VCLUSTER my_gp TYPE GENERAL SIZE 4;

-- 创建分析型集群（弹性 1-4 副本）
CREATE VCLUSTER my_ap TYPE ANALYTICS SIZE 8 MIN_INSTANCE 1 MAX_INSTANCE 4;

-- 启动 / 停止
ALTER VCLUSTER my_gp RESUME;
ALTER VCLUSTER my_gp SUSPEND;

-- 查看所有集群
SHOW VCLUSTERS;
```

---

## 用户与权限体系

### 用户层级

```
全局账号用户（Global User）
│  在账户层面管理，user_name 全局唯一
│
└── 服务实例用户（Instance User）
    │  全局用户自动同步，默认获得 instance_user 角色（无数据权限）
    │
    └── 工作空间用户（Workspace User）
        通过 GRANT ROLE 授予工作空间角色后才能操作数据
```

### 用户类型

| 类型 | 说明 |
|---|---|
| 普通用户 | 代表实际人员，可 Web 登录 |
| 系统服务用户 | 平台内置，默认禁用（如 sysservice_auto_mv） |
| 自定义服务用户 | 用于自动化程序，不可 Web 登录，可用 JDBC |

### 预置角色

| 角色 | 级别 | 权限范围 |
|---|---|---|
| instance_admin | 实例级 | 管理所有工作空间、用户、External Catalog |
| instance_user | 实例级 | 默认角色，无数据权限 |
| workspace_admin | 工作空间级 | 管理空间内所有对象和用户 |
| workspace_dev | 工作空间级 | 读写权限 + 任务管理 |
| workspace_analyst | 工作空间级 | 只读权限 |

### 授权命令

```sql
-- 将角色授予用户
GRANT ROLE workspace_dev TO USER alice;

-- 授予表权限
GRANT SELECT ON TABLE my_schema.my_table TO ROLE analyst_role;
GRANT SELECT ON ALL TABLES IN SCHEMA my_schema TO ROLE analyst_role;

-- 授予 information_schema 查询权限
GRANT ALL ON ALL VIEWS IN SCHEMA information_schema TO ROLE analyst_role;

-- 撤销权限
REVOKE SELECT ON TABLE my_schema.my_table FROM ROLE analyst_role;

-- 创建自定义角色（仅工作空间级，仅 SQL）
CREATE ROLE my_custom_role;
```

---

## 数据类型速查

| 分类 | 类型 |
|---|---|
| 整数 | TINYINT / SMALLINT / INT / BIGINT |
| 浮点 | FLOAT / DOUBLE / DECIMAL(p,s) |
| 字符串 | CHAR(n) / VARCHAR(n) / STRING（最大 16MB） |
| 时间 | DATE / TIMESTAMP（带时区 LTZ）/ TIMESTAMP_NTZ / INTERVAL |
| 布尔 | BOOLEAN |
| 复杂 | ARRAY\<T\> / MAP\<K,V\> / STRUCT\<field:type,...\> |
| AI 专用 | VECTOR(FLOAT, n)（最大 65535 维）/ VECTOR(TINYINT, n) |
| 特殊 | JSON / BINARY / BITMAP（Roaring Bitmap） |

---

## 平台架构层次

```
客户端层：Studio IDE · JDBC/ODBC · Python SDK · ZettaPark · BI 工具 · MCP Server
    ↓
计算层：VCluster（GENERAL / ANALYTICS / INTEGRATION）
    ↓
服务层：SQL 解析优化 · 向量化执行引擎 · Dynamic Table · AI Gateway · Result Cache
    ↓
存储层：内部表(Iceberg) · 外部表 · Volume · Time Travel · External Catalog · Share
    ↓
底层对象存储：阿里云 OSS · AWS S3 · 腾讯云 COS
```

**存算分离**：计算层和存储层独立扩展，VCluster 停止时不产生计算费用，存储按 GiB 计费。

---

## 数据对象横向对比

### Dynamic Table vs Materialized View vs View

| 维度 | 动态表 (Dynamic Table) | 物化视图 (Materialized View) | 视图 (View) |
|---|---|---|---|
| 数据存储 | 有（物化） | 有（物化） | 无（虚拟） |
| 刷新方式 | 自动增量/全量（CBO 决策） | 手动或定时全量 | 每次查询实时执行 |
| 最小刷新间隔 | 1 分钟 | 无限制（手动） | — |
| Time Travel | 支持 | 不支持 | 不支持 |
| UNDROP | 支持 | 不支持 | 不支持 |
| CREATE OR REPLACE | 支持（保留数据和权限） | 支持 | 支持 |
| 推荐集群 | GP（通用型） | GP 或 AP | — |
| 适用场景 | 实时 ETL、多层级联 | BI 加速、固定聚合 | 简单逻辑封装 |

### Table Stream 两种模式

| 模式 | 捕获内容 | 典型用途 |
|---|---|---|
| STANDARD | INSERT + UPDATE_BEFORE + UPDATE_AFTER + DELETE | CDC UPSERT，MERGE INTO 消费 |
| APPEND_ONLY | 仅 INSERT | 日志追加，简单 ETL |

**STANDARD 模式的 delta 语义**：记录两个 offset 之间的净变化。若一行先 INSERT 后 DELETE，delta 中该行消失（不会出现 INSERT+DELETE 两条记录）。

### Pipe 两种导入模式

| 模式 | 触发方式 | 适用场景 | 云支持 |
|---|---|---|---|
| LIST_PURGE | 定期扫描 Volume 目录 | 通用，任何对象存储 | 全部 |
| EVENT_NOTIFICATION | 云消息队列事件触发 | 低延迟，近实时 | 仅阿里云 OSS + AWS S3 |

---

## 地域与连接信息

| 云服务商 | 地域 | 区域代码 | API Endpoint |
|---|---|---|---|
| 阿里云 | 华东2（上海） | cn-shanghai-alicloud | cn-shanghai-alicloud.api.clickzetta.com |
| 腾讯云 | 华东（上海） | ap-shanghai-tencentcloud | ap-shanghai-tencentcloud.api.clickzetta.com |
| 腾讯云 | 华北（北京） | ap-beijing-tencentcloud | ap-beijing-tencentcloud.api.clickzetta.com |
| 腾讯云 | 华南（广州） | ap-guangzhou-tencentcloud | ap-guangzhou-tencentcloud.api.clickzetta.com |
| AWS | 北京 | cn-north-1-aws | cn-north-1-aws.api.clickzetta.com |

JDBC URL 格式：`jdbc:clickzetta://<instance_name>.<region_id>.api.clickzetta.com/`

