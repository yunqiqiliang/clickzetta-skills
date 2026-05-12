# GRANT / REVOKE 权限管理参考

> 来源：https://www.yunqi.tech/documents/grant-user-privileges 和 revoke-user-privileges

## GRANT 语法

### 授权给用户

```sql
GRANT privilege_type ON object_type object_name TO USER user_name [WITH GRANT OPTION];
```

### 授权给角色

```sql
GRANT privilege_type ON object_type object_name TO ROLE role_name;
```

## 权限类型速查

### 工作空间级（ON WORKSPACE）

```sql
-- 创建对象权限
GRANT CREATE SCHEMA ON WORKSPACE ws_name TO USER alice;
GRANT CREATE VCLUSTER ON WORKSPACE ws_name TO USER alice;
```

### 工作空间对象级（ON SCHEMA / VCLUSTER / ROLE / FUNCTION）

```sql
-- Schema 权限
GRANT ALTER ON SCHEMA public TO USER alice;
GRANT DROP ON SCHEMA public TO USER alice;
GRANT READ METADATA ON SCHEMA public TO USER alice;
GRANT ALL PRIVILEGES ON SCHEMA public TO USER alice;

-- VCluster 权限
GRANT USE ON VCLUSTER default_ap TO USER alice;
GRANT ALTER ON VCLUSTER default_ap TO USER alice;
```

### Schema 级（ON SCHEMA，创建对象）

```sql
GRANT CREATE TABLE ON SCHEMA public TO USER alice;
GRANT CREATE VIEW ON SCHEMA public TO USER alice;
GRANT CREATE MATERIALIZED VIEW ON SCHEMA public TO USER alice;
GRANT ALL ON SCHEMA public TO USER alice;
```

### 表/视图级（ON TABLE / VIEW / MATERIALIZED VIEW）

```sql
-- 表权限
GRANT SELECT ON TABLE public.orders TO USER alice;
GRANT INSERT ON TABLE public.orders TO USER alice;
GRANT ALTER ON TABLE public.orders TO USER alice;
GRANT DROP ON TABLE public.orders TO USER alice;
GRANT ALL ON TABLE public.orders TO USER alice;

-- 授权给角色
GRANT SELECT ON TABLE public.orders TO ROLE analyst_role;
```

## REVOKE 语法

```sql
REVOKE privilege_type ON object_type object_name FROM USER user_name;
REVOKE privilege_type ON object_type object_name FROM ROLE role_name;
```

## REVOKE 示例

```sql
-- 撤销创建 VCluster 权限
REVOKE CREATE VCLUSTER ON WORKSPACE ws_name FROM USER alice;

-- 撤销表查询权限
REVOKE SELECT ON TABLE public.orders FROM USER alice;

-- 撤销 Schema 下所有权限
REVOKE ALL PRIVILEGES ON WORKSPACE ws_name FROM USER alice;

-- 从角色撤销权限
REVOKE CREATE VIEW ON SCHEMA sales FROM ROLE reporting_role;
```

## SHOW GRANTS（查看权限）

```sql
-- 查看当前用户的权限
SHOW GRANTS;

-- 查看指定用户的权限
SHOW GRANTS TO USER user_name;

-- 查看工作空间角色的权限
SHOW GRANTS TO ROLE role_name;

-- 查看实例角色的权限
SHOW GRANTS TO INSTANCE ROLE role_name;
```
