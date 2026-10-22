# Amazon 美国站自动上架 Skill

> 竞品逆向 → 差异化文案 → 图片托管 → SP-API 提交。
> **AI 只做调度，正确性交给脚本。**

## 状态

| 项 | 状态 |
|---|---|
| 版本 | v0.1.0 |
| 实测案例 | 摩托腰带 SKU `MGB-1PC-BLK` → ASIN `B0HNVY631Q` |
| 已跑通 PT | `HARDWARE_HANDLE` |
| 仅支持 | **美国站**（CA/AU/MX 由跨站复制任务处理）|

## 快速开始

```bash
cd scripts
export GITHUB_TOKEN=...        # 如果走 GitHub 图床
PY="C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"

# ① 上传图片拿直链
"$PY" image_host.py upload-dir "D:/图/产品名" --prefix "english-slug"

# ② 组装 + 预校验（不创建）
"$PY" build_listing.py --input _product.json --validate

# ③ status=VALID 后正式提交
"$PY" build_listing.py --input _product.json --submit

# ④ 等 ASIN
"$PY" poll_asin.py --sku YOUR-SKU
```

## 目录

| 目录 | 内容 |
|---|---|
| `SKILL.md` | AI 执行入口（流程 + 硬规则）|
| `references/KNOWN_ISSUES.md` | ⭐ **踩坑清单，用前必读** |
| `references/FIELD_SPEC.md` | 各 PT 的字段格式 |
| `references/COMPLIANCE.md` | 文案禁词表 |
| `scripts/` | 可执行脚本 |
| `profiles/` | `fast`（快速铺货）/ `pro`（精做主推）|
| `templates/` | listing 模板 + 输入样例 |
| `docs/` | 案例与补充说明 |

## 两条路线

| profile | 适合 | 差异 |
|---|---|---|
| `fast` | 铺货、试款 | 跳过深度竞品分析，模板文案，只做必要校验 |
| `pro` | 主推款 | 全量竞品拆解、关键词反查、差异化文案、提交前人工确认 |

同一个代码库，`--profile fast|pro` 切换。**修 bug 两条路同时受益**（不用 cherry-pick）。

## 关键约束（血泪）

1. **`requirements` 必须是 `LISTING`** —— 写错会让所有产品字段被静默忽略
2. **提交前必须 `--validate`** —— VALIDATION_PREVIEW 是免费的 dry-run
3. **图片必须用 imgbb** —— jsDelivr 拉取经常超时（实测 34~50s）
4. **商品价 = 买家总价 − 运费** —— US 默认运费 $5.99
5. **遇错先 grep KNOWN_ISSUES** —— 不要盲试

## 密钥管理

- `config/image_host.json` **不进仓库**（已在 `.gitignore`）
- 首次使用：`cp config/image_host.json.example config/image_host.json`，填入自己的 key
- GitHub PAT 走环境变量 `GITHUB_TOKEN`

## 贡献约定

每次踩到新坑，**必须同时更新**：
1. `references/KNOWN_ISSUES.md` — 加一条 LI-XXX
2. `CHANGELOG.md` — 记一行

这是这个 skill 能持续变强的唯一方式。
