# 维度表 JOIN 场景详解

## 核心机制

将某张表标记为维度表（dimension table）后，增量引擎会将该表的变更数据视为**空**。即：
- 维度表的任何数据变更（INSERT/UPDATE/DELETE）都**不会触发增量计算**
- 增量计算时，维度表始终读取**最新全量数据**
- 只有非维度表（事实表）的变更才会驱动增量刷新

## 配置方式

```sql
-- 方式1：DT 表属性（推荐，跟随 DT 定义）
CREATE DYNAMIC TABLE my_dt
TBLPROPERTIES('mv_const_tables'='dim_table1,dim_table2')
AS SELECT ...;

-- 方式2：Session 配置（在 REFRESH 前设置，灵活可动态调整）
-- set CZ_OPTIMIZER_INCREMENTAL_DIMENSION_TABLES=dim_table1:dim_table2
```

## 各 JOIN 类型下的增量行为

### A LEFT JOIN B（B 为维度表）

这是最常见的维度表 JOIN 场景。

**Case 1：A 有增量数据，B 无变化**
```
增量计划：A 的变更数据 LEFT JOIN B 的全量数据
```
- 新增的 A 行与 B 的最新数据做 LEFT JOIN
- 如果 JOIN 上 → 输出完整行
- 如果没 JOIN 上 → B 侧输出 NULL
- ✅ 结果正确

**Case 2：B 有数据变更，A 无变化**
```
增量计划：不触发计算（变更数据为空）
```
- B 的变更被完全忽略
- 之前 A 行没 JOIN 上 B 输出的 `(xxx, NULL)` 不会被修正为 `(xxx, yyy)`
- 之前 A 行 JOIN 上的旧 B 数据不会被更新为新值
- ⚠️ 结果与全量重算不一致，但这是**预期行为**

**Case 3：A 和 B 同时有变化**
```
增量计划：A 的变更数据 LEFT JOIN B 的全量数据
```
- 只处理 A 的增量，B 的变更被忽略
- 新增的 A 行会 JOIN 到 B 的最新数据
- 但已有的 A 行不会因 B 的变更而更新
- ⚠️ 新旧数据可能存在不一致

### A INNER JOIN B（B 为维度表）

**Case 1：A 有增量数据，B 无变化**
```
增量计划：A 的变更数据 INNER JOIN B 的全量数据
```
- 新增的 A 行与 B 做 INNER JOIN
- JOIN 不上的 A 行被丢弃
- ✅ 结果正确

**Case 2：B 有数据变更，A 无变化**
```
增量计划：不触发计算
```
- B 新增了能匹配已有 A 行的数据 → 不会产出新结果
- B 删除了匹配已有 A 行的数据 → 已输出的结果不会被撤回
- ⚠️ 结果与全量重算不一致

### 多表 JOIN 中的维度表

```sql
-- t2, t3 都是维度表
CREATE DYNAMIC TABLE dt
TBLPROPERTIES('mv_const_tables'='t2,t3')
AS
SELECT t1.*, t2.v1, t3.v1
FROM t1
LEFT JOIN t2 ON t1.id = t2.id
LEFT JOIN t3 ON t1.id = t3.id;
```

- 只有 t1 的变更会触发增量计算
- t2、t3 的变更都被忽略
- 增量计划：t1 的变更数据 LEFT JOIN t2 的全量数据 LEFT JOIN t3 的全量数据

## 适合使用维度表的场景

### ✅ 推荐场景

1. **码表/字典表 JOIN**
   - 如：地区码表、产品分类表、状态码映射表
   - 特点：数据量小、极少变更、即使变更也不影响历史分析
   ```sql
   -- 地区码表几乎不变
   TBLPROPERTIES('mv_const_tables'='dim_region')
   ```

2. **T+1 维度表 + 实时事实表**
   - 维度表每天批量更新一次，事实表持续写入
   - 在两次维度表更新之间，维度表可视为不变
   ```sql
   -- 用户画像表每天更新，订单表实时写入
   TBLPROPERTIES('mv_const_tables'='dim_user_profile')
   ```

3. **配置表 JOIN**
   - 如：业务规则配置、阈值配置、权重配置
   - 变更频率极低，且变更后可以手动触发全量刷新
   ```sql
   TBLPROPERTIES('mv_const_tables'='config_rules')
   ```

4. **大事实表 JOIN 小维度表，且对维度表变更的实时性要求低**
   - 核心诉求是事实表的增量计算性能
   - 维度表偶尔变更后，可以接受短暂的数据不一致
   ```sql
   -- 商品信息表偶尔更新，订单表持续写入
   TBLPROPERTIES('mv_const_tables'='dim_product')
   ```

5. **不支持 time travel 的外部表作为 JOIN 右表**
   - 外部表无法提供变更数据，标记为维度表后可以正常进行增量计算
   - 增量引擎会读取外部表的最新快照
   ```sql
   -- 外部 MySQL 表不支持 time travel
   TBLPROPERTIES('mv_const_tables'='external_mysql_table')
   ```

### ❌ 不推荐场景

1. **维度表频繁更新且要求结果实时一致**
   - 如：用户状态表每分钟更新，且下游报表要求实时反映最新状态
   - 此时不应标记为维度表，应让两侧都参与增量计算

2. **维度表变更会影响聚合结果的正确性**
   - 如：价格表更新后，历史订单的金额计算应该用旧价格
   - 但维度表标记后，新的事实行会 JOIN 到新价格，旧事实行保持旧价格
   - 如果业务要求所有行统一使用最新价格，不应使用维度表

