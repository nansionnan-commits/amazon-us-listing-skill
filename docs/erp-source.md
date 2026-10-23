# ERP 数据源上架（兰谷 ERP → 亚马逊 US）

> 分支：`feature/erp-source`　首版：2026-10-23
> 适用：从公司 ERP（兰谷，`erp.hzcwin.com`）直接抓产品数据上架，替代手工收集输入。

---

## 一、什么时候用

| 场景 | 用什么 |
|---|---|
| 老板给竞品 ASIN + 图片目录 | `build_listing.py`（原有流程） |
| **从 ERP 批量选品上架** | **`erp_listing.py`（本分支新增）** |

---

## 二、ERP 接口（需浏览器登录态 + CDP）

```python
# 列表（分页）
POST http://api.hzcwin.com/hzkj-product/product/productLibrary/spu/list
body: {"pageNo":1,"pageSize":50,"productStatus":5,"column":"createTime","order":"desc"}

# 详情（一次返回全字段）
GET  http://api.hzcwin.com/hzkj-product/product/productLibrary/spu/queryById?id={spuId}

# 统计（状态对账用，权威）
GET  http://api.hzcwin.com/hzkj-product/product/productLibrary/spu/statisticsCount
     → {sourcePending, developmentPending, auditPending, completed, reject, all}
```

**鉴权**：Header `X-Access-Token` = `localStorage["pro__Access-Token"]` 解析出的 `.value`。
必须在浏览器上下文内发请求（CDP `/eval`），token 有时效。

⚠️ `column` 排序参数**无效**，接口始终按 createTime 排序。

---

## 三、productStatus 枚举（血泪教训）

| 值 | 含义 | 数量（2026-10-23） |
|---|---|---|
| 1 | 待寻源 sourcePending | 599 |
| 2 | 待开发 developmentPending | 910 |
| **4** | **待审核 auditPending** | 207 |
| **5** | **已完成 completed** | **22,660** |

**只做 5（已完成）**。判状态前先调 `statisticsCount` 对账，不要靠猜。

---

## 四、字段映射

| 上架需要 | ERP 字段 | 备注 |
|---|---|---|
| SKU | `skuList[].skuCode` | 直接用 ERP SKU，便于追溯 |
| 变体 | `skuList[].attributes` | JSON 数组，如 `[{"name":"颜色","value":"灰色"}]` |
| 重量 | `skuList[].weight` | **kg** |
| 包装尺寸 | `skuList[].length/width/height` | **cm** |
| 采购价 | `skuList[].purchasePrice` | **CNY**，是采购价不是售价 |
| 主图/副图 | `skuList[].imageList[]` | 按 `sort` 排序，0=主图，1~6=副图 |
| 竞品链接 | `referenceLink` | FAQ：可能是亚马逊也可能是别的站 |
| 1688 链接 | `supplier.purchaseLink` | 补图/采购用 |
| 材质 | `customs.materialEn` | |
| 英文名 | `customs.nameEn` | |
| **五点 + 长描** | `description.point1~point5` + `description.description` | **ERP 的文案质量不错，可直接用** |

**ERP 没有的**：售价（要算）、productType（要从竞品反查）、brand（固定 EAOEIHD）。

---

## 五、图片流程（两条通路）

| 来源 | 处理 | 说明 |
|---|---|---|
| `cbu01.alicdn.com` / `img.alicdn.com` | **直接用** | 阿里 CDN，Amazon 能拉 |
| `file.hzcwin.com`（ERP） | **下载 → 上传 imgbb → 用 i.ibb.co 直链** | ERP 图床会超时 + 中文名 404 |

**ERP 图的两个坑**：
1. 文件名含中文/括号（`猫(1).jpg`）→ 必须 `urllib.parse.quote` 编码，否则 404
2. 图床不稳定 → 同一条 payload 有时 VALID 有时 `Media Download Timed Out`

imgbb key 在 `config/image_host.json`。
alicdn 链接若带 `_.webp` 后缀，**去掉才是原始 jpg**。

---

## 六、算价（`calc_price.py`）

```python
price_50_usd(采购价CNY, 重量g)
```

```
云途美国运费 = 单价(RMB/KG) × 重量kg + 挂号费   （按 6 档重量）
产品成本     = 采购价 + 包装费1 + 运费
定价(CNY)    = 产品成本 / (0.85 − 0.50) = /0.35
美元定价     = 定价 / 6.7367 → 向上取 .99
```

**售价必须 ≥ $20**。不够就做多件装：`采购价×N`、`重量×N` 再算（`--pc 2`）。

云途美国费率：

| 重量g | 单价RMB/KG | 挂号费 |
|---|---|---|
| ≤100 | 84 | 23 |
| ≤200 | 79 | 21 |
| ≤450 | 76 | 19 |
| ≤700 | 75 | 19 |
| ≤2000 | 74 | 12 |
| ≤30000 | 69 | 12 |

---

## 七、变体维度（关键）

`variation_theme` 的 `maxItems` 是 1，但**name 可以是复合值**：

```
COLOR / SIZE / COLOR/SIZE / SIZE/COLOR / COLOR/SIZE/NUMBER_OF_ITEMS ...
```

⇒ **同款不同颜色 + 不同尺寸 = 一个父体，`COLOR/SIZE` 主题**。
不要把同款不同规格拆成多条独立链接——**会被 100730 判重复**。

---

## 八、踩过的坑

### LI-E01 · 100730 identical listing
同款不同规格拆成多条独立链接，第 3 条起被拒：
```
Your contribution was rejected because an identical listing with the same product details
```
**解法**：合并成一个父体，用 `COLOR/SIZE` 复合变体主题。

### LI-E02 · model_name 不能填中文
`100095 The value 'BJX-室内猫用睡袋' of the attribute 'Model Name' is not a valid value`
**解法**：用 `customs.nameEn`。

### LI-E03 · 颜色解析不能取末两字
ERP 属性值形如"冬季保暖兔绒猫窝猫睡袋"，直接取末两字会得到"睡袋"→ `100095`。
**解法**：颜色词典映射（灰/棕/绿/藏青…）+ 无法识别时兜底 `Beige`。

### LI-E04 · PET_BED_MAT 的隐藏必填
schema 只报 6 个 required，实际还要：`unit_count` / `directions` / `fill_material` / `item_shape` / `special_feature` / `breed_recommendation` / `specific_uses_for_product` / `item_length_width_thickness`。
同时 `handle` / `item_length_width` / `manufacturer_minimum_age` / `safety_warning` **不适用**，要排除。

---

## 九、用法

```bash
# 1. 先扫描候选（需要 Chrome CDP + erp_scan.py）
python erp_scan.py --limit 3000 --no-amz --any-battery --min-img 1 --exclude-apparel

# 2. 单个 SPU 上架
python scripts/erp_listing.py --src _spu_xxx.json --pt PET_BED_MAT --validate
python scripts/erp_listing.py --src _spu_xxx.json --pt PET_BED_MAT --submit
# 不足 $20 就加 --pc 2
```

---

## 十、已验证结果（2026-10-23）

| SPU | 售价 | 变体 | 结果 |
|---|---|---|---|
| HJZ20261017216 | $22.99 | Gray/Brown | ✅ DISCOVERABLE（B0HNX6LYDF / B0HNXG3MZT） |
| HJZ20261017215 | $51.99 | Green/Beige | ✅ ACCEPTED |
| HJZ20261017173 | $24.99 | Brown/Navy | ❌ 100730（应合并进同一父体） |
