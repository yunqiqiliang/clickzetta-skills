# Dynamic Table 增量计算配置参考

本文档列出 Dynamic Table / Materialized View 增量刷新中可供用户调整的配置项。所有配置均通过 `SET` 语句在 Session 级别生效。

---

## 刷新策略

控制增量刷新与全量刷新之间的切换行为。

### `cz.optimizer.incremental.force.full.refresh`

- 类型：bool，默认值：`false`

强制当次刷新使用全量模式，跳过增量逻辑，对所有源表做全量扫描重算。

**适用场景：**
- 增量刷新结果出现数据异常（如数据缺失、重复），需要做一次全量修复
- 维度表发生了重要变更（如修正了映射关系），需要让所有历史数据重新 JOIN 到最新维度
- DT 的状态表被误删或损坏，增量刷新报错，需要从头重算

**优势：** 全量重算可以保证结果与直接执行 SQL 完全一致，是最可靠的数据修复手段。

**风险：** 全量刷新需要扫描所有源表的全部数据，计算量和耗时远大于增量刷新。对于大数据量的 DT，一次全量刷新可能需要数分钟甚至数小时。

**注意：** 这是一个 Session 级别的一次性开关。刷新完成后必须手动设回 `false`，否则后续每次 REFRESH 都会走全量，浪费计算资源。

```sql
SET cz.optimizer.incremental.force.full.refresh = true;
REFRESH DYNAMIC TABLE my_dt;
SET cz.optimizer.incremental.force.full.refresh = false;
```

### `cz.optimizer.incremental.try.incremental.refresh.enabled`

- 类型：bool，默认值：`false`

优先尝试增量刷新；若增量计划生成失败（如 SQL 中包含不支持增量的算子），自动回退至全量刷新，而非直接报错。

**适用场景：**
- 刚将一个复杂 SQL 迁移为 DT，不确定所有算子是否都支持增量计算，希望"能增量就增量，不行就全量"
- 生产环境中希望保证刷新任务不因增量计划生成失败而中断

**优势：** 提高了 DT 刷新的容错性。即使 SQL 中包含增量引擎暂不支持的模式，刷新任务也不会失败，而是自动降级为全量刷新。

**风险：** 如果增量计划生成持续失败，每次刷新都会静默回退为全量，用户可能不知道自己的 DT 一直在走全量，浪费计算资源。建议配合日志监控，关注是否频繁回退。

```sql
-- 在 REFRESH 语句前执行
SET cz.optimizer.incremental.try.incremental.refresh.enabled = true;
REFRESH DYNAMIC TABLE my_dt;
```

---

## 源表数据特征声明

通过声明源表的数据特征，引导增量引擎选择更高效的计算策略。

### `cz.optimizer.incremental.dimension.tables`

- 类型：string，默认值：`""`

将指定的源表标记为维度表。标记后，增量引擎不再读取该表的变更数据，每次刷新时直接读取其最新全量数据。只有非维度表（事实表）的变更才会驱动增量计算。

格式为逗号或冒号分隔的表名，支持完整路径 `instanceId.ws.schema.table` 或简短名称。

**这是一个用正确性换性能的权衡。** 标记为维度表后，该表的任何数据变更（INSERT/UPDATE/DELETE）都不会触发增量计算，已输出的结果行不会因维度表变更而更新。作为回报，增量引擎可以获得显著的性能提升：
- 跳过维度表的变更数据扫描（不需要读取变更日志）
- 减少状态表数量（JOIN 一侧全是维度表时不需要创建状态表）
- 简化增量计划（只需要用事实表的变更数据 JOIN 维度表的全量数据，不需要反向计算）
- 减少增量数据的去重合并操作

**适用场景：**
- 事实表 LEFT JOIN 码表/字典表（如地区码表、产品分类表），码表极少变更，不需要跟踪其变更
- 大事实表 JOIN 小维度表，核心诉求是事实表的增量性能，维度表偶尔变更后可以接受短暂不一致
- 外部表（如 MySQL 外表）不支持 time travel，无法提供变更数据，标记为维度表后可正常增量计算
- T+1 维度表 + 实时事实表：维度表每天批量更新一次，在两次更新之间可视为不变

