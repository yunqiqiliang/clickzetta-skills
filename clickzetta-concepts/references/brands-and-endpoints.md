# ClickZetta 品牌关系与服务地址

## 品牌关系

ClickZetta 是技术品牌名，同一产品在不同市场使用不同品牌：

| 品牌 | 市场 | 官网 | 文档 |
|---|---|---|---|
| **云器（Yunqi）** | 国内 | www.yunqi.tech | www.yunqi.tech/documents |
| **Singdata** | 国际 | www.singdata.com | www.singdata.com/documents |
| **ClickZetta** | 技术品牌（通用） | — | — |

> **云器 Lakehouse = ClickZetta Lakehouse = Singdata Lakehouse**，三者指同一产品。
> 用户提到"云器"、"Singdata"、"ClickZetta"时，均指同一 Lakehouse 平台。

---

## 国内（云器）服务地址

控制台：`https://<instance_name>.app.clickzetta.com`

JDBC URL 格式：`jdbc:clickzetta://<instance_name>.<region_code>.api.clickzetta.com/<workspace>`

| 云服务商 | 区域 | Region Code | API 地址 |
|---|---|---|---|
| 阿里云 | 上海 | `cn-shanghai-alicloud` | `<instance>.cn-shanghai-alicloud.api.clickzetta.com` |
| 阿里云 | 杭州 | `cn-hangzhou-alicloud` | `<instance>.cn-hangzhou-alicloud.api.clickzetta.com` |
| 阿里云 | 北京 | `cn-beijing-alicloud` | `<instance>.cn-beijing-alicloud.api.clickzetta.com` |
| 腾讯云 | 上海 | `cn-shanghai-tencentcloud` | `<instance>.cn-shanghai-tencentcloud.api.clickzetta.com` |
| 华为云 | 上海 | `cn-shanghai-huaweicloud` | `<instance>.cn-shanghai-huaweicloud.api.clickzetta.com` |

---

## 国际（Singdata）服务地址

账户控制台：`https://accounts.app.singdata.com` 或 `https://<account_name>.accounts.app.singdata.com`

实例控制台：`https://<instance_name>.app.singdata.com`

工作空间列表：`https://<instance_name>.app.lakehouse.singdata.com/workspace`

JDBC URL 格式：`jdbc:clickzetta://<instance_name>.<region_code>.api.singdata.com/<workspace>`

Streaming API Host：`<instance_name>.streamingapi.singdata.com`

| 云服务商 | 区域 | Region Code | API 地址 |
|---|---|---|---|
| 阿里云 | 新加坡 | `ap-southeast-1-alicloud` | `<instance>.ap-southeast-1-alicloud.api.singdata.com` |
| Amazon Web Services | 新加坡 | `ap-southeast-1-aws` | `<instance>.ap-southeast-1-aws.api.singdata.com` |

---

## SDK / 连接参数中的地址格式

Python SDK（`clickzetta-connector-python`）的 `service` 参数填 API 地址（不含 `jdbc:clickzetta://` 前缀和实例名）：

```python
# 国内（云器）
conn = connect(service='cn-shanghai-alicloud.api.clickzetta.com', instance='your_instance', ...)

# 国际（Singdata）
conn = connect(service='ap-southeast-1-alicloud.api.singdata.com', instance='your_instance', ...)
```

Java SDK（`clickzetta-java`）的 `.service()` 参数同理：

```java
// 国内（云器）
ClickZettaClient.newBuilder()
    .service("cn-shanghai-alicloud.api.clickzetta.com")
    .instance("your_instance")
    ...

// 国际（Singdata）
ClickZettaClient.newBuilder()
    .service("ap-southeast-1-alicloud.api.singdata.com")
    .instance("your_instance")
    ...
```
