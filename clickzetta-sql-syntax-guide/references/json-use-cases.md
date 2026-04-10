# JSON 字段代替大宽表实战指南

> 云器 Lakehouse 半结构化数据能力详解与客户案例

---

## 概述

云器 Lakehouse 提供强大的 JSON 数据类型支持，允许用户在关系型表中嵌入半结构化数据。这一能力使得**用 JSON 字段代替传统大宽表**成为可能，特别适合以下场景：

- **事件日志存储**：用户行为日志、系统审计日志等字段频繁变化的场景
- **电商商品属性**：不同类目商品具有不同的属性集合
- **IoT 设备数据**：设备上报数据格式多样且经常扩展
- **SaaS 多租户配置**：各租户自定义字段差异大
- **敏捷开发迭代**：业务字段频繁变更，避免频繁 DDL

---

## 为什么用 JSON 代替大宽表？

### 传统大宽表的问题

```sql
-- ❌ 传统方式：数百列的宽表
CREATE TABLE user_events (
    event_id        BIGINT,
    user_id         BIGINT,
    event_type      STRING,
    event_time      TIMESTAMP,
    
    -- 页面浏览事件字段
    page_url        STRING,
    page_title      STRING,
    referrer        STRING,
    session_id      STRING,
    
    -- 点击事件字段
    click_element   STRING,
    click_position  STRING,
    click_target    STRING,
    
    -- 搜索事件字段
    search_query    STRING,
    search_filters  STRING,
    search_results  INT,
    
    -- 购买事件字段
    product_id      BIGINT,
    product_name    STRING,
    product_price   DECIMAL(18,2),
    quantity        INT,
    coupon_code     STRING,
    
    -- ... 还有 100+ 列，大部分为 NULL
    -- 每次新增事件类型都要 ALTER TABLE
);
```

**问题：**
1. **稀疏数据**：大部分列为 NULL，存储效率低
2. **Schema 僵化**：新增字段需要 DDL，影响线上服务
3. **维护成本高**：数百列的表难以理解和维护
4. **查询复杂**：需要处理大量 NULL 值

### JSON 方案的优势

```sql
-- ✅ 云器 Lakehouse 方案：核心字段 + JSON 扩展
CREATE TABLE user_events (
    event_id        BIGINT,
    user_id         BIGINT,
    event_type      STRING,
    event_time      TIMESTAMP,
    event_data      JSON,           -- 半结构化数据容器
    created_at      TIMESTAMP DEFAULT current_timestamp()
);
```

**优势：**
1. **灵活扩展**：新增字段无需 DDL，直接写入 JSON
2. **存储高效**：只存储实际存在的字段
3. **查询便捷**：支持 JSON 路径访问和索引
4. **Schema 演进**：业务迭代不影响现有数据

---

## 客户案例

### 案例一：电商平台商品管理系统

**背景：**
某跨境电商平台经营 50+ 商品类目，从服装到电子产品，每个类目的属性差异巨大：
- 服装：颜色、尺码、材质、款式
- 手机：CPU、内存、存储、屏幕尺寸
- 图书：作者、出版社、ISBN、页数

**传统方案问题：**
- 设计 200+ 列的宽表，90% 列为 NULL
- 新增类目需要 DBA 审批修改表结构
- 查询性能随列数增加而下降

**云器 Lakehouse 方案：**

```sql
-- 商品主表：核心字段 + JSON 扩展属性
CREATE TABLE products (
    product_id      BIGINT,
    category_id     INT,
    product_name    STRING,
    base_price      DECIMAL(18,2),
    stock_quantity  INT,
    
    -- 核心属性（所有商品共有）
    brand           STRING,
    origin_country  STRING,
    
    -- 扩展属性（按类目差异化）
    attributes      JSON,
    
    -- 元数据
    created_at      TIMESTAMP DEFAULT current_timestamp(),
    updated_at      TIMESTAMP DEFAULT current_timestamp(),
    version         INT DEFAULT 1
);
```

**数据示例：**

