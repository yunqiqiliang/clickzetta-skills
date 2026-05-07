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
