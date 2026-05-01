# 数仓建模模式参考

## 传统数仓分层详细说明

### 分层职责

```
ODS（Operational Data Store）
├── 贴源存储，不做业务转换
├── 保留原始字段名和类型
├── 增加 dw_insert_time、dw_source 等元数据字段
└── 按时间分区，支持增量同步

DWD（Data Warehouse Detail）
├── 数据清洗：去重、NULL 处理、格式标准化
├── 维度退化：将常用维度字段冗余到事实表
├── 业务规则：状态码映射、金额单位统一
└── 建立主键约束（逻辑主键，ClickZetta 不强制）

DWS（Data Warehouse Summary）
├── 轻度聚合：按天/周/月汇总
├── 使用 Dynamic Table 自动增量刷新
├── 面向主题域：用户域、商品域、交易域
└── 不直接对外提供查询（由 ADS 层封装）

ADS（Application Data Store）
├── 面向具体应用/报表的宽表
├── 使用 Dynamic Table 或直接查询 DWS
└── 字段命名业务友好
```

### 命名规范建议

```
Schema 命名：ods_<业务域> / dwd_<业务域> / dws / ads
表命名：
  ODS：ods_<源系统>_<表名>（如 ods_mysql_orders）
  DWD：dwd_<主题>_<粒度>（如 dwd_trade_order_detail）
  DWS：dws_<主题>_<维度>_<周期>（如 dws_user_order_1d）
  ADS：ads_<应用>_<指标>（如 ads_report_gmv_daily）
```

---

## 大奖牌架构（Medallion）详细说明

### 分层职责

```
Bronze（铜牌层）
├── 原始数据，零转换原则
├── 支持多种格式：结构化/半结构化/非结构化
├── 保留所有历史版本（Time Travel）
└── 数据来源标记（source_system、ingestion_time）

Silver（银牌层）
├── 可信数据：去重、清洗、标准化
├── 跨源整合：统一字段命名和类型
├── 业务实体识别：用户、订单、商品
└── 可直接用于数据科学和探索性分析

Gold（金牌层）
├── 业务就绪数据：聚合指标、宽表
├── 使用 Dynamic Table 自动刷新
├── 面向 BI 工具和应用系统
└── 语义清晰，字段命名业务友好
```

### Schema 命名建议

```
bronze.<source>_<entity>   -- 如 bronze.mysql_orders
silver.<entity>            -- 如 silver.orders
gold.<domain>_<metric>     -- 如 gold.trade_gmv_daily
```

---

## Dynamic Table vs 物化视图对比

| 特性 | Dynamic Table | 物化视图 |
|---|---|---|
| 刷新机制 | CBO 增量计算，只刷新变化分区 | 全量或手动增量 |
| 调度方式 | TARGET_LAG 自动控制 | 需手动配置调度 |
| Time Travel | ✅ 支持 | ❌ 不支持 |
| 数据恢复 | ✅ RESTORE TABLE | ❌ 不支持 |
| 语法复杂度 | 简单，类似 CREATE TABLE | 较复杂 |
| 推荐场景 | **新项目首选** | 遗留项目兼容 |

**结论：新建项目一律使用 Dynamic Table，不使用物化视图。**

---

## 常见建模陷阱

1. **过度规范化**：DWD 层不要拆太细，适当冗余维度字段，减少下游 JOIN
2. **分区粒度过细**：按小时分区会产生大量小文件，日批场景用按天分区
3. **ADS 层直接写 SQL**：ADS 层应该用 Dynamic Table，不要让 BI 工具直接跑复杂 SQL
4. **忽略数据质量**：ODS 层入库时就应该检查 NULL 比例，不要等到 DWS 层才发现问题
5. **Bronze 层做转换**：Bronze 层一旦做了转换，原始数据就丢失了，回溯困难
