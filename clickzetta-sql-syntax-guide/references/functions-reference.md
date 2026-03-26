# 函数完整参考

> 含与 Snowflake / Spark SQL 的差异标注

---

## 数值函数

```sql
ABS(x)                          -- 绝对值
CEIL(x) / CEILING(x)            -- 向上取整
FLOOR(x)                        -- 向下取整
ROUND(x, d)                     -- 四舍五入，d位小数
TRUNCATE(x, d)                  -- 截断，d位小数
MOD(x, y) / x % y               -- 取模
POWER(x, y) / POW(x, y)         -- 幂运算
SQRT(x)                         -- 平方根
EXP(x)                          -- e^x
LN(x) / LOG(x)                  -- 自然对数
LOG(base, x)                    -- 指定底数对数
LOG2(x) / LOG10(x)              -- 以2/10为底
SIGN(x)                         -- 符号（-1/0/1）
GREATEST(a, b, c, ...)          -- 最大值
LEAST(a, b, c, ...)             -- 最小值
RANDOM() / RAND()               -- 0-1随机数
PI()                            -- π
SIN(x) / COS(x) / TAN(x)       -- 三角函数
ASIN(x) / ACOS(x) / ATAN(x)    -- 反三角函数
ATAN2(y, x)                     -- 反正切
DEGREES(x) / RADIANS(x)        -- 角度/弧度转换
FACTORIAL(n)                    -- 阶乘
BIN(x)                          -- 转二进制字符串
HEX(x)                          -- 转十六进制字符串
UNHEX(s)                        -- 十六进制转字符串
CONV(x, from_base, to_base)     -- 进制转换
```

**与 Snowflake 差异：**
- Snowflake `SQUARE(x)` → ClickZetta `POWER(x, 2)`
- Snowflake `HAVERSINE(lat1, lon1, lat2, lon2)` → ClickZetta 不支持
- Snowflake `WIDTH_BUCKET` → ClickZetta 不支持

---

## 字符串函数

```sql
-- 基本操作
LENGTH(s) / CHAR_LENGTH(s)      -- 字符长度
OCTET_LENGTH(s)                 -- 字节长度
UPPER(s) / LOWER(s)             -- 大小写转换
INITCAP(s)                      -- 首字母大写
TRIM(s) / LTRIM(s) / RTRIM(s)  -- 去空格
TRIM(BOTH 'x' FROM s)           -- 去指定字符
LPAD(s, n, pad) / RPAD(s, n, pad)  -- 填充
REPEAT(s, n)                    -- 重复
REVERSE(s)                      -- 反转
SPACE(n)                        -- n个空格

-- 拼接
CONCAT(s1, s2, ...)             -- 拼接（NULL 传播）
CONCAT_WS(sep, s1, s2, ...)     -- 带分隔符拼接（跳过 NULL）
s1 || s2                        -- 拼接运算符

-- 截取
SUBSTR(s, pos) / SUBSTRING(s, pos)
SUBSTR(s, pos, len) / SUBSTRING(s, pos, len)
LEFT(s, n) / RIGHT(s, n)
MID(s, pos, len)                -- 同 SUBSTR

-- 查找
INSTR(s, substr)                -- 查找位置（1-based，0表示未找到）
LOCATE(substr, s)               -- 同 INSTR，参数顺序不同
LOCATE(substr, s, pos)          -- 从pos开始查找
POSITION(substr IN s)           -- 标准SQL语法
FIND_IN_SET(s, list)            -- 在逗号分隔列表中查找

-- 替换
REPLACE(s, old, new)            -- 替换所有
TRANSLATE(s, from_chars, to_chars)  -- 字符级替换
OVERLAY(s PLACING new FROM pos FOR len)  -- 覆盖替换

-- 正则
REGEXP_EXTRACT(s, pattern, group)   -- 提取匹配组
REGEXP_EXTRACT_ALL(s, pattern)      -- 提取所有匹配
REGEXP_REPLACE(s, pattern, repl)    -- 正则替换
REGEXP_LIKE(s, pattern)             -- 正则匹配（返回布尔）
RLIKE(s, pattern)                   -- 同 REGEXP_LIKE
s RLIKE pattern                     -- 运算符形式
REGEXP_COUNT(s, pattern)            -- 匹配次数
REGEXP_SUBSTR(s, pattern)           -- 提取第一个匹配

-- 分割
SPLIT(s, delimiter)             -- 按分隔符分割，返回 ARRAY
SPLIT_PART(s, delimiter, n)     -- 取第n个分割部分（1-based）

-- 格式化
FORMAT(x, d)                    -- 数字格式化（千分位）
PRINTF(fmt, args...)            -- printf 风格格式化

-- 编码
BASE64(s) / UNBASE64(s)         -- Base64 编解码
MD5(s)                          -- MD5 哈希
SHA1(s) / SHA2(s, bits)         -- SHA 哈希
CRC32(s)                        -- CRC32
ENCODE(s, charset) / DECODE(s, charset)  -- 字符集编解码

-- 其他
ASCII(s)                        -- 首字符 ASCII 码
CHAR(n)                         -- ASCII 码转字符
SOUNDEX(s)                      -- 语音相似度编码
LEVENSHTEIN(s1, s2)             -- 编辑距离
HAMMING_DISTANCE(s1, s2)        -- 汉明距离（字符串）
```

