# 数据分享 DDL 参考

> 来源：https://www.yunqi.tech/documents/datasharing 等

## 概念

数据分享（Share）是 Lakehouse 提供的**无复制**跨账户/跨实例数据共享功能：
- 数据提供方创建 Share 对象，将表或视图授权给指定服务实例
- 数据消费方通过 `CREATE SCHEMA FROM SHARE` 在本地创建只读 Schema 访问共享数据
- 数据实时更新，消费方无需同步，无需为存储付费

**限制：**
- 共享数据为**只读**，消费方不可修改
- 一个 Share 只能包含同一工作空间下的数据
- 一个 Share 最多包含 1000 个 table/view
- 不支持二次分享
- 需要 `instance_admin` 角色才能创建 Share

---

## 提供方操作（OUTBOUND）

### 1. 创建 Share

```sql
CREATE SHARE share_demo;
```

### 2. 将表/视图加入 Share

```sql
-- 添加单张表
GRANT SELECT, READ METADATA ON TABLE public.orders TO SHARE share_demo;

-- 添加视图（推荐：用视图控制分享范围）
GRANT SELECT, READ METADATA ON VIEW public.orders_summary TO SHARE share_demo;

-- 添加多张表
GRANT SELECT, READ METADATA ON TABLE public.orders, public.customers TO SHARE share_demo;

-- 添加 Schema 下所有表（含未来新建的表，谨慎使用）
GRANT SELECT, READ METADATA ON ALL TABLES IN SCHEMA public TO SHARE share_demo;
```

### 3. 指定接收实例

```sql
-- 添加接收方实例
ALTER SHARE share_demo ADD INSTANCE consumer_instance_name;

-- 移除接收方实例（立即撤销访问权限）
ALTER SHARE share_demo REMOVE INSTANCE consumer_instance_name;
```

### 4. 从 Share 移除数据对象

```sql
-- 撤销表的分享权限
REVOKE SELECT, READ METADATA ON TABLE public.orders FROM SHARE share_demo;

-- 撤销视图的分享权限
REVOKE SELECT ON VIEW public.orders_summary FROM SHARE share_demo;
```

### 5. 查看与管理

```sql
-- 查看所有 Share
SHOW SHARES;

-- 查看本实例分享出去的 Share
SHOW SHARES WHERE kind = 'OUTBOUND';

-- 查看 Share 包含的数据对象
DESC SHARE share_demo;

-- 删除 Share
DROP SHARE IF EXISTS share_demo;
```

---

## 消费方操作（INBOUND）

### 1. 查看收到的 Share

```sql
-- 查看所有 Share（含 INBOUND）
SHOW SHARES;

-- 只看收到的 Share
SHOW SHARES WHERE kind = 'INBOUND';
```

### 2. 查看 Share 内容

```sql
-- 格式：DESC SHARE <provider_instance>.<share_name>
DESC SHARE provider_instance.share_demo;
```

返回字段：`kind`（schema/table/view）、`name`（对象名）、`shared_on`（共享时间）

### 3. 创建本地只读 Schema（消费数据）

```sql
-- 格式：CREATE SCHEMA <local_schema> FROM SHARE SHARE <instance>.<share>.<schema>
CREATE SCHEMA data_from_provider FROM SHARE SHARE provider_instance.share_demo.public;
```

创建后即可直接查询：

```sql
SELECT * FROM data_from_provider.orders LIMIT 10;

-- 与本地表关联查询
SELECT o.*, c.name
FROM data_from_provider.orders o
JOIN my_schema.customers c ON o.customer_id = c.id;
```

---

## SHOW SHARES 返回字段说明

| 字段 | 说明 |
|---|---|
| share_name | Share 名称 |
| provider | 提供方租户名 |
| provider_instance | 提供方服务实例名 |
| provider_workspace | Share 所属工作空间 |
| scope | 分享范围（当前仅 PRIVATE） |
| to_instance | 接收方实例名（逗号分隔） |
| kind | OUTBOUND（分享出）/ INBOUND（收到） |
