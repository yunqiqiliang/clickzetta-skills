---
name: clickzetta-pipeline-review
description: |
  对 ClickZetta Lakehouse 数据管道进行全面 Review 与诊断。从任意入口（任务名/schema/表名/
  业务域关键词）出发，自主发现管道涉及的全部对象（Studio 任务、Lakehouse 表、管道对象、
  运行记录），识别调度依赖缺失、DDL 幂等问题、分层跳层、DT 反模式等常见问题，
  给出优先级排序的修复建议并执行。
  当用户说"Review 管道"、"检查数据管道"、"管道诊断"、"管道有问题"、"任务跑失败了"、
  "数据不对"、"管道 Review"、"pipeline review"、"检查 ETL"、"管道健康检查"、
  "数据链路检查"、"管道全貌"、"管道梳理"时触发。
  Keywords: pipeline review, diagnosis, task dependency, data lineage, DT health, pipeline discovery
---

# ClickZetta 数据管道 Review 指南

## 向导：收集必要信息

收到 Review 请求后，**不要立即开始探索**。先通过向导收集必要信息，再启动五阶段流程。

### 第 0 步：信息收集（必须完成，不得跳过）

向用户提出以下问题（一次性问完，不要逐一追问）：

> 为了开始管道 Review，需要确认几个信息：
>
> **1. 管道入口**（选一个或多个）：
> - 业务域/项目名称（如"shenyu_gateway"、"ecommerce_order"）
> - Studio 任务目录名或任务 ID
> - Lakehouse schema 名称
> - 具体表名或 Pipe/DT 名称
>
> **2. Review 范围**（选一个）：
> - A. 全量 Review（发现所有问题，给出完整报告）
> - B. 专项诊断（只看某类问题，如"任务依赖"、"DT 刷新失败"、"数据不一致"）
> - C. 快速健康检查（只看 P0 问题，5 分钟内出结论）
>
> **3. 执行权限**（影响能做什么）：
> - 只读（只能查，不能改）
> - 可读写（可以执行修复操作）
>
> **4. 已知症状**（可选，有助于快速定位）：
> - 有没有具体的报错信息、失败的任务名、或数据异常的表？

### 根据回答调整策略

| Review 范围 | 执行权限 | 策略 |
|---|---|---|
| 全量 Review | 可读写 | 走完五阶段，发现问题后询问是否执行修复 |
| 全量 Review | 只读 | 走完五阶段，输出问题报告，不执行修复 |
| 专项诊断 | 任意 | 只执行对应阶段的检查项，跳过无关步骤 |
| 快速健康检查 | 任意 | 只检查 P0 问题（依赖缺失、DT 持续失败），5 分钟内出结论 |

**如果用户已经在请求中提供了足够信息（如"帮我 Review shenyu_gateway 管道，全量 Review，可以修复"），直接进入第一阶段，不再重复询问。**

---

## 工作模式：五阶段 Review 流程

收集到必要信息后，按以下五阶段执行：

```
发现 → 分析 → 识别问题 → 执行修复 → 验证
```

---

## 第一阶段：发现（管道全貌探索）

### 入口识别

用户可能从任意层给出入口，从入口向上下游展开：

| 用户给出的入口 | 展开方向 |
|---|---|
| 业务域关键词（如"shenyu_gateway"） | 同时搜索 Studio 任务和 Lakehouse schema |
| Studio 任务名/目录 | 读任务脚本 → 找涉及的表 → 找上下游任务 |
| Lakehouse 表名/schema | 找写入该表的任务 → 找读取该表的 DT/任务 |
| 管道对象（Pipe/DT/Stream） | 找源表和目标表 → 找关联任务 |
| 错误信息/运行 ID | 先定位任务 → 再展开全貌 |

### 探索四层

**无论入口是什么，都要探索以下四层，缺一不可：**

**层 1 — Studio 任务层**
```bash
# 按业务域关键词找任务目录
cz-cli task list-folders

# 列出目录下所有任务
cz-cli task list --folder <folder>

# 读每个任务的脚本和配置（重点看：task_type、cron_express、task_dependencies、edit_state）
cz-cli task content <task_id>
```

**层 2 — Lakehouse 对象层**
```sql
-- 找相关 schema
SHOW SCHEMAS;

-- 列出各层表
SHOW TABLES IN <ods_schema>;
SHOW TABLES IN <dwd_schema>;
SHOW TABLES IN <dws_schema>;
SHOW TABLES IN <ads_schema>;

-- 找 Dynamic Table
SHOW TABLES IN <schema> WHERE is_dynamic;

-- 找 Pipe
SHOW PIPES;

-- 找 Table Stream
SHOW TABLE STREAMS;
```