**正确性影响：** 维度表变更后，已输出的结果不会自动更新。例如维度表中某行的 `name` 从 `'A'` 改为 `'B'`，已经 JOIN 过该行的历史结果仍然显示 `'A'`。只有新的事实表增量才会 JOIN 到最新的 `'B'`。如果需要订正历史数据，必须手动执行一次全量刷新。

详细的正确性影响分析和各 JOIN 类型下的行为，请参阅《维度表 JOIN 场景详解》文档（dimension-table-join-guide）。

```sql
-- 推荐：通过 DT 表属性声明（跟随 DT 定义，不需要每次 REFRESH 前设置）
CREATE DYNAMIC TABLE my_dt
TBLPROPERTIES('mv_const_tables' = 'dim_product,dim_region')
AS SELECT ...;

-- 查看已设置的 TBLPROPERTIES（⚠️ 不支持 SHOW TBLPROPERTIES 语法）
SHOW CREATE TABLE my_dt;

-- 或通过 Session 配置（在 REFRESH 语句前执行）
SET cz.optimizer.incremental.dimension.tables = 'dim_product,dim_region';
REFRESH DYNAMIC TABLE my_dt;

-- 维度表发生重要变更后，手动全量刷新订正数据
SET cz.optimizer.incremental.force.full.refresh = true;
REFRESH DYNAMIC TABLE my_dt;
SET cz.optimizer.incremental.force.full.refresh = false;
```

### `cz.optimizer.incremental.append.only.tables`

- 类型：string，默认值：`""`

将指定的源表标记为"预期仅追加"。这是一个优化 hint，告诉优化器该表预期只有 INSERT 操作，优化器据此选择更高效的增量计划（如提前创建针对仅追加场景优化的中间状态）。

**这不影响正确性。** 即使标记为 append-only 的表后续实际发生了 UPDATE 或 DELETE，增量引擎仍然会正常捕获并计算这些变更，结果不会出错。区别在于：当实际发生了 UPDATE/DELETE 时，优化器之前基于"仅追加"假设选择的计划可能不是最优的，性能上可能不如未标记时的计划。

**适用场景：**
- Kafka 消费落地表、日志表、埋点表等绝大多数时候只有 INSERT 的数据源
- 源表偶尔可能有少量 UPDATE/DELETE（如数据修正），但主要写入模式是 INSERT

**优势：** 优化器基于"仅追加"假设可以选择更高效的增量计划，减少不必要的中间状态维护开销。对于聚合场景，可以直接累加而不需要维护完整的中间状态。性能提升显著，尤其是在包含 JOIN 和聚合的复杂 SQL 中。

**风险：** 如果该表实际频繁发生 UPDATE/DELETE，优化器基于"仅追加"假设选择的计划可能不是最优的，增量刷新性能可能不如不标记时好。但结果的正确性不受影响。

```sql
-- 推荐：通过表属性声明（永久生效，不需要每次刷新前设置）
ALTER TABLE event_log SET PROPERTIES('INCR_APPEND_ONLY_TABLE' = 'true');

-- 或通过 Session 配置（在 REFRESH 语句前执行）
SET cz.optimizer.incremental.append.only.tables = 'event_log,click_stream';
REFRESH DYNAMIC TABLE my_dt;
```

---

## 全量刷新回退策略

当源表变更量过大或特定表发生变更时，自动从增量切换为全量刷新。

### `cz.optimizer.incremental.full.refresh.if.these.tables.change`

- 类型：string，默认值：`""`

逗号分隔的表名列表。当列表中的任意表在本次刷新周期内有数据变更时，自动触发全量刷新。

**适用场景：**
- DT 的 SQL 中 JOIN 了一张关键维度表（如价格表、汇率表），该表一旦变更，所有历史数据都需要按新值重算
- 与 `cz.optimizer.incremental.dimension.tables` 的区别：`dimension.tables` 是忽略变更继续增量；本配置是检测到变更后触发全量重算

**优势：** 保证了关键表变更后结果的正确性——一旦检测到变更，自动全量重算，不需要人工干预。

**风险：** 如果指定的表变更频繁（如每小时都有更新），每次刷新都会触发全量，完全失去增量的性能优势。应仅用于变更频率极低但变更影响面大的表。

