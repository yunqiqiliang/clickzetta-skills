---
name: clickzetta-data-sharing
description: |
  管理 ClickZetta Lakehouse 跨账户/跨实例数据分享（Share）。无需复制数据，
  实时共享表或视图给其他服务实例。覆盖提供方完整流程（CREATE SHARE →
  GRANT TO SHARE → ALTER SHARE ADD INSTANCE）和消费方流程
  （SHOW SHARES → DESC SHARE → CREATE SCHEMA FROM SHARE → 查询）。
  当用户说"数据分享"、"数据共享"、"Share"、"跨账户共享"、"跨实例共享"、
  "CREATE SHARE"、"GRANT TO SHARE"、"CREATE SCHEMA FROM SHARE"、
  "无复制共享"、"分享数据给其他公司"、"接收共享数据"、"INBOUND"、"OUTBOUND"时触发。
  Keywords: data sharing, SHARE, cross-account, cross-instance, provider, consumer
---

# ClickZetta 数据分享

数据分享（Share）实现跨账户/跨实例的**无复制、实时只读**数据共享。提供方授权数据，消费方直接查询，无需数据同步。

阅读 [references/share-ddl.md](references/share-ddl.md) 了解完整语法。

> ⚠️ 创建 Share 需要 `instance_admin` 角色。

---

## 提供方：分享数据（3步）

### 步骤 1：创建 Share 对象

```sql
CREATE SHARE my_share;
```

### 步骤 2：将表/视图加入 Share

```sql
-- 分享指定表
GRANT SELECT, READ METADATA ON TABLE public.orders TO SHARE my_share;

-- 分享视图（推荐：用视图控制分享字段和行范围）
GRANT SELECT, READ METADATA ON VIEW public.orders_public_view TO SHARE my_share;

-- 分享多张表
GRANT SELECT, READ METADATA ON TABLE public.orders, public.customers TO SHARE my_share;
```

### 步骤 3：指定接收方实例

```sql
-- 添加接收方（消费方提供其实例名称）
ALTER SHARE my_share ADD INSTANCE consumer_instance_id;
```

---

## 消费方：使用共享数据（3步）

### 步骤 1：查看收到的 Share

```sql
SHOW SHARES WHERE kind = 'INBOUND';
```

### 步骤 2：查看 Share 内容

```sql
-- 格式：DESC SHARE <提供方实例名>.<share名>
DESC SHARE provider_instance.my_share;
```

### 步骤 3：创建本地只读 Schema

```sql
-- 格式：CREATE SCHEMA <本地名> FROM SHARE SHARE <实例>.<share>.<schema>
CREATE SCHEMA shared_data FROM SHARE SHARE provider_instance.my_share.public;

-- 直接查询
SELECT * FROM shared_data.orders LIMIT 10;

-- 与本地表关联
SELECT o.*, c.region
FROM shared_data.orders o
JOIN my_schema.dim_customer c ON o.customer_id = c.id;
```

---

## 管理操作

```sql
-- 查看所有 Share（含 INBOUND/OUTBOUND）
SHOW SHARES;

-- 只看分享出去的
SHOW SHARES WHERE kind = 'OUTBOUND';

-- 查看 Share 包含的对象
DESC SHARE my_share;

-- 撤销某张表的分享
REVOKE SELECT, READ METADATA ON TABLE public.orders FROM SHARE my_share;

-- 移除接收方（立即生效）
ALTER SHARE my_share REMOVE INSTANCE consumer_instance_id;

-- 删除 Share
DROP SHARE IF EXISTS my_share;
```

---

## 典型场景

### 场景：A 公司向 B 公司分享数据

**A 公司（提供方）操作：**

```sql
-- 1. 创建 Share
CREATE SHARE partner_share;

-- 2. 创建视图控制分享范围（只分享脱敏后的数据）
CREATE VIEW public.orders_for_partner AS
SELECT order_id, product_id, amount, order_date
FROM public.orders
WHERE status = 'completed';

-- 3. 将视图加入 Share
GRANT SELECT, READ METADATA ON VIEW public.orders_for_partner TO SHARE partner_share;

-- 4. 指定 B 公司实例（B 公司提供其实例名）
ALTER SHARE partner_share ADD INSTANCE b_company_instance;
```

**B 公司（消费方）操作：**

```sql
-- 1. 查看收到的 Share
SHOW SHARES WHERE kind = 'INBOUND';

-- 2. 查看内容
DESC SHARE a_company_instance.partner_share;

-- 3. 创建本地 Schema
CREATE SCHEMA a_company_data FROM SHARE SHARE a_company_instance.partner_share.public;

-- 4. 查询使用
SELECT * FROM a_company_data.orders_for_partner
WHERE order_date >= '2024-01-01';
```

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| CREATE SHARE 报权限不足 | 需要 instance_admin 角色 | 联系管理员授予 instance_admin |
| 消费方看不到 Share | 提供方未 ADD INSTANCE | 提供方执行 `ALTER SHARE ADD INSTANCE` |
| DESC SHARE 报错 | instance_name 填错 | 通过 `SHOW SHARES` 确认 provider_instance 字段 |
| 共享 Schema 下查不到表 | GRANT 时未包含该表 | 提供方重新 `GRANT ... TO SHARE` |
| 想只分享部分列/行 | 直接分享表会暴露全量数据 | 创建 VIEW 过滤后再分享 VIEW |
