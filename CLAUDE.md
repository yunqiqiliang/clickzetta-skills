# ClickZetta Skills 开发规范

本文档为 AI Agent（Claude Code、czcode 等）和人类开发者提供 Skill 开发指南。

## 仓库结构

```
clickzetta-skills/
├── .well-known/skills/index.json   ← Skill 注册表（必须同步更新）
├── clickzetta-<name>/              ← 每个 Skill 一个目录
│   ├── SKILL.md                    ← 主入口（必须存在）
│   └── references/                 ← 参考文档（可选）
│       └── *.md
├── CLAUDE.md                       ← 本文件（开发规范）
└── README.md                       ← 仓库说明
```

## Skill 目录命名

- 统一前缀：`clickzetta-<功能名>`
- 使用小写 + 连字符：`clickzetta-dynamic-table`、`clickzetta-vcluster-manager`
- 名称应反映功能领域，不要过于具体

## SKILL.md 规范

### Front-matter（必须）

```yaml
---
name: clickzetta-<name>
description: |
  一段话描述 Skill 的功能范围。
  当用户说"关键词1"、"关键词2"、"关键词3"时触发。
  Keywords: english, keywords, for, LLM, matching
---
```

**要求：**
- `name` 必须与目录名一致
- `description` 包含中文触发词和英文 Keywords 行
- 触发词要覆盖用户可能的各种表述方式

### 内容结构（建议）

1. **快速入门** — 3-5 行最常用的 SQL 示例
2. **核心概念** — 简要说明关键概念
3. **详细参考** — 放在 `references/` 子目录
4. **常见问题** — 排障表（问题 | 原因 | 解决方案）

## cz-cli 命令引用规范

Skill 中引用 cz-cli 命令时，遵守以下原则：

### 只说"用哪个命令"，不硬编码参数

Skill 的职责是告诉 Agent **有哪些命令可用**，具体参数让用户或 Agent 通过 `--help` 查询。
命令参数会随版本迭代变化，硬编码在 Skill 里会导致文档过时。

```markdown
<!-- ✅ 正确：说明命令用途，参数指向 --help -->
配置调度：`cz-cli task save-cron <task> --help`
查看运行：`cz-cli runs list --task <task>`
补数据：`cz-cli runs refill <task> --help`

<!-- ❌ 错误：硬编码具体参数值 -->
cz-cli task save-cron "my_task" --cron "0 2 * * *" --vc DEFAULT
cz-cli runs refill my_task --from 2026-05-01 --to 2026-05-10 -y
```

**例外**：命令名本身（`--type SQL`、`-y`、`-o json`）和必填位置参数可以写出来，
因为这些是命令的核心语义，不会频繁变化。

### 安装和配置方式

不要在 Skill 里写具体的安装命令（`pip install`、`brew install` 等），
这些随平台和版本变化。统一写：

```markdown
已安装 cz-cli 并完成 profile 配置（`cz-cli profile status` 验证连接）
```

### UI_ONLY 任务类型说明

以下任务类型（SPARK/400、FLOW/500、INTEGRATION/1、REALTIME/14、DYNAMIC_TABLE/16、
STREAMING/17、FULL_INCREMENTAL/280、MULTI_REALTIME/281、MULTI_DI/291、
DATABRICKS_SQL/300、DATABRICKS_NOTEBOOK/301）的脚本内容必须在 Studio UI 中配置，
cz-cli 的 `task save-content` 对这些类型会报错拦截。

对这些类型，cz-cli 支持的操作是：
- `task create` — 创建任务，返回 `studio_url` 供用户在 UI 中配置
- `task content` — 查看任务信息（datasource_id、session_schema_name 等）
- `task save-cron` / `task save-config` — 配置调度和重试策略
- `task deploy` / `task undeploy` — 发布/下线
- `task execute` — 临时执行（测试自动化）
- `runs list` / `runs detail` / `attempts log` — 查看运行状态和日志
- `runs refill` — 补数据

在 Skill 中描述这类任务的工作流时，应明确说明：
> 内容配置（数据源选择、字段映射等）必须在 Studio UI 中完成，cz-cli 负责创建、调度和运维。