```sql
-- 在 REFRESH 语句前执行
SET cz.optimizer.incremental.full.refresh.if.these.tables.change = 'dim_pricing,dim_exchange_rate';
REFRESH DYNAMIC TABLE my_dt;
```

### `cz.optimizer.incremental.full.refresh.if.source.table.changes.significantly`

- 类型：bool，默认值：`false`

启用后，当源表的增量数据量占全量数据量的比例超过阈值时，自动切换为全量刷新。

**适用场景：**
- 源表偶尔会发生大批量数据导入（如历史数据回灌），此时增量数据量接近甚至超过全量，增量刷新反而比全量更慢
- 希望系统自动判断"增量划不划算"，不划算时自动切全量

**优势：** 自动在增量和全量之间选择最优策略，避免增量数据量过大时增量刷新反而更慢的问题（增量需要额外的变更数据计算、去重合并、状态表读写等开销）。

**风险：** 阈值判断基于统计信息，可能不完全准确。如果统计信息不精确，可能出现不必要的全量刷新或该切全量时没切的情况。

需配合 `cz.optimizer.incremental.threshold.of.source.table.change.for.full.refresh` 设置阈值。

### `cz.optimizer.incremental.threshold.of.source.table.change.for.full.refresh`

- 类型：double，默认值：`1.0`

触发全量刷新的变更比例阈值。当增量数据量 / 全量数据量超过此值时触发全量刷新。

- `1.0`：增量数据量超过全量时才触发（非常保守）
- `0.5`：增量超过全量的一半就触发
- `0.1`：增量超过全量的 10% 就触发（激进，适用于增量计算开销较大的复杂 SQL）

```sql
-- 在 REFRESH 语句前执行
SET cz.optimizer.incremental.full.refresh.if.source.table.changes.significantly = true;
SET cz.optimizer.incremental.threshold.of.source.table.change.for.full.refresh = 0.5;
REFRESH DYNAMIC TABLE my_dt;
```

---

## 状态表管理

状态表是增量引擎在刷新过程中自动创建的内部表，用于存储中间计算结果（如聚合的中间状态、JOIN 的历史数据等），以加速后续的增量刷新。

### `cz.optimizer.incremental.enable.state.table`

- 类型：bool，默认值：`true`

状态表总开关。系统默认限制每个 DT 最多创建 5 个状态表，以防止极端场景下状态表过多导致磁盘存储占用过大。当 DT 的 SQL 中包含的有状态计算算子（如聚合、JOIN、窗口函数等）超过 5 个时，若用户未显式开启此配置，系统将**放弃创建所有状态表**，增量刷新退化为每次从源表重新计算中间结果。

如果用户希望为这些算子创建状态表以获得更优的增量刷新性能，需要显式设置此配置为 `true`。**显式开启此配置意味着用户理解并接受以额外的磁盘存储为代价换取更优的增量刷新性能。**

设为 `false` 后，增量引擎不创建也不复用任何状态表，所有中间结果每次都从源表重新计算。

**适用场景：**

设为 `true`（显式开启）：
- DT 的 SQL 包含大量有状态算子（如多层 JOIN + 聚合 + 窗口函数），默认的 5 个状态表限制不足以覆盖所有算子，希望创建更多状态表以获得最优增量性能
- 用户已评估存储开销，确认可以接受额外的状态表存储占用

设为 `false`（关闭）：
- 排查状态表相关的问题（如怀疑状态表数据不一致导致增量结果异常）
- 源表数据量较小，全量重算的代价可以接受，不需要状态表加速
- 需要严格控制存储开销，不希望系统自动创建额外的表

**优势：** 显式开启后，系统可以为所有有状态算子创建状态表，最大化增量刷新的性能收益。关闭后则消除了状态表带来的所有存储开销。

**风险：** 显式开启后，状态表数量可能超过默认的 5 个限制，带来额外的磁盘存储占用。关闭后，包含聚合或多表 JOIN 的复杂 DT 每次增量刷新都需要读取源表的全量数据来重算中间结果，性能可能显著下降。

```sql
-- 显式开启：允许系统为所有有状态算子创建状态表（在 REFRESH 语句前执行）
SET cz.optimizer.incremental.enable.state.table = true;
REFRESH DYNAMIC TABLE my_dt;

-- 关闭：不创建也不复用任何状态表
SET cz.optimizer.incremental.enable.state.table = false;
REFRESH DYNAMIC TABLE my_dt;
```

