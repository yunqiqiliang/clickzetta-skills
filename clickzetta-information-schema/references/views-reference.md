# 空间级 INFORMATION_SCHEMA 视图字段说明

> 来源：https://www.yunqi.tech/documents/worksapce-informaiton_schema-views

访问路径：`information_schema.<视图名>`
权限要求：workspace_admin

---

## SCHEMAS 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| CATALOG_NAME | STRING | 当前 WORKSPACE 的名称 |
| SCHEMA_NAME | STRING | Schema 名称 |
| SCHEMA_CREATOR | STRING | Schema 所有者账号名称 |
| TYPE | STRING | EXTERNAL（外部）/ INTERNAL（内部） |
| COMMENT | STRING | 创建时的注释 |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| LAST_MODIFY_TIME | TIMESTAMP | 修改时间 |
| PROPERTIES | MAP | 创建时指定的 PROPERTIES |

---

## TABLES 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| TABLE_CATALOG | STRING | 当前 WORKSPACE 名称 |
| TABLE_SCHEMA | STRING | 所属 Schema |
| TABLE_NAME | STRING | 表名 |
| TABLE_TYPE | STRING | EXTERNAL / VIEW / MATERIALIZED VIEW / BASE TABLE / SNAPSHOT |
| ROW_COUNT | BIGINT | 行数（VIEW 为 NULL，估计值） |
| BYTES | BIGINT | 存储大小字节（VIEW 为 NULL，估计值） |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| LAST_MODIFY_TIME | TIMESTAMP | 修改时间 |
| TABLE_CREATOR | STRING | 表所有者账号名称 |
| IS_PARTITIONED | BOOLEAN | 是否分区表（VIEW 为 NULL） |
| IS_CLUSTERED | BOOLEAN | 是否分桶表（VIEW 为 NULL） |
| COMMENT | STRING | 表注释 |
| DATA_LIFECYCLE | BIGINT | 生命周期（天），NULL 表示永久 |
| PROPERTIES | MAP | 创建时指定的 PROPERTIES |

---

## COLUMNS 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| TABLE_CATALOG | STRING | 当前 WORKSPACE 名称 |
| TABLE_SCHEMA | STRING | 所属 Schema |
| TABLE_NAME | STRING | 表名 |
| COLUMN_NAME | STRING | 字段名 |
| COLUMN_DEFAULT | STRING | 字段默认值 |
| IS_NULLABLE | BOOLEAN | 是否可为 NULL |
| DATA_TYPE | STRING | 字段类型 |
| CREATE_TIME | TIMESTAMP_LTZ | 表创建时间 |
| IS_CLUSTERING_COLUMN | BOOLEAN | 是否 CLUSTER 字段 |
| IS_PRIMARY_KEY | BOOLEAN | 是否主键 |
| COMMENT | STRING | 字段注释 |

---

## VIEWS 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| TABLE_CATALOG | STRING | 当前 WORKSPACE 名称 |
| TABLE_SCHEMA | STRING | 所属 Schema |
| TABLE_NAME | STRING | 视图名 |
| TABLE_CREATOR | STRING | 视图所有者账号名称 |
| VIEW_DEFINITION | STRING | 创建视图的 SQL 语句 |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| LAST_MODIFY_TIME | TIMESTAMP | 修改时间 |
| COMMENT | STRING | 视图注释 |

---

## USERS 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_NAME | STRING | 空间名称 |
| USER_NAME | STRING | 用户名称 |
| ROLE_NAME | STRING | 拥有的角色（多个用逗号分隔） |
| CREATE_TIME | TIMESTAMP | 用户加入时间 |
| EMAIL | STRING | 用户邮箱 |
| TELEPHONE | STRING | 用户电话 |
| COMMENT | STRING | 描述信息 |
| PROPERTIES | MAP | 保留字段 |

---

## ROLES 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_NAME | STRING | 空间名称 |
| ROLE_NAME | STRING | 角色名称 |
| USER_NAMES | STRING | 被授予该角色的用户（逗号分隔） |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| COMMENT | STRING | 描述信息 |
| PROPERTIES | MAP | 保留字段 |

---

