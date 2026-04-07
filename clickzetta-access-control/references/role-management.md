# 角色管理参考

> 来源：https://www.yunqi.tech/documents/roles

## 角色类型

| 类型 | 说明 |
|---|---|
| **预置角色** | 平台自动配置，不可修改权限或删除，可直接授予用户 |
| **自定义角色** | 在工作空间范围内创建，权限可随时修改，仅支持 SQL 操作 |

## 角色级别

- **实例角色（Instance Role）**：用于实例级资源全局管控，或跨多工作空间授权
- **工作空间角色（Workspace Role）**：作用于特定工作空间，以工作空间为边界互不影响

## 系统预置角色

| 角色名 | 级别 | 说明 |
|---|---|---|
| `instance_admin` | 实例 | 实例管理员，最高权限 |
| `workspace_admin` | 工作空间 | 工作空间管理员 |
| `workspace_dev` | 工作空间 | 开发者，可创建和管理数据对象 |
| `workspace_analyst` | 工作空间 | 分析师，只读权限 |

详细权限列表参考：https://www.yunqi.tech/documents/permissions-of-built-in-workspace-level-roles

## CREATE ROLE（创建自定义角色）

```sql
-- 工作空间角色
CREATE ROLE [IF NOT EXISTS] role_name [COMMENT 'comment'];

-- 实例级角色（Instance Role，跨工作空间）
CREATE INSTANCE ROLE [IF NOT EXISTS] role_name [COMMENT 'comment'];
```

注意：自定义角色只能通过 SQL 创建，Web 端暂不支持。

## GRANT ROLE（将角色授予用户）

```sql
-- 将角色授予用户
GRANT ROLE role_name TO USER user_name;

-- 将角色授予另一个角色（角色继承）
GRANT ROLE role_name TO ROLE target_role_name;
```

## REVOKE ROLE（从用户撤销角色）

```sql
REVOKE ROLE role_name FROM USER user_name;
```

## SHOW ROLES（列出所有角色）

```sql
SHOW ROLES;
```

## DROP ROLE（删除自定义角色）

```sql
DROP ROLE [IF EXISTS] role_name;
```