**与 Snowflake 差异：**
- Snowflake `CHARINDEX(substr, s)` → ClickZetta `INSTR(s, substr)` 或 `LOCATE(substr, s)`（参数顺序不同！）
- Snowflake `EDITDISTANCE(s1, s2)` → ClickZetta `LEVENSHTEIN(s1, s2)`
- Snowflake `STRTOK(s, delim, n)` → ClickZetta `SPLIT_PART(s, delim, n)`
- Snowflake `ILIKE(s, pattern)` → ClickZetta `LOWER(s) LIKE LOWER(pattern)`
- Snowflake `CONTAINS(s, substr)` → ClickZetta `INSTR(s, substr) > 0`
- Snowflake `STARTSWITH(s, prefix)` → ClickZetta `s LIKE 'prefix%'` 或 `STARTSWITH(s, prefix)`
- Snowflake `ENDSWITH(s, suffix)` → ClickZetta `s LIKE '%suffix'` 或 `ENDSWITH(s, suffix)`

---

## 日期时间函数

```sql
-- 获取当前时间
CURRENT_DATE()                  -- 当前日期
CURRENT_TIMESTAMP() / NOW()     -- 当前时间戳（带时区）
CURRENT_TIME()                  -- 当前时间
LOCALTIMESTAMP()                -- 本地时间戳

-- 提取部分
YEAR(dt) / MONTH(dt) / DAY(dt)
HOUR(dt) / MINUTE(dt) / SECOND(dt)
DAYOFWEEK(dt)                   -- 1=周日, 7=周六
DAYOFMONTH(dt)                  -- 同 DAY
DAYOFYEAR(dt)                   -- 年中第几天
WEEKOFYEAR(dt)                  -- 年中第几周
QUARTER(dt)                     -- 季度（1-4）
EXTRACT(YEAR FROM dt)           -- 标准SQL提取
DATE_PART('year', dt)           -- 同 EXTRACT

-- 日期加减
DATE_ADD(dt, n)                 -- 加n天
DATE_SUB(dt, n)                 -- 减n天
dt + INTERVAL n DAY             -- 加n天（标准SQL）
dt - INTERVAL n DAY             -- 减n天
dt + INTERVAL '1-2' YEAR TO MONTH  -- 加1年2个月
ADDDATE(dt, n)                  -- 同 DATE_ADD
SUBDATE(dt, n)                  -- 同 DATE_SUB
ADD_MONTHS(dt, n)               -- 加n个月
MONTHS_BETWEEN(dt1, dt2)        -- 月份差

-- 日期差
DATEDIFF(end_dt, start_dt)      -- ⚠️ end在前！返回天数差
TIMESTAMPDIFF(unit, dt1, dt2)   -- 指定单位的差值

-- 截断
DATE_TRUNC('year', dt)          -- 截断到年
DATE_TRUNC('month', dt)         -- 截断到月
DATE_TRUNC('day', dt)           -- 截断到天
DATE_TRUNC('hour', dt)          -- 截断到小时
DATE_TRUNC('week', dt)          -- 截断到周（周一）
TRUNC(dt, 'MM')                 -- Oracle 风格截断

-- 格式化
DATE_FORMAT(dt, 'yyyy-MM-dd')   -- 格式化为字符串
DATE_FORMAT(dt, 'yyyy-MM-dd HH:mm:ss')
TO_CHAR(dt, 'YYYY-MM-DD')       -- 同 DATE_FORMAT

-- 转换
TO_DATE('2024-01-01')           -- 字符串转日期
TO_DATE('2024-01-01', 'yyyy-MM-dd')
TO_TIMESTAMP('2024-01-01 12:00:00')
TO_TIMESTAMP('2024-01-01', 'yyyy-MM-dd')
CAST('2024-01-01' AS DATE)
CAST('2024-01-01 12:00:00' AS TIMESTAMP)
FROM_UNIXTIME(unix_ts)          -- Unix时间戳转时间戳
FROM_UNIXTIME(unix_ts, fmt)     -- 转格式化字符串
UNIX_TIMESTAMP()                -- 当前Unix时间戳
UNIX_TIMESTAMP(dt)              -- 日期转Unix时间戳
UNIX_TIMESTAMP(s, fmt)          -- 字符串转Unix时间戳

-- 其他
LAST_DAY(dt)                    -- 月末日期
NEXT_DAY(dt, 'Monday')          -- 下一个指定星期几
MAKEDATE(year, dayofyear)       -- 构造日期
MAKETIME(h, m, s)               -- 构造时间
PERIOD_ADD(period, n)           -- 期间加减
PERIOD_DIFF(p1, p2)             -- 期间差
```

