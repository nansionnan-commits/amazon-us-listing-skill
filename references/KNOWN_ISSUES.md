# KNOWN ISSUES — 踩过的坑（持续更新）

> **用前必读。遇到报错先在这里 grep，不要盲试。**
> 格式：现象 → 根因 → 解法。每条都标注首次遇到的日期。

---

## LI-001 · `requirements` 写错导致所有字段被静默忽略
**日期**：2026-10-22　**严重度**：🔴 高

**现象**：`VALIDATION_PREVIEW` 返回 15 个 WARNING，全是 `90000900 xxx does not belong or is no longer applicable`，涉及 `brand` / `item_name` / `bullet_point` / `main_product_image_locator` 等基础字段。

**根因**：payload 里写了 `"requirements": "LISTING_OFFER_ONLY"`。该 PT 的 `requirements` 是 `LISTING`，模式不匹配时 Amazon 认为整个 payload 的字段都不属于这个 PT。

**解法**：`"requirements": "LISTING"`

**验证方法**：从 `GET /definitions/2020-09-01/productTypes/{pt}` 的响应里读 `requirements` 字段，照抄。

---

## LI-002 · HARDWARE_HANDLE 的 6 个 required 字段
**日期**：2026-10-22

**必需**：
```
brand / bullet_point / country_of_origin / item_name / product_description / supplier_declared_dg_hz_regulation
```

**其中容易漏的两个**：

| 字段 | 格式 |
|---|---|
| `country_of_origin` | `[{"value":"CN","marketplace_id"}]` — 两位国家码，`CN` 在 268 个国家码枚举里 |
| `supplier_declared_dg_hz_regulation` | `[{"value":"not_applicable","marketplace_id"}]` — 枚举：ghs / not_applicable / other / storage / transportation / unknown / waste |

---

## LI-003 · 另有 6 个"隐性必填"（不报 required 但校验报 90220）
**日期**：2026-10-22

补齐 6 个 required 后，仍报：
```
90220 'Model Number' is required but missing        → model_number
90220 'Handle Type' is required but missing          → handle
90220 'Manufacturer' is required but missing         → manufacturer
90220 'Included Components' is required but missing  → included_components
90220 'Item Width Unit' is required but missing      → item_length_width
90220 'Model Name' is required but missing           → model_name
```

**格式**：
```
model_number            : [{"value":str,"marketplace_id"}]            ← 无 language_tag
model_name              : [{"language_tag","value","marketplace_id"}]
manufacturer            : [{"language_tag","value","marketplace_id"}]
included_components     : [{"language_tag","value","marketplace_id"}]
handle                  : [{"material":[{"language_tag","value"}],
                            "type":[{"language_tag","value"}],"marketplace_id"}]
item_length_width       : [{"length":{"value":9.84,"unit":"inches"},
                            "width":{"value":6.69,"unit":"inches"},"marketplace_id"}]
```
- `handle.material.value` / `handle.type.value` 是**自由文本**（无枚举）
- `item_length_width` 的 unit **只能是 `inches`**，传 centimeters 会失败

---

## LI-004 · jsDelivr 拉图超时 → 上架必须用 imgbb
**日期**：2026-10-22　**严重度**：🔴 高

**现象**：
```
"code":"InvalidInput",
"message":"Unable to Retrieve Media Content for URL 'Media Download Timed Out from Server': https://cdn.jsdelivr.net/..."
```

**根因**：实测 jsDelivr 拉 7 张图，多次出现 34s / 40s / 50s 超时，甚至 `Remote end closed connection`。Amazon 侧拉取同样超时。

**解法**：
- **listing 的 `media_location` 一律用 imgbb 直链**（`https://i.ibb.co/xxx/yyy.jpg`）
- jsDelivr 只用于**备份/长期存档**，不要用于上架
- 上传后必须用 `image_host.py check <url>` 验证 HTTP 200 + Content-Type + 尺寸

---

## LI-005 · `includedData` 不支持 `images` 值
**日期**：2026-10-22

**现象**：`GET /catalog/2022-04-01/items/{asin}` 返回
```
400 InvalidInput: Invalid 'includedData' provided: 'images'.
```

**解法**：合法值用 `summaries,attributes,offers,relationships,productTypes,salesRanks`。图片通过 `attributes.main_product_image_locator` 拿。

---

## LI-006 · 图片 URL 必须是公网直链
**日期**：2026-10-22

**现象/根因**：
- 本地文件路径 ❌ Amazon 访问不到
- 飞书云盘链接 ❌ 是网页不是图片直链
- 需要 `https://` 直接返回 `image/jpeg` 的地址

**解法**：用 imgbb 或 GitHub+jsDelivr（后者不稳定，见 LI-004）。

---

## LI-007 · 中文/空格路径必须 URL 编码
**日期**：2026-10-22

**现象**：`https://cdn.jsdelivr.net/.../544 摩托腰带/A1.jpg` → Python urllib 报 `URL can't contain control characters`；Amazon 侧也可能解析失败。

**解法**：
- URL 编码后可用：`544%20%E6%91%A9%E6%89%98%E8%85%B0%E5%B8%A6/A1.jpg`
- **但规范做法是仓库路径只用** `小写字母 / 数字 / - / _`
- 例：`544-moto-belt/A1_main.jpg`

---

## LI-008 · `100521` 不是错误，是新品审核
**日期**：2026-10-22

**现象**：
```
status: DISCOVERABLE
offers: []
fulfillment: []
issues: [{"severity":"ERROR","code":"100521",
  "message":"We are reviewing this listing to determine if any additional information is required.
             Please allow up to 48 hours..."}]
```

**根因**：Amazon 新品/新品牌/新类目审核流程。

