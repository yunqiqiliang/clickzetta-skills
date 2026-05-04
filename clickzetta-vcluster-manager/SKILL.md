---
name: clickzetta-vcluster-manager
description: |
  管理 ClickZetta Lakehouse 计算集群（VCluster）的完整生命周期。
  覆盖创建（通用型/分析型/同步型）、启动/停止、规格调整、弹性扩缩容、
  缓存配置（PRELOAD_TABLES）、查看集群状态等操作。
  当用户说"创建集群"、"计算集群"、"VCluster"、"启动集群"、"停止集群"、
  "调整集群规格"、"集群扩容"、"集群缩容"、"自动停止"、"自动启动"、
  "预加载缓存"、"PRELOAD"、"集群类型"、"GP集群"、"AP集群"、"分析型集群"、
  "通用型集群"、"同步型集群"时触发。
  Keywords: VCluster, compute cluster, create, suspend, resume, resize, auto-scale
---

# ClickZetta 计算集群管理

阅读 [references/vcluster-ddl.md](references/vcluster-ddl.md) 了解完整语法。

## 集群类型选择

| 类型 | 关键字 | 适用场景 | 扩缩容方式 |
|---|---|---|---|
| 通用型（GP） | `GENERAL` | 离线 ETL、数据摄取、综合场景 | 纵向（规格大小） |
| 分析型（AP） | `ANALYTICS` | 高并发在线查询、BI 报表、Ad-Hoc | 横向（副本数） |
| 同步型 | `INTEGRATION` | 数据集成同步任务 | 纵向（规格大小） |

**规格单位**：CRU（Compute Resource Unit）
- 通用型/同步型：1-256 CRU，步长 1（同步型额外支持 0.25、0.5）
- 分析型：1-256 CRU，须为 2 的 n 次幂（1、2、4、8、16...）

---

## 创建集群

```sql
-- 通用型：离线 ETL，8 CRU，作业完成后 60 秒自动停止
CREATE VCLUSTER IF NOT EXISTS etl_vc
  VCLUSTER_TYPE = GENERAL
  VCLUSTER_SIZE = 8
  AUTO_SUSPEND_IN_SECOND = 60
  AUTO_RESUME = TRUE
  COMMENT '离线ETL专用集群';

-- 通用型：弹性规格（1-16 CRU）
CREATE VCLUSTER IF NOT EXISTS etl_elastic_vc
  VCLUSTER_TYPE = GENERAL
  MIN_VCLUSTER_SIZE = 1
  MAX_VCLUSTER_SIZE = 16
  AUTO_SUSPEND_IN_SECOND = 300;

-- 分析型：BI 报表，4 CRU，1-10 副本，最大 80 并发
CREATE VCLUSTER IF NOT EXISTS bi_vc
  VCLUSTER_TYPE = ANALYTICS
  VCLUSTER_SIZE = 4
  MIN_REPLICAS = 1
  MAX_REPLICAS = 10
  MAX_CONCURRENCY = 8
  AUTO_SUSPEND_IN_SECOND = 1800
  AUTO_RESUME = TRUE
  COMMENT 'BI报表在线查询集群';

-- 同步型：数据集成任务
CREATE VCLUSTER IF NOT EXISTS sync_vc
  VCLUSTER_TYPE = INTEGRATION
  VCLUSTER_SIZE = 1
  AUTO_RESUME = TRUE;
```

---

## 启动 / 停止

```sql
-- 启动集群
ALTER VCLUSTER IF EXISTS etl_vc RESUME;

-- 正常停止（等待当前作业完成）
ALTER VCLUSTER IF EXISTS etl_vc SUSPEND;

-- 强制停止（立即中断所有作业）
ALTER VCLUSTER IF EXISTS etl_vc SUSPEND FORCE;

-- 取消集群中所有作业
ALTER VCLUSTER IF EXISTS etl_vc CANCEL ALL JOBS;
```

---

## 修改集群属性

```sql
-- 调整规格
ALTER VCLUSTER IF EXISTS etl_vc SET VCLUSTER_SIZE = 16;

-- 修改自动停止时间
ALTER VCLUSTER IF EXISTS etl_vc SET AUTO_SUSPEND_IN_SECOND = 300;

-- 分析型：调整副本数和并发
ALTER VCLUSTER IF EXISTS bi_vc SET
  MIN_REPLICAS = 2
  MAX_REPLICAS = 5
  MAX_CONCURRENCY = 16;

-- 修改注释
ALTER VCLUSTER IF EXISTS etl_vc SET COMMENT '新注释';
```

---

## 缓存配置（仅分析型）

阅读 [references/vc-cache.md](references/vc-cache.md) 了解缓存详情。

```sql
-- 设置预加载表（覆盖写，需带上所有已有表）
ALTER VCLUSTER bi_vc SET PRELOAD_TABLES = "public.orders,public.customers";

-- 查看当前集群缓存状态
SHOW PRELOAD CACHED STATUS;

-- 查看指定集群缓存状态
SHOW VCLUSTER bi_vc PRELOAD CACHED STATUS;
```

---

## 查看集群信息

```sql
-- 列出所有集群
SHOW VCLUSTERS;

-- 按类型过滤
SHOW VCLUSTERS WHERE vcluster_type = 'ANALYTICS';
SHOW VCLUSTERS WHERE state = 'SUSPENDED';

-- 按名称模糊匹配
SHOW VCLUSTERS LIKE 'etl%';

-- 查看集群详情
DESC VCLUSTER etl_vc;
DESC VCLUSTER EXTENDED bi_vc;
```

---

## 删除集群

```sql
-- 等待当前作业完成后删除
DROP VCLUSTER IF EXISTS etl_vc;

-- 立即强制删除（中断正在运行的作业）
DROP VCLUSTER IF EXISTS etl_vc FORCE;
```

---

## 切换当前会话集群

```sql
USE VCLUSTER bi_vc;
```

---

## 典型场景

### 场景 1：离线 ETL 集群

```sql
CREATE VCLUSTER IF NOT EXISTS etl_daily
  VCLUSTER_TYPE = GENERAL
  VCLUSTER_SIZE = 8
  AUTO_SUSPEND_IN_SECOND = 60
  AUTO_RESUME = TRUE
  COMMENT '每日ETL作业，完成后1分钟自动停止';
```

### 场景 2：在线 BI 报表集群（高并发）

```sql
CREATE VCLUSTER IF NOT EXISTS bi_online
  VCLUSTER_TYPE = ANALYTICS
  VCLUSTER_SIZE = 4
  MIN_REPLICAS = 1
  MAX_REPLICAS = 10
  MAX_CONCURRENCY = 8
  AUTO_SUSPEND_IN_SECOND = 1800
  AUTO_RESUME = TRUE
  COMMENT 'BI在线查询，最大支持80并发';
```

### 场景 3：数据集成同步集群

```sql
CREATE VCLUSTER IF NOT EXISTS cdc_sync
  VCLUSTER_TYPE = INTEGRATION
  VCLUSTER_SIZE = 0.5
  AUTO_RESUME = TRUE
  COMMENT '轻量CDC同步任务';
```

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 分析型集群规格报错 | 规格须为 2 的 n 次幂 | 使用 1、2、4、8、16、32... |
| PRELOAD_TABLES 不生效 | 仅 AP 型集群支持 | 确认集群类型为 ANALYTICS |
| 添加预加载表后原有表消失 | PRELOAD_TABLES 是覆盖写 | 设置时带上所有已有表 |
| 集群停止后缓存丢失 | 本地缓存随集群停止释放 | 重启后自动重新加载 PRELOAD 表 |