```sql
-- 插入服装类商品
INSERT INTO products VALUES (
    1001, 10, '纯棉 T 恤', 99.00, 500,
    '优衣库', '中国',
    PARSE_JSON('{
        "material": "100% 纯棉",
        "colors": ["白色", "黑色", "灰色"],
        "sizes": ["S", "M", "L", "XL"],
        "style": "休闲",
        "season": ["春", "夏", "秋"],
        "care_instructions": "机洗，低温烘干"
    }'),
    current_timestamp(), current_timestamp(), 1
);

-- 插入手机类商品
INSERT INTO products VALUES (
    2001, 20, '智能手机 X1', 4999.00, 100,
    '小米', '中国',
    PARSE_JSON('{
        "cpu": "骁龙 8 Gen 2",
        "ram_gb": 12,
        "storage_gb": 256,
        "screen_size_inch": 6.7,
        "resolution": "2400x1080",
        "battery_mah": 4500,
        "camera_mp": 50,
        "os": "MIUI 14",
        "5g_support": true
    }'),
    current_timestamp(), current_timestamp(), 1
);
```

**查询示例：**

```sql
-- 查询所有白色服装
SELECT product_id, product_name, base_price
FROM products
WHERE category_id = 10
  AND ARRAY_CONTAINS(attributes['colors'], '白色');

-- 查询内存大于 8GB 的手机
SELECT product_id, product_name, attributes['ram_gb'] as ram
FROM products
WHERE category_id = 20
  AND CAST(attributes['ram_gb'] AS INT) > 8;

-- 统计各材质服装数量
SELECT attributes['material'] as material, COUNT(*) as cnt
FROM products
WHERE category_id = 10
GROUP BY attributes['material'];

-- 动态字段提取（不同类目不同属性）
SELECT 
    product_id,
    product_name,
    category_id,
    CASE 
        WHEN category_id = 10 THEN attributes['material']
        WHEN category_id = 20 THEN attributes['cpu']
        WHEN category_id = 30 THEN attributes['author']
    END as key_attribute
FROM products;
```

**效果：**
- 表结构稳定，2 年未进行 DDL 变更
- 新增 10+ 商品类目，无需修改表结构
- 查询性能优于原宽表方案（减少扫描列数）
- 开发效率提升：新增属性无需等待 DBA 审批

---

### 案例二：IoT 设备监控平台

**背景：**
某工业 IoT 平台接入 10 万+ 设备，设备类型包括：
- 温度传感器：温度、湿度
- 压力传感器：压力、流速
- 摄像头：分辨率、帧率、编码格式
- PLC 控制器：输入输出点数、通信协议

**挑战：**
- 设备类型多样，上报数据格式不统一
- 新设备类型不断接入，字段频繁扩展
- 需要支持毫秒级写入和实时查询

**云器 Lakehouse 方案：**

```sql
-- 设备元数据表
CREATE TABLE devices (
    device_id       STRING,
    device_type     STRING,
    location        STRING,
    install_date    DATE,
    config          JSON,           -- 设备配置
    status          STRING,
    last_heartbeat  TIMESTAMP
);

-- 设备遥测数据表（时序数据）
CREATE TABLE telemetry_data (
    device_id       STRING,
    timestamp       TIMESTAMP,
    metric_name     STRING,
    metric_value    DOUBLE,
    tags            JSON,           -- 动态标签
    metadata        JSON            -- 扩展元数据
)
PARTITIONED BY (days(timestamp));
```

**数据示例：**

```sql
-- 温度传感器配置
INSERT INTO devices VALUES (
    'TEMP_001', 'temperature_sensor', '车间 A-01',
    DATE '2024-01-15',
    PARSE_JSON('{
        "measurement_range": {"min": -40, "max": 85},
        "accuracy": 0.5,
        "sampling_interval_sec": 60,
        "alert_thresholds": {"high": 50, "low": -10},
        "calibration_date": "2024-01-01",
        "protocol": "MQTT",
        "firmware_version": "2.3.1"
    }'),
    'online', current_timestamp()
);

-- 摄像头配置
INSERT INTO devices VALUES (
    'CAM_001', 'camera', '仓库 B-入口',
    DATE '2024-02-20',
    PARSE_JSON('{
        "resolution": "1920x1080",
        "frame_rate": 30,
        "codec": "H.265",
        "night_vision": true,
        "motion_detection": true,
        "storage_days": 30,
        "stream_url": "rtsp://192.168.1.100/stream"
    }'),
    'online', current_timestamp()
);

-- 遥测数据写入
INSERT INTO telemetry_data VALUES (
    'TEMP_001', TIMESTAMP '2024-06-15 10:30:00',
    'temperature', 25.5,
    PARSE_JSON('{"unit": "celsius", "quality": "good"}'),
    PARSE_JSON('{"battery_level": 85, "signal_strength": -65}')
);
```

