# External Function DDL 参考

> 来源：https://www.yunqi.tech/documents/CREATE_EXTERNATL_FUNCTION 等

## 概念

External Function（外部函数）是通过 Python/Java 编写、在云函数服务（阿里云 FC / 腾讯云 SCF / AWS Lambda）上执行的自定义 UDF。可调用：
- **在线服务**：LLM API、图像识别 API 等
- **离线模型**：打包上传的 Hugging Face 模型等

支持函数类型：UDF（标量）、UDAF（聚合，仅 Java）、UDTF（表函数，仅 Java）

---

## CREATE API CONNECTION（云函数连接）

```sql
CREATE API CONNECTION IF NOT EXISTS my_fc_conn
  TYPE CLOUD_FUNCTION
  PROVIDER = 'aliyun'           -- 'aliyun' | 'tencent' | 'aws'
  REGION = 'cn-shanghai'
  ROLE_ARN = 'acs:ram::1234567890:role/CzUDFRole'
  NAMESPACE = 'default'         -- 腾讯云必填，其他填 'default'
  CODE_BUCKET = 'my-oss-bucket';
```

| 参数 | 说明 |
|---|---|
| PROVIDER | `'aliyun'` / `'tencent'` / `'aws'` |
| REGION | 阿里云：`cn-shanghai`；腾讯云：`ap-beijing`；AWS：`cn-northwest-1` |
| ROLE_ARN | 授权给 Lakehouse 的 RAM 角色 ARN |
| NAMESPACE | 腾讯云命名空间（必填）；其他填 `'default'` |
| CODE_BUCKET | 存放函数代码包的 OSS/COS/S3 bucket 名称 |

---

## CREATE EXTERNAL FUNCTION

```sql
CREATE EXTERNAL FUNCTION IF NOT EXISTS my_schema.my_udf
  AS 'module_name.ClassName'
  USING FILE = 'oss://my-bucket/functions/code.zip'
  CONNECTION = my_fc_conn
  WITH PROPERTIES (
      'remote.udf.api' = 'python3.mc.v0'   -- Python: python3.mc.v0 | Java: java8.hive2.v0
  )
  COMMENT '自定义函数说明';
```

### 资源文件地址格式

```
-- OSS/COS/S3
oss://bucket-name/path/to/code.zip
cos://bucket-name/path/to/code.zip
s3://bucket-name/path/to/code.zip

-- User Volume（无需开通对象存储）
volume:user://~/code.zip

-- External Volume
volume://workspace.schema.volume_name/code.zip
```

### WITH PROPERTIES 参数

| 参数 | 值 | 说明 |
|---|---|---|
| `remote.udf.api` | `python3.mc.v0` | Python 3.10 运行时 |
| `remote.udf.api` | `java8.hive2.v0` | Java 8 Hive 风格 UDF |
| `remote.udf.protocol` | `http.arrow.v0` | 默认，访问云函数的协议 |

---

## Python UDF 代码结构

```python
#!/usr/bin/env python
try:
    from cz.udf import annotate
except ImportError:
    annotate = lambda _: lambda _: _

@annotate("string->string")   # 函数签名：输入类型->返回类型
class Upper(object):
    def evaluate(self, arg):
        if arg is None:
            return None
        return arg.upper()
```

### 函数签名格式

```
"input_type1,input_type2->return_type"

# 示例
"string->string"           # 字符串转字符串
"string,int->double"       # 两个输入，返回 double
"string->array<string>"    # 返回数组
```

支持类型：`string`、`int`、`bigint`、`double`、`float`、`boolean`、`array<T>`、`map<K,V>`

### 打包上传

```bash
# 安装依赖到当前目录
pip3 install httpx pydantic -t .

# 打包（< 500MB）
zip -rq code.zip ./*

# 上传到 User Volume（无需 OSS）
PUT 'code.zip' TO USER VOLUME;
```

---

## 管理操作

```sql
-- 查看外部函数列表
SHOW EXTERNAL FUNCTIONS;
SHOW EXTERNAL FUNCTIONS LIKE 'my_%';

-- 删除外部函数
DROP FUNCTION IF EXISTS my_schema.my_udf;
```

---

## 内置 AI 函数（无需部署云函数）

### AI_COMPLETE（调用 LLM）

```sql
-- 通过 API Connection 调用（需先创建连接）
CREATE API CONNECTION conn_bailian
    TYPE ai_function
    PROVIDER = 'bailian'
    BASE_URL = 'https://dashscope.aliyuncs.com/api/v1'
    API_KEY = 'sk-xxxxxxxxxxxxxxxxxxxxxxxx';

-- 调用 LLM 生成文本
SELECT AI_COMPLETE('connection:conn_bailian', '请用一句话总结：' || content) AS summary
FROM articles
LIMIT 10;

-- 通过平台 Endpoint 调用（管理员预配置）
SELECT AI_COMPLETE('endpoint:my_llm_endpoint', prompt_col) AS result
FROM my_table;
```

### AI_EMBEDDING（文本向量化）

```sql
-- 将文本转为向量（用于语义搜索）
SELECT id, content,
       AI_EMBEDDING('connection:conn_bailian', content) AS embedding
FROM documents;

-- 结合向量索引做语义搜索
SELECT id, content,
       cosine_distance(embedding, AI_EMBEDDING('connection:conn_bailian', '查询文本')) AS dist
FROM doc_embeddings
ORDER BY dist
LIMIT 10;
```
