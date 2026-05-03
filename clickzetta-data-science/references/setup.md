# 环境搭建与项目配置

## 环境搭建

```bash
# 方式 1：venv（推荐）
python3.12 -m venv .venv
source .venv/bin/activate          # macOS/Linux
pip install clickzetta_zettapark_python clickzetta-connector-python \
    python-dotenv pandas numpy scikit-learn pyarrow jupyterlab matplotlib seaborn

# 方式 2：pyenv（需要切换 Python 版本时）
pyenv install 3.12.9 && pyenv local 3.12.9
python -m venv .venv && source .venv/bin/activate
pip install clickzetta_zettapark_python clickzetta-connector-python \
    python-dotenv pandas numpy scikit-learn pyarrow jupyterlab matplotlib seaborn

# 方式 3：conda
conda create -n lakehouse-ds python=3.12 -y && conda activate lakehouse-ds
pip install clickzetta_zettapark_python clickzetta-connector-python \
    python-dotenv pandas numpy scikit-learn pyarrow jupyterlab matplotlib seaborn
```

| 问题 | 修复 |
|------|------|
| Python 3.8/3.9 | `pyenv install 3.12.9` 或 `python3.12 -m venv .venv` |
| `pyarrow` 版本冲突 | `pip install pyarrow==14.0.0` |
| M1/M2 Mac 报错 | `pip install --no-binary :all:` 或改用 conda |
| 连接超时 | VCluster 未启动，在 Studio 中手动启动 |

---

## Jupyter Kernel 配置

```bash
# 注册 venv 为 Jupyter kernel（关键步骤，否则 notebook 用系统 Python）
source .venv/bin/activate
pip install ipykernel jupyterlab
python -m ipykernel install --user --name lakehouse-ds --display-name "Python (lakehouse-ds)"

# 启动 JupyterLab
jupyter lab --port=8888
```

VS Code / Cursor：打开 `.ipynb` → 右上角 "Select Kernel" → 选 "Python (lakehouse-ds)"

| 问题 | 修复 |
|------|------|
| `ModuleNotFoundError: clickzetta` | kernel 未选对，切换到注册的 venv kernel |
| `.env` 读不到 | `load_dotenv(dotenv_path='../.env')` 指定路径 |
| `to_pandas()` OOM | 加 `TABLESAMPLE ROW(1)` 或 `LIMIT` |
| 图表不显示 | notebook 开头加 `%matplotlib inline` |

---

## src/config.py 模板

```python
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from clickzetta.zettapark.session import Session
import clickzetta

# 多位置查找 .env
for _p in [
    Path(__file__).parent.parent / ".env",
    Path.home() / ".config" / "kilo" / ".env",
    Path.home() / ".czcode" / ".env",
    Path.home() / ".env",
]:
    if _p.exists():
        load_dotenv(dotenv_path=_p)
        break

def check_environment():
    """在 00-env-check.ipynb 里调用，打印环境诊断。"""
    ver = sys.version_info
    if ver < (3, 10):
        raise RuntimeError(
            f"Python {ver.major}.{ver.minor} 不满足要求。ZettaPark 需要 Python 3.10+。\n"
            "升级：brew install pyenv && pyenv install 3.12.9 && pyenv local 3.12.9"
        )
    print(f"✅ Python {ver.major}.{ver.minor}.{ver.micro}")
    for pkg, mod in [
        ("clickzetta_zettapark_python", "clickzetta.zettapark"),
        ("clickzetta-connector-python", "clickzetta"),
        ("pandas", "pandas"), ("python-dotenv", "dotenv"),
    ]:
        try:
            m = __import__(mod.split(".")[0])
            print(f"✅ {pkg}: {getattr(m, '__version__', 'ok')}")
        except ImportError:
            print(f"❌ {pkg}: 未安装 → pip install {pkg}")
    try:
        s = get_session()
        print(f"✅ Lakehouse: {s.sql('SELECT current_workspace(), current_user()').collect()}")
    except Exception as e:
        print(f"❌ Lakehouse 连接失败: {e}")

def get_session() -> Session:
    return Session.builder.configs({
        "service":   os.environ["CLICKZETTA_SERVICE"],
        "instance":  os.environ["CLICKZETTA_INSTANCE"],
        "workspace": os.environ["CLICKZETTA_WORKSPACE"],
        "username":  os.environ["CLICKZETTA_USERNAME"],
        "password":  os.environ["CLICKZETTA_PASSWORD"],
        "vcluster":  os.environ.get("CLICKZETTA_VCLUSTER", "default_ap"),
        "schema":    os.environ.get("CLICKZETTA_SCHEMA", "public"),
    }).create()

def get_connector_connection():
    """仅用于 pd.read_sql。禁止用于 df.to_sql()。"""
    return clickzetta.connect(
        service=os.environ["CLICKZETTA_SERVICE"],
        instance=os.environ["CLICKZETTA_INSTANCE"],
        workspace=os.environ["CLICKZETTA_WORKSPACE"],
        username=os.environ["CLICKZETTA_USERNAME"],
        password=os.environ["CLICKZETTA_PASSWORD"],
        vcluster=os.environ.get("CLICKZETTA_VCLUSTER", "default_ap"),
        schema=os.environ.get("CLICKZETTA_SCHEMA", "public"),
    )
```

---

## .env 模板

```bash
CLICKZETTA_SERVICE=cn-shanghai-alicloud.api.clickzetta.com
CLICKZETTA_INSTANCE=<instance-id>
CLICKZETTA_WORKSPACE=<workspace>
CLICKZETTA_USERNAME=<username>
CLICKZETTA_PASSWORD=<password>
CLICKZETTA_VCLUSTER=default_ap
CLICKZETTA_SCHEMA=ds_workspace
```

## pyproject.toml

```toml
[project]
name = "my-lakehouse-ds-project"
requires-python = ">=3.10"
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
