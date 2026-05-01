# 实例级 INFORMATION_SCHEMA 视图字段说明

> 来源：https://www.yunqi.tech/documents/instance-informaiton-schema

访问路径：`SYS.information_schema.<视图名>`
权限要求：INSTANCE ADMIN

实例级视图覆盖所有工作空间，包含已删除对象（`DELETE_TIME IS NULL` 过滤现存对象）。

---

## WORKSPACES 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_ID | STRING | 工作空间 ID |
| WORKSPACE_NAME | STRING | 工作空间名称 |
| WORKSPACE_CREATOR | STRING | 工作空间所有者 |
| WORKSPACE_CREATOR_ID | STRING | 所有者账号 ID |
| WORKSPACE_STORAGE | BIGINT | 存储用量（字节，不含外部表和外部数据湖） |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| LAST_MODIFY_TIME | TIMESTAMP | 修改时间 |
| COMMENT | STRING | 注释 |
| DELETE_TIME | TIMESTAMP | 删除时间（NULL 表示未删除） |
| PROPERTIES | MAP\<STRING,STRING> | 自定义属性 |

---

## SCHEMAS 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| CATALOG_NAME | STRING | 所属 WORKSPACE 名称 |
| SCHEMA_ID | STRING | Schema ID |
| SCHEMA_NAME | STRING | Schema 名称 |
| TYPE | STRING | EXTERNAL / MANAGED |
| SCHEMA_CREATOR | STRING | 所有者账号名称 |
| SCHEMA_CREATOR_ID | STRING | 所有者账号 ID |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| LAST_MODIFY_TIME | TIMESTAMP | 修改时间 |
| COMMENT | STRING | 注释 |
| DELETE_TIME | TIMESTAMP | 删除时间（NULL 表示未删除） |
| PROPERTIES | MAP\<STRING,STRING> | 自定义属性 |

---

## TABLES 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| TABLE_CATALOG | STRING | 所属 WORKSPACE 名称 |
| TABLE_CATALOG_ID | STRING | WORKSPACE ID |
| TABLE_SCHEMA | STRING | 所属 Schema |
| TABLE_SCHEMA_ID | STRING | Schema ID |
| TABLE_NAME | STRING | 表名 |
| TABLE_ID | STRING | 表 ID |
| TABLE_CREATOR | STRING | 表所有者 |
| TABLE_CREATOR_ID | STRING | 表创建者 ID |
| TABLE_TYPE | STRING | EXTERNAL TABLE / VIRTUAL_VIEW / MATERIALIZED VIEW / MANAGED_TABLE |
| ROW_COUNT | BIGINT | 行数（估计值） |
| BYTES | BIGINT | 存储大小（估计值） |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| LAST_MODIFY_TIME | TIMESTAMP | 修改时间 |
| DATA_LIFECYCLE | BIGINT | 生命周期（天），NULL 表示永久 |
| IS_PARTITIONED | BOOLEAN | 是否分区表 |
| IS_CLUSTERED | BOOLEAN | 是否分桶表 |
| COMMENT | STRING | 表注释 |
| DELETE_TIME | TIMESTAMP | 删除时间（NULL 表示未删除） |
| PROPERTIES | MAP\<STRING,STRING> | 自定义属性 |

---

## COLUMNS 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| TABLE_CATALOG | STRING | 所属 WORKSPACE 名称 |
| TABLE_CATALOG_ID | STRING | WORKSPACE ID |
| TABLE_SCHEMA | STRING | 所属 Schema |
| TABLE_SCHEMA_ID | STRING | Schema ID |
| TABLE_NAME | STRING | 表名 |
| TABLE_ID | STRING | 表 ID |
| COLUMN_NAME | STRING | 字段名 |
| COLUMN_ID | STRING | 字段 ID |
| COLUMN_DEFAULT | STRING | 字段默认值（保留值） |
| IS_NULLABLE | BOOLEAN | 是否可为 NULL |
| DATA_TYPE | STRING | 字段类型 |
| IS_PARTITIONING_COLUMN | BOOLEAN | 是否分区字段 |
| IS_CLUSTERING_COLUMN | BOOLEAN | 是否 CLUSTER 字段 |
| IS_PRIMARY_KEY | BOOLEAN | 是否主键 |
| COMMENT | STRING | 字段注释 |
| DELETE_TIME | TIMESTAMP | 删除时间（NULL 表示未删除） |

---

