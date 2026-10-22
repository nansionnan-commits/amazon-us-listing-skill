# 图片托管方案（Amazon 上架用）

> **为什么需要这一步**：Amazon 创建 listing 时，图片字段 `media_location` 填的是**公网 HTTPS 直链**，Amazon 服务器自己去下载。本地文件、飞书链接都不行。

---

# 方案一：imgbb（已配好，立即可用）

## 状态：✅ **已配好并实测通过**

你的 API Key 已写入 `config/image_host.json`。

## 实测结果

```
上传 → https://i.ibb.co/Wvw3jCJT/test-a1.jpg
直链 HTTP 200 | image/jpeg | 1600×1600 | 四角 RGB(255,255,255) 纯白底
```

## 用法

```bash
cd D:/workbuddy-ml/D盘默认/sp-api
PY="C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"

# 单张上传
"$PY" image_host.py upload "D:/图片/beige_main.jpg"

# 整个变体目录批量上传（会写映射表）
"$PY" image_host.py upload-dir "D:/图片/加热围巾" --prefix "heated-scarf"

# 校验直链（尺寸 + 白底 + 可访问性）
"$PY" image_host.py check "https://i.ibb.co/xxx/a.jpg"

# 看已上传清单
"$PY" image_host.py list
```

上传结果自动写入 `sp-api/_image_urls.json`，格式：

```json
{
  "beige_main.jpg": "https://i.ibb.co/xxxx/beige-main.jpg",
  "beige_02.jpg": "https://i.ibb.co/yyyy/beige-02.jpg"
}
```

**listing 生成脚本会直接读这个文件**，不用你手动抄链接。

## 限制

| 项 | imgbb 免费版 |
|---|---|
| 每张大小 | ≤ 32MB（Amazon 上限 10MB，不冲突） |
| 总量 | 无明确上限，但官方保留调整权 |
| 有效期 | 默认永久 |
| 国内上传速度 | 一般（图片会先传海外） |

---

# 方案二：GitHub + jsDelivr（长期最稳，免费无限量）

## 为什么推荐

| 优点 | 说明 |
|---|---|
| **完全免费，无流量限制** | jsDelivr 是全球公益 CDN |
| **全球加速** | Amazon 从哪拉都很快 |
| **永久有效** | 只要仓库不删 |
| **可版本管理** | 图片有历史记录，误删能找回 |

## 保姆级步骤

### 第 1 步：注册 GitHub（已有可跳过）

1. 打开 **https://github.com/signup**
2. 填邮箱 → 设密码 → 设用户名（**记住用户名，后面要用**）
3. 验证邮箱

### 第 2 步：建一个 public 仓库

1. 登录后，点右上角 **「+」→ New repository**
2. **Repository name** 填：`listing-images`
3. 选 **Public**（⚠️ 必须 Public，Private 的 jsDelivr 拉不到）
4. 勾选 **Add a README file**
5. 点 **Create repository**

### 第 3 步：上传图片（两种方式，选一个）

#### 方式 A：网页上传（简单，适合少量）

1. 进入仓库，点 **Add file → Upload files**
2. 把图片文件夹**整个拖进去**（GitHub 支持拖拽目录）
3. 下面 **Commit changes** 框里随便写 `add images`
4. 点绿色 **Commit changes**

> ⚠️ 网页拖拽有数量限制（一次 100 个文件）。

#### 方式 B：命令行上传（推荐，适合批量）

```bash
# 1. 克隆仓库到本地
cd D:/workbuddy-ml/D盘默认
git clone https://github.com/你的用户名/listing-images.git

# 2. 把图片按"产品名"分目录放进去
#    listing-images/
#    ├── heated-scarf/
#    │   ├── beige_main.jpg
#    │   ├── beige_02.jpg
#    │   └── black_main.jpg
#    └── christmas-tree/
#        └── ...

# 3. 提交并推送
cd listing-images
git add .
git commit -m "add heated-scarf images"
git push
```

### 第 4 步：拿到 jsDelivr 直链

