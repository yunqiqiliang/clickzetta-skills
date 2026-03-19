# clickzetta-skills

[云器 Lakehouse](https://www.yunqi.tech) 的 Claude Code Skills 集合，帮助开发者在 AI 编程助手中更高效地使用 ClickZetta Lakehouse。

## Skills 列表

### [clickzetta-lakehouse-connect](./clickzetta-lakehouse-connect/)

连接 ClickZetta Lakehouse 的完整指南。支持四种连接方式：

- **Python SDK** (`clickzetta-connector-python`) — 执行 SQL、自动化脚本
- **ZettaPark Session** — DataFrame API、数据工程
- **SQLAlchemy** — ORM、Web 应用、BI 工具（Superset）
- **JDBC** — Java 应用、DBeaver

自动从本地配置文件读取连接参数，覆盖国内版（`clickzetta.com`）和国际版（`singdata.com`）多区域。

**触发词**：ClickZetta、云器、Lakehouse 连接、ZettaPark、JDBC 连接、连接数据库、执行 SQL 查询

**相关文档**：
[如何连接到 Lakehouse](https://www.yunqi.tech/documents/tutorial_connect_to_lakehouse) ·
[Python SDK](https://www.yunqi.tech/documents/python-sdk-summary) ·
[ZettaPark 快速上手](https://www.yunqi.tech/documents/ZettaparkQuickStart) ·
[SQLAlchemy](https://www.yunqi.tech/documents/sqlalchemy) ·
[JDBC 驱动](https://www.yunqi.tech/documents/JDBC-Driver) ·
[云服务和地域](https://www.yunqi.tech/documents/Supported_Cloud_Platforms) ·
[相关下载](https://www.yunqi.tech/documents/Lakehouse-client-repository)

---

### [clickzetta-manage-comments](./clickzetta-manage-comments/)

管理 ClickZetta Lakehouse 各类对象的注释（COMMENT）。支持增加、修改、删除注释，覆盖对象类型：

- Schema、普通表、外部表、字段
- 动态表（Dynamic Table）、物化视图（Materialized View）
- VCluster（计算集群）、Workspace（工作空间）

包含 ClickZetta 特有语法（与标准 SQL `COMMENT ON` 不同）及单引号转义处理。

**触发词**：加注释、改注释、删注释、补注释、加 comment、补充元数据、字段描述、表说明

**相关文档**：
[ALTER TABLE](https://www.yunqi.tech/documents/ALTERTABLE) ·
[ALTER SCHEMA](https://www.yunqi.tech/documents/ALTER-SCHEMA) ·
[ALTER DYNAMIC TABLE](https://www.yunqi.tech/documents/alter-dynamic-table) ·
[ALTER MATERIALIZED VIEW](https://www.yunqi.tech/documents/alter-materialzied-view) ·
[修改工作空间](https://www.yunqi.tech/documents/alter-worksapce)

---

### [clickzetta-data-recovery](./clickzetta-data-recovery/)

ClickZetta Lakehouse 数据恢复与历史查询。覆盖完整数据恢复工作流：

- **Time Travel** — 查询任意历史时间点的数据（`TIMESTAMP AS OF`）
- **UNDROP TABLE** — 恢复被误删的表、动态表、物化视图
- **RESTORE TABLE** — 将表回滚到历史版本
- **DESC HISTORY / SHOW TABLES HISTORY** — 查看表的变更记录与删除记录
- **数据保留周期** — 配置 `data_retention_days`（默认 1 天，最长 90 天）

**触发词**：恢复误删的表、回滚数据、时间旅行查询、UNDROP、RESTORE TABLE、数据保留周期

**相关文档**：
[备份和恢复](https://www.yunqi.tech/documents/data-recover) ·
[TIME TRAVEL](https://www.yunqi.tech/documents/TIMETRAVEL) ·
[RESTORE TABLE](https://www.yunqi.tech/documents/restore) ·
[UNDROP TABLE](https://www.yunqi.tech/documents/UNDROP-TABLE) ·
[SHOW TABLES HISTORY](https://www.yunqi.tech/documents/show-tables-history)

---

## 安装

将对应 skill 目录复制到你的项目或全局 skills 目录，Claude Code 会自动识别并加载。

```bash
git clone https://github.com/clickzetta/clickzetta-skills.git
```

## 相关资源

- [云器 Lakehouse 文档](https://www.yunqi.tech/documents/Overview)
- [LLM 全量文档索引](https://yunqi.tech/llms-full.txt) — 适合 AI 助手直接消费的完整文档，涵盖所有 SQL 命令、SDK、连接方式等
- [Lakehouse MCP Server](https://www.yunqi.tech/documents/LakehouseMCPServer) — 通过 MCP 协议将 Lakehouse 能力暴露给 Claude 等 AI 助手
- [AI 生态集成](https://www.yunqi.tech/documents/AI_eco) — Dify、LangChain、N8N 等集成方案