## JOB_HISTORY 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_NAME | STRING | 作业所在空间 |
| JOB_ID | STRING | 作业 ID |
| JOB_NAME | STRING | 作业名称 |
| JOB_CREATOR | STRING | 执行用户 |
| STATUS | STRING | SCHEDULE / PROCESS / SUCCEEDED / FAILED / CANCELLED |
| CRU | DECIMAL | 消耗的计算资源 |
| ERROR_MESSAGE | STRING | 错误信息（失败时有值） |
| JOB_TYPE | STRING | 作业类型：COPY / SQL / DATALAKE |
| JOB_TEXT | STRING | 执行的 SQL 语句 |
| QUERY_TAG | STRING | 用户设置的 TAG |
| START_TIME | TIMESTAMP | 开始时间 |
| END_TIME | TIMESTAMP | 结束时间 |
| EXECUTION_TIME | DOUBLE | 执行时间（秒，精确到毫秒） |
| INPUT_BYTES | BIGINT | 实际扫描数据量 |
| OUTPUT_BYTES | BIGINT | 输出字节数 |
| INPUT_OBJECTS | STRING | 输入表名 |
| OUTPUT_OBJECTS | STRING | 输出表名 |
| CLIENT_INFO | STRING | 客户端信息（JDBC/SDK/Web） |
| VIRTUAL_CLUSTER | STRING | 使用的计算集群 |
| ROW_PRODUCED | BIGINT | 处理的总记录数 |
| ROW_INSERTED | BIGINT | 插入行数 |
| ROW_UPDATED | BIGINT | 更新行数 |
| ROW_DELETED | BIGINT | 删除行数 |
| JOB_CONFIG | STRING | 提交时的参数信息 |
| CACHE_HIT | BIGINT | 从缓存读取的数据量 |
| JOB_PRIORITY | STRING | 作业优先级 |
| INPUT_TABLES | STRING | 输入表名 |
| OUTPUT_TABLES | STRING | 输出表名 |

---

## MATERIALIZED_VIEW_REFRESH_HISTORY 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_NAME | STRING | 空间名称 |
| SCHEMA_NAME | STRING | Schema 名称 |
| MATERIALIZED_VIEW_NAME | STRING | 物化视图名称 |
| CRU | DECIMAL | 刷新消耗的计费 |
| VIRTUAL_CLUSTER_NAME | STRING | 使用的虚拟集群（自动刷新时有值） |
| STATUS | STRING | PENDING / RUNNING / FINISHED / FAILED |
| SCHEDULED_START_TIME | TIMESTAMP_LTZ | 计划刷新时间 |
| START_TIME | TIMESTAMP_LTZ | 实际开始时间 |
| END_TIME | TIMESTAMP_LTZ | 结束时间 |
| ERROR_CODE | STRING | 错误码 |
| ERROR_MESSAGE | STRING | 刷新失败信息 |

---

## AUTOMV_REFRESH_HISTORY 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_NAME | STRING | 空间名称 |
| SCHEMA_NAME | STRING | Schema 名称 |
| MATERIALIZED_VIEW_NAME | STRING | 物化视图名称 |
| CRU | DECIMAL | 刷新消耗的计费 |
| STATUS | STRING | PROCESSING / SUCCEEDED / FAILED / CANCELLED |
| MV_PROCESS_TYPE | STRING | BUILD（构建）/ REFRESH（刷新） |
| START_TIME | TIMESTAMP_LTZ | 开始时间 |
| END_TIME | TIMESTAMP_LTZ | 结束时间 |
| BUILD_FROM_WORKSPACE | STRING | 构建 MV 对应的源表空间 |
| JOB_ID | STRING | 构建 MV 的作业 ID |
| ERROR_MESSAGE | STRING | 刷新失败信息 |

---

## VOLUMES 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| VOLUME_CATALOG | STRING | 所属 Workspace 名称 |
| VOLUME_SCHEMA | STRING | 所属 Schema 名称 |
| VOLUME_NAME | STRING | Volume 名称 |
| VOLUME_URL | STRING | Volume 绑定的 URL |
| VOLUME_REGION | STRING | Volume 所属区域 |
| VOLUME_TYPE | STRING | INTERNAL / EXTERNAL |
| VOLUME_CREATOR | STRING | Volume 的 owner |
| CONNECTION_NAME | STRING | 引用的 Connection 名称 |
| COMMENT | STRING | 注释 |
| PROPERTIES | MAP\<STRING,STRING> | 保留字段 |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| LAST_MODIFY_TIME | TIMESTAMP | 修改时间 |

---

## CONNECTIONS 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_NAME | STRING | 所在空间 |
| CONNECTION_NAME | STRING | 连接对象名称 |
| CONNECTION_KIND | STRING | STORAGE CONNECTION / API CONNECTION |
| TYPE | STRING | FILE_SYSTEM（存储）/ CLOUD_FUNCTION（云函数） |
| PROVIDER | STRING | FILE_SYSTEM 时：OSS / COS；CLOUD_FUNCTION 时：aliyun / tencent |
| REGION | STRING | 连接的 region（如 ap-shanghai / cn-beijing） |
| SOURCE_CREATOR | STRING | 创建者 |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| LAST_MODIFY_TIME | TIMESTAMP | 修改时间 |
| COMMENT | STRING | 注释 |
| PROPERTIES | MAP\<STRING,STRING> | 保留字段 |

---

## 授权管理

```sql
-- 授予用户查询 information_schema 的权限
GRANT ALL ON ALL VIEWS IN SCHEMA information_schema TO ROLE <role_name>;
GRANT ALL ON ALL VIEWS IN SCHEMA information_schema TO USER <user_name>;
```
