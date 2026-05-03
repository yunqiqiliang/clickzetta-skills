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
---

# ClickZetta Lakehouse 数据科学工作流

## 工作流全景

```
环境准备 → Jupyter 配置 → 项目结构 → 数据发现 → 数据质量评估 → 数据清洗整合
                                                                        ↓
                                      模型推理上线 ← 特征工程 ← EDA ← 数据集构建
```

---

## Jupyter Notebook 配置与使用

Jupyter 是数据科学的主要工作环境。以下覆盖从 kernel 配置到 Lakehouse 连接的完整流程。

### Kernel 配置

```bash
# 1. 在项目 venv 里安装 ipykernel
source .venv/bin/activate
pip install ipykernel jupyterlab

# 2. 将 venv 注册为 Jupyter kernel（关键步骤，否则 notebook 用的是系统 Python）
python -m ipykernel install --user --name lakehouse-ds --display-name "Python (lakehouse-ds)"

# 3. 启动 JupyterLab
jupyter lab
# 或指定端口/不自动打开浏览器
jupyter lab --port=8888 --no-browser
```

> **常见问题**：notebook 里 `import clickzetta` 报 ModuleNotFoundError → kernel 没有选对。
> 在 JupyterLab 右上角切换到 "Python (lakehouse-ds)"，或在 VS Code 里选择对应 venv 的 Python 解释器。

### 在 Notebook 里连接 Lakehouse

**方式 A：ZettaPark Session（推荐，DataFrame API）**

```python
# Cell 1 — 初始化（每个 notebook 开头执行一次）
import os
from dotenv import load_dotenv
from clickzetta.zettapark.session import Session

load_dotenv()  # 读取项目根目录的 .env

session = Session.builder.configs({
    "service":   os.environ["CZ_SERVICE"],
    "instance":  os.environ["CZ_INSTANCE"],
    "workspace": os.environ["CZ_WORKSPACE"],
    "username":  os.environ["CZ_USERNAME"],
    "password":  os.environ["CZ_PASSWORD"],
    "vcluster":  os.environ.get("CZ_VCLUSTER", "default_ap"),
    "schema":    os.environ.get("CZ_SCHEMA", "public"),
    "hints": {"query_tag": "jupyter_notebook"},
}).create()

print(f"✅ 连接成功: {session.sql('SELECT current_workspace(), current_user()').collect()}")
```

**方式 B：connector-python（纯 SQL，适合简单查询）**

```python
import clickzetta
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

conn = clickzetta.connect(
    service=os.environ["CZ_SERVICE"],
    instance=os.environ["CZ_INSTANCE"],
    workspace=os.environ["CZ_WORKSPACE"],
    username=os.environ["CZ_USERNAME"],
    password=os.environ["CZ_PASSWORD"],
    vcluster=os.environ.get("CZ_VCLUSTER", "default_ap"),
    schema=os.environ.get("CZ_SCHEMA", "public"),
)

# 直接读成 pandas DataFrame
df = pd.read_sql("SELECT * FROM my_schema.orders LIMIT 1000", conn)
df.head()
```

### SQL Magic Commands

安装 `jupysql` 后可以在 notebook cell 里直接写 SQL：

```bash
pip install jupysql
```

```python
# Cell — 加载 magic 扩展
%load_ext sql

# 配置连接（使用 clickzetta SQLAlchemy dialect）
%sql clickzetta://username:password@service/instance/workspace?vcluster=default_ap&schema=public
```

```sql
-- Cell — 单行 SQL（结果显示为表格）
%sql SELECT COUNT(*) FROM my_schema.orders

-- Cell — 多行 SQL
%%sql
SELECT
    DATE_TRUNC('month', order_date) AS month,
    COUNT(*)                        AS order_cnt,
    SUM(amount)                     AS revenue
FROM my_schema.orders
GROUP BY 1
ORDER BY 1
```

```python
# Cell — 把 SQL 结果存入 pandas DataFrame
result = %sql SELECT * FROM my_schema.orders LIMIT 10000
df = result.DataFrame()
df.describe()
```

### Notebook 里的典型数据科学 Cell 模式

