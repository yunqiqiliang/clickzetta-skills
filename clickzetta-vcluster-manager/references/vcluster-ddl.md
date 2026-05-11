# CREATE / ALTER / DROP VCLUSTER 参考

> 来源：https://www.yunqi.tech/documents/create_cluster 和 alter-vcluster 和 drop-vcluster

---

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

## CREATE VCLUSTER

```sql
CREATE VCLUSTER [IF NOT EXISTS] <name>
  VCLUSTER_TYPE = GENERAL | ANALYTICS | INTEGRATION
  VCLUSTER_SIZE = num                    -- 固定规格
  -- 或弹性规格（通用型/同步型）
  MIN_VCLUSTER_SIZE = num
  MAX_VCLUSTER_SIZE = num
  AUTO_SUSPEND_IN_SECOND = num           -- 空闲自动停止秒数，-1 表示不停止，默认 600
  AUTO_RESUME = TRUE | FALSE             -- 是否自动启动，默认 TRUE
  QUERY_RUNTIME_LIMIT_IN_SECOND = num    -- 单作业最大执行时长（秒），默认 86400
  [COMMENT '']
```

### 分析型专有参数

```sql
  MIN_REPLICAS = num          -- 最小实例数（1-10），默认 1
  MAX_REPLICAS = num          -- 最大实例数（1-10），默认 1
  MAX_CONCURRENCY = num       -- 每实例最大并发数（1-32），默认 8
  PRELOAD_TABLES = "schema.table1,schema.table2"  -- 预加载缓存表
```

### 示例

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

## ALTER VCLUSTER

```sql
-- 启动集群
ALTER VCLUSTER [IF EXISTS] <name> RESUME;

-- 停止集群
ALTER VCLUSTER [IF EXISTS] <name> SUSPEND [FORCE];

-- 取消集群中所有作业
ALTER VCLUSTER [IF EXISTS] <name> CANCEL ALL JOBS;

-- 修改属性
ALTER VCLUSTER [IF EXISTS] <name> SET
  VCLUSTER_SIZE = num
  AUTO_SUSPEND_IN_SECOND = num
  AUTO_RESUME = TRUE | FALSE
  MAX_CONCURRENCY = num          -- 仅分析型
  MIN_REPLICAS = num             -- 仅分析型
  MAX_REPLICAS = num             -- 仅分析型
  PRELOAD_TABLES = "schema.table";

-- 修改注释
ALTER VCLUSTER [IF EXISTS] <name> SET COMMENT '新注释';
```

---

## DROP VCLUSTER

```sql
-- 等待当前作业完成后删除
DROP VCLUSTER [IF EXISTS] <name>;

-- 立即强制删除（中断正在运行的作业）
DROP VCLUSTER [IF EXISTS] <name> FORCE;
```

---

## DESC / SHOW VCLUSTER

```sql
-- 查看集群基本信息
DESC VCLUSTER <name>;

-- 查看扩展信息
DESC VCLUSTER EXTENDED <name>;

-- 列出所有集群
SHOW VCLUSTERS;

-- 按类型过滤
SHOW VCLUSTERS WHERE vcluster_type = 'GENERAL';
SHOW VCLUSTERS WHERE state = 'SUSPENDED';
SHOW VCLUSTERS WHERE vcluster_type = 'ANALYTICS';

-- 按名称模糊匹配
SHOW VCLUSTERS LIKE 'etl%';
```

---

## USE VCLUSTER（切换当前会话集群）

```sql
USE VCLUSTER <name>;
```