### `cz.optimizer.incremental.state.table.lifecycle`

- 类型：string，默认值：`"3"`

状态表数据保留天数。超过此天数的历史版本数据将被自动清理。

**适用场景：**
- DT 的刷新间隔较长（如每周一次），默认 3 天会导致状态表在两次刷新之间被清理，下次刷新时无法复用状态表，退化为全量刷新。此时需要增大此值
- 希望减少状态表的存储占用，可以适当缩短保留期（但不能短于刷新间隔）
- 状态表内容很大，希望及时回收存储空间，可以显式缩短生命周期（例如设为 1 天），让过期版本尽快被清理

**优势：** 增大保留期可以确保状态表在刷新间隔内不被清理，保证增量刷新能正常复用状态。

**风险：** 保留期越长，状态表占用的存储空间越大。每个版本的状态表都会保留到过期，如果刷新频率高（如每小时一次）且保留期长（如 30 天），状态表的存储量会非常可观。

```sql
-- 在 REFRESH 语句前执行
SET cz.optimizer.incremental.state.table.lifecycle = '10';
REFRESH DYNAMIC TABLE my_dt;
```

### `cz.optimizer.incremental.rebuild.rule.based.state.table`

- 类型：bool，默认值：`false`

设为 `true` 后，下次刷新时重建所有状态表。重建过程会清除旧的状态表数据，基于当前源表数据重新生成。

**适用场景：**
- 状态表数据损坏（如因系统异常导致状态表写入不完整），增量刷新结果异常
- DT 的 SQL 发生了变更（如修改了聚合逻辑），旧的状态表 Schema 与新 SQL 不匹配
- 增量刷新持续报错，怀疑是状态表问题，希望从头重建

**优势：** 重建后状态表数据与当前源表完全一致，消除了历史累积的数据不一致问题。

**风险：** 重建过程中该次刷新会走全量，耗时较长。重建完成前，增量刷新不可用。

**注意：** 这是一个一次性开关。重建完成后必须设回 `false`，否则每次刷新都会重建状态表，完全失去增量的意义。

```sql
SET cz.optimizer.incremental.rebuild.rule.based.state.table = true;
REFRESH DYNAMIC TABLE my_dt;
SET cz.optimizer.incremental.rebuild.rule.based.state.table = false;
```

### `cz.optimizer.incremental.state.table.specified.schema`

- 类型：string，默认值：`""`

指定状态表存放的 Schema。默认情况下，状态表与 DT 目标表在同一个 Schema 中。

**适用场景：**
- 希望将状态表与业务表隔离，便于统一管理和监控状态表的存储占用
- 多个 DT 共享同一个 Schema 存放状态表，方便批量清理

**优势：** 业务表和状态表分离后，可以独立设置 Schema 级别的权限、配额和生命周期策略，避免状态表干扰业务表的管理。

**风险：** 跨 Schema 访问可能带来轻微的元数据查询开销。此外，如果指定的 Schema 不存在或权限不足，状态表创建会失败。

```sql
SET cz.optimizer.incremental.state.table.specified.schema = 'incr_state';
```

---

## DT 定义变更

控制 `CREATE OR REPLACE DYNAMIC TABLE` 时的兼容性检查行为。

### `cz.sql.mv.check.before.replacing.sql`

- 类型：bool，默认值：`true`

控制 `CREATE OR REPLACE DYNAMIC TABLE` 时是否对新旧 SQL 进行兼容性检查。

**开启检查（`true`，默认）：** 系统会比较新旧 SQL 的列结构，判断是否兼容。如果判定为兼容（如仅新增列），系统会保留已有的增量状态，后续继续增量刷新。但兼容性判断并非完美——对于被判定为"兼容"的变更，新增列在历史数据中将填充 NULL，且已有的历史行不会按新 SQL 重新计算，可能导致新旧数据不一致。

**关闭检查（`false`）：** 系统跳过兼容性检查，直接认定新旧 SQL 不兼容，重置增量状态（清除状态表和历史版本信息）。替换后的下一次刷新将执行全量计算，确保所有数据按新 SQL 重新生成。

**适用场景：**

