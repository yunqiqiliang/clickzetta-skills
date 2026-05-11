---
name: dt-creator
description: |
  创建 Dynamic Table 的参考资料索引。涵盖静态分区 DT 与动态分区 DT 的声明策略、
  增量计算支持的 SQL 模式、增量刷新配置项说明、以及刷新历史的查询方式。
---

# DT Creator — 参考资料索引

## references/

- **dt-declaration-strategy.md** — DT 声明策略（静态分区 DT vs 动态分区 DT 的创建语法与选择）
- **sql-limitations.md** — SQL 支持矩阵（JOIN、聚合、窗口函数、非确定性函数等的支持情况）
- **incremental-config-reference.md** — 增量计算配置参考（刷新策略、源表特征声明、状态表管理等）
- **refresh-history-guide.md** — 增量刷新历史查询（SHOW REFRESH HISTORY / DESC HISTORY / information_schema）