**层 3 — 运行记录层**（配置是"应该怎样"，运行记录是"实际怎样"）
```bash
# 查每个关键任务的最近运行记录
cz-cli runs list --task <task_name> --limit 10

# 发现失败时查日志
cz-cli runs logs <run_id>

# 查运行统计（成功率、平均耗时）
cz-cli runs stats --task <task_name>
```

**层 4 — 管道对象状态层**
```sql
-- Dynamic Table 刷新历史（每张 DT 都要查）
SHOW DYNAMIC TABLE REFRESH HISTORY <schema>.<table> LIMIT 10;

-- Pipe 状态
DESC PIPE <pipe_name>;

-- Table Stream 积压
SELECT COUNT(*) FROM <stream_name>;
```

### 发现阶段输出

完成四层探索后，向用户呈现管道全貌摘要：
```
管道全貌：
- Studio 任务：N 个（列出名称、类型、状态、cron）
- ODS 层：N 张表
- DWD 层：N 张表
- DWS/ADS 层：N 张 Dynamic Table
- 管道对象：Pipe × N，Table Stream × N
- 运行记录：最近 N 次，成功率 X%
```

---

## 第二阶段：分析（深度读取）

发现阶段只是"找到了什么"，分析阶段要"读懂内容"：

```bash
# 读每个任务的完整脚本
cz-cli task content <task_id>

# 重点关注：
# - task_dependencies：是否配置了上下游依赖
# - cron_express：调度时间是否合理
# - edit_state：20=DRAFT，30=PUBLISHED
# - task_type：SQL任务/同步任务/实时同步
```

**同步任务运行模式判断（不能只看单一字段）：**

| 字段 | 不能单独判断 | 需要综合判断 |
|---|---|---|
| `readMode: BINLOG` | ❌ 不代表 CDC 实时 | 还需看 cron_express、pkWriteMode、运行记录 |
| `pkWriteMode: OVERWRITE` | 覆盖写 → 离线批量 | 结合 cron 和运行记录确认 |
| 运行记录只有 1 条手动触发 | → 定时调度可能未生效 | 需确认 cron 是否正常触发 |

**综合判断规则**：
- `cron_express` 有值 + `pkWriteMode: OVERWRITE` + 运行记录为定时触发 → **离线批量同步**
- `cron_express` 为空 + 任务持续运行状态 → **实时同步（CDC/Kafka）**
- 运行记录全是手动触发 → **调度未生效，需排查**

---

## 第三阶段：识别问题

### 检查清单（按优先级）

**🔴 P0 — 调度依赖缺失**

```bash
# 检查每个 ETL/转换任务的依赖配置
cz-cli task content <task_id>
# 查看 task_dependencies 字段是否为空数组 []
```

- ETL 转换任务的 `task_dependencies` 为空 → **P0，必须修复**
- 上游同步任务未完成时下游就开始执行 → 读到旧数据或空数据
- 运行记录时间线混乱（多次手动触发、时间间隔异常）→ 依赖缺失的典型症状

**🔴 P0 — Dynamic Table 刷新持续失败**

```sql
SHOW DYNAMIC TABLE REFRESH HISTORY <schema>.<table> LIMIT 10;
-- status 连续出现 FAILED → P0
```

**🟡 P1 — DDL 幂等性问题**

Dynamic Table 的 DDL 应统一使用 `CREATE OR REPLACE`，不要用 `DROP + CREATE` 两步：
- `DROP` 和 `CREATE` 之间存在竞态条件
- 如果 `CREATE` 失败，表已被删除，数据丢失

```sql
-- ❌ 有竞态风险
DROP DYNAMIC TABLE IF EXISTS schema.table;
CREATE DYNAMIC TABLE schema.table ...;

-- ✅ 原子操作
CREATE OR REPLACE DYNAMIC TABLE schema.table ...;
```

> ⚠️ `CREATE OR REPLACE` 有类型变更限制：字段类型变更（如 `TINYINT → BOOLEAN`）会报错。
> 解决方案：用 `CAST(col AS TINYINT)` 保持类型兼容，或先 `DROP` 再 `CREATE`。

**🟡 P1 — DWS 层跳过 DWD 直接读 ODS**

```sql
-- 检查 DWS 层 DT 的 SQL 定义，看 FROM 子句引用的是哪一层
SHOW CREATE TABLE <dws_schema>.<table>;
```

- DWS 层应从 DWD 层读取，不应直接读 ODS
- 跳层问题：重复计算（DWD 已做的 JSON 解析/类型转换在 DWS 又做一遍）、口径不一致、维护成本高

**🟡 P1 — Dynamic Table 定义中包含 ORDER BY**

```sql
-- 查看 DT 定义
SHOW CREATE TABLE <schema>.<dt_name>;
-- 如果 AS 子句中有 ORDER BY → 需要移除
```

- DT 的 `ORDER BY` 仅在查询时生效，不影响存储顺序
- 每次刷新额外消耗计算资源做排序，无实际收益
- 排序逻辑应放在查询端（BI 工具或下游 SQL）