### 数据源类型

不要在 Skill 里硬编码数据源支持列表（容易过时），改为：
> 支持的数据源类型以 Studio UI 中显示为准，可通过 `cz-cli datasource list` 查看已配置的数据源

如果需要引用 dsType 数值（用于 API 调用或 agent 提示），参考以下映射：

| dsType | 名称 |
|--------|------|
| 1 | LakeHouse |
| 2 | Kafka |
| 3 | Hive |
| 4 | ClickHouse |
| 5 | MySQL |
| 7 | PostgreSQL |
| 8 | SQL Server |
| 14 | Doris |
| 17 | TiDB |
| 19 | PolarDB MySQL |
| 25 | Oracle |
| 26 | DM |
| 39 | Aurora MySQL |
| 40 | Aurora PostgreSQL |
| 48 | PolarDB PostgreSQL |

## SQL 示例规范

### 必须遵守

1. **所有 SQL 必须经过实际环境验证** — 不要凭记忆或推断写 SQL
2. **使用 ClickZetta 特有语法** — 不要用 Snowflake/Spark/MySQL 语法
3. **VCluster 名称用 `default`** — 不要用 `default_ap`（AP 型不支持小文件合并）
4. **REFRESH 语法**：`REFRESH INTERVAL 10 MINUTE vcluster default`（不是 TARGET_LAG）
5. **COMMENT 语法**：CREATE VCLUSTER 用 `COMMENT '...'`（不带等号）
6. **COPY INTO VOLUME 导出**：用 `FILE_FORMAT = (TYPE = CSV)`（不是 `USING CSV`）
7. **SHOW 命令不支持**：ORDER BY、子查询、SHOW TBLPROPERTIES
8. **SHOW TABLES 列名**：`table_name`（不是 `name`）
9. **information_schema.columns**：没有 `ordinal_position` 列

### 格式要求

```sql
-- 注释说明用途
CREATE DYNAMIC TABLE my_schema.my_dt
REFRESH INTERVAL 10 MINUTE vcluster default
AS
SELECT col1, col2
FROM source_table;
```

- SQL 关键字大写：`CREATE`、`SELECT`、`FROM`、`WHERE`
- 表名/列名小写
- 每个示例前加注释说明用途
- 不要在 SHOW/DESC 命令后加 LIMIT（部分不支持）

## 新增 Skill 流程

1. 创建目录 `clickzetta-<name>/SKILL.md`
2. 编写内容，确保 SQL 经过验证
3. 更新 `.well-known/skills/index.json`，添加条目：
   ```json
   {
     "name": "clickzetta-<name>",
     "description": "简短描述",
     "files": ["SKILL.md", "references/xxx.md"]
   }
   ```
4. 更新 `README.md` 的 Skills 总览表，添加新 Skill 到对应类别
5. 提交并推送

## 修改现有 Skill

- 修改后确保不引入错误语法
- 如果不确定语法是否正确，先在 Lakehouse 环境验证
- 提交时说明修改原因（关联 issue 编号）
- 修改 cz-cli 相关内容时，先通过 `cz-cli <command> --help` 确认命令存在和参数正确

## 常见错误模式（避免）