设为 `false`（关闭检查）：
1. **`CREATE OR REPLACE` 卡住或报错**：某些情况下兼容性检查本身可能耗时较长或因元数据问题报错，导致 `CREATE OR REPLACE` 无法完成。关闭检查可跳过该步骤，让替换操作顺利完成。代价是下次刷新会变成全量。
2. **SQL 发生了实质性变更，希望从头重算**：如修改了 JOIN 逻辑、聚合方式等核心计算逻辑，需要全量重算以保证数据正确性。关闭检查可确保系统不会错误地判定为"兼容"而保留旧的增量状态。

保持 `true`（开启检查，默认）：
1. **仅新增列等简单变更**：希望系统自动判断兼容性，兼容时保留增量状态避免全量刷新。适用于对历史数据中新增列为 NULL 可以接受的场景。
2. **日常迭代中频繁调整 DT 定义**：依赖系统自动判断，减少不必要的全量刷新。

**开启检查的风险：** 兼容性判断可能将实际不完全兼容的变更判定为"兼容"，导致新增列在历史数据中为 NULL，或已有历史行永远不会按新 SQL 更新。

**关闭检查的风险：** 下一次刷新将执行全量计算，对于大数据量的 DT 可能耗时较长。

```sql
-- 关闭检查，确保替换后全量重算
SET cz.sql.mv.check.before.replacing.sql = false;
CREATE OR REPLACE DYNAMIC TABLE my_dt AS SELECT ...;
SET cz.sql.mv.check.before.replacing.sql = true;
-- 注意：下次 REFRESH 将执行全量刷新
```

---

## 历史分区回填（Backfill）

### `cz.optimizer.incremental.backfill.enabled`

- 类型：bool，默认值：`false`

启用回填模式。用于对 DT 的历史分区进行数据回填或修正。开启后，系统会自动执行以下操作：
- 强制当次刷新使用全量模式（等同于开启 `force.full.refresh`）
- 跳过增量数据的读取，避免读取大量历史变更日志
- 对于分区 DT，禁用状态表的创建和匹配（因为回填的分区不需要增量状态）
- 允许对 DT 执行 DML 操作（如 `INSERT OVERWRITE`）

**适用场景：**

设为 `true`（开启回填）：
1. **历史分区数据修正**：某个历史分区的数据出现问题，需要用正确的源数据重新生成该分区。
2. **新建 DT 后补充历史数据**：DT 创建后，需要为已有的历史分区逐个生成数据。
3. **源表数据回灌后重算**：源表进行了历史数据回灌，需要对受影响的分区重新计算。

**注意：**
- 回填模式是一次性操作，回填完成后应设回 `false`，否则后续每次刷新都会走全量。
- 回填模式下不会创建或更新状态表，因此不会影响后续正常增量刷新的状态。
- 回填通常配合 `INSERT OVERWRITE` 使用，覆盖目标分区的已有数据。

```sql
-- 回填指定历史分区（在 REFRESH 语句前执行）
SET cz.optimizer.incremental.backfill.enabled = true;
SET dt.args.ds = '2025-01-01';
REFRESH DYNAMIC TABLE my_dt PARTITION(ds = '2025-01-01');
SET cz.optimizer.incremental.backfill.enabled = false;

-- 也可以通过 INSERT OVERWRITE 直接回填
SET cz.optimizer.incremental.backfill.enabled = true;
INSERT OVERWRITE TABLE my_dt
SELECT id, amount, '2025-01-01' AS ds
FROM source_table
WHERE ds = '2025-01-01';
SET cz.optimizer.incremental.backfill.enabled = false;
```

---

## 全量刷新时分区表的写入行为

### `cz.optimizer.incremental.full.refresh.overwrite.partitioned.table`

- 类型：bool，默认值：`true`

控制分区 DT 在全量刷新时的写入模式。

**背景：** 对于分区表，全量刷新（`force.full.refresh = true` 或系统自动触发的全量刷新）默认采用覆盖写入（OVERWRITE）模式——这是大数据领域的通用行为，即全量重算的结果会覆盖目标表的所有分区。但在某些场景下，DT 的 SQL 只计算部分分区的数据（例如只查询最近 7 天），全量刷新的结果也只包含这部分分区。此时如果使用覆盖写入，会导致历史分区（如 7 天前的数据）被清空。

