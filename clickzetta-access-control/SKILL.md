---
name: clickzetta-access-control
description: |
  管理 ClickZetta Lakehouse 的用户、角色和权限（RBAC），以及列级动态数据脱敏。
  覆盖用户创建/修改/删除、自定义角色管理、GRANT/REVOKE 细粒度授权、
  SHOW GRANTS 权限查看、动态脱敏策略创建与绑定等完整安全治理工作流。
  当用户说"创建用户"、"添加用户"、"授权"、"GRANT"、"REVOKE"、"撤销权限"、
  "创建角色"、"角色管理"、"RBAC"、"权限管理"、"查看权限"、"数据脱敏"、
  "动态脱敏"、"列级安全"、"敏感数据保护"、"用户权限"、"网络策略"、
  "IP 白名单"、"IP 黑名单"、"NETWORK POLICY"时触发。
---

# ClickZetta 访问控制与数据安全

## 权限体系概览

```
账户（Account）
└── 服务实例（Instance）
    ├── 实例角色（instance_admin 等）
    └── 工作空间（Workspace）
        ├── 工作空间角色（workspace_admin / workspace_dev / workspace_analyst）
        ├── 自定义角色（CREATE ROLE）
        └── 用户（User）
```

**推荐做法**：优先使用角色（RBAC）管理权限，而非直接对用户逐个授权（ACL）。

## ⚠️ 关键注意事项

- `CREATE USER` **不是创建新账户**，而是将已有账户用户添加到当前工作空间。用户必须先在管理中心（账户管理系统）中创建，才能执行 `CREATE USER`
- 自定义角色只能通过 SQL 创建，Web 端暂不支持
- 动态脱敏功能当前处于受邀预览阶段，需联系技术支持开通

---

阅读 [references/user-management.md](references/user-management.md)

```sql
-- 将已有账户用户添加到工作空间
CREATE USER alice DEFAULT_VCLUSTER = default_ap DEFAULT_SCHEMA = public;

-- 修改用户默认集群/Schema
ALTER USER alice SET DEFAULT_VCLUSTER = default_ap DEFAULT_SCHEMA = dw;

-- 查看所有用户
SHOW USERS;

-- 从工作空间移除用户
DROP USER IF EXISTS alice;
```

---

## 步骤 2：角色管理

阅读 [references/role-management.md](references/role-management.md)

```sql
-- 查看所有角色（含预置角色）
SHOW ROLES;

-- 创建自定义角色
CREATE ROLE analyst_role COMMENT '数据分析师角色';

-- 将角色授予用户
GRANT ROLE analyst_role TO USER alice;

-- 从用户撤销角色
REVOKE ROLE analyst_role FROM USER alice;

-- 删除自定义角色
DROP ROLE IF EXISTS analyst_role;
```

系统预置角色：`instance_admin`、`workspace_admin`、`workspace_dev`、`workspace_analyst`

---

## 步骤 3：权限授予与撤销

阅读 [references/grant-revoke.md](references/grant-revoke.md)

### 常用授权场景

```sql
-- 授予表查询权限
GRANT SELECT ON TABLE public.orders TO USER alice;
GRANT SELECT ON TABLE public.orders TO ROLE analyst_role;

-- 授予 Schema 下所有权限
GRANT ALL ON SCHEMA public TO ROLE dev_role;

-- 授予使用计算集群权限
GRANT USE ON VCLUSTER default_ap TO USER alice;

-- 授予创建表权限
GRANT CREATE TABLE ON SCHEMA public TO USER alice;
```

### 撤销权限

```sql
REVOKE SELECT ON TABLE public.orders FROM USER alice;
REVOKE ALL PRIVILEGES ON WORKSPACE ws_name FROM USER alice;
```

### 查看权限

```sql
-- 查看当前用户权限
SHOW GRANTS;

-- 查看指定用户权限
SHOW GRANTS TO USER alice;

-- 查看工作空间角色权限
SHOW GRANTS TO ROLE analyst_role;

-- 查看实例级角色权限
SHOW GRANTS TO INSTANCE ROLE instance_admin;
```

---

## 步骤 4：动态数据脱敏（预览功能）

阅读 [references/dynamic-masking.md](references/dynamic-masking.md)

> ⚠️ 当前处于受邀预览阶段，需联系技术支持开通。

