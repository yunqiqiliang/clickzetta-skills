# clickzetta-connector-python 详细参考

## 安装

```bash
pip install clickzetta-connector-python -U
```

## 建立连接

```python
from clickzetta import connect

conn = connect(
    username='your_username',
    password='your_password',
    service='api.clickzetta.com',
    instance='your_instance',
    workspace='your_workspace',
    schema='public',
    vcluster='default'
)
```

## 基本查询

```python
cursor = conn.cursor()
cursor.execute('SELECT * FROM orders LIMIT 10')
results = cursor.fetchall()
for row in results:
    print(row)
cursor.close()
conn.close()
```

## 参数绑定

支持两种风格（PEP-249 规范）：

### qmark 风格（推荐）

```python
# 单行插入
cursor.execute('INSERT INTO test (id, name) VALUES (?, ?)', binding_params=[1, 'test'])

# 批量插入（executemany）
data = [
    (1, 'test1'),
    (2, 'test2'),
    (3, 'test3')
]
cursor.executemany('INSERT INTO test (id, name) VALUES (?, ?)', data)
```

### pyformat 风格

```python
data = {'id': 1, 'name': 'test'}
cursor.execute('INSERT INTO test (id, name) VALUES (%(id)s, %(name)s)', data)
```

## SQL hints（超时控制等）

```python
my_param = {
    'hints': {
        'sdk.job.timeout': 30    # 查询超时秒数
    }
}
cursor.execute('SELECT * FROM large_table', my_param)
```

## 异步执行（长时间查询）

```python
import time

cursor.execute_async('SELECT * FROM large_table')

while not cursor.is_job_finished():
    print("查询执行中...")
    time.sleep(1)

results = cursor.fetchall()
```

## 结果保存到 CSV

```python
import csv

cursor.execute('SELECT * FROM orders LIMIT 1000')
results = cursor.fetchall()

with open('output.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow([col[0] for col in cursor.description])
    writer.writerows(results)

cursor.close()
conn.close()
```

## SQLAlchemy 集成

```python
from sqlalchemy import create_engine, text

engine = create_engine(
    "clickzetta://username:password@instance.api.clickzetta.com/workspace"
    "?schema=public&vcluster=default"
)

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM orders LIMIT 10"))
    for row in result:
        print(row)
```

### SQLAlchemy + pandas

```python
import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine(
    "clickzetta://username:password@instance.api.clickzetta.com/workspace"
    "?schema=public&vcluster=default"
)

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM orders"))
    df = pd.DataFrame(result.fetchall(), columns=result.keys())

print(df.head())
```

## 注意事项

- 不支持 `commit()` 和 `rollback()` 接口
- 需要 `clickzetta-connector-python >= 0.8.82` 才能使用参数绑定和异步执行
- 旧版 `clickzetta-connector` 已停止维护，请迁移到 `clickzetta-connector-python`
