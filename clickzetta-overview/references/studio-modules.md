# Studio 各模块详细说明

> 来源：https://www.yunqi.tech/documents/LakehouseStudioTour 等官方文档

---

## 任务类型完整列表

| 任务类型 | 触发方式 | 使用 VCluster | 典型用途 |
|---|---|---|---|
| SQL 任务 | 周期调度 / 手动 | GP 或 AP | ETL、Ad-Hoc 查询、DDL 操作 |
| Python 任务 | 周期调度 / 手动 | 不使用 | ZettaPark 数据处理、文件操作 |
| Shell 任务 | 周期调度 / 手动 | 不使用 | 系统命令、文件处理 |
| JDBC 任务 | 周期调度 / 手动 | 不使用 | 操作 MySQL/Hive/ClickHouse 等 |
| 动态表任务 | 向导式创建 | GP 或 AP | 声明式增量计算 |
| 离线同步任务 | 周期调度 | 同步型 | 全量/增量批量同步 |
| 实时同步任务（单表） | 持续运行 | 同步型 | Kafka/MySQL/PG 实时写入 |
| 多表实时 CDC | 持续运行 | 同步型 | 整库镜像、分库分表合并 |
| 组合任务 | 周期调度 | 取决于子任务 | 封装多个任务统一调度 |
| 虚拟节点 | 周期调度 | 不使用 | 占位节点，用于依赖编排 |

---

## 任务状态说明

| 状态 | 含义 |
|---|---|
| 已提交，有修改 | 任务已提交到生产，但本地有未提交的修改 |
| 已提交，无修改 | 生产版本与本地版本一致 |
| 已下线 | 任务已停止调度 |
| 未提交 | 仅在开发环境，未发布到生产 |

---

## 调度配置关键参数

### Cron 表达式示例

```
# 每天凌晨 2 点执行
0 2 * * *

# 每小时执行一次
0 * * * *

# 每 5 分钟执行一次
*/5 * * * *

# 每月 1 号凌晨 1 点执行
0 1 1 * *
```

### 依赖策略

| 策略 | 说明 | 适用场景 |
|---|---|---|
| 默认 | 上游当天实例完成后触发下游 | 标准 ETL 链路 |
| 向前 | 上游最近一个完成的实例触发 | 上游频率高于下游 |
| 向前就近 | 上游最近且时间最接近的实例触发 | 时间对齐要求高 |

---

## 任务参数内置时间函数

| 表达式 | 含义 | 示例（今天 2024-01-15） |
|---|---|---|
| `$[yyyy-MM-dd]` | 当天日期 | 2024-01-15 |
| `$[yyyy-MM-dd, -1d]` | 昨天 | 2024-01-14 |
| `$[yyyy-MM-dd, +1d]` | 明天 | 2024-01-16 |
| `$[yyyyMM]` | 当月 | 202401 |
| `$[yyyyMM, -1M]` | 上月 | 202312 |
| `$[yyyy-MM-dd HH:mm:ss]` | 当前时间 | 2024-01-15 10:30:00 |
| `$[HH:mm:ss]` | 当前时间（仅时分秒） | 10:30:00 |
| `sys_plan_datetime` | 任务计划执行时间 | 系统内置参数 |

---

## 数据质量规则六大维度

| 维度 | 说明 | 示例规则 |
|---|---|---|
| 完整性 | 字段非空率 | `user_id` 非空率 ≥ 99% |
| 唯一性 | 主键/唯一键重复检测 | `order_id` 无重复 |
| 一致性 | 跨表数据一致 | 订单表与明细表金额一致 |
| 准确性 | 数值范围合理性 | `age` 在 0-150 之间 |
| 有效性 | 格式/枚举值合法 | `status` 在 ['active','inactive'] 中 |
| 及时性 | 数据更新时效 | 每天 8 点前数据已更新 |

### 触发方式

- **定时触发**：Cron 表达式，独立于任务调度
- **调度任务触发**：绑定到某个 SQL/同步任务，任务完成后自动触发质量检测
- **手动触发**：在 Studio 界面手动执行

---

## 数据目录（Data Catalog）功能

### 表详情页六大 Tab

| Tab | 内容 |
|---|---|
| 详情 | DDL 语句（一键复制）、权限管理入口 |
| 字段 | 字段名/类型/描述/主键/标准化标签 |
| 预览 | 100 行数据预览（需 SELECT 权限 + 指定 VCluster） |
| 血缘 | 上下游表关系图（数据血缘） |
| 作业 | 该表相关的查询历史 |
| 上传 | 本地文件直接上传到表 |

### 搜索支持的过滤条件

- 对象类型：Table / View / Materialized View
- 工作空间 / Schema
- 创建时间范围
- 负责人

---

## 运维监控告警

### 内置告警规则

| 规则 | 触发条件 |
|---|---|
| 周期任务实例运行失败 | 任务实例执行失败 |
| 数据质量检测失败 | 质量规则校验不通过 |
| Pipe 延迟告警 | Kafka/OSS Pipe 消费延迟超阈值 |
| 同步任务失败 | 离线/实时同步任务异常 |
| 自定义规则 | 用户自定义 SQL 条件 |

### 告警通知渠道

- 飞书 webhook
- 企业微信 webhook
- 邮件（部分版本）

---

## 数据同步支持的数据源（部分）

### 离线同步（批量）

MySQL · PostgreSQL · SQL Server · Oracle · Aurora · PolarDB · ClickHouse · Hive · HDFS · OSS/S3/COS · Lakehouse

### 实时同步（CDC）

MySQL（Binlog）· PostgreSQL（WAL）· Kafka（JSON/Avro/CSV）

### 连接方式

- 公网直连
- SSH Tunnel（连接 VPC 内数据库）
- 私网连接（PrivateLink）

---

## Python 任务中使用数据源

Studio Python 任务内置 `clickzetta-dbutils` 工具包，可直接使用预配置的数据源：

```python
from clickzetta import dbutils

# 使用预配置的 Lakehouse 数据源
conn = dbutils.get_connection('my_lakehouse_datasource')
cursor = conn.cursor()
cursor.execute("SELECT * FROM my_schema.my_table LIMIT 10")
rows = cursor.fetchall()
print(rows)

# 使用预配置的 MySQL 数据源
mysql_conn = dbutils.get_connection('my_mysql_datasource')
```