**查询分析：**

```sql
-- 查询温度超过阈值的设备
SELECT d.device_id, d.location, t.metric_value, t.timestamp
FROM telemetry_data t
JOIN devices d ON t.device_id = d.device_id
WHERE t.metric_name = 'temperature'
  AND t.metric_value > CAST(d.config['alert_thresholds']['high'] AS DOUBLE)
  AND t.timestamp >= CURRENT_DATE() - INTERVAL 1 DAY;

-- 统计各类型设备在线率
SELECT 
    device_type,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online,
    ROUND(100.0 * SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) / COUNT(*), 2) as online_rate
FROM devices
GROUP BY device_type;

-- 查询特定固件版本的设备
SELECT device_id, location, config['firmware_version'] as firmware
FROM devices
WHERE config['firmware_version'] = '2.3.1';
```

**效果：**
- 支持 10 万+ 设备，日均写入 1 亿+ 条记录
- 新设备类型接入时间从 3 天缩短至 2 小时
- 查询响应时间 < 1 秒（亿级数据）
- 存储空间节省 40%（相比宽表）

---

### 案例三：SaaS 多租户配置管理

**背景：**
某 SaaS 服务商为 5000+ 企业提供 HR 管理系统，各企业自定义字段差异大：
- 员工字段：不同企业需要不同的员工属性
- 审批流程：各企业审批节点和条件不同
- 报表配置：自定义报表维度和指标

**云器 Lakehouse 方案：**

```sql
-- 租户配置表
CREATE TABLE tenant_configs (
    tenant_id       STRING,
    config_type     STRING,
    config_version  INT,
    config_data     JSON,           -- 完整配置
    is_active       BOOLEAN,
    updated_at      TIMESTAMP,
    updated_by      STRING
);

-- 员工扩展字段定义
CREATE TABLE tenant_employee_fields (
    tenant_id       STRING,
    field_name      STRING,
    field_type      STRING,
    field_config    JSON,           -- 验证规则、显示配置等
    display_order   INT,
    is_required     BOOLEAN,
    created_at      TIMESTAMP
);
```

**配置示例：**

```sql
-- 企业 A 的员工扩展字段
INSERT INTO tenant_employee_fields VALUES (
    'tenant_a', 'employee_id', 'STRING',
    PARSE_JSON('{
        "label": "工号",
        "placeholder": "请输入 6 位工号",
        "validation": {"pattern": "^[0-9]{6}$", "message": "工号格式不正确"},
        "searchable": true,
        "visible_in_list": true
    }'),
    1, true, current_timestamp()
);

INSERT INTO tenant_employee_fields VALUES (
    'tenant_a', 'department', 'SELECT',
    PARSE_JSON('{
        "label": "部门",
        "options": [
            {"value": "tech", "label": "技术部"},
            {"value": "sales", "label": "销售部"},
            {"value": "hr", "label": "人力资源部"}
        ],
        "multi_select": false,
        "default_value": "tech"
    }'),
    2, true, current_timestamp()
);

-- 企业 B 的员工扩展字段（完全不同）
INSERT INTO tenant_employee_fields VALUES (
    'tenant_b', 'cost_center', 'STRING',
    PARSE_JSON('{
        "label": "成本中心",
        "validation": {"required": true},
        "finance_visible": true
    }'),
    1, true, current_timestamp()
);
```

**效果：**
- 支持 5000+ 租户，每个租户独立配置
- 新增自定义字段无需修改数据库 Schema
- 配置变更实时生效，无需重启服务
- 配置版本管理，支持回滚

---

## JSON 查询最佳实践

### 1. 常用 JSON 操作

```sql
-- 访问嵌套字段
SELECT event_data['user']['profile']['name'] AS user_name
FROM user_events;

-- 访问数组元素
SELECT event_data['items'][0]['price'] AS first_item_price
FROM orders;

-- 类型转换
SELECT CAST(event_data['amount'] AS DOUBLE) AS amount
FROM transactions;

-- 条件过滤
SELECT * FROM products
WHERE CAST(attributes['ram_gb'] AS INT) >= 16;

-- JSON 聚合
SELECT 
    category_id,
    TO_JSON(COLLECT_LIST(STRUCT(product_id, product_name, base_price))) AS products_json
FROM products
GROUP BY category_id;
```

### 2. 性能优化

