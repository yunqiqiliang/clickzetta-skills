# Result Cache（查询结果缓存）参考

> 来源：https://www.yunqi.tech/documents/result_cache

## 概述

ClickZetta Lakehouse 提供三种缓存：
1. **查询结果缓存（Result Cache）** — 本文档
2. 元数据缓存（Metadata Cache）— 工作空间内共享
3. 虚拟集群本地缓存（Local Disk Cache）— 仅限指定集群

## 启用 / 禁用

```sql
-- 开启结果缓存（SESSION 级别）
SET cz.sql.enable.shortcut.result.cache = true;

-- 关闭结果缓存
SET cz.sql.enable.shortcut.result.cache = false;
```

> 注意：当前默认未开启，需手动启用。

## 缓存复用条件（同时满足才能命中）

1. 查询中使用的表数据未发生变更
2. 查询中不包含视图引用
3. 新 SQL 与之前执行的 SQL 语法精确匹配
4. 查询中不包含非确定性函数（如 `CURRENT_TIMESTAMP()`）或 UDF
5. 之前的 Result Cache 未过期

## 过期周期

- 默认保留 **24 小时**
- 24 小时内有查询复用，则额外延长 24 小时
- 超过 24 小时无复用则清除

## 约束与限制

| 项目 | 限制 |
|---|---|
| 缓存保留周期 | 24 小时 |
| 单工作空间最大缓存作业数 | 10 万 |
| 缓存大小 | 无限制（≤10MB 存内存，>10MB 持久化到对象存储） |
| 不支持 | 含非确定性函数、UDF 的查询 |

## 验证是否命中缓存

第二次执行相同查询后，在 Job Profile 的执行计划图中查看是否出现 `JOB RESULT REUSE` 标记。命中缓存的查询通常在 15ms 内返回。