3. **维度表数据量大且变更频繁**
   - 维度表标记的优化收益来自跳过变更数据的计算
   - 如果维度表本身很大且频繁变更，应该考虑让它正常参与增量

## 维度表变更后的数据订正

由于维度表的变更不会触发增量计算，当维度表发生了重要变更（如修正了错误数据、更新了映射关系），DT 中已有的结果不会自动更新。**如果需要订正数据，必须执行全量刷新。**

```sql
-- 强制全量刷新（推荐）
-- set cz.optimizer.incremental.force.full.refresh=true
REFRESH DYNAMIC TABLE my_dt;
-- 刷新完成后记得关闭，否则后续每次都是全量
-- set cz.optimizer.incremental.force.full.refresh=false

-- 如果是分区表，也可以只全量刷新指定分区
-- set cz.optimizer.incremental.force.full.refresh=true
-- set dt.args.ds=2025-01-01
REFRESH DYNAMIC TABLE my_dt PARTITION(ds = '2025-01-01');
-- set cz.optimizer.incremental.force.full.refresh=false
```

配置说明：
- `cz.optimizer.incremental.force.full.refresh`：默认 `false`。设为 `true` 后，下一次 REFRESH 会忽略增量逻辑，对所有源表做全量扫描重算
- 该配置是 session 级别的，刷新完成后需要手动设回 `false`，否则后续所有 REFRESH 都会走全量
- backfill 模式（`cz.optimizer.incremental.backfill.enabled=TRUE`）也会自动开启全量刷新

## 性能收益

标记维度表后的优化效果：
- **跳过维度表的变更数据扫描**：不需要读取维度表的变更日志
- **简化增量计划**：只需要用事实表的变更数据 JOIN 维度表的全量数据，不需要反向计算

## ⚠️ 开启维度表后可能出现的数据不一致与重复

标记维度表是一种**用一致性换性能**的权衡。以下是具体会出现问题的场景，使用前务必评估业务是否可以接受。

### 场景 1：LEFT JOIN 维度表更新导致 NULL 不被修正

```sql
-- DT 定义
SELECT order.*, product.name
FROM order LEFT JOIN product ON order.pid = product.id;
-- product 标记为维度表
```

| 时间 | 事件 | DT 中的结果 | 全量重算应有的结果 |
|------|------|------------|------------------|
| T1 | order 插入 (pid=100)，product 中无 id=100 | (pid=100, name=NULL) | (pid=100, name=NULL) |
| T2 | product 插入 id=100, name='手机' | (pid=100, name=NULL) **不变** | (pid=100, name='手机') |

**原因**：product 的变更不触发增量计算，T1 输出的 NULL 行永远不会被修正。

### 场景 2：INNER JOIN 维度表新增数据导致结果缺失

```sql
SELECT order.*, product.name
FROM order INNER JOIN product ON order.pid = product.id;
-- product 标记为维度表
```

| 时间 | 事件 | DT 中的结果 | 全量重算应有的结果 |
|------|------|------------|------------------|
| T1 | order 插入 (pid=200)，product 中无 id=200 | 无输出（INNER JOIN 不匹配） | 无输出 |
| T2 | product 插入 id=200, name='电脑' | **仍然无输出** | (pid=200, name='电脑') |

**原因**：product 的新增不触发增量，已有的 order 行不会被重新 JOIN。

### 场景 3：维度表删除/更新导致过期数据残留

```sql
SELECT order.*, product.name, product.price
FROM order LEFT JOIN product ON order.pid = product.id;
-- product 标记为维度表
```

| 时间 | 事件 | DT 中的结果 | 全量重算应有的结果 |
|------|------|------------|------------------|
| T1 | order 插入 (pid=100)，product id=100 price=99 | (pid=100, price=99) | (pid=100, price=99) |
| T2 | product 更新 id=100 price=**199** | (pid=100, price=**99**) 旧值残留 | (pid=100, price=199) |
| T3 | product 删除 id=100 | (pid=100, price=**99**) 仍然残留 | (pid=100, name=NULL) |

**原因**：维度表的 UPDATE/DELETE 都被忽略，已输出的行保持旧值。

### 场景 4：维度表 + 聚合导致聚合结果不一致

```sql
SELECT product.category, SUM(order.amount) as total
FROM order LEFT JOIN product ON order.pid = product.id
GROUP BY product.category;
-- product 标记为维度表
```

| 时间 | 事件 | DT 中的结果 | 全量重算应有的结果 |
|------|------|------------|------------------|
| T1 | order (pid=1, amount=100)，product (id=1, category='A') | category='A', total=100 | 同左 |
| T2 | product 更新 id=1 的 category 从 'A' 改为 'B' | category='A', total=100 **不变** | category='B', total=100 |
| T3 | order 新增 (pid=1, amount=200) | category='B', total=200（新行 JOIN 到新 category）| category='B', total=300 |

**原因**：T2 的 category 变更不触发重算，T1 的旧数据仍按旧 category 聚合。T3 的新数据按新 category 聚合。最终结果中同一个 pid 的数据被分到了不同 category，聚合结果错乱。

### 总结：什么时候结果会不一致

| 维度表变更类型 | LEFT JOIN | INNER JOIN |
|--------------|-----------|------------|
| 新增匹配行 | 旧 fact 行的 NULL 不被修正 | 旧 fact 行不会产出新结果 |
| 更新已有行 | 旧 fact 行保持旧值 | 旧 fact 行保持旧值 |
| 删除已有行 | 旧 fact 行保持旧值（不会变 NULL） | 旧 fact 行不会被撤回 |

**核心原则**：维度表的任何变更都不会影响已经输出的结果行。只有新的事实表增量才会 JOIN 到维度表的最新快照。