**与 Snowflake 差异：**
- Snowflake `DATEADD(day, n, dt)` → ClickZetta `DATE_ADD(dt, n)` 或 `dt + INTERVAL n DAY`
- Snowflake `DATEDIFF(day, start, end)` → ClickZetta `DATEDIFF(end, start)` ⚠️ 参数顺序相反！
- Snowflake `DATE_TRUNC('day', dt)` → ClickZetta 相同
- Snowflake `TO_DATE(s)` → ClickZetta 相同
- Snowflake `CONVERT_TIMEZONE(tz, dt)` → ClickZetta `CONVERT_TZ(dt, from_tz, to_tz)`
- Snowflake `SYSDATE()` / `GETDATE()` → ClickZetta `CURRENT_TIMESTAMP()` / `NOW()`
- Snowflake `TIMESTAMPADD(unit, n, dt)` → ClickZetta `dt + INTERVAL n unit`

**与 Spark SQL 差异：**
- 大部分函数相同，ClickZetta 兼容 Spark 日期函数

---

## 条件函数

```sql
-- IF
IF(condition, true_val, false_val)

-- CASE WHEN
CASE WHEN cond1 THEN val1
     WHEN cond2 THEN val2
     ELSE default_val
END

-- 简单 CASE
CASE status
    WHEN 'A' THEN 'Active'
    WHEN 'I' THEN 'Inactive'
    ELSE 'Unknown'
END

-- NULL 处理
COALESCE(a, b, c)               -- 第一个非NULL值
NVL(a, b)                       -- a为NULL时返回b（同 IFNULL）
IFNULL(a, b)                    -- 同 NVL
NULLIF(a, b)                    -- a=b时返回NULL，否则返回a
NVL2(a, b, c)                   -- a非NULL返回b，否则返回c
ISNULL(a)                       -- 是否为NULL（返回布尔）
ISNOTNULL(a)                    -- 是否非NULL

-- DECODE（Oracle/Hive 风格）
DECODE(expr, val1, res1, val2, res2, ..., default)

-- 类型检查
TYPEOF(expr)                    -- 返回类型名称字符串
```

**与 Snowflake 差异：**
- Snowflake `IFF(cond, a, b)` → ClickZetta `IF(cond, a, b)`
- Snowflake `ZEROIFNULL(x)` → ClickZetta `COALESCE(x, 0)` 或 `NVL(x, 0)`
- Snowflake `NULLIFZERO(x)` → ClickZetta `NULLIF(x, 0)`
- Snowflake `BOOLAND(a, b)` / `BOOLOR(a, b)` → ClickZetta `a AND b` / `a OR b`

---

## 聚合函数