**解法**：
- **不要重试、不要修改、不要重复提交**
- 等 24~48 小时
- 期间 offer（价格/库存）不会生效，标题/主图也可能暂不索引
- 48h 后仍未放行 → 后台「库存 → 管理库存」看是否有补资料提示

---

## LI-009 · `VALIDATION_PREVIEW` 是免费的 dry-run
**日期**：2026-10-22　**严重度**：⭐ 重要技巧

**用法**：
```
PUT /listings/2021-08-01/items/{sellerId}/{sku}?marketplaceIds=US&mode=VALIDATION_PREVIEW
```

**好处**：完整跑一遍校验（包括图片是否能拉、字段是否合规），**但不创建 listing**。

**判读**：
- `status: VALID` → 可以正式提交
- `status: INVALID` + issues → 按 issues 修
- 有 WARNING 但 VALID → 可以提交，被忽略的字段会在日志里提示

---

## LI-010 · 拉 PT schema 看 required 的正确姿势
**日期**：2026-10-22

**两步**：
```python
# ① 拿 PT 元信息
GET /definitions/2020-09-01/productTypes/{pt}?marketplaceIds=US&requirements=LISTING&locale=en_US
# → 响应里 schema 是 {"link": {"resource": "<S3 presigned URL>"}}，不是直接内容！

# ② 下载 schema
urllib.request.urlopen(r['schema']['link']['resource'])
# → 里面有 properties（全部字段）和 required（必填）
```

**坑**：`r['schema']['link']` 是 **dict** 不是字符串，直接当 URL 用会报 `unknown url type: {'resource'`。

---

## LI-011 · SKU 必须带 `sku`（广告侧同理）
**日期**：2026-10-21

**说明**：建 productAd 时只给 `asin` 会报 `merchantSku is empty`；listing 侧绑产品也要 sku。
**ASIN → SKU 反查**：
```python
GET /listings/2021-08-01/items/{sellerId}?marketplaceIds=US&pageSize=20&includedData=summaries
# 翻页找 summaries.asin == target，取 item.sku
```

---

# 已确认的能力边界

| 项 | 结论 |
|---|---|
| UPC | 本店（zhangaodi US）已开 GTIN 豁免，`supplier_declared_has_product_identifier_exemption: true` 即可，不需要真实 UPC |
| 配送模板 | US 默认 `a08cfb00-f40d-4cbd-a231-51d5f48f37d9`，**已设 $5.99 运费** |
| 商品价算法 | **商品价 = 买家总价 − $5.99** |
| 品牌 | 张奥迪 US = `EAOEIHD`；其他站点/店铺 = `Generic` |
| ASIN 生成时间 | 3~10 分钟 |
| BUYABLE 时间 | ASIN 生成后 30~60 分钟（审核通过后）|

---

## LI-012 · 飞书 Base 作为输入源时的字段坑
**日期**：2026-10-22

### 坑 1：`--app-token` 是错参数
正确是 `--base-token`。

### 坑 2：`+record-list` 默认输出 ndjson 到文件
不写 `--format json` 的话，stdout 只是 manifest 摘要，真数据在 `.ndjson` 文件里。

### 坑 3：`--format json` 返回矩阵，列序不可信
`data.data` 是数组的数组，但顺序**不等于** manifest `columns` 的顺序。必须按内容语义映射：

| 位置 | 实际字段 | 典型值 |
|---|---|---|
| 0 | 日期 | `2026-10-22T00:00:00+08:00` |
| 1 | 核心词/产品名 | `Unisex Lightweight Chest Bag` |
| 2 | 附图+视频文件包 | 附件数组 |
| 3 | 主图 | 附件数组 |
| 4 | 空 | null |
| 5 | 价格 | 截图附件 |
| 6 | 备注 | 文本或 null |
| 7 | 参考链接 | Amazon URL |
| 8 | 姓名 | `[{id, name}]` |
| 9 | SKU登记 | `QBB20261015106` |
| 10 | 关键词 | 空格分隔 |

### 坑 4：`+field-list` 返回 `data.fields` 不是 `data.items`

### 坑 5：**上传后必须回填「上传了吗」**
- 字段 `上传了吗`（select），选项 `已传` / `没有`
- 不回填会导致下次重复上架
- 命令见下方
```bash
lark-cli base +record-batch-update --base-token <token> --table-id <tid> \
  --json '{"update_records":{"<record_id>":{"上传了吗":["已传"]}}}'
```

### 坑 6：老板本人的记录要跳过
`姓名` 为 **杨梓杭**（openId `ou_d419c611863df62de469e69ebe5160cc`）的记录 = 已上传过，跳过。

---

## LI-013 · 图床：raw.githubusercontent.com 才是 Amazon 能拉的那个
**日期**：2026-10-22　**严重度**：🔴 高（覆盖 LI-004 的结论）

同一批图实测：

| 图床 | 本地 check | Amazon 能否拉取 |
|---|---|---|
| `i.ibb.co` | ✅ 200 | ❌ `Unable to Download from Server`（当天传 14 张后失效，疑限流）|
| `cdn.jsdelivr.net` | ✅ 200（偶发 34~50s） | ❌ 失败 |
| **`raw.githubusercontent.com`** | ✅ 200 | ✅ **成功，status=VALID** |

**结论**：
```
首选 https://raw.githubusercontent.com/{owner}/{repo}/main/{path}
```
- imgbb 作本地预览/备份，不保证 Amazon 能拉
- jsDelivr 不要用于 listing 的 `media_location`

**排查顺序**：本地 200 但 Amazon 报错 → 直接换图床，不要折腾图片格式。

**补充**：PNG（980KB）在 imgbb 失败，转 JPG（166KB）同样失败 → 证明是图床问题不是格式问题。