**直链格式（固定公式）：**

```
https://cdn.jsdelivr.net/gh/{你的用户名}/{仓库名}@{分支}/{文件路径}
```

**举例**：

假设你的用户名是 `zhangshuai`，仓库名 `listing-images`，文件放在 `heated-scarf/beige_main.jpg`

```
https://cdn.jsdelivr.net/gh/zhangshuai/listing-images@main/heated-scarf/beige_main.jpg
```

**把这个链接直接填进 listing 的 `media_location` 就行。**

### 第 5 步：验证链接能不能用

**方法 1：浏览器直接打开** —— 能看到图就说明通

**方法 2：用我们的脚本验证（推荐，会顺便查尺寸和白底）**

```bash
cd D:/workbuddy-ml/D盘默认/sp-api
PY="C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"
"$PY" image_host.py check "https://cdn.jsdelivr.net/gh/zhangshuai/listing-images@main/heated-scarf/beige_main.jpg"
```

输出里确认：
- `"ok": true`
- `"content_type": "image/jpeg"`
- `"long_side_ok": true`
- `"white_bg": true`（主图必须是）

### 第 6 步：让我接管（可选，一次配置）

把这两个信息告诉我：
- GitHub 用户名
- 仓库名

我填进 `config/image_host.json` 的 `github` 段，并设置 `default_provider: "github"`。

之后 `image_host.py` 会**自动走 GitHub 通道**（通过 GitHub API 上传），你不用手动 git push。

> 走这条路需要给我一个 **GitHub Personal Access Token**（classic，勾 `repo` 权限），设到环境变量 `GITHUB_TOKEN`。
> 你有 GitHub connector 已连，也可以直接让我用它上传。

---

## ⚠️ 常见问题

### Q1：jsDelivr 打不开 / 403

**原因**：仓库是 Private，或文件刚提交还没同步到 CDN。

**解法**：
1. 确认仓库是 **Public**
2. 等 1~5 分钟（CDN 有缓存同步延迟）
3. 访问 `https://cdn.jsdelivr.net/gh/用户名/仓库@main/文件` 手动刷一次

### Q2：图片更新了但链接还是旧的

**原因**：jsDelivr 有缓存。

**解法**：在 URL 后面加 `?v=2` 之类，或者用 commit hash 代替 `main`：
```
https://cdn.jsdelivr.net/gh/用户名/仓库@a1b2c3d/heated-scarf/beige_main.jpg
```

### Q3：Amazon 说图片拉不到

**检查清单**：
1. 链接必须是 **https**（http 不行）
2. 直链打开要**直接是图片**（不是网页）
3. 文件大小 ≤ **10MB**
4. 最长边 ≥ **1000px**
5. 主图必须**纯白底**、无文字水印

用 `image_host.py check` 一次全查。

### Q4：一个链接能长期用吗？

- **imgbb**：默认永久，但理论上有被清理风险
- **GitHub + jsDelivr**：只要仓库在就一直有效（**推荐长期用这个**）

---

# 两个方案怎么选

| 场景 | 用哪个 |
|---|---|
| 现在就想跑通流程、试 1~2 个品 | **imgbb**（已配好，直接用） |
| 长期做、图片会积累到几百上千张 | **GitHub + jsDelivr** |
| 两个都配 | 最好 —— `default_provider` 切换即可 |

---

# Amazon 图片硬要求（上传前自查）

| 要求 | 标准 |
|---|---|
| 主图背景 | **纯白 RGB(255,255,255)** |
| 主图占比 | 产品占画面 **85%** |
| 最小尺寸 | 最长边 **≥ 1000px**（建议 1600px 以上） |
| 格式 | JPEG / PNG / GIF / TIFF |
| 单文件 | ≤ 10MB |
| 主图禁止 | 无文字、无 logo、无水印、无边框、无道具 |
| 副图允许 | 可以有文字说明、场景、尺寸标注 |

`image_host.py check` 会自动验证：可访问性、Content-Type、尺寸、四角是否纯白。