```python
# ── 数据加载 ──────────────────────────────────────────────
df = session.sql("""
    SELECT * FROM my_schema.orders
    TABLESAMPLE ROW (10)   -- 10% 采样，避免 OOM
""").to_pandas()

print(f"Shape: {df.shape}")
df.head()
```

```python
# ── 快速 EDA ──────────────────────────────────────────────
import matplotlib.pyplot as plt
import seaborn as sns

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

df['amount'].hist(bins=50, ax=axes[0])
axes[0].set_title('Amount Distribution')

df.groupby('status')['amount'].sum().plot(kind='bar', ax=axes[1])
axes[1].set_title('Revenue by Status')

plt.tight_layout()
plt.savefig('../reports/figures/eda_overview.png', dpi=150)
plt.show()
```

```python
# ── 结果写回 Lakehouse ────────────────────────────────────
result_df = df[df['amount'] > 100][['user_id', 'amount', 'order_date']]

session.create_dataframe(result_df) \
    .write.mode("overwrite") \
    .save_as_table("ds_workspace.high_value_orders")

print(f"✅ 写入 {len(result_df)} 行到 ds_workspace.high_value_orders")
```

### VS Code / Cursor 里使用 Notebook

VS Code 和 Cursor 原生支持 `.ipynb`，无需启动 JupyterLab：

1. 打开 `.ipynb` 文件
2. 右上角 "Select Kernel" → 选择 "Python (lakehouse-ds)"（即之前注册的 venv kernel）
3. 直接在 IDE 里运行 cell，支持变量查看、调试

> **推荐**：用 VS Code/Cursor 开发 notebook，比浏览器版 JupyterLab 有更好的代码补全和 Git 集成。

### Notebook 转 Python 脚本

探索完成后，将 notebook 转为可调度的 `.py` 脚本：

```bash
# 方式 A：nbconvert（保留所有 cell）
jupyter nbconvert --to script notebooks/05-feature-engineering.ipynb
# 输出：notebooks/05-feature-engineering.py

# 方式 B：只导出非 EDA cell（手动整理后放入 src/）
# 建议：把核心逻辑提取到 src/features/build_features.py，notebook 只做调用
```

### 常见 Notebook 问题

| 问题 | 原因 | 修复 |
|------|------|------|
| `ModuleNotFoundError: clickzetta` | kernel 未选对 | 切换到注册的 venv kernel |
| `.env` 读不到 | `load_dotenv()` 路径问题 | 改为 `load_dotenv(dotenv_path='../.env')` |
| `to_pandas()` OOM | 数据量太大 | 加 `TABLESAMPLE ROW(1)` 或 `LIMIT` |
| kernel 死掉/无响应 | 内存溢出 | 重启 kernel，减小采样比例 |
| 图表不显示 | 缺少 `%matplotlib inline` | 在 notebook 开头加 `%matplotlib inline` |
| JupyterLab 端口占用 | 上次未正常关闭 | `jupyter lab --port=8889` 换端口 |

---

## 阶段 0：开发环境准备

### 路径 A：检查现有环境（最常见）

```python
# 1. 检查 Python 版本（推荐 3.12，最低 3.10）
import sys
print(sys.version)
assert sys.version_info >= (3, 10), f"需要 Python 3.10+，当前 {sys.version}"
if sys.version_info < (3, 12):
    print("⚠️  建议升级到 Python 3.12 以获得最佳兼容性")

# 2. 检查关键包
packages = {
    'clickzetta_zettapark_python': 'clickzetta.zettapark',
    'clickzetta-connector-python': 'clickzetta.connector',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'pyarrow': 'pyarrow',
    'python-dotenv': 'dotenv',
}
for pkg, module in packages.items():
    try:
        m = __import__(module.split('.')[0])
        ver = getattr(m, '__version__', 'unknown')
        print(f"✅ {pkg}: {ver}")
    except ImportError:
        print(f"❌ {pkg}: 未安装 → pip install {pkg}")

# 3. 验证 Lakehouse 连接
from src.config import get_session
session = get_session()
result = session.sql("SELECT current_workspace(), current_user(), current_vcluster()").collect()
print(f"✅ 连接成功: {result}")
```

### 路径 B：全新搭建

