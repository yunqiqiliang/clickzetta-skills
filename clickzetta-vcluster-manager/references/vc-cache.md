# 计算集群缓存参考

> 来源：https://www.yunqi.tech/documents/vc_cache

## 缓存类型

Lakehouse 提供三种缓存：
1. **查询结果缓存（ResultCache）** - 服务层，工作空间内共享
2. **元数据缓存（MetadataCache）** - 服务层，工作空间内共享
3. **计算集群本地缓存（Local Disk Cache）** - 保存在集群本地节点，仅使用指定集群时可用

## 主动缓存（PRELOAD_TABLES）

仅适用于**分析型（AP）**集群。集群每次启动时自动加载预缓存表的最新数据/分区。

```sql
-- 设置预加载表（覆盖写，需带上所有已有表）
ALTER VCLUSTER default SET PRELOAD_TABLES = "schema1.table1,schema2.table2";

-- 添加新表时，必须包含原有表，否则会覆盖
ALTER VCLUSTER default SET PRELOAD_TABLES = "schema1.table1,schema2.table2,schema3.table3";

-- 支持通配符
ALTER VCLUSTER bi_vc SET PRELOAD_TABLES = "sales.*,public.dim_date";
```

⚠️ 注意：执行缓存命令后，只有新写入的数据才会被缓存。

## 被动缓存

首次查询时自动缓存读取的文件，后续相同查询直接命中缓存。支持 GP 型和 AP 型集群。

## 查看缓存状态

```sql
-- 显示当前集群的预加载表/分区状态
SHOW PRELOAD CACHED STATUS;

-- 显示指定集群的预加载状态
SHOW VCLUSTER <vc_name> PRELOAD CACHED STATUS;

-- 按表名过滤
SHOW VCLUSTER <vc_name> PRELOAD CACHED STATUS WHERE table LIKE '%table_name%';

-- 显示预加载缓存汇总信息
SHOW EXTENDED PRELOAD CACHED STATUS;
```

## 注意事项

- 集群停止时，本地缓存自动释放
- AP 型集群重启时只缓存最新写入的数据或分区
- `SHOW PRELOAD` 状态更新可能有约 10 分钟延迟，但缓存实际已生效
- PRELOAD_TABLES 是覆盖写，添加新表时需带上所有已有表
