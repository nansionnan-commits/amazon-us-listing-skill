#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SKU 归属台账 —— 保证「多维表格上架」与「ERP 上架」两条流程互不覆盖

背景：
  - 流程 A（base）：飞书多维表格 → _product_*.json → build_listing.py
  - 流程 B（erp） ：兰谷 ERP    → _spu_*.json     → erp_listing.py
  两条流程共用同一个 Amazon 卖家账号，如果 SKU 撞车，后提交的会覆盖前一条 listing。

机制：
  1. claim()  —— 提交前登记 SKU 归属；若该 SKU 已被【另一条流程】占用，拒绝
  2. release() —— 需要接管时显式释放（必须人工确认）
  3. 台账文件：config/sku_ledger.json

用法（脚本内）：
  from listing_guard import guard
  guard.claim(sku, source="base")     # 撞车会抛 SkuConflict
  guard.record(sku, source="base", asin="B0...", price=14.0)   # 提交成功后回写
"""
import json
import os
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = os.path.join(ROOT, "config", "sku_ledger.json")

SOURCES = {"base": "多维表格", "erp": "ERP兰谷", "cross": "跨站复制", "manual": "手工"}
_LOCK = threading.Lock()


class SkuConflict(Exception):
    """SKU 已被另一条流程占用"""


def _load():
    if not os.path.exists(LEDGER):
        return {"_desc": "SKU 归属台账：防止不同上架流程互相覆盖", "skus": {}}
    try:
        with open(LEDGER, encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("skus", {})
        return d
    except (json.JSONDecodeError, OSError):
        return {"_desc": "SKU 归属台账（读取失败，已重建）", "skus": {}}


def _save(d):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, LEDGER)


def claim(sku, source, force=False):
    """
    提交前登记。

    ⚠️ SKU 是通用的（都来自 ERP），同一个 SKU 就是一个产品。
    所以撞车规则不看「哪条流程」，只看「这个 SKU 是否已经上过」：

      - 台账里没有                → 通过（首次上架）
      - 台账里有，force=False     → 抛 SkuConflict（拒绝重复上架 = 拒绝覆盖）
      - 台账里有，force=True      → 通过（显式更新，需人工确认后加 --force）

    source 只用于记录「这次是谁上的」，不参与放行判断。
    """
    if source not in SOURCES:
        raise ValueError(f"source 必须是 {list(SOURCES)}，收到 {source}")
    with _LOCK:
        d = _load()
        rec = d["skus"].get(sku)
        if rec and not force:
            raise SkuConflict(
                f"SKU {sku} 已经上架过（来源【{SOURCES.get(rec['source'], rec['source'])}】"
                f" / ASIN {rec.get('asin') or '待分配'} / 首次 {rec.get('created_at', '?')}）。"
                f"重复提交会覆盖现有 listing。确需更新请加 --force（并确认是同一个产品）。"
            )
        d["skus"][sku] = {
            **({"created_at": rec["created_at"]} if rec else {"created_at": time.strftime("%Y-%m-%d %H:%M:%S")}),
            "source": source,
            "asin": (rec or {}).get("asin"),
            "price": (rec or {}).get("price"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        _save(d)
        return True


def record(sku, source, asin=None, price=None, status=None):
    """提交成功后回写结果"""
    with _LOCK:
        d = _load()
        rec = d["skus"].get(sku) or {"created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "source": source}
        if asin:
            rec["asin"] = asin
        if price is not None:
            rec["price"] = price
        if status:
            rec["status"] = status
        rec["source"] = rec.get("source") or source
        rec["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        d["skus"][sku] = rec
        _save(d)


def release(sku, confirm=False):
    """释放占用（接管前必须人工确认）"""
    if not confirm:
        raise RuntimeError(f"释放 {sku} 需要 confirm=True，且应人工确认后再执行")
    with _LOCK:
        d = _load()
        old = d["skus"].pop(sku, None)
        _save(d)
        return old


def owner(sku):
    """查 SKU 归属，返回 (source, record) 或 (None, None)"""
    return (lambda r: (r.get("source"), r) if r else (None, None))(_load()["skus"].get(sku))


def by_source(source):
    """列出某条流程已占用的所有 SKU"""
    return {k: v for k, v in _load()["skus"].items() if v.get("source") == source}


def summary():
    d = _load()
    out = {}
    for sku, v in d["skus"].items():
        s = v.get("source", "?")
        out.setdefault(s, []).append(sku)
    return {SOURCES.get(k, k): len(v) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        d = _load()
        print(f"台账共 {len(d['skus'])} 个 SKU")
        for src, n in summary().items():
            print(f"  {src}: {n}")
        for sku, v in list(d["skus"].items())[:20]:
            print(f"  {sku:<28} {v.get('source'):<6} {v.get('asin') or '-':<12} {v.get('price') or '-'}")
    else:
        print(__doc__)
