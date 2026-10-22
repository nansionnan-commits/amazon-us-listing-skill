# 字段规范（按 productType）

> 每个 PT 的 required 完全不同。**新 PT 第一次用必须先拉 schema。**
> 拉法见 `KNOWN_ISSUES.md` LI-010。

---

## 通用包装器

```python
MP = "ATVPDKIKX0DER"   # 美国站

def L(v):  # 带 language_tag 的字段
    return [{"language_tag": "en_US", "value": v, "marketplace_id": MP}]
```

---

## HARDWARE_HANDLE（Hardware Handle）✅ 已跑通

**实测日期**：2026-10-22　**schema 字段数**：136　**required**：6

### required

| 字段 | 格式 |
|---|---|
| `brand` | `L("EAOEIHD")` |
| `bullet_point` | `[{language_tag, value, marketplace_id}, ...]` ≤5 条 |
| `country_of_origin` | `[{"value":"CN","marketplace_id"}]` |
| `item_name` | `L("...")` ≤200 字符 |
| `product_description` | `L("<p>...</p>")` HTML |
| `supplier_declared_dg_hz_regulation` | `[{"value":"not_applicable","marketplace_id"}]` |

### 隐性必填（不报 required 但校验报 90220）

| 字段 | 格式 |
|---|---|
| `model_number` | `[{"value":str,"marketplace_id"}]`（**无 language_tag**）|
| `model_name` | `L("...")` |
| `manufacturer` | `L("EAOEIHD")` |
| `included_components` | `L("1 x ...")` |
| `handle` | `[{"material":[{"language_tag":"en_US","value":"Plastic"}], "type":[{"language_tag":"en_US","value":"Molded Grip Handle"}], "marketplace_id"}]` |
| `item_length_width` | `[{"length":{"value":9.84,"unit":"inches"},"width":{"value":6.69,"unit":"inches"},"marketplace_id"}]` |

### 可选但建议填

| 字段 | 格式 |
|---|---|
| `color` | `L("Black")` |
| `size` | `L("One Size")` |
| `material` | `L("Nylon")` |
| `number_of_items` | `[{"value":1,"marketplace_id"}]` |
| `condition_type` | `[{"value":"new_new","marketplace_id"}]` |
| `list_price` | `[{"currency":"USD","value":29.99,"marketplace_id"}]` |
| `purchasable_offer` | 见下 |
| `main_product_image_locator` | `[{"media_location":"https://...","marketplace_id"}]` |
| `other_product_image_locator_1..8` | 同上 |
| `fulfillment_availability` | `[{"fulfillment_channel_code":"DEFAULT","quantity":999,"lead_time_to_ship_max_days":2}]` |
| `merchant_shipping_group` | `[{"value":"a08cfb00-f40d-4cbd-a231-51d5f48f37d9","marketplace_id"}]` |
| `item_package_dimensions` | `[{"length":{"value":25,"unit":"centimeters"},"width":{...},"height":{...},"marketplace_id"}]` |
| `item_package_weight` | `[{"value":0.27,"unit":"kilograms","marketplace_id"}]` |
| `supplier_declared_has_product_identifier_exemption` | `[{"value":true,"marketplace_id"}]` |

### 价格写法

```json
"purchasable_offer": [{
  "currency": "USD",
  "audience": "ALL",
  "our_price": [{"schedule": [{"value_with_tax": 17.00}]}],
  "marketplace_id": "ATVPDKIKX0DER"
}]
```

⚠️ **our_price = 买家总价 − 运费**。US 默认运费 $5.99，所以 $22.99 的总价 → 填 17.00。

---

## 待补充（遇到新 PT 时追加）

| PT | 状态 | 备注 |
|---|---|---|
| `BLANKET` | 参考（现有 listing 用） | 模板来自它 |
| `MOTORCYCLE_ACCESSORY` | 存在但未测 | 拉 schema 时返回 200 |

**新增 PT 的记录模板**：
```md
## {PT_NAME}
**实测日期**：YYYY-MM-DD　**required**：N
| 字段 | 格式 |
...
**坑**：
```