```bash
# 方式 1：venv（Python 内置，推荐）
python3.12 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows
pip install clickzetta_zettapark_python clickzetta-connector-python \
    python-dotenv pandas numpy scikit-learn pyarrow jupyterlab matplotlib seaborn

# 方式 2：pyenv（需要切换 Python 版本时）
pyenv install 3.12.9 && pyenv local 3.12.9
python -m venv .venv && source .venv/bin/activate
pip install clickzetta_zettapark_python clickzetta-connector-python \
    python-dotenv pandas numpy scikit-learn pyarrow jupyterlab matplotlib seaborn

# 方式 3：conda（数据科学环境）
conda create -n lakehouse-ds python=3.12 -y && conda activate lakehouse-ds
pip install clickzetta_zettapark_python clickzetta-connector-python \
    python-dotenv pandas numpy scikit-learn pyarrow jupyterlab matplotlib seaborn
```

### 常见问题修复

| 问题 | 原因 | 修复 |
|---|---|---|
| `Python 3.8/3.9` | 版本不满足 | `pyenv install 3.12.9` 或 `python3.12 -m venv .venv` 新建环境 |
| `pyarrow` 版本冲突 | 与其他包冲突 | `pip install pyarrow==14.0.0` |
| 连接超时 | VCluster 未启动 | 在 Studio 中手动启动集群 |
| M1/M2 Mac 报错 | ARM 架构兼容 | 用 `pip install --no-binary :all:` 或改用 conda |

---

## 阶段 1：项目结构规范

基于 **Cookiecutter Data Science v2** 标准，适配 Lakehouse：

```
my-ds-project/
│
├── data/                           # 本地数据（全部加入 .gitignore）
│   ├── raw/                        # 从 Lakehouse 拉取的原始样本，只读不改
│   ├── interim/                    # 中间处理结果（清洗、去重后）
│   ├── processed/                  # 最终建模用数据集
│   └── external/                   # 第三方外部数据
│
├── notebooks/                      # Jupyter Notebooks
│   ├── 01-env-check.ipynb          # 命名规范：序号-描述
│   ├── 02-data-discovery.ipynb
│   ├── 03-data-quality.ipynb
│   ├── 04-eda.ipynb
│   ├── 05-feature-engineering.ipynb
│   └── 06-modeling.ipynb
│
├── src/                            # 可复用 Python 模块（入 git）
│   ├── __init__.py
│   ├── config.py                   # 连接配置（从 .env 读取）
│   ├── data/
│   │   ├── loader.py               # 从 Lakehouse 加载数据
│   │   └── quality.py              # 数据质量检查函数
│   ├── features/
│   │   └── build_features.py       # 特征工程函数
│   └── models/
│       ├── train.py
│       └── predict.py
│
├── sql/                            # SQL 脚本（入 git）
│   ├── quality/                    # 数据质量检查 SQL
│   ├── features/                   # 特征工程 SQL
│   └── inference/                  # 批量推理 SQL
│
├── models/                         # 训练好的模型（.gitignore 或 DVC 管理）
├── reports/figures/                # 生成的图表
├── references/                     # 数据字典、字段说明
│
├── .env                            # 实际密钥（绝不入 git）
├── .env.example                    # 密钥模板（入 git）
├── .gitignore
├── pyproject.toml
└── README.md
```

### 核心文件模板

**`.env`（不入 git）：**
```bash
CZ_SERVICE=cn-shanghai-alicloud.api.clickzetta.com
CZ_INSTANCE=your-instance-id
CZ_WORKSPACE=your-workspace
CZ_USERNAME=your-username
CZ_PASSWORD=your-password
CZ_VCLUSTER=default_ap
CZ_SCHEMA=ds_workspace
```

**`.env.example`（入 git，作为模板）：**
```bash
CZ_SERVICE=cn-shanghai-alicloud.api.clickzetta.com
CZ_INSTANCE=<instance-id>
CZ_WORKSPACE=<workspace>
CZ_USERNAME=<username>
CZ_PASSWORD=<password>
CZ_VCLUSTER=default_ap
CZ_SCHEMA=ds_workspace
```

