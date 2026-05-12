# 用户管理参考

> 来源：https://www.yunqi.tech/documents/CREAREUSER、ALTER USER、DROP USER、SHOW USERS

## CREATE USER（将用户添加到工作空间）

> ⚠️ `CREATE USER` 不是创建新账户，而是将已在账户管理系统中存在的用户添加到当前工作空间。
> 用户必须先在管理中心创建账户，才能执行此命令。

```sql
CREATE USER [IF NOT EXISTS] user_name
[DEFAULT_VCLUSTER = vc_name]
[DEFAULT_SCHEMA = schema_name]
[COMMENT "comment"];
```

参数说明：
- `user_name`：必须是已在账户管理系统中创建的用户名
- `DEFAULT_VCLUSTER`：用户默认计算集群，未指定则使用全局默认
- `DEFAULT_SCHEMA`：用户默认 Schema，未指定则登录时需手动指定

示例：
```sql
-- 基础添加
CREATE USER alice;

-- 指定默认集群和 Schema
CREATE USER alice DEFAULT_VCLUSTER = default_ap DEFAULT_SCHEMA = public;

-- 带注释
CREATE USER alice COMMENT "数据分析师";
```

## ALTER USER（修改用户属性）

```sql
ALTER USER user_name SET
[DEFAULT_VCLUSTER = vc_name]
[DEFAULT_SCHEMA = schema_name];
```

示例：
```sql
ALTER USER alice SET DEFAULT_VCLUSTER = default_ap DEFAULT_SCHEMA = dw;
```

## DROP USER（从工作空间移除用户）

```sql
DROP USER [IF EXISTS] user_name;
```

注意：移除后用户无法访问该工作空间的任何资源。

## SHOW USERS（列出所有用户）

```sql
SHOW USERS;
```

返回当前工作空间下所有用户的用户名和权限等级。
