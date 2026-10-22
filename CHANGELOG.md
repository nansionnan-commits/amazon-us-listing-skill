# CHANGELOG

## v0.1.0 — 2026-10-22
**首个可用版本**，基于摩托腰带（SKU `MGB-1PC-BLK` / ASIN `B0HNVY631Q`）全流程实测。

### 已实现
- 竞品数据抓取（Catalog API）
- 差异化文案生成（标题 3 版 / 五点 / HTML 长描述）
- 图片托管（imgbb 主用 / GitHub+jsDelivr 备用）
- PT schema 拉取 + 必填字段推断
- `VALIDATION_PREVIEW` 预校验
- 正式提交 + ASIN 轮询

### 已收录的坑（11 条）
见 `references/KNOWN_ISSUES.md`

### 待办
- [ ] `fetch_competitor.py` 脚本化（目前是内联代码）
- [ ] 多 PT 支持（BLANKET / MOTORCYCLE_ACCESSORY 等）
- [ ] 变体（父子结构）支持
- [ ] fast / pro profile 的实际逻辑分支
- [ ] 失败自动重试（图片拉取超时类）