**`src/config.py`（入 git）：**
```python
import os
from dotenv import load_dotenv
from clickzetta.zettapark.session import Session

load_dotenv()  # 读取 .env

def get_session() -> Session:
    """创建 ZettaPark Session，优先读 .env，fallback 到 connections.json"""
    config = {
        "service":   os.environ["CZ_SERVICE"],
        "instance":  os.environ["CZ_INSTANCE"],
        "workspace": os.environ["CZ_WORKSPACE"],
        "username":  os.environ["CZ_USERNAME"],
        "password":  os.environ["CZ_PASSWORD"],
        "vcluster":  os.environ["CZ_VCLUSTER"],
        "schema":    os.environ.get("CZ_SCHEMA", "public"),
    }
    return Session.builder.configs(config).create()
```

**`.gitignore` 关键内容：**
```
.env
data/
models/
__pycache__/
*.pyc
.ipynb_checkpoints/
```

**`pyproject.toml`：**
```toml
[project]
name = "my-lakehouse-ds-project"
requires-python = ">=3.10"   # 最低 3.10，推荐 3.12
dependencies = [
    "clickzetta_zettapark_python>=0.1.2",
    "clickzetta-connector-python>=1.0.0",
    "python-dotenv>=1.0.0",
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "scikit-learn>=1.3.0",
    "pyarrow>=14.0.0",
    "jupyterlab>=4.0.0",
    "matplotlib>=3.7.0",
    "seaborn>=0.12.0",
]
```

---

## 阶段 2：数据发现

```python
from src.config import get_session
session = get_session()

# 查看可用 Schema
schemas = session.sql("SHOW SCHEMAS").to_pandas()
print(schemas)

# 查看 Schema 下的表
tables = session.sql("SHOW TABLES IN my_schema").to_pandas()
print(tables[['table_name', 'is_view', 'is_dynamic', 'is_external']])

# 查看表结构（字段名、类型、注释）
session.sql("DESC EXTENDED my_schema.orders").show()

# 查看完整建表语句（了解分区、索引等）
session.sql("SHOW CREATE TABLE my_schema.orders").show()

# 查看表行数和大小
session.sql("""
    SELECT table_name, row_count,
           ROUND(bytes / 1024.0 / 1024 / 1024, 2) AS size_gb,
           last_modify_time
    FROM information_schema.tables
    WHERE table_schema = 'my_schema'
    ORDER BY bytes DESC
""").show()
```

---

## 阶段 3：数据质量评估

在动手清洗之前，先用 SQL 快速摸底：

```sql
-- 1. 基础统计：行数、时间范围、关键字段覆盖率
SELECT
    COUNT(*)                                          AS total_rows,
    COUNT(DISTINCT user_id)                           AS unique_users,
    MIN(event_time)                                   AS earliest,
    MAX(event_time)                                   AS latest,
    -- 缺失率
    ROUND(100.0 * SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                      AS user_id_null_pct,
    ROUND(100.0 * SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                      AS amount_null_pct
FROM my_schema.orders;

-- 2. 重复值检查（主键唯一性）
SELECT order_id, COUNT(*) AS cnt
FROM my_schema.orders
GROUP BY order_id
HAVING cnt > 1
LIMIT 10;

-- 3. 数值分布（近似分位数，大表高效）
SELECT
    approx_percentile(amount, 0.25) AS p25,
    approx_percentile(amount, 0.50) AS median,
    approx_percentile(amount, 0.75) AS p75,
    approx_percentile(amount, 0.95) AS p95,
    approx_percentile(amount, 0.99) AS p99,
    MIN(amount) AS min_val,
    MAX(amount) AS max_val,
    AVG(amount)  AS mean_val
FROM my_schema.orders;

-- 4. 近似直方图（了解分布形态）
SELECT approx_histogram(amount, 10) AS hist
FROM my_schema.orders;
-- 返回结构体数组：[{min, max, count}, ...]

-- 5. 高频值 TOP-K（类别型字段）
SELECT approx_top_k(status, 10) AS top_statuses
FROM my_schema.orders;

-- 6. 近似 UV（大表去重计数）
SELECT approx_count_distinct(user_id) AS approx_uv
FROM my_schema.events;
```

```python
# 拉到 pandas 做可视化
import pandas as pd
import matplotlib.pyplot as plt

# 采样后做分布图（避免 OOM）
df = session.sql("""
    SELECT amount, status, event_date
    FROM my_schema.orders
    TABLESAMPLE ROW (5)   -- 5% 精确行级采样，适合 < 1000万行
""").to_pandas()

df['amount'].hist(bins=50)
plt.title('Amount Distribution (5% sample)')
plt.savefig('reports/figures/amount_dist.png')
```

