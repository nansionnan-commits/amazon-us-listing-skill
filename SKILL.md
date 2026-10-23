---
name: amazon-us-listing
description: 亚马逊美国站新品自动上架（竞品逆向 → 差异化文案 → 图片托管 → SP-API 提交）。当老板给一个竞品 ASIN + 变体/价格 + 图片，要求"上架/开新品/做个类似的品"时触发。含 VALIDATION_PREVIEW 预校验、PT schema 字段规范、踩坑清单。
---

# Amazon 美国站自动上架

> **核心原则：AI 只做调度，正确性交给脚本。**
> 不许自己拼字段名、不许绕过校验、不许在报错上盲试。

---

## 何时用这个 skill

| 触发场景 | 示例 |
|---|---|
| ✅ **用** | "给 B0XXXX 这个竞品开个新品"、"上架这个摩托腰带"、"照这个做一个" |
| ✅ **用（ERP 数据源）** | "从 ERP 挑品上架"、"按 ERP 已完成的产品上架" → 见 `docs/erp-source.md` |
| ❌ **不用** | 跟卖（用 Sell on Amazon）、跨站复制（用 `amazon-us-to-ca/au/mx-listing`）、改已有 listing |

**只做美国站。** CA/AU/MX 由 `amazon-us-to-*-listing` 三个定时任务自动复制，不要在这里做。

---

## 两条数据源通道

| 数据源 | 入口 | 说明 |
|---|---|---|
| 老板给竞品 ASIN + 图片目录 | `scripts/build_listing.py` | 主流程，手工收集输入 |
| **公司 ERP（兰谷）批量选品** | `scripts/erp_listing.py` + `docs/erp-source.md` | 自动抓数据 / 算价 / 图片转换 |

ERP 通道要点（详见 `docs/erp-source.md`）：
- 只做 `productStatus=5`（已完成）；判状态前先调 `statisticsCount` 对账，别猜
- 售价必须 **≥ $20**（`calc_price.py` 云途美国 50% 利润率 + 向上取 .99）；不够就做多件装 `--pc 2`
- 图片：alicdn 直接用；ERP 图要下载后传 imgbb
- **同款不同规格必须合并成一个父体**（`COLOR/SIZE` 复合变体主题）——拆成多条独立链接会被 `100730` 拒

### 两条通道互不覆盖（`scripts/listing_guard.py`）

两条流程共用同一个卖家账号，**唯一风险是 SKU 撞车导致后提交覆盖前一条**。闸门在提交层：

```python
import listing_guard as _lg

_lg.claim(sku, source="base")    # 或 "erp"、"cross"；跨流程撞车抛 SkuConflict
# ... 提交 ...
_lg.record(sku, "base", asin=..., price=...)   # 成功后回写台账
```

| 情况 | 行为 |
|---|---|
| 台账里没有该 SKU | 登记通过 |
| 台账有，**同一 source** | 通过（自己更新自己） |
| 台账有，**不同 source** | **拒绝提交**，提示被哪条流程占用 |

台账文件：`config/sku_ledger.json`。强制接管要 `_lg.release(sku, confirm=True)`，且必须人工确认。

**已自动接入**：`build_listing.py` 的 `submit()`（source 取自 product JSON 的 `source` 字段，默认 `base`）、`erp_listing.py` 的提交循环（固定 `erp`）。

---

## 执行流程（严格按顺序）

### 第 0 步：读文档（每次必做，不许跳过）

```
references/KNOWN_ISSUES.md      ← 先看有没有已知坑
references/FIELD_SPEC.md        ← 当前 PT 的字段规范
references/COMPLIANCE.md        ← 禁词表
```

### 第 1 步：收集输入（缺一不可）

| 输入 | 必需 | 说明 |
|---|---|---|
| 竞品 ASIN | ✅ | 1~3 个，用于文案差异化 |
| 变体 | ✅ | 单款 / 多色 / 多码；写清变体名 |
| 售价 | ✅ | **商品价 = 买家总价 − 运费**（US 默认运费 $5.99）|
| 品牌 | ✅ | 张奥迪 US = `EAOEIHD`；其他一律 `Generic` |
| 图片目录 | ✅ | 本地文件夹，脚本自动传图床 |
| 尺寸/重量 | ✅ | 包装长宽高 cm + kg |
| 划线价 | 可选 | 建议零售价的 1.7 倍左右 |

**缺任何一项 → 停下来问老板，不要猜。**

### 第 2 步：抓竞品 + 出文案

```bash
python scripts/fetch_competitor.py --asin B0XXXXXXXX
```

脚本会输出竞品标题/五点/描述/属性/装量。**人工（AI）基于它写差异化文案**：

- 学**结构**，不抄词
- 找评分最高但**卖点没讲透**的地方切入
- 所有承诺必须有实据，不编认证/功效/销量

### 第 3 步：图片上传

```bash
export GITHUB_TOKEN=...   # 或走 imgbb
python scripts/image_host.py upload-dir "D:/图/产品名" --prefix "english-slug"
```

⚠️ **Amazon listing 的图片必须用 imgbb**（jsDelivr 拉取经常超时，见 KNOWN_ISSUES #4）

### 第 4 步：组装 + 预校验（关键门禁）

```bash
python scripts/build_listing.py --input _product.json --validate
```

**必须 status = VALID 才能继续。** 有 ERROR 就按 KNOWN_ISSUES 修，不要硬提。

### 第 5 步：正式提交

```bash
python scripts/build_listing.py --input _product.json --submit
```

期望返回 `status: ACCEPTED`。

### 第 6 步：轮询 ASIN + 记录

```bash
python scripts/poll_asin.py --sku MGB-1PC-BLK
```

- ASIN 通常 **1~10 分钟**生成
- 生成后状态多为 `DISCOVERABLE`
- 若带 `100521` 错误 → **Amazon 新品审核，最多 48h，正常，不要重试**

---

## 硬规则（违反必出错）

| # | 规则 |
|---|---|
| 1 | **`requirements` 必须是 `LISTING`**，绝不能写 `LISTING_OFFER_ONLY`（会让所有产品字段被静默忽略）|
| 2 | **提交前必须跑 `--validate`**，不许跳过 |
| 3 | **字段名只能来自 `FIELD_SPEC.md`**，不许自创 |
| 4 | **商品价 = 总价 − 运费**，US 默认运费 $5.99 |
| 5 | `item_length_width` 的 unit **只能是 inches** |
| 6 | 新 PT 第一次用，**必须先拉 schema 看 required** |
| 7 | 报错第一反应是 **grep KNOWN_ISSUES**，不是改代码重试 |
| 8 | 同一报错**连续 2 次**未解决 → 停下报告老板，附完整报错原文 |

---

## 目录说明

```
scripts/      可执行脚本（AI 只调这些）
references/   文档（AI 每次必读）
profiles/     fast / pro 两套参数
templates/    listing 模板 + 输入样例
docs/         补充说明
```

---

## 版本

见 `CHANGELOG.md`。**每次踩到新坑，必须同时更新 `KNOWN_ISSUES.md` 和 `CHANGELOG.md`。**