**开启覆盖（`true`，默认）：** 全量刷新时，目标表的所有分区都会被覆盖。刷新结果中不包含的分区将被清空。这适用于 DT 的 SQL 覆盖了目标表的全部数据范围的场景。

**关闭覆盖（`false`）：** 全量刷新时，只写入本次计算产生的分区数据，不影响目标表中已有的其他分区。历史分区的数据保持不变。

**适用场景：**

设为 `false`（关闭覆盖）：
1. **DT 的 SQL 只计算部分分区**：例如 SQL 中有 `WHERE ds >= '2025-01-01'` 的过滤条件，只计算最近一段时间的数据。全量刷新时不希望清空更早的历史分区。
2. **按分区逐步积累数据的 DT**：每次刷新只产生当前分区的数据，历史分区由之前的刷新产生。全量刷新时只需要重算当前分区，不应影响历史分区。
3. **滑动窗口场景**：DT 的 SQL 基于分区参数计算一个时间窗口内的数据，全量刷新时只重算窗口内的分区。

保持 `true`（开启覆盖，默认）：
1. **DT 的 SQL 覆盖全部数据**：SQL 没有分区过滤条件，全量刷新的结果包含目标表的所有数据。
2. **需要全量重建目标表**：希望全量刷新后目标表的数据与直接执行 SQL 的结果完全一致，不保留任何历史残留。

**风险：**
- 开启覆盖时，如果 DT 的 SQL 只计算部分分区，全量刷新会清空未被计算到的历史分区，导致数据丢失。
- 关闭覆盖时，如果 DT 的 SQL 覆盖全部数据，全量刷新后目标表中可能残留旧数据（因为旧分区没有被清空），导致数据不一致。

```sql
-- 关闭覆盖：全量刷新时保留历史分区（在 REFRESH 语句前执行）
SET cz.optimizer.incremental.full.refresh.overwrite.partitioned.table = false;
SET cz.optimizer.incremental.force.full.refresh = true;
REFRESH DYNAMIC TABLE my_dt;
SET cz.optimizer.incremental.force.full.refresh = false;
```

---

## 配置速查表

按使用场景快速定位所需配置：

| 场景 | 配置项 | 推荐值 |
|------|--------|--------|
| 数据异常，需要全量重算修复 | `cz.optimizer.incremental.force.full.refresh` | `true`（一次性） |
| 不确定 SQL 是否支持增量 | `cz.optimizer.incremental.try.incremental.refresh.enabled` | `true` |
| 小表 JOIN 不需要跟踪变更 | `cz.optimizer.incremental.dimension.tables` 或表属性 `mv_const_tables` | 表名列表 |
| 源表主要是 INSERT，希望优化增量性能 | `cz.optimizer.incremental.append.only.tables` 或表属性 `INCR_APPEND_ONLY_TABLE` | 表名列表 / `true` |
| 关键表变更时必须全量重算 | `cz.optimizer.incremental.full.refresh.if.these.tables.change` | 表名列表 |
| 增量数据量过大时自动切全量 | `cz.optimizer.incremental.full.refresh.if.source.table.changes.significantly` + `threshold` | `true` + `0.5` |
| SQL 算子多，需要更多状态表加速 | `cz.optimizer.incremental.enable.state.table` | `true`（显式开启） |
| 不需要状态表，或排查状态表问题 | `cz.optimizer.incremental.enable.state.table` | `false` |
| 状态表数据损坏，需要重建 | `cz.optimizer.incremental.rebuild.rule.based.state.table` | `true`（一次性） |
| 刷新间隔长，状态表被提前清理 | `cz.optimizer.incremental.state.table.lifecycle` | 增大至覆盖刷新间隔 |
| 状态表与业务表隔离管理 | `cz.optimizer.incremental.state.table.specified.schema` | Schema 名 |
| `CREATE OR REPLACE` 卡住或 SQL 实质性变更 | `cz.sql.mv.check.before.replacing.sql` | `false`（一次性） |
| 历史分区数据回填或修正 | `cz.optimizer.incremental.backfill.enabled` | `true`（一次性） |
| 全量刷新时保留历史分区数据 | `cz.optimizer.incremental.full.refresh.overwrite.partitioned.table` | `false` |