---

## 阶段 4：数据清洗与整合

```sql
-- 1. 去重（保留最新一条）
SELECT *
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY order_id
               ORDER BY update_time DESC
           ) AS rn
    FROM my_schema.orders_raw
)
WHERE rn = 1;

-- 2. 缺失值处理
SELECT
    order_id,
    user_id,
    COALESCE(amount, 0.0)                    AS amount,
    COALESCE(status, 'UNKNOWN')              AS status,
    COALESCE(city, '未知')                   AS city,
    CAST(order_date AS DATE)                 AS order_date  -- 字符串转日期
FROM my_schema.orders_raw
WHERE user_id IS NOT NULL;   -- 过滤主键为空的行

-- 3. 异常值过滤
SELECT *
FROM my_schema.orders_raw
WHERE amount BETWEEN 0 AND 1000000   -- 过滤负数和极端值
  AND order_date >= '2020-01-01';    -- 过滤明显错误的历史数据

-- 4. 多表整合（事实表 + 维度表）
SELECT
    o.order_id,
    o.user_id,
    o.amount,
    o.order_date,
    u.age_group,
    u.city,
    u.register_date,
    p.category,
    p.brand
FROM my_schema.orders o
LEFT JOIN my_schema.users u ON o.user_id = u.user_id
LEFT JOIN my_schema.products p ON o.product_id = p.product_id;
```

---

## 阶段 5：数据集构建（写回 Lakehouse）

```python
# 方式 A：ZettaPark save_as_table（推荐）
clean_df = session.sql("""
    SELECT o.*, u.age_group, u.city
    FROM my_schema.orders_raw o
    LEFT JOIN my_schema.users u ON o.user_id = u.user_id
    WHERE o.amount > 0 AND o.user_id IS NOT NULL
""")

# 写回 Lakehouse（overwrite 模式）
clean_df.write.mode("overwrite").save_as_table("ds_workspace.orders_clean")

# 方式 B：pandas DataFrame 写回
import pandas as pd
local_df = pd.read_csv("data/processed/features.csv")

zp_df = session.create_dataframe(local_df)
zp_df.write.mode("append").save_as_table("ds_workspace.features_v1")
```

```sql
-- 设置数据集生命周期（DS 中间表不需要永久保留）
ALTER TABLE ds_workspace.orders_clean
SET PROPERTIES ('data_lifecycle' = '30');  -- 30 天后自动清理
```

---

## 阶段 6：EDA（探索性分析）

```python
# 大表采样策略选择
# SYSTEM 模式：文件级采样，极快，适合 > 100万行的快速预览
df_quick = session.sql("""
    SELECT * FROM my_schema.events
    TABLESAMPLE SYSTEM (0.1) LIMIT 50000
""").to_pandas()

# ROW 模式：行级精确采样，适合 ML 训练集构建
df_ml = session.sql("""
    SELECT * FROM my_schema.events
    TABLESAMPLE ROW (10)   -- 精确 10%
""").to_pandas()

# 时序分析（窗口函数）
session.sql("""
    SELECT
        DATE_TRUNC('day', order_time)          AS dt,
        COUNT(*)                               AS daily_orders,
        SUM(amount)                            AS daily_revenue,
        AVG(amount)                            AS avg_order_value,
        -- 7日移动平均
        AVG(SUM(amount)) OVER (
            ORDER BY DATE_TRUNC('day', order_time)
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        )                                      AS revenue_7d_ma
    FROM my_schema.orders
    GROUP BY 1
    ORDER BY 1
""").to_pandas().plot(x='dt', y=['daily_revenue', 'revenue_7d_ma'])
```

---

## 阶段 7：特征工程

### SQL 侧特征工程（利用 Lakehouse 算力，推荐）

