#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片托管上传工具（imgbb / GitHub+jsDelivr）

用法：
  # 上传单张
  python image_host.py upload "D:/图片/beige_main.jpg"

  # 上传整个变体目录（推荐）
  python image_host.py upload-dir "D:/图片/加热围巾" --prefix "heated-scarf"

  # 检查直链可访问性 + 尺寸合规（Amazon 要求）
  python image_host.py check "https://i.ibb.co/xxx/a.jpg"

  # 读回已上传结果
  python image_host.py list

输出：
  _image_urls.json  —— 文件名 → 直链 的映射，供 listing 生成器直接消费
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "..", "config", "image_host.json")
OUT_PATH = os.path.join(HERE, "_image_urls.json")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_out():
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_out(d):
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


# ---------------- imgbb ----------------

def imgbb_upload(path, cfg, name=None):
    key = cfg["imgbb"]["api_key"]
    endpoint = cfg["imgbb"]["endpoint"]
    raw = open(path, "rb").read()
    b64 = base64.b64encode(raw).decode()
    payload = {"image": b64}
    if name:
        payload["name"] = name
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(f"{endpoint}?key={key}", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode())
    if not d.get("success"):
        raise RuntimeError(f"imgbb 返回失败: {json.dumps(d, ensure_ascii=False)[:300]}")
    dd = d["data"]
    return {
        "url": dd.get("url"),
        "display_url": dd.get("display_url"),
        "thumb": (dd.get("thumb") or {}).get("url"),
        "delete_url": dd.get("delete_url"),
        "size": dd.get("size"),
        "provider": "imgbb",
    }


# ---------------- GitHub + jsDelivr ----------------

def github_upload(path, cfg, remote_path):
    """
    用 GitHub Contents API 上传。需要环境变量 GITHUB_TOKEN（有 repo 写权限）。
    remote_path 例：heated-scarf/beige_main.jpg
    """
    gh = cfg["github"]
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("未设置环境变量 GITHUB_TOKEN，无法走 GitHub 通道")
    if not gh.get("username") or not gh.get("repo"):
        raise RuntimeError("config/image_host.json 里 github.username / repo 未填")

    url = f"https://api.github.com/repos/{gh['username']}/{gh['repo']}/contents/{urllib.parse.quote(remote_path)}"
    raw = open(path, "rb").read()
    body = json.dumps({
        "message": f"upload {remote_path}",
        "content": base64.b64encode(raw).decode(),
        "branch": gh.get("branch", "main"),
    }).encode()

    # 若文件已存在，需要带 sha 才能覆盖
    try:
        req0 = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req0, timeout=30) as r:
            sha = json.loads(r.read().decode()).get("sha")
        if sha:
            body = json.dumps({
                "message": f"update {remote_path}",
                "content": base64.b64encode(raw).decode(),
                "branch": gh.get("branch", "main"),
                "sha": sha,
            }).encode()
    except urllib.error.HTTPError:
        pass  # 404 = 新文件，正常

    req = urllib.request.Request(url, data=body, method="PUT", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    cdn = gh["cdn_base"].format(
        username=gh["username"], repo=gh["repo"], branch=gh.get("branch", "main"))
    return {
        "url": cdn + remote_path,
        "size": len(raw),
        "provider": "github",
        "commit": (d.get("commit") or {}).get("sha"),
    }


# ---------------- 校验 ----------------

def check_url(url, cfg):
    """验证直链可访问 + Content-Type + 尺寸（若可解析）"""
    out = {"url": url, "ok": False}
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            out["http"] = r.status
            out["content_type"] = r.headers.get("Content-Type")
            out["bytes"] = len(data)
            out["ok"] = r.status == 200 and (out["content_type"] or "").startswith("image/")
    except Exception as e:
        out["error"] = str(e)[:200]
        return out

    # 尝试读尺寸（不装 PIL 也行，用简易 PNG/JPEG 解析）
    try:
        from PIL import Image  # noqa
        import io
        im = Image.open(io.BytesIO(data))
        out["width"], out["height"] = im.size
        out["format"] = im.format
        out["long_side_ok"] = max(im.size) >= cfg["constraints"]["amazon_min_long_side"]
        # 主图白底检查（取四角像素）
        rgb = im.convert("RGB")
        w, h = rgb.size
        corners = [rgb.getpixel(p) for p in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]]
        out["corners"] = corners
        out["white_bg"] = all(min(c) >= 245 for c in corners)
    except ImportError:
        out["note"] = "未装 Pillow，跳过尺寸/白底检查（pip install pillow 可启用）"
    except Exception as e:
        out["note"] = f"尺寸解析失败: {str(e)[:120]}"
    return out


