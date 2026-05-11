# 费用计量视图字段说明

> 已通过实际 Lakehouse 连接验证（cn-shanghai-alicloud, f8866243）
> 访问路径：`SYS.information_schema.<视图名>`
> 权限要求：INSTANCE ADMIN

---

## STORAGE_METERING 视图

存储费用明细，按天、按工作空间、按 SKU 记录存储计量数据。

实际字段（16列）：

| 字段名 | 类型 | 说明 |
|---|---|---|
| ACCOUNT_ID | BIGINT | 账户 ID |
| ACCOUNT_NAME | STRING | 账户名称 |
| INSTANCE_ID | BIGINT | 实例 ID |
| REGION_NAME | STRING | 地域名称（如 阿里云-华东2（上海）） |
| SKU_CATEGORY | STRING | 费用类别：`storage` / `network` |
| SKU_NAME | STRING | 具体 SKU 名称（见下表） |
| WORKSPACE_ID | BIGINT | 工作空间 ID |
| WORKSPACE_NAME | STRING | 工作空间名称 |
| MEASUREMENT_START | TIMESTAMP | 计量周期开始时间（通常为某天 00:00:00） |
| MEASUREMENT_END | TIMESTAMP | 计量周期结束时间（通常为某天 23:59:59） |
| MEASUREMENTS_UNIT | STRING | 计量单位（如 `yuan/GB/day`、`yuan/gb`、`none`） |
| MEASUREMENTS_CONSUMPTION | DECIMAL | 消耗量（单位由 MEASUREMENTS_UNIT 决定） |
| PRICE_RATE | DECIMAL | 单价 |
| AMOUNT | DECIMAL | 费用金额（元） |
| DISCOUNT_RATE | DECIMAL | 折扣率（1.0 = 无折扣） |
| TOTAL_AFTER_DISCOUNT | DECIMAL | 折后金额（元） |

### SKU 枚举值

| SKU_CATEGORY | SKU_NAME | MEASUREMENTS_UNIT | 说明 |
|---|---|---|---|
| storage | 托管存储容量 | yuan/GB/day | 内部表数据文件存储 |
| storage | 多版本未删除存储 | none | Time Travel 历史版本存储 |
| network | 数据查询Internet数据传输 | yuan/gb | 公网数据传输 |

---

## INSTANCE_USAGE 视图

计算费用明细，按天、按工作空间、按 SKU 记录计算资源使用数据。

实际字段（16列，与 STORAGE_METERING 相同结构）：

| 字段名 | 类型 | 说明 |
|---|---|---|
| ACCOUNT_ID | BIGINT | 账户 ID |
| ACCOUNT_NAME | STRING | 账户名称 |
| INSTANCE_ID | BIGINT | 实例 ID |
| REGION_NAME | STRING | 地域名称 |
| SKU_CATEGORY | STRING | 费用类别：`compute` |
| SKU_NAME | STRING | 具体 SKU 名称（见下表） |
| WORKSPACE_ID | BIGINT | 工作空间 ID |
| WORKSPACE_NAME | STRING | 工作空间名称 |
| MEASUREMENT_START | TIMESTAMP | 计量周期开始时间 |
| MEASUREMENT_END | TIMESTAMP | 计量周期结束时间 |
| MEASUREMENTS_UNIT | STRING | 计量单位（`yuan/cru`） |
| MEASUREMENTS_CONSUMPTION | DECIMAL | 消耗的 CRU 量 |
| PRICE_RATE | DECIMAL | 单价（元/CRU） |
| AMOUNT | DECIMAL | 费用金额（元） |
| DISCOUNT_RATE | DECIMAL | 折扣率 |
| TOTAL_AFTER_DISCOUNT | DECIMAL | 折后金额（元） |

### SKU 枚举值

| SKU_CATEGORY | SKU_NAME | 说明 |
|---|---|---|
| compute | AP类型计算集群 | 分析型 VCluster 费用 |
| compute | GP类型计算集群 | 通用型 VCluster 费用 |
| compute | 任务调度 | Studio 任务调度费用 |
| compute | 数据集成 | 离线/实时同步任务费用 |
| compute | 流式集成 | 流式数据集成费用 |

---

## 常用费用查询

```sql
-- 本月各工作空间计算费用汇总
SELECT workspace_name,
       sku_name,
       ROUND(SUM(measurements_consumption), 2) AS total_cru,
       ROUND(SUM(amount), 2) AS total_yuan
FROM SYS.information_schema.instance_usage
WHERE measurement_start >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY workspace_name, sku_name
ORDER BY total_yuan DESC;

-- 本月各工作空间存储费用汇总
SELECT workspace_name,
       sku_name,
       ROUND(SUM(measurements_consumption), 4) AS consumption,
       measurements_unit,
       ROUND(SUM(amount), 4) AS total_yuan
FROM SYS.information_schema.storage_metering
WHERE measurement_start >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY workspace_name, sku_name, measurements_unit
ORDER BY workspace_name, total_yuan DESC;

-- 按天统计计算费用趋势（最近 30 天）
SELECT DATE(measurement_start) AS dt,
       sku_name,
       ROUND(SUM(amount), 2) AS daily_yuan
FROM SYS.information_schema.instance_usage
WHERE measurement_start >= CURRENT_DATE - INTERVAL 30 DAY
GROUP BY DATE(measurement_start), sku_name
ORDER BY dt, daily_yuan DESC;

-- 存储 + 计算综合费用（本月）
SELECT cost_type, workspace_name,
       ROUND(SUM(amount), 2) AS total_yuan
FROM (
  SELECT 'compute' AS cost_type, workspace_name, amount
  FROM SYS.information_schema.instance_usage
  WHERE measurement_start >= DATE_TRUNC('month', CURRENT_DATE)
  UNION ALL
  SELECT 'storage' AS cost_type, workspace_name, amount
  FROM SYS.information_schema.storage_metering
  WHERE measurement_start >= DATE_TRUNC('month', CURRENT_DATE)
) t
GROUP BY cost_type, workspace_name
ORDER BY cost_type, total_yuan DESC;
```

---

## 注意事项

- 两个视图数据保留范围：从实例创建起至今（验证数据最早可追溯到 2025-01）
- `WORKSPACE_NAME` 可能为 NULL（对应实例级别的费用，不归属特定工作空间）
- `AMOUNT` 字段为实际计费金额（元），`TOTAL_AFTER_DISCOUNT` 为折后金额
- 与 `JOB_HISTORY.CRU` 的区别：JOB_HISTORY 记录单次作业的 CRU 消耗，INSTANCE_USAGE 是按天汇总的计费数据，含金额
