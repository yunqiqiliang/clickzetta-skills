---
name: clickzetta-external-function
description: |
  在 ClickZetta Lakehouse 中创建和使用外部函数（External Function / UDF），
  通过 Python 或 Java 扩展 SQL 计算能力，调用 LLM、图像识别、自定义算法等外部服务。
  覆盖 CREATE API CONNECTION（阿里云FC/腾讯云SCF/AWS Lambda）、
  CREATE EXTERNAL FUNCTION、Python UDF 代码结构与打包、
  内置 AI_COMPLETE 和 AI_EMBEDDING 函数的使用。
  当用户说"外部函数"、"UDF"、"自定义函数"、"External Function"、
  "Remote Function"、"调用 LLM"、"AI_COMPLETE"、"AI_EMBEDDING"、
  "文本向量化"、"调用阿里云函数计算"、"调用云函数"、"Python UDF"、
  "Java UDF"、"CREATE EXTERNAL FUNCTION"时触发。
---

# ClickZetta External Function

External Function 让 SQL 可以调用外部计算能力（LLM、图像识别、自定义算法），通过 Python/Java 编写函数逻辑，部署在云函数服务上执行。

阅读 [references/external-function-ddl.md](references/external-function-ddl.md) 了解完整语法。

---

## 两种使用路径

| 路径 | 适用场景 | 复杂度 |
|---|---|---|
| **内置 AI 函数**（AI_COMPLETE / AI_EMBEDDING） | 调用 LLM 生成文本、文本向量化 | 低，只需创建 API Connection |
| **External Function** | 自定义算法、图像处理、私有模型 | 高，需部署云函数 |

---

## 路径一：内置 AI 函数（推荐）

### 1. 创建 AI API Connection

```sql
CREATE API CONNECTION conn_bailian
    TYPE ai_function
    PROVIDER = 'bailian'
    BASE_URL = 'https://dashscope.aliyuncs.com/api/v1'
    API_KEY = 'sk-xxxxxxxxxxxxxxxxxxxxxxxx';
```

### 2. AI_COMPLETE — 调用 LLM

```sql
-- 文本摘要
SELECT id,
       AI_COMPLETE('connection:conn_bailian', '请用一句话总结：' || content) AS summary
FROM articles;

-- 情感分析
SELECT id, review,
       AI_COMPLETE('connection:conn_bailian',
           '判断以下评论的情感（正面/负面/中性），只返回一个词：' || review) AS sentiment
FROM user_reviews;

-- 通过平台 Endpoint（管理员预配置）
SELECT AI_COMPLETE('endpoint:my_llm_endpoint', prompt_col) AS result
FROM my_table;
```

### 3. AI_EMBEDDING — 文本向量化

```sql
-- 批量生成 embedding
SELECT id, content,
       AI_EMBEDDING('connection:conn_bailian', content) AS vec
FROM documents;

-- 语义搜索（结合向量索引）
SELECT id, content,
       cosine_distance(vec, AI_EMBEDDING('connection:conn_bailian', '用户查询')) AS dist
FROM doc_embeddings
ORDER BY dist
LIMIT 10;
```

---

## 路径二：External Function（自定义 UDF）

### 整体流程

```
1. 开通云函数服务（阿里云FC / 腾讯云SCF / AWS Lambda）
2. 编写 Python/Java 函数代码
3. 打包上传到对象存储或 User Volume
4. 授权 Lakehouse 访问云函数服务（RAM 角色）
5. CREATE API CONNECTION
6. CREATE EXTERNAL FUNCTION
7. 在 SQL 中调用
```

### 步骤 1：创建云函数 API Connection

```sql
-- 阿里云 FC
CREATE API CONNECTION IF NOT EXISTS my_fc_conn
  TYPE CLOUD_FUNCTION
  PROVIDER = 'aliyun'
  REGION = 'cn-shanghai'
  ROLE_ARN = 'acs:ram::1234567890:role/CzUDFRole'
  NAMESPACE = 'default'
  CODE_BUCKET = 'my-oss-bucket';

-- 腾讯云 SCF
CREATE API CONNECTION IF NOT EXISTS my_scf_conn
  TYPE CLOUD_FUNCTION
  PROVIDER = 'tencent'
  REGION = 'ap-shanghai'
  ROLE_ARN = 'qcs::cam::uin/1234567890:roleName/CzUDFRole'
  NAMESPACE = 'default'
  CODE_BUCKET = 'my-cos-bucket';
```

### 步骤 2：编写 Python UDF

```python
# upper.py
try:
    from cz.udf import annotate
except ImportError:
    annotate = lambda _: lambda _: _

@annotate("string->string")
class Upper(object):
    def evaluate(self, arg):
        if arg is None:
            return None
        return arg.upper()
```

打包上传：
```bash
zip -rq upper.zip upper.py
```

```sql
-- 上传到 User Volume（在 ClickZetta Studio 或 CLI 中执行，source_path 使用绝对路径）
PUT '/path/to/upper.zip' TO USER VOLUME;
```

### 步骤 3：创建 External Function

```sql
-- 使用 User Volume 存放代码（无需 OSS）
CREATE EXTERNAL FUNCTION IF NOT EXISTS public.str_upper
  AS 'upper.Upper'
  USING FILE = 'volume:user://~/upper.zip'
  CONNECTION = my_fc_conn
  WITH PROPERTIES ('remote.udf.api' = 'python3.mc.v0')
  COMMENT '字符串转大写';

-- 使用 OSS 存放代码
CREATE EXTERNAL FUNCTION IF NOT EXISTS public.str_upper
  AS 'upper.Upper'
  USING FILE = 'oss://my-bucket/functions/upper.zip'
  CONNECTION = my_fc_conn
  WITH PROPERTIES ('remote.udf.api' = 'python3.mc.v0');
```

### 步骤 4：调用函数

```sql
SELECT id, str_upper(name) AS upper_name FROM my_table;
```

---

## 管理操作

```sql
-- 查看所有外部函数
SHOW EXTERNAL FUNCTIONS;
SHOW EXTERNAL FUNCTIONS LIKE 'str_%';

-- 删除函数
DROP FUNCTION IF EXISTS public.str_upper;
```

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 函数调用超时 | 云函数冷启动或执行慢 | 增大超时配置，或预热函数 |
| 依赖库 ABI 不兼容 | 在 macOS/Windows 打包 | 用 `quay.io/pypa/manylinux2014_x86_64` 容器打包 |
| 代码包 > 500MB | 依赖过大 | 改用容器镜像方式部署 |
| AI_COMPLETE 报错 | API Key 无效或余额不足 | 检查 API Connection 的 API_KEY |
| ROLE_ARN 权限不足 | RAM 角色未授权 | 参考文档配置 AliyunFCFullAccess + OSS 权限 |