# ---------------- 命令 ----------------

def cmd_upload(args):
    if not args:
        print("用法: image_host.py upload <文件路径> [远程文件名]"); return 1
    path = args[0]
    name = args[1] if len(args) > 1 else os.path.splitext(os.path.basename(path))[0]
    cfg = load_config()
    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}"); return 1
    use_gh = cfg.get("default_provider") == "github" and cfg["github"].get("username")
    remote = f"{name}{os.path.splitext(path)[1]}"
    try:
        if use_gh:
            r = github_upload(path, cfg, remote)
        else:
            r = imgbb_upload(path, cfg, name)
    except Exception as e:
        print(f"❌ 上传失败: {e}"); return 2
    print(f"✅ {os.path.basename(path)}  [{r['provider']}]")
    print(f"   url: {r['url']}")
    store = load_out()
    store[remote if use_gh else os.path.basename(path)] = r["url"]
    save_out(store)
    return 0


def cmd_upload_dir(args):
    if not args:
        print("用法: image_host.py upload-dir <目录> [--prefix 前缀]"); return 1
    d = args[0]
    prefix = ""
    if "--prefix" in args:
        prefix = args[args.index("--prefix") + 1]
    if not os.path.isdir(d):
        print(f"❌ 目录不存在: {d}"); return 1
    cfg = load_config()
    exts = {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff"}
    files = sorted(f for f in os.listdir(d) if os.path.splitext(f)[1].lower() in exts)
    if not files:
        print(f"❌ 目录里没有图片: {d}"); return 1
    print(f"待上传 {len(files)} 张")
    store = load_out()
    ok, fail = 0, []
    for f in files:
        p = os.path.join(d, f)
        remote = f"{prefix}/{f}" if prefix else f
        if cfg.get("default_provider") == "github" and cfg["github"].get("username"):
            try:
                r = github_upload(p, cfg, remote)
            except Exception as e:
                fail.append((f, f"github: {e}"))
                print(f"  ❌ {f}: {e}")
                continue
        else:
            try:
                r = imgbb_upload(p, cfg, os.path.splitext(f)[0])
            except Exception as e:
                fail.append((f, f"imgbb: {e}"))
                print(f"  ❌ {f}: {e}")
                continue
        store[remote] = r["url"]
        ok += 1
        print(f"  ✅ {f} → {r['url']}")
    save_out(store)
    print(f"\n完成：成功 {ok} / 失败 {len(fail)}")
    print(f"映射已写入 {OUT_PATH}")
    if fail:
        for f, e in fail:
            print(f"  失败: {f} — {e}")
    return 0 if not fail else 2


def cmd_check(args):
    if not args:
        print("用法: image_host.py check <url>"); return 1
    cfg = load_config()
    r = check_url(args[0], cfg)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r.get("ok") else 2


def cmd_list(_args):
    store = load_out()
    if not store:
        print("还没有上传记录"); return 0
    print(f"已上传 {len(store)} 张：")
    for k, v in store.items():
        print(f"  {k}\n    {v}")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    cmd, args = sys.argv[1], sys.argv[2:]
    return {
        "upload": cmd_upload,
        "upload-dir": cmd_upload_dir,
        "check": cmd_check,
        "list": cmd_list,
    }.get(cmd, lambda _: print(f"未知命令: {cmd}") or 1)(args)


if __name__ == "__main__":
    sys.exit(main())