| ❌ 错误 | ✅ 正确 | 说明 |
|---|---|---|
| `REFRESH AUTO EVERY '1 hours'` | `REFRESH INTERVAL 60 MINUTE vcluster default` | MV/DT 刷新语法 |
| `USING CSV` (在 COPY INTO) | `FILE_FORMAT = (TYPE = CSV)` | USING 仅用于 SELECT FROM VOLUME |
| `COMMENT = '...'` (在 CREATE VCLUSTER) | `COMMENT '...'` | VCLUSTER 不带等号 |
| `SHOW TBLPROPERTIES table` | `SHOW CREATE TABLE table` | 不存在 SHOW TBLPROPERTIES |
| `WHERE name = 'x'` (在 SHOW TABLES) | `WHERE table_name = 'x'` | 列名是 table_name |
| `ORDER BY ordinal_position` | `ORDER BY column_name` | 不存在 ordinal_position |
| `SHOW ... ORDER BY ...` | 不支持 | SHOW 命令不支持 ORDER BY |
| `SELECT FROM (SHOW ...)` | 不支持 | SHOW 不能作为子查询 |
| `ALTER DYNAMIC TABLE ... SET REFRESH` | `CREATE OR REPLACE DYNAMIC TABLE ...` | 修改刷新需重建 |
| `vcluster default_ap` | `vcluster default` | 通用型 VC 默认名是 default |
| `cz-cli task create --task-type 10` | `cz-cli task create "name" --type DI` | 正确的 task create 语法 |
| `cz-cli task schedule --task-id x` | `cz-cli task save-cron <task> --help` | 不存在 task schedule 命令 |
| `cz-cli task publish --task-id x` | `cz-cli task deploy <task> -y` | 不存在 task publish 命令 |
| `cz-cli vcluster list --type INTEGRATION` | `cz-cli sql --sync "SHOW VCLUSTERS"` | 不存在 vcluster list 命令 |
| `pip install cz-cli` | `cz-cli profile status`（验证已安装） | 安装方式不在 Skill 职责范围内 |
| task_type=28（实时同步） | task_type=14（REALTIME/CDC） | 正确的 task type 数值 |
| task_type=10（单表离线同步） | task_type=1（DI/INTEGRATION） | 正确的 task type 数值 |

## 测试验证

修改 Skill 后，建议用 czcode 实际执行一遍相关操作验证：

```bash
# 启动 czcode 连接 Lakehouse
czcode

# 切换到数据工程师角色（有写权限）
/cz_role → 选择"数据工程师"

# 让 agent 按 skill 执行操作，观察是否报错
```

如果 agent 生成了错误 SQL，czcode 会自动创建 GitHub Issue（通过 `/cz_skill-fix` 命令），方便追踪和修复。

## 发布

Skills 通过 GitHub Pages 分发：
- 推送到 main 分支后自动部署到 https://clickzetta.github.io/clickzetta-skills/
- czcode 通过 `.well-known/skills/index.json` 发现和下载 skills
- czcode 发布新版本时也会打包最新 skills 到二进制中


本文档为 AI Agent（Claude Code、czcode 等）和人类开发者提供 Skill 开发指南。

## 仓库结构

```
clickzetta-skills/
├── .well-known/skills/index.json   ← Skill 注册表（必须同步更新）
├── clickzetta-<name>/              ← 每个 Skill 一个目录
│   ├── SKILL.md                    ← 主入口（必须存在）
│   └── references/                 ← 参考文档（可选）
│       └── *.md
├── CLAUDE.md                       ← 本文件（开发规范）
└── README.md                       ← 仓库说明
```

## Skill 目录命名

- 统一前缀：`clickzetta-<功能名>`
- 使用小写 + 连字符：`clickzetta-dynamic-table`、`clickzetta-vcluster-manager`
- 名称应反映功能领域，不要过于具体

## SKILL.md 规范

### Front-matter（必须）

```yaml
---
name: clickzetta-<name>
description: |
  一段话描述 Skill 的功能范围。
  当用户说"关键词1"、"关键词2"、"关键词3"时触发。
  Keywords: english, keywords, for, LLM, matching
---
```

**要求：**
- `name` 必须与目录名一致
- `description` 包含中文触发词和英文 Keywords 行
- 触发词要覆盖用户可能的各种表述方式

### 内容结构（建议）

1. **快速入门** — 3-5 行最常用的 SQL 示例
2. **核心概念** — 简要说明关键概念
3. **详细参考** — 放在 `references/` 子目录
4. **常见问题** — 排障表（问题 | 原因 | 解决方案）

## SQL 示例规范

### 必须遵守