**🟢 P2 — DDL 任务保留 Cron 配置**

```bash
cz-cli task content <ddl_task_id>
# edit_state=20（DRAFT）但 cron_express 不为空 → P2
```

- DRAFT 状态不会实际执行，但保留 Cron 配置容易误导维护者
- 建议清理，非紧急

**🟢 P2 — Studio 任务脚本与实际 DT 定义不一致**

直接通过 SQL 重建 DT 后，Studio 任务脚本不会自动同步：

```bash
# 检查：读 Studio 任务脚本
cz-cli task content <task_id>

# 对比：读实际 DT 定义
# write_query: SHOW CREATE TABLE <schema>.<table>

# 如果不一致，同步 Studio 任务脚本
cz-cli task save-content <task_id> --content "<new_sql>"
```

---

## 第四阶段：执行修复

### 修复依赖配置

```bash
# 为 ETL 任务配置上游依赖
cz-cli task save-config <task_id> --deps replace \
  --dep-tasks '[{"taskId":<upstream_id>,"taskName":"<upstream_name>"}]'

# 部署生效
cz-cli task deploy <task_id> -y
```

### 修复 DT DDL（统一为 CREATE OR REPLACE）

```sql
-- 先确认字段类型，避免类型变更报错
SHOW CREATE TABLE <schema>.<table>;

-- 执行重建（如有类型变更，用 CAST 保持兼容）
CREATE OR REPLACE DYNAMIC TABLE <schema>.<table>
  REFRESH INTERVAL <n> <unit> vcluster <gp_cluster>
AS
SELECT ...
FROM <dwd_schema>.<table>  -- 确保从 DWD 层读取，不跳层
...;  -- 移除 ORDER BY

-- 立即触发首次刷新
REFRESH DYNAMIC TABLE <schema>.<table>;
```

### 同步 Studio 任务脚本

```bash
# SQL 重建 DT 后，同步 Studio 任务脚本保持一致
cz-cli task save-content <task_id> --content "<updated_sql>"
```

### 执行原则

- **直接 SQL 操作**（重建 DT、修改表结构）→ 用 `write_query`，执行前向用户确认
- **Studio 任务配置**（依赖、Cron、脚本）→ 用 `cz-cli task save-*` + `deploy`
- **两者都改时**：先改 SQL（数据层），再同步 Studio（配置层）

---

## 第五阶段：验证

修复完成后，**逐项验证**，不跳过：

```sql
-- 1. Dynamic Table 刷新状态
SHOW DYNAMIC TABLE REFRESH HISTORY <schema>.<table> LIMIT 5;
-- 确认最近一次 status = SUCCESS

-- 2. 各层行数
SELECT COUNT(*) FROM <ods_schema>.<table>;
SELECT COUNT(*) FROM <dwd_schema>.<table>;
SELECT COUNT(*) FROM <dws_schema>.<table>;

-- 3. 关键字段非空率
SELECT ROUND(COUNT(key_field) * 100.0 / COUNT(*), 2) AS non_null_pct
FROM <schema>.<table>;
```

```bash
# 4. 确认任务依赖已生效
cz-cli task content <task_id>
# 查看 task_dependencies 不再为空

# 5. 确认 Studio 任务脚本已同步
cz-cli task content <task_id>
# 对比脚本内容与实际 DT 定义一致
```

向用户输出 Review 结论：
```
Review 结论：
- 发现问题：P0 × N，P1 × N，P2 × N
- 已修复：（列出每项）
- 未修复/建议：（列出每项及原因）
- 验证结果：各层行数、DT 刷新状态
```

---

## 常见问题速查

| 现象 | 根因 | 排查命令 |
|---|---|---|
| ETL 任务读到旧数据 | 依赖缺失，上游未完成就开始执行 | `cz-cli task content` 查 task_dependencies |
| 运行记录时间线混乱 | 依赖缺失，多次手动触发 | `cz-cli runs list` 看触发方式 |
| DT 刷新报"表已存在" | DROP+CREATE 竞态，或 CREATE OR REPLACE 类型冲突 | `SHOW CREATE TABLE` 确认字段类型 |
| DT 刷新时间与预期不符 | REFRESH INTERVAL 以创建时间为基准，不对齐整点 | 创建后立即执行 `REFRESH DYNAMIC TABLE` |
| Studio 脚本与实际 DT 不一致 | 直接 SQL 重建后未同步 Studio | `cz-cli task save-content` 同步 |
| 同步任务判断为 CDC 但实为离线 | 只看 readMode 字段，未综合判断 | 结合 cron、pkWriteMode、运行记录综合判断 |
| DWS 数据与 DWD 口径不一致 | DWS 跳层读 ODS，重复计算 | `SHOW CREATE TABLE` 检查 FROM 子句 |