## VIEWS 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| TABLE_CATALOG | STRING | 所属 WORKSPACE 名称 |
| TABLE_CATALOG_ID | STRING | WORKSPACE ID |
| TABLE_SCHEMA | STRING | 所属 Schema |
| TABLE_SCHEMA_ID | STRING | Schema ID |
| TABLE_NAME | STRING | 视图名 |
| TABLE_ID | STRING | 视图 ID |
| TABLE_CREATOR | STRING | 视图所有者账号名称 |
| TABLE_CREATOR_ID | STRING | 视图所有者账号 ID |
| VIEW_DEFINITION | STRING | 创建视图的 SQL 语句 |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| LAST_MODIFY_TIME | TIMESTAMP | 修改时间 |
| COMMENT | STRING | 视图注释 |
| DELETE_TIME | TIMESTAMP | 删除时间（NULL 表示未删除） |

---

## USERS 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_NAME | STRING | 所在工作空间 |
| WORKSPACE_ID | STRING | 空间 ID |
| USER_ID | STRING | 系统生成的用户 ID |
| USER_NAME | STRING | 用户名（WORKSPACE_NAME + USER_NAME 拼接） |
| ROLE_NAME | STRING | 拥有的角色（逗号分隔） |
| ADD_TIME | TIMESTAMP | 用户创建时间 |
| EMAIL | STRING | 用户邮箱 |
| TELEPHONE | STRING | 用户电话 |
| LAST_SUCCESS_LOGIN | TIMESTAMP | 上次登录时间 |
| COMMENT | STRING | 描述信息 |
| DELETE_TIME | TIMESTAMP | 删除时间（NULL 表示未删除） |
| PROPERTIES | MAP\<STRING,STRING> | 自定义属性 |

---

## ROLES 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_NAME | STRING | 所在工作空间 |
| WORKSPACE_ID | STRING | 空间 ID |
| ROLE_NAME | STRING | 角色名称 |
| ROLE_ID | STRING | 角色 ID |
| USER_NAME | STRING | 被授予该角色的用户（逗号分隔） |
| USER_ID | STRING | 被授予该角色的用户 ID |
| COMMENT | STRING | 描述信息 |
| DELETE_TIME | TIMESTAMP | 删除时间（NULL 表示未删除） |

---

## JOB_HISTORY 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_NAME | STRING | 作业所在空间 |
| WORKSPACE_ID | STRING | 空间 ID |
| JOB_ID | STRING | 作业 ID |
| JOB_NAME | STRING | 作业名称 |
| JOB_CREATOR_ID | STRING | 执行用户 ID |
| JOB_CREATOR | STRING | 执行用户 |
| STATUS | STRING | SETUP / RESUMING_CLUSTER / QUEUED / RUNNING / SUCCESS / FAILED / CANCELED |
| CRU | DECIMAL(38,5) | 消耗的计算资源 |
| ERROR_MESSAGE | STRING | 错误信息 |
| JOB_TYPE | STRING | 作业类型：SQL |
| JOB_TEXT | STRING | 执行的 SQL 语句 |
| START_TIME | TIMESTAMP | 开始时间 |
| END_TIME | TIMESTAMP | 结束时间 |
| EXECUTION_TIME | DOUBLE | 执行时间（秒） |
| INPUT_BYTES | BIGINT | 实际扫描数据量 |
| CACHE_HIT | BIGINT | 从缓存读取的数据量 |
| OUTPUT_BYTES | BIGINT | 输出字节数 |
| INPUT_OBJECTS | STRING | 输入表名（格式：[SCHEMA].[TABLE]，多个逗号分隔） |
| OUTPUT_OBJECTS | STRING | 输出表名 |
| CLIENT_INFO | STRING | 客户端信息（JDBC/SDK/Web/Java SDK） |
| VIRTUAL_CLUSTER | STRING | 使用的计算集群 |
| VIRTUAL_CLUSTER_ID | BIGINT | 计算集群 ID |
| ROWS_PRODUCED | BIGINT | 处理的总记录数 |
| ROWS_INSERTED | BIGINT | 插入行数 |
| ROWS_UPDATED | BIGINT | 更新行数 |
| ROWS_DELETED | BIGINT | 删除行数 |
| JOB_CONFIG | STRING | 提交时的参数信息 |
| JOB_PRIORITY | STRING | 作业优先级 |
| INPUT_TABLES | STRING | 输入表（JSON 格式数组） |
| OUTPUT_TABLES | STRING | 输出对象名称 |
| QUERY_TAG | STRING | 用户设置的 TAG |

