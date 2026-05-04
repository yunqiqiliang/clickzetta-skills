# clickzetta-ingestion-python BulkLoad 详细参考

## 安装

```bash
# 按云环境选择（推荐按需安装，all 安装较慢且可能冲突）
pip install "clickzetta-ingestion-python[oss]" -U    # 阿里云
pip install "clickzetta-ingestion-python[s3]" -U     # AWS
pip install "clickzetta-ingestion-python[cos]" -U    # 腾讯云
pip install "clickzetta-ingestion-python[gcp]" -U    # Google Cloud
pip install "clickzetta-ingestion-python[all]" -U    # 全部
```

## 工作原理

```
[SDK 写入数据] → [对象存储] → [调用 commit()] → [触发 SQL 导入] → [Lakehouse 表]
```

- 数据上传阶段不消耗计算资源
- `commit()` 触发从对象存储到 Lakehouse 表的导入，消耗少量计算资源
- `commit()` 只能调用一次，commit 后数据可见

## 使用限制

- **不支持主键（pk）表写入**
- **不适合时间间隔小于 5 分钟的高频写入**

## 单线程写入

### 建表

```sql
CREATE TABLE public.bulkload_test (
    i BIGINT,
    s STRING,
    d DOUBLE
);
```

### 完整示例

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

bulkload_stream = conn.create_bulkload_stream(schema='public', table='bulkload_test')

writer = bulkload_stream.open_writer(0)  # 单线程传 0
for index in range(1000000):
    row = writer.create_row()
    row.set_value('i', index)      # 按列名设值
    row.set_value('s', 'Hello')
    row.set_value('d', 123.456)
    writer.write(row)
writer.close()

bulkload_stream.commit()           # 提交，数据可见
```

## 读取 CSV 写入示例

```python
from clickzetta import connect
import csv

conn = connect(
    username='',
    password='',
    service='api.clickzetta.com',
    instance='',
    workspace='',
    schema='public',
    vcluster='default_ap'
)

bulkload_stream = conn.create_bulkload_stream(schema='public', table='bulk_order_payments')
writer = bulkload_stream.open_writer(0)

with open('olist_order_payments_dataset.csv', 'r') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # 跳过 header
    for record in reader:
        row = writer.create_row()
        row.set_value('order_id', record[0])
        row.set_value('payment_sequence', int(record[1]))
        row.set_value('payment_type', record[2])
        row.set_value('payment_installments', int(record[3]))
        row.set_value('payment_value', float(record[4]))
        writer.write(row)  # ⚠️ 必须调用，否则数据不发送到服务端

writer.close()
bulkload_stream.commit()
```

## 写入模式

```python
from clickzetta.bulkload.bulkload_enums import BulkLoadOperation

# APPEND 模式（默认）：新数据追加，不影响旧数据
bulkload_stream = conn.create_bulkload_stream(schema='public', table='my_table')

# OVERWRITE 模式：清空旧数据，写入新数据
bulkload_stream = conn.create_bulkload_stream(
    schema='public',
    table='my_table',
    operation=BulkLoadOperation.OVERWRITE
)

# 分区表 OVERWRITE（只覆盖指定分区）
bulkload_stream = conn.create_bulkload_stream(
    schema='public',
    table='my_partitioned_table',
    partition_spec='pt=2024-01-01',
    operation=BulkLoadOperation.OVERWRITE
)
```

## 分布式并发写入

适合 GB 级以上数据，多进程并发写入同一 stream，最后统一 commit。

### 控制进程

```python
import subprocess
from clickzetta import connect

conn = connect(username='username', password='password',
               service='api.clickzetta.com', instance='instance',
               workspace='quickstart_ws', schema='public', vcluster='default')

bulkload_stream = conn.create_bulkload_stream(schema='public', table='bulkload_test')
stream_id = bulkload_stream.get_stream_id()

# 启动多个写入进程，每个进程用不同的 writer_id
p1 = subprocess.Popen(['python', 'writer.py', stream_id, '1'])
p2 = subprocess.Popen(['python', 'writer.py', stream_id, '2'])
p1.wait()
p2.wait()

bulkload_stream.commit()  # 所有 writer 完成后统一 commit
```

### 写入进程

```python
import sys
from clickzetta import connect

conn = connect(username='username', password='password',
               service='api.clickzetta.com', instance='instance',
               workspace='quickstart_ws', schema='public', vcluster='default')

stream_id = sys.argv[1]
writer_id = int(sys.argv[2])

# 通过 stream_id 获取已有 stream（不创建新的）
bulkload_stream = conn.get_bulkload_stream(
    schema='public', table='bulkload_test', stream_id=stream_id
)

writer = bulkload_stream.open_writer(writer_id)  # writer_id 必须唯一
for index in range(1, 1000000):
    row = writer.create_row()
    row.set_value('i', index)
    row.set_value('s', 'Hello')
    row.set_value('d', 123.456)
    writer.write(row)
writer.close()
# 写入进程不调用 commit，只有控制进程调用
```

## 关键 API

| API | 说明 |
|---|---|
| `conn.create_bulkload_stream(schema, table)` | 创建新的 bulkload stream |
| `conn.get_bulkload_stream(schema, table, stream_id)` | 获取已有 stream（分布式写入用） |
| `bulkload_stream.get_stream_id()` | 获取 stream id（传给写入进程） |
| `bulkload_stream.open_writer(writer_id)` | 创建 writer，id 必须唯一 |
| `writer.create_row()` | 创建行对象 |
| `row.set_value(column_name, value)` | 按列名设值 |
| `writer.write(row)` | 写入行（必须调用） |
| `writer.close()` | 关闭 writer（写完必须调用） |
| `bulkload_stream.commit()` | 提交，数据可见（只能调用一次） |
