# clickzetta-ingestion-python-v2 实时写入详细参考

## 安装

```bash
pip install clickzetta-ingestion-python-v2
```

> 注意：这是独立的包，与 `clickzetta-ingestion-python`（BulkLoad）不同。

## 与 BulkLoad 的区别

| 特性 | BulkLoad (`ingestion-python`) | 实时写入 (`ingestion-python-v2`) |
|---|---|---|
| 写入延迟 | 分钟级（commit 后可见） | 秒级可查 |
| 适用频率 | 间隔 ≥ 5 分钟 | 高频小批（5 分钟以内） |
| 主键表支持 | ❌ 不支持 | ✅ 支持（CDC 模式） |
| UPDATE/DELETE | ❌ | ✅ UPSERT / DELETE_IGNORE |
| 写入原理 | 上传对象存储 → commit 导入 | 直写 Ingestion Service |

## 工作原理

```
[SDK 写入] → [Ingestion Service] → [混合表（秒级可查）] → [~1分钟后自动 commit] → [普通表（stream/DT 可见）]
```

- 写入后秒级即可 SELECT 查到数据
- table stream、materialized view、dynamic table 需等约 1 分钟（commit 后）才能看到
- commit 后后台合并为普通表，之后可执行 UPDATE/MERGE/DELETE

## 普通表写入（APPEND_ONLY）

```python
from clickzetta.connector.v0.connection import connect
from clickzetta.connector.v0.enums import RealtimeOperation
from clickzetta_ingestion.realtime.realtime_options import RealtimeOptionsBuilder, FlushMode
from clickzetta_ingestion.realtime.arrow_stream import RowOperator

with connect(
    username='your_username',
    password='your_password',
    service='your_service_endpoint',
    instance='your_instance',
    workspace='your_workspace',
    schema='your_schema',
    vcluster='default'
) as conn:
    stream = conn.get_realtime_stream(
        schema='your_schema',
        table='your_table',
        operate=RealtimeOperation.APPEND_ONLY,
        options=RealtimeOptionsBuilder()
            .with_flush_mode(FlushMode.AUTO_FLUSH_BACKGROUND)
            .build()
    )

    for i in range(1000):
        row = stream.create_row(RowOperator.INSERT)
        row.set_value('id', str(i))
        row.set_value('name', f'user_{i}')
        stream.apply(row)

    stream.close()
```

## 主键表写入（CDC 模式）

主键表**必须**使用 `RealtimeOperation.CDC` + `FlushMode.AUTO_FLUSH_SYNC`。

```python
from clickzetta.connector.v0.connection import connect
from clickzetta.connector.v0.enums import RealtimeOperation
from clickzetta_ingestion.realtime.realtime_options import RealtimeOptionsBuilder, FlushMode
from clickzetta_ingestion.realtime.arrow_stream import RowOperator

with connect(...) as conn:
    stream = conn.get_realtime_stream(
        schema='your_schema',
        table='your_pk_table',
        operate=RealtimeOperation.CDC,
        options=RealtimeOptionsBuilder()
            .with_flush_mode(FlushMode.AUTO_FLUSH_SYNC)  # PK 表强制同步刷写
            .build()
    )

    # UPSERT：存在则更新，不存在则插入
    row = stream.create_row(RowOperator.UPSERT)
    row.set_value('id', 'id_1')
    row.set_value('name', 'alice')
    row.set_value('age', 30)
    stream.apply(row)

    # DELETE_IGNORE：删除，目标行不存在时自动忽略
    row = stream.create_row(RowOperator.DELETE_IGNORE)
    row.set_value('id', 'id_1')
    stream.apply(row)

    stream.close()
```

## 操作类型对照

| Stream 模式 | 可用 RowOperator | 适用表类型 |
|---|---|---|
| `APPEND_ONLY` | `INSERT` | 普通表 |
| `CDC` | `UPSERT`、`DELETE_IGNORE` | 主键表（必须） |

## FlushMode 说明

| 模式 | 说明 | 适用场景 |
|---|---|---|
| `AUTO_FLUSH_BACKGROUND` | 异步刷写，高吞吐 | 普通表，对顺序无要求 |
| `AUTO_FLUSH_SYNC` | 同步刷写，阻塞式 | 主键表（强制），需保证顺序 |
| `MANUAL_FLUSH` | 手动调用 `stream.flush()` | 精确控制刷写时机 |

> ⚠️ 主键表不支持 `AUTO_FLUSH_BACKGROUND`，会自动重置为 `AUTO_FLUSH_SYNC`。

## 关键注意事项

- 表结构变更前需先停止实时写入任务，变更后约 90 分钟再重启（Flink Connector 的 schema change sink 除外）
- 分区列必须是 primary key 的子集
- 避免 `flush()` 过于频繁，会产生大量小文件