---

## MATERIALIZED_VIEW_REFRESH_HISTORY 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_ID | BIGINT | 空间 ID |
| WORKSPACE_NAME | STRING | 空间名称 |
| SCHEMA_ID | BIGINT | Schema ID |
| SCHEMA_NAME | STRING | Schema 名称 |
| MATERIALIZED_VIEW_ID | BIGINT | 物化视图 ID |
| MATERIALIZED_VIEW_NAME | STRING | 物化视图名称 |
| CREDITS_USED | DECIMAL | 刷新消耗的计费 |
| VIRTUAL_CLUSTER_ID | BIGINT | 虚拟集群 ID |
| VIRTUAL_CLUSTER | STRING | 虚拟集群名称（自动刷新时有值） |
| STATUS | STRING | PENDING / RUNNING / FINISHED / FAILED |
| REFRESH_MODE | STRING | INCREMENTAL / FULL_REFRESH / NO_DATA |
| STATISTICS | STRING | 增量刷新的记录数 |
| SCHEDULE_START_TIME | TIMESTAMP_LTZ | 计划刷新时间 |
| START_TIME | TIMESTAMP_LTZ | 实际开始时间 |
| END_TIME | TIMESTAMP_LTZ | 结束时间 |
| ERROR_MESSAGE | STRING | 刷新失败信息 |

---

## VOLUMES 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| VOLUME_CATALOG | STRING | 所属 Workspace 名称 |
| VOLUME_CATALOG_ID | STRING | 所属 Workspace ID |
| VOLUME_SCHEMA | STRING | 所属 Schema 名称 |
| VOLUME_SCHEMA_ID | STRING | Schema ID |
| VOLUME_NAME | STRING | Volume 名称 |
| VOLUME_ID | STRING | Volume ID |
| VOLUME_URL | STRING | Volume 绑定的 URL |
| VOLUME_REGION | STRING | Volume 所属区域 |
| VOLUME_TYPE | STRING | INTERNAL / EXTERNAL |
| VOLUME_CREATOR | STRING | Volume 的 owner |
| CONNECTION_NAME | STRING | 引用的 Connection 名称 |
| CONNECTION_ID | STRING | 引用的 Connection ID |
| PROPERTIES | MAP\<STRING,STRING> | 保留字段 |
| COMMENT | STRING | 注释 |
| CREATE_TIME | TIMESTAMP | 创建时间 |
| LAST_MODIFY_TIME | TIMESTAMP | 修改时间 |

---

## CONNECTIONS 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| WORKSPACE_NAME | STRING | 所在空间 |
| WORKSPACE_ID | STRING | 空间 ID |
| CONNECTION_NAME | STRING | 连接对象名称 |
| CONNECTION_ID | STRING | 连接 ID |
| CONNECTION_KIND | STRING | STORAGE CONNECTION / API CONNECTION |
| TYPE | STRING | FILE_SYSTEM / CLOUD_FUNCTION |
| PROVIDER | STRING | FILE_SYSTEM 时：OSS / COS；CLOUD_FUNCTION 时：aliyun / tencent |
| REGION | STRING | 连接的 region（如 ap-shanghai / cn-beijing） |
| SOURCE_CREATOR | STRING | 创建者 |
| CREATED_TIME | TIMESTAMP | 创建时间 |
| COMMENT | STRING | 注释 |
| PROPERTIES | MAP\<STRING,STRING> | 保留字段 |

---

## OBJECT_PRIVILEGES 视图

| 字段名 | 类型 | 说明 |
|---|---|---|
| GRANTOR | TEXT | 授出权限的用户 |
| GRANTEE | TEXT | 被授予权限的 user_name 或 role_name |
| GRANTED_TO | TEXT | USER / ROLE |
| OBJECT_CATALOG | TEXT | 被授予对象所在的工作空间或 catalog 名称 |
| OBJECT_SCHEMA | TEXT | 被授予对象所在的 Schema（对象不在 Schema 下则为空） |
| OBJECT_NAME | TEXT | 被授权的对象名称 |
| OBJECT_TYPE | TEXT | 被授权对象的类型 |
| SUB_OBJECT_TYPE | TEXT | 子对象类型 |
| PRIVILEGE_TYPE | TEXT | 被授予的具体权限 |
| IS_GRANTABLE | TEXT | 授权时是否有 WITH GRANT OPTION |
| AUTHORIZATION_TIME | TIMESTAMP_LTZ | 权限授予时间 |