```sql
-- 基本聚合
COUNT(*) / COUNT(col) / COUNT(DISTINCT col)
SUM(col) / AVG(col) / MAX(col) / MIN(col)
STDDEV(col) / STDDEV_POP(col) / STDDEV_SAMP(col)
VARIANCE(col) / VAR_POP(col) / VAR_SAMP(col)

-- 布尔聚合
BOOL_OR(cond)                   -- 任意一个为真
BOOL_AND(cond)                  -- 全部为真
EVERY(cond)                     -- 同 BOOL_AND

-- 字符串聚合
GROUP_CONCAT(col ORDER BY col SEPARATOR ',')   -- 替代 Snowflake LISTAGG
GROUP_CONCAT(DISTINCT col SEPARATOR ',')

-- 数组聚合
ARRAY_AGG(col)                  -- 收集为数组（含NULL）
COLLECT_LIST(col)               -- 同 ARRAY_AGG
COLLECT_SET(col)                -- 去重收集

-- 近似聚合
APPROX_COUNT_DISTINCT(col)      -- 近似去重计数（HyperLogLog）
APPROX_PERCENTILE(col, p)       -- 近似百分位数

-- 统计聚合
CORR(x, y)                      -- 相关系数
COVAR_POP(x, y) / COVAR_SAMP(x, y)  -- 协方差
REGR_SLOPE(y, x) / REGR_INTERCEPT(y, x)  -- 线性回归

-- 有序集合聚合
PERCENTILE(col, p)              -- 精确百分位数
PERCENTILE_APPROX(col, p)       -- 近似百分位数
MEDIAN(col)                     -- 中位数
```

**与 Snowflake 差异：**
- Snowflake `LISTAGG(col, ',') WITHIN GROUP (ORDER BY col)` → ClickZetta `GROUP_CONCAT(col ORDER BY col SEPARATOR ',')`
- Snowflake `ARRAY_AGG(col) WITHIN GROUP (ORDER BY col)` → ClickZetta `ARRAY_AGG(col)` 不支持 WITHIN GROUP
- Snowflake `OBJECT_AGG(key, value)` → ClickZetta `MAP_AGG(key, value)`
- Snowflake `BITAND_AGG / BITOR_AGG / BITXOR_AGG` → ClickZetta `BIT_AND / BIT_OR / BIT_XOR`

---

## 类型转换函数

```sql
-- 显式转换
CAST(expr AS target_type)
expr::target_type               -- 简写语法

-- 安全转换（失败返回NULL而非报错）
TRY_CAST(expr AS target_type)

-- 字符串转换
TO_NUMBER(s) / TO_DECIMAL(s)
TO_DOUBLE(s)
TO_BOOLEAN(s)                   -- 'true'/'false'/'1'/'0'

-- 示例
CAST('123' AS INT)
CAST(123 AS STRING)
CAST('2024-01-01' AS DATE)
CAST('[1,2,3]' AS VECTOR(3))    -- 字符串转向量
TRY_CAST('abc' AS INT)          -- 返回 NULL
```

**与 Snowflake 差异：**
- Snowflake `TRY_TO_NUMBER / TRY_TO_DATE` → ClickZetta `TRY_CAST`
- Snowflake `TO_VARIANT(x)` → ClickZetta `PARSE_JSON(TO_JSON(x))`

---

## 系统/上下文函数

```sql
CURRENT_USER()                  -- 当前用户名
CURRENT_WORKSPACE()             -- 当前工作空间
CURRENT_SCHEMA()                -- 当前 Schema
CURRENT_VCLUSTER()              -- 当前计算集群
CURRENT_INSTANCE_ID()           -- 当前实例ID
VERSION()                       -- 版本信息
```

**与 Snowflake 差异：**
- Snowflake `CURRENT_DATABASE()` → ClickZetta `CURRENT_WORKSPACE()`
- Snowflake `CURRENT_WAREHOUSE()` → ClickZetta `CURRENT_VCLUSTER()`
- Snowflake `CURRENT_ROLE()` → ClickZetta 无直接对应

---

## 向量函数

```sql
-- 距离计算
L2_DISTANCE(v1, v2)             -- 欧几里得距离（越小越相似）
COSINE_DISTANCE(v1, v2)         -- 余弦距离（越小越相似）
DOT_PRODUCT(v1, v2)             -- 点积（越大越相似，需归一化）
HAMMING_DISTANCE(v1, v2)        -- 汉明距离（二值向量）
JACCARD_DISTANCE(v1, v2)        -- 雅卡德距离

-- 向量操作
BINARY_QUANTIZE(v)              -- float向量二值化
VECTOR(v1, v2, ...)             -- 构建向量

-- 构建向量
SELECT VECTOR(0.1, 0.2, 0.3, 0.4);
SELECT CAST('[0.1, 0.2, 0.3]' AS VECTOR(3));
```
