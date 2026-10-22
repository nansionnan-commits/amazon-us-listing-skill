#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把本地 skill 同步到 GitHub（绕过本机 git push 的 SSL 问题）

用法：
  export GITHUB_TOKEN=ghp_xxx
  python sync.py            # 推送所有改动
  python sync.py --check    # 只看差异，不推送

为什么不用 git push：
  本机直连 github.com 的 SSL 握手会失败（schannel handshake failed），
  但 api.github.com 是通的。所以走 Contents API 逐文件上传。

自动排除：
  .git / __pycache__ / config/image_host.json / *.pyc / 运行产物
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

OWNER = "nansionnan-commits"
REPO = "amazon-us-listing-skill"
BRANCH = "main"
ROOT = os.path.dirname(os.path.abspath(__file__))

# 永不推送
IGNORE_PATHS = {
    ".git", "__pycache__", ".DS_Store",
    "config/image_host.json",   # 密钥
}
IGNORE_SUFFIX = (".pyc", ".log")
IGNORE_PREFIX = ("_image_urls", "_listing_", "_product_", "_result_", "_poll_", "_imgs_")


def token():
    t = os.environ.get("GITHUB_TOKEN")
    if not t:
        print("❌ 未设置 GITHUB_TOKEN 环境变量")
        sys.exit(1)
    return t


def api(path, method="GET", body=None, tk=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"https://api.github.com{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {tk}",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json",
                 "User-Agent": "listing-skill-sync"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw.decode()) if raw else {}


def remote_sha(rel, tk):
    try:
        info = api(f"/repos/{OWNER}/{REPO}/contents/{rel}?ref={BRANCH}", tk=tk)
        return info.get("sha"), info.get("size")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        raise


def collect():
    out = []
    for dirpath, dirnames, files in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for f in files:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            if rel in IGNORE_PATHS or rel.endswith(IGNORE_SUFFIX):
                continue
            if os.path.basename(rel).startswith(IGNORE_PREFIX):
                continue
            out.append((rel, full))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只显示差异")
    ap.add_argument("--message", default="sync skill", help="提交信息")
    args = ap.parse_args()

    tk = token()
    files = collect()
    print(f"本地待检查 {len(files)} 个文件\n")

    pushed, skipped, fail = 0, 0, []
    for rel, full in files:
        try:
            content = base64.b64encode(open(full, "rb").read()).decode()
            sha, size = remote_sha(rel, tk)
            # 简单判重：本地字节数 vs 远程 size（对文本够用）
            local_size = os.path.getsize(full)
            if sha and size == local_size:
                skipped += 1
                continue
            if args.check:
                print(f"  🔄 有变化: {rel}")
                pushed += 1
                continue
            body = {"message": f"{args.message}: {rel}", "content": content, "branch": BRANCH}
            if sha:
                body["sha"] = sha
            api(f"/repos/{OWNER}/{REPO}/contents/{rel}", "PUT", body, tk=tk)
            print(f"  ✅ {rel}")
            pushed += 1
        except Exception as e:
            fail.append((rel, str(e)[:140]))
            print(f"  ❌ {rel}: {e}")

    print(f"\n{'待推送' if args.check else '已推送'} {pushed} | 未变化 {skipped} | 失败 {len(fail)}")
    if fail:
        for r, e in fail:
            print(f"  失败: {r} — {e}")
        return 2
    if not args.check and pushed:
        print(f"\n🔗 https://github.com/{OWNER}/{REPO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