```sql
-- 1. 创建脱敏函数（管理员看原文，其他人看脱敏）
CREATE FUNCTION public.mask_phone(phone STRING)
RETURNS STRING
AS CASE
    WHEN current_user() = 'admin' THEN phone
    ELSE CONCAT(SUBSTR(phone, 1, 3), '****', SUBSTR(phone, 8, 4))
END;

-- 2. 绑定到列
ALTER TABLE customers
CHANGE COLUMN phone
SET MASK public.mask_phone;

-- 3. 解除脱敏
ALTER TABLE customers
CHANGE COLUMN phone
UNSET MASK;
```

---

## 典型场景

### 场景 A：新员工入职授权

```sql
-- 1. 添加用户到工作空间
CREATE USER new_employee DEFAULT_VCLUSTER = default_ap;

-- 2. 授予分析师角色
GRANT ROLE workspace_analyst TO USER new_employee;

-- 3. 额外授予特定表的写入权限
GRANT INSERT ON TABLE public.reports TO USER new_employee;
```

### 场景 B：创建只读角色并批量授权

```sql
-- 1. 创建只读角色
CREATE ROLE readonly_role COMMENT '只读访问角色';

-- 2. 授予 Schema 下所有表的查询权限
GRANT SELECT ON TABLE public.orders TO ROLE readonly_role;
GRANT SELECT ON TABLE public.customers TO ROLE readonly_role;
GRANT USE ON VCLUSTER default_ap TO ROLE readonly_role;

-- 3. 将角色授予多个用户
GRANT ROLE readonly_role TO USER alice;
GRANT ROLE readonly_role TO USER bob;
```

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| CREATE USER 报错用户不存在 | 用户未在账户管理系统中创建 | 先在管理中心创建账户用户，再执行 CREATE USER |
| GRANT 后用户仍无法查询 | 缺少 USE VCLUSTER 权限 | `GRANT USE ON VCLUSTER default_ap TO USER alice` |
| 自定义角色无法在 Web 端创建 | 产品限制 | 只能通过 SQL 创建自定义角色 |
| 脱敏函数不生效 | 功能未开通 | 联系技术支持开通动态脱敏预览功能 |

---

## 步骤 5：网络策略（IP 白名单/黑名单）

通过网络策略控制对 Lakehouse 服务实例的 JDBC、SDK 及 Web 访问，支持白名单和黑名单模式。

```sql
-- 创建网络策略（白名单模式：仅允许指定 IP 访问）
CREATE NETWORK POLICY office_only
  ALLOWED_IP_LIST = ('10.0.0.0/8', '172.16.0.0/12')
  COMMENT '仅允许办公网络访问';

-- 创建网络策略（黑名单模式：阻止指定 IP）
CREATE NETWORK POLICY block_external
  BLOCKED_IP_LIST = ('203.0.113.0/24')
  COMMENT '阻止外部 IP';

-- 同时设置白名单和黑名单（Deny 优先）
CREATE NETWORK POLICY mixed_policy
  ALLOWED_IP_LIST = ('10.0.0.0/8')
  BLOCKED_IP_LIST = ('10.0.1.100/32')
  COMMENT '允许内网但阻止特定 IP';

-- 查看网络策略
SHOW NETWORK POLICIES;

-- 删除网络策略
DROP NETWORK POLICY IF EXISTS office_only;
```

> ⚠️ 网络策略遵循 **Deny 优先** 原则：同时出现在白名单和黑名单中的 IP 会被拒绝。

---

## 参考文档

- [访问控制概览](https://www.yunqi.tech/documents/access-control-general)
- [角色](https://www.yunqi.tech/documents/roles)
- [GRANT](https://www.yunqi.tech/documents/grant-user-privileges)
- [REVOKE](https://www.yunqi.tech/documents/revoke-user-privileges)
- [CREATE USER](https://www.yunqi.tech/documents/CREAREUSER)
- [ALTER USER](https://www.yunqi.tech/documents/alter-user)
- [DROP USER](https://www.yunqi.tech/documents/DROPUSER)
- [SHOW USERS](https://www.yunqi.tech/documents/SHOWUSERS)
- [动态脱敏](https://www.yunqi.tech/documents/dynamic-mask)
- [系统内置角色权限列表](https://www.yunqi.tech/documents/permissions-of-built-in-workspace-level-roles)
- [网络策略](https://www.yunqi.tech/documents/network_policy)
