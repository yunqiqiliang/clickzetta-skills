# 动态数据脱敏参考

> 来源：https://www.yunqi.tech/documents/dynamic-mask
> ⚠️ 本功能当前处于**受邀预览发布**阶段，如需使用请联系技术支持。

## 概述

列级安全（Column-level Security）通过动态脱敏（Dynamic Data Masking）提供细粒度数据保护。系统仅存储原始数据，在查询时动态执行脱敏函数，根据用户身份或角色决定显示方式。

## 步骤 1：创建脱敏策略函数

```sql
CREATE FUNCTION [schema_name.]function_name (col_name column_type)
RETURNS output_type
AS expression_with_conditional_logic;
```

关键要素：
- 返回类型必须与原始列类型相同
- 使用安全上下文函数：
  - `current_user()` — 获取当前用户名（注意大小写）
  - `current_roles()` — 获取用户角色数组

示例：手机号脱敏（管理员看全部，其他人看脱敏）

```sql
CREATE FUNCTION public.mask_phone(phone STRING)
RETURNS STRING
AS CASE
    WHEN current_user() = 'admin' THEN phone
    ELSE CONCAT(SUBSTR(phone, 1, 3), '****', SUBSTR(phone, 8, 4))
END;
```

示例：基于角色的脱敏

```sql
CREATE FUNCTION public.mask_salary(salary DECIMAL(10,2))
RETURNS DECIMAL(10,2)
AS CASE
    WHEN array_contains(current_roles(), 'hr_role') THEN salary
    ELSE 0.0
END;
```

## 步骤 2：绑定脱敏策略到列

### 建表时指定

```sql
CREATE TABLE employees (
    emp_id INT,
    name STRING,
    phone STRING MASK public.mask_phone,
    salary DECIMAL(10,2) MASK public.mask_salary
);
```

### 修改已有表的列

```sql
ALTER TABLE employees
CHANGE COLUMN phone
SET MASK public.mask_phone;
```

### 添加新列时指定脱敏

```sql
ALTER TABLE employees
ADD COLUMN id_card STRING MASK public.mask_id_card;
```

## 步骤 3：解除脱敏策略

```sql
ALTER TABLE employees
CHANGE COLUMN phone
UNSET MASK;
```

## 注意事项

- 脱敏函数的返回类型必须与列类型完全一致
- `current_user()` 返回值区分大小写
- `current_roles()` 返回角色数组，用 `array_contains()` 判断