```sql
-- 用户行为聚合特征
SELECT
    user_id,
    -- 统计特征
    COUNT(*)                                   AS order_cnt_30d,
    SUM(amount)                                AS total_amount_30d,
    AVG(amount)                                AS avg_amount_30d,
    MAX(amount)                                AS max_amount_30d,
    STDDEV(amount)                             AS std_amount_30d,
    -- 时序特征
    DATEDIFF('day', MIN(order_date), MAX(order_date))
                                               AS active_days,
    COUNT(DISTINCT DATE(order_date))           AS active_day_cnt,
    -- 环比特征（窗口函数）
    SUM(amount) - LAG(SUM(amount)) OVER (
        PARTITION BY user_id ORDER BY DATE_TRUNC('month', order_date)
    )                                          AS mom_revenue_delta,
    -- 排名特征
    NTILE(10) OVER (ORDER BY SUM(amount) DESC) AS revenue_decile
FROM my_schema.orders
WHERE order_date >= CURRENT_DATE - INTERVAL 30 DAY
GROUP BY user_id;
```

### ZettaPark 侧特征工程（Python 逻辑）

```python
from clickzetta.zettapark.functions import col, when, udf
from clickzetta.zettapark.types import FloatType

# DataFrame 变换
features = session.table("ds_workspace.orders_clean")

features = features \
    .with_column("log_amount", col("amount").cast("double").apply(lambda x: __import__('math').log1p(x))) \
    .with_column("is_high_value", when(col("amount") > 1000, 1).otherwise(0)) \
    .with_column("weekday", col("order_date").apply(lambda d: d.weekday()))

# 与 pandas/scikit-learn 集成
df = features.to_pandas()

from sklearn.preprocessing import StandardScaler, LabelEncoder
scaler = StandardScaler()
df[['amount_scaled']] = scaler.fit_transform(df[['amount']])

# 结果写回
session.create_dataframe(df).write.mode("overwrite") \
    .save_as_table("ds_workspace.features_final")
```

---

## 阶段 8：模型推理上线

### BITMAP 用户画像（人群圈选）

```sql
-- 构建用户标签 BITMAP
CREATE TABLE ds_workspace.user_tags AS
SELECT
    tag_name,
    group_bitmap_state(user_id) AS user_bitmap
FROM my_schema.user_behavior
GROUP BY tag_name;

-- 人群交集（同时满足多个标签）
SELECT bitmap_count(
    bitmap_and(
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = '高消费'),
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = '近30天活跃')
    )
) AS target_user_count;

-- 人群差集（排除某类用户）
SELECT bitmap_to_array(
    bitmap_andnot(
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = '高消费'),
        (SELECT user_bitmap FROM ds_workspace.user_tags WHERE tag_name = '已流失')
    )
) AS target_users;
```

### SQL UDF 批量推理

```sql
-- 调用已部署的模型 UDF 做批量推理
-- ⚠️ 必须用完整 Schema 路径调用
SELECT
    user_id,
    ds_workspace.credit_score_model(
        total_amount_30d,
        order_cnt_30d,
        active_days,
        avg_amount_30d
    ) AS predicted_score
FROM ds_workspace.features_final;

-- 结果写回
INSERT INTO ds_workspace.predictions
SELECT user_id, predicted_score, CURRENT_TIMESTAMP() AS predict_time
FROM (
    SELECT user_id,
           ds_workspace.credit_score_model(
               total_amount_30d, order_cnt_30d, active_days, avg_amount_30d
           ) AS predicted_score
    FROM ds_workspace.features_final
);
```

### 向量检索（推荐/语义搜索）

```sql
-- 查找与目标用户最相似的 TOP-10 用户
SELECT
    candidate_id,
    cosine_distance(
        (SELECT embedding FROM ds_workspace.user_embeddings WHERE user_id = 'target_user'),
        embedding
    ) AS similarity
FROM ds_workspace.user_embeddings
WHERE user_id != 'target_user'
ORDER BY similarity
LIMIT 10;
```

---

## 参考文档

- [ZettaPark 快速上手](references/zettapark-api.md)
- [统计分析函数](references/stats-functions.md)
- [BITMAP 用户画像](references/bitmap-profile.md)
- [TABLESAMPLE 采样](https://www.yunqi.tech/documents/tablesample)
- [信用评分端到端示例](https://github.com/yunqiqiliang/clickzetta_quickstart/tree/main/Zettapark-credit-scoring)
- [特征工程示例](https://github.com/yunqiqiliang/clickzetta_quickstart/blob/main/Zettapark/FeatureEngineeringForExpandingCustomerFeatureswithZettapark.ipynb)