1. **所有 SQL 必须经过实际环境验证** — 不要凭记忆或推断写 SQL
2. **使用 ClickZetta 特有语法** — 不要用 Snowflake/Spark/MySQL 语法
3. **VCluster 名称用 `default`** — 不要用 `default_ap`（AP 型不支持小文件合并）
4. **REFRESH 语法**：`REFRESH INTERVAL 10 MINUTE vcluster default`（不是 TARGET_LAG）
5. **COMMENT 语法**：CREATE VCLUSTER 用 `COMMENT '...'`（不带等号）
6. **COPY INTO VOLUME 导出**：用 `FILE_FORMAT = (TYPE = CSV)`（不是 `USING CSV`）
7. **SHOW 命令不支持**：ORDER BY、子查询、SHOW TBLPROPERTIES
8. **SHOW TABLES 列名**：`table_name`（不是 `name`）
9. **information_schema.columns**：没有 `ordinal_position` 列

### 格式要求

```sql
-- 注释说明用途
CREATE DYNAMIC TABLE my_schema.my_dt
REFRESH INTERVAL 10 MINUTE vcluster default
AS
SELECT col1, col2
FROM source_table;
```

- SQL 关键字大写：`CREATE`、`SELECT`、`FROM`、`WHERE`
- 表名/列名小写
- 每个示例前加注释说明用途
- 不要在 SHOW/DESC 命令后加 LIMIT（部分不支持）

## 新增 Skill 流程

1. 创建目录 `clickzetta-<name>/SKILL.md`
2. 编写内容，确保 SQL 经过验证
3. 更新 `.well-known/skills/index.json`，添加条目：
   ```json
   {
     "name": "clickzetta-<name>",
     "description": "简短描述",
     "files": ["SKILL.md", "references/xxx.md"]
   }
   ```
4. 更新 `README.md` 的 Skills 总览表，添加新 Skill 到对应类别
5. 提交并推送

## 修改现有 Skill

- 修改后确保不引入错误语法
- 如果不确定语法是否正确，先在 Lakehouse 环境验证
- 提交时说明修改原因（关联 issue 编号）

## 常见错误模式（避免）

| ❌ 错误 | ✅ 正确 | 说明 |
|---|---|---|
| `REFRESH AUTO EVERY '1 hours'` | `REFRESH INTERVAL 60 MINUTE vcluster default` | MV/DT 刷新语法 |
| `USING CSV` (在 COPY INTO) | `FILE_FORMAT = (TYPE = CSV)` | USING 仅用于 SELECT FROM VOLUME |
| `COMMENT = '...'` (在 CREATE VCLUSTER) | `COMMENT '...'` | VCLUSTER 不带等号 |
| `SHOW TBLPROPERTIES table` | `SHOW CREATE TABLE table` | 不存在 SHOW TBLPROPERTIES |
| `WHERE name = 'x'` (在 SHOW TABLES) | `WHERE table_name = 'x'` | 列名是 table_name |
| `ORDER BY ordinal_position` | `ORDER BY column_name` | 不存在 ordinal_position |
| `SHOW ... ORDER BY ...` | 不支持 | SHOW 命令不支持 ORDER BY |
| `SELECT FROM (SHOW ...)` | 不支持 | SHOW 不能作为子查询 |
| `ALTER DYNAMIC TABLE ... SET REFRESH` | `CREATE OR REPLACE DYNAMIC TABLE ...` | 修改刷新需重建 |
| `vcluster default_ap` | `vcluster default` | 通用型 VC 默认名是 default |

## 测试验证

修改 Skill 后，建议用 czcode 实际执行一遍相关操作验证：

```bash
# 启动 czcode 连接 Lakehouse
czcode

# 切换到数据工程师角色（有写权限）
/cz_role → 选择"数据工程师"

# 让 agent 按 skill 执行操作，观察是否报错
```

如果 agent 生成了错误 SQL，czcode 会自动创建 GitHub Issue（通过 `/cz_skill-fix` 命令），方便追踪和修复。

## 发布

Skills 通过 GitHub Pages 分发：
- 推送到 main 分支后自动部署到 https://clickzetta.github.io/clickzetta-skills/
- czcode 通过 `.well-known/skills/index.json` 发现和下载 skills
- czcode 发布新版本时也会打包最新 skills 到二进制中
