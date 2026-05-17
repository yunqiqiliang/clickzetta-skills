---
name: clickzetta-data-science
description: |
  数据科学家使用 ClickZetta Lakehouse 的端到端工作流指南。按工作阶段组织：
  开发环境准备（Python 3.10+ 检查/搭建）、Jupyter Notebook 配置与使用、
  项目结构规范（Cookiecutter DS 标准）、数据发现、数据质量评估、
  数据清洗与整合、数据集构建、EDA 探索分析、
  特征工程（SQL + ZettaPark）、模型推理上线（BITMAP 用户画像/UDF 批量推理/向量检索）。
  当用户说"数据科学"、"机器学习"、"特征工程"、"EDA"、"数据探索"、
  "ZettaPark 机器学习"、"Jupyter 连接 Lakehouse"、"notebook"、"ipynb"、
  "jupyter kernel"、"%%sql"、"magic command"、"pandas 读取数据"、
  "数据质量检查"、"数据采样"、"TABLESAMPLE"、"approx_percentile"、
  "BITMAP 用户画像"、"人群圈选"、"批量推理"、"Python 3.10"、
  "scikit-learn"、"项目目录结构"、"config.json"、".env"时触发。
  Keywords: data science, Jupyter, EDA, feature engineering, ML, pandas, notebook
---

# ClickZetta Lakehouse 数据科学工作流

## 工作流全景

```
环境准备 → Jupyter 配置 → 项目结构 → 数据发现 → 数据质量评估 → 数据清洗整合
                                                                        ↓
                                      模型推理上线 ← 特征工程 ← EDA ← 数据集构建
```

---

## 硬性前提条件

**Python 3.10+**（ZettaPark 硬性要求）。用户环境是 3.9 或更低时，先给升级方案再继续：

```bash
brew install pyenv && pyenv install 3.12.9 && pyenv local 3.12.9
python -m venv .venv && source .venv/bin/activate
```

详细搭建步骤见 [references/setup.md](references/setup.md)。

---

## 项目结构

```
my-ds-project/
├── notebooks/          # 00-env-check.ipynb 必须是第一个
│   ├── 00-env-check.ipynb
│   ├── 01-data-discovery.ipynb
│   ├── 02-data-quality.ipynb
│   ├── 03-eda.ipynb
│   ├── 04-feature-engineering.ipynb
│   └── 05-modeling.ipynb
├── src/
│   ├── config.py       # 连接配置，见 references/setup.md
│   ├── data/
│   └── features/
├── sql/
├── data/               # 全部加入 .gitignore
├── models/             # 全部加入 .gitignore
├── .env                # 绝不入 git
└── .env.example        # 入 git
```

环境变量命名规范：`CLICKZETTA_SERVICE` / `CLICKZETTA_INSTANCE` / `CLICKZETTA_WORKSPACE` / `CLICKZETTA_USERNAME` / `CLICKZETTA_PASSWORD` / `CLICKZETTA_VCLUSTER` / `CLICKZETTA_SCHEMA`。

---

## 数据写入规则（禁止事项）

| 方式 | 结论 |
|------|------|
| `session.create_dataframe(df).write.save_as_table()` | ✅ 推荐 |
| `cursor` 批量 INSERT（每批 500 行） | ✅ Python 3.9 / ZettaPark 不可用时的 fallback |
| `df.to_sql(conn, ...)` | ❌ 禁止，报 `'list' object has no attribute 'keys'` |
| SQLAlchemy `clickzetta://...` | ❌ 禁止，dialect 不可靠 |

代码模板见 [references/write-and-infer.md](references/write-and-infer.md)。

---

## 数据查看规则

- 快速查看用 `.show()`，不需要 pandas 时不要 `.to_pandas()`
- 大表操作默认加 `TABLESAMPLE ROW(10)` 采样，避免 OOM

---

## 数据验证规则

导入数据后，**立即用已知基准值验证统计结果**，再进行后续分析。

常见陷阱：运动员/用户级别的原始数据，团体项目每个参与者各有一条记录，直接 SUM 会重复计算。正确做法：先 `SELECT DISTINCT event, medal, ...` 去重，再聚合。

---

## ClickZetta SQL 不支持的语法

| 不支持 | 替代方案 |
|--------|---------|
| `CREATE OR REPLACE TABLE` | `CREATE TABLE IF NOT EXISTS`（普通表不支持 OR REPLACE） |
| `ARRAY_AGG(col IGNORE NULLS)` | `MAX(col)` 或 `COALESCE()` |
| `QUALIFY` 子句 | 子查询 + `WHERE rn = 1` |
| `UNION` / `INTERSECT` / `EXCEPT` | JOIN + 应用层合并 |
| `BEGIN; COMMIT; ROLLBACK;` | 用 MERGE 实现原子操作 |
| `NOW()` | `CURRENT_TIMESTAMP()` |

遇到其他语法报错，加载 `clickzetta-sql-syntax-guide` skill。

---

## Schema 上下文

Python 代码中 SQL 语句始终使用完整表名 `schema.table`，不依赖当前 schema 上下文。

---

## 参考文档

- [环境搭建与项目配置](references/setup.md) — 环境搭建、config.py 模板、Jupyter 配置
- [数据发现/质量/清洗/EDA 示例](references/data-patterns.md)
- [数据写入/特征工程/模型推理示例](references/write-and-infer.md)
- [ZettaPark API](references/zettapark-api.md)
- [统计分析函数](references/stats-functions.md)
- [BITMAP 用户画像](references/bitmap-profile.md)