```sql
-- ✅ 推荐：在 WHERE 中使用 JSON 字段时，先过滤结构化字段
SELECT * FROM products
WHERE category_id = 20                    -- 先过滤分区/索引列
  AND CAST(attributes['ram_gb'] AS INT) > 8;  -- 再过滤 JSON 字段

-- ✅ 推荐：对频繁查询的 JSON 字段创建生成列
ALTER TABLE products 
ADD COLUMN ram_gb INT GENERATED ALWAYS AS (CAST(attributes['ram_gb'] AS INT));

CREATE INDEX idx_ram ON products(ram_gb);

-- ✅ 推荐：使用 LATERAL VIEW 展开 JSON 数组
SELECT product_id, color
FROM products
LATERAL VIEW EXPLODE(attributes['colors']) AS color
WHERE category_id = 10;
```

### 3. 数据验证

```sql
-- 在应用层验证 JSON Schema
-- 或在写入时使用 CHECK 约束（如果支持）

-- 查询 JSON 格式无效的记录
SELECT event_id
FROM user_events
WHERE TRY_CAST(event_data AS STRING) IS NULL
  AND event_data IS NOT NULL;
```

---

## 与 Snowflake VARIANT 对比

| 功能 | Snowflake | 云器 Lakehouse |
|------|-----------|----------------|
| 数据类型 | `VARIANT` | `JSON` |
| 访问语法 | `data:key` | `data['key']` |
| 类型转换 | `data:key::STRING` | `CAST(data['key'] AS STRING)` 或 `data['key']::STRING` |
| 对象构建 | `OBJECT_CONSTRUCT(k, v)` | `STRUCT(...)` + `TO_JSON` 或 `MAP_AGG(k, v)` |
| 数组展开 | `LATERAL FLATTEN()` | `LATERAL VIEW EXPLODE()` |
| 写入字符串 | ✅ 隐式转换 | ❌ 需 `PARSE_JSON()` 或 `CAST()` |

---

## 注意事项

### ⚠️ ClickZetta JSON 使用限制

1. **写入时必须显式转换**
   ```sql
   -- ❌ 错误：直接写入字符串
   INSERT INTO t VALUES ('{"key": "value"}');
   
   -- ✅ 正确：使用 PARSE_JSON 或 CAST
   INSERT INTO t VALUES (PARSE_JSON('{"key": "value"}'));
   INSERT INTO t VALUES (CAST('{"key": "value"}' AS JSON));
   ```

2. **访问语法使用方括号**
   ```sql
   -- ❌ 错误：Snowflake 冒号语法
   SELECT data:key FROM t;
   
   -- ✅ 正确：方括号语法
   SELECT data['key'] FROM t;
   ```

3. **不支持的 JSON 函数**
   - `JSON_EXTRACT_PATH_TEXT` → 使用 `data['key']` 访问
   - `JSON_ARRAY_LENGTH` → 使用 `SIZE(data['array'])`

### ✅ 推荐实践

1. **混合建模**：核心查询字段用结构化列，扩展字段用 JSON
2. **文档化**：维护 JSON Schema 文档，便于团队协作
3. **版本管理**：JSON 结构变更时，增加版本号字段
4. **索引策略**：对频繁查询的 JSON 字段创建生成列 + 索引

---

## 总结

云器 Lakehouse 的 JSON 能力为**大宽表现代化改造**提供了理想方案：

| 维度 | 传统宽表 | JSON 方案 |
|------|----------|-----------|
| Schema 灵活性 | 低（需 DDL） | 高（免 DDL） |
| 存储效率 | 低（大量 NULL） | 高（按需存储） |
| 查询性能 | 中（扫描列多） | 高（精准扫描） |
| 开发效率 | 低（DBA 依赖） | 高（自主迭代） |
| 维护成本 | 高 | 低 |

**适用场景：**
- ✅ 字段频繁变化的业务
- ✅ 多租户 SaaS 系统
- ✅ IoT/日志等半结构化数据
- ✅ 敏捷开发、快速迭代

**不适用场景：**
- ❌ 字段固定、极少变更
- ❌ 需要强 Schema 约束
- ❌ 频繁 JSON 字段 JOIN（建议提取为结构化列）

---

## 参考文档

- [DDL 参考](ddl-reference.md) - JSON 列定义
- [DQL 参考](dql-reference.md) - JSON 查询语法
- [DML 参考](dml-reference.md) - JSON 数据写入
- [Snowflake 迁移指南](migration-snowflake.md) - VARIANT 到 JSON
