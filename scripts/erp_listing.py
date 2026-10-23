# -*- coding: utf-8 -*-
"""ERP SPU 一键上架：自动处理图片（ERP图→imgbb）、算价、变体、校验、提交

用法：
  python process_spu.py --src _spu_xxx.json --pt PET_BED_MAT --validate
  python process_spu.py --src _spu_xxx.json --pt PET_BED_MAT --submit
"""
import argparse
import base64
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth
from calc_price import price_50_usd, to_dot99

MP = "ATVPDKIKX0DER"
LANG = "en_US"
CTX = ssl._create_unverified_context()
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(_ROOT, "config", "image_host.json"), encoding="utf-8"))
IMGBB_KEY = CFG["imgbb"]["api_key"]
SHIP_GROUP = "a08cfb00-f40d-4cbd-a231-51d5f48f37d9"

COLOR_MAP = {"绿": "Green", "灰": "Gray", "棕": "Brown", "藏青": "Navy Blue", "黑": "Black",
             "白": "White", "米": "Beige", "粉": "Pink", "红": "Red", "蓝": "Blue",
             "咖": "Brown", "黄": "Yellow", "紫": "Purple"}


def L(v):
    return [{"language_tag": LANG, "value": v, "marketplace_id": MP}]


def N(v):
    return [{"value": v, "marketplace_id": MP}]


def upload_imgbb(local_bytes):
    body = urllib.parse.urlencode({"key": IMGBB_KEY,
                                   "image": base64.b64encode(local_bytes).decode()}).encode()
    req = urllib.request.Request("https://api.imgbb.com/1/upload", data=body, method="POST")
    r = json.loads(urllib.request.urlopen(req, timeout=90, context=CTX).read())
    if not r.get("success"):
        raise RuntimeError(f"imgbb fail: {r}")
    return r["data"]["url"]


def fix_img(url):
    """ERP 图：下载 → 上传 imgbb → 返回新直链；alicdn 原样返回。"""
    if "alicdn" in url:
        return url
    p = urllib.parse.urlsplit(url)
    enc = urllib.parse.urlunsplit((p.scheme or "https", p.netloc, urllib.parse.quote(p.path), p.query, ""))
    try:
        data = urllib.request.urlopen(enc, timeout=40, context=CTX).read()
        return upload_imgbb(data)
    except Exception as e:
        print(f"    ! 图片处理失败 {os.path.basename(p.path)}: {e}")
        return None


def parse_variants(spu):
    """从 skuList 解析出变体；返回 [(sku, color, size)]"""
    out = []
    for s in spu.get("skuList") or []:
        attrs = json.loads(s["attributes"]) if isinstance(s.get("attributes"), str) else (s.get("attributes") or [])
        color, size = None, None
        for a in attrs:
            v = str(a.get("value") or "")
            if any(ch.isdigit() for ch in v[:2]) and ("*" in v or "x" in v.lower() or "cm" in v.lower()):
                size = v
            else:
                for cn, en in COLOR_MAP.items():
                    if cn in v:
                        color = en
                        break
                if not color and v:
                    color = v.strip()[-2:] if len(v) > 8 else v
        # 颜色名兜底：解析出的不是颜色（如"睡袋""猫窝"）就按默认色处理
        if color and (len(color) > 7 or any(k in str(color) for k in ("睡", "窝", "垫", "袋", "款"))):
            color = "Beige"
        out.append({"sku": s, "color": color or "Standard", "size": size or ""})
    # 若颜色重复，用序号区分
    seen = {}
    for x in out:
        c = x["color"]
        seen[c] = seen.get(c, 0) + 1
        if seen[c] > 1:
            x["color"] = f"{c} {seen[c]}"
    return out


def build(spu, pt, price_usd, parent_sku, variant_theme="COLOR"):
    d = spu.get("description") or {}
    bullets = [d.get(f"point{i}") for i in range(1, 6)]
    bullets = [b for b in bullets if b]
    name_en = (spu.get("customs") or {}).get("nameEn") or "Pet Product"
    title = spu["_title"]
    desc = (d.get("description") or "").replace("\n", "<br>")
    variants = parse_variants(spu)
    material = (spu.get("customs") or {}).get("materialEn") or "Polyester"

    def base(is_parent):
        return {
            "brand": L("EAOEIHD"),
            "item_name": L(title),
            "bullet_point": [{"language_tag": LANG, "value": b, "marketplace_id": MP} for b in bullets],
            "product_description": L(desc),
            "country_of_origin": N("CN"),
            "supplier_declared_dg_hz_regulation": N("not_applicable"),
            "variation_theme": [{"name": variant_theme}],
            "parentage_level": N("parent" if is_parent else "child"),
            "batteries_required": N(False),
        }

    tasks = [(parent_sku, {"productType": pt, "requirements": "LISTING", "attributes": base(True)}, "父体")]
    for v in variants:
        s = v["sku"]
        imgs = []
        for im in sorted(s.get("imageList") or [], key=lambda z: z.get("sort", 0)):
            u = fix_img(im.get("imageUrl") or "")
            if u:
                imgs.append(u)
            if len(imgs) >= 7:
                break
        if not imgs:
            raise RuntimeError(f"{s['skuCode']} 没有可用图片")
        a = base(False)
        a.update({
            "child_parent_sku_relationship": [{"child_relationship_type": "variation",
                                               "parent_sku": parent_sku, "marketplace_id": MP}],
            "color": L(v["color"]),
            "material": L(material),
            "model_number": N(s["skuCode"]),
            "model_name": L(name_en),
            "manufacturer": L("EAOEIHD"),
            "part_number": N(s["skuCode"]),
            "number_of_boxes": N(1),
            "unit_count": [{"value": 1, "type": {"language_tag": LANG, "value": "Count"}, "marketplace_id": MP}],
            "directions": L("Place on a flat indoor surface. Spot clean with a damp cloth or hand wash."),
            "fill_material": L(material),
            "item_shape": L("Enclosed Cave"),
            "special_feature": L("Enclosed hooded design; soft plush trim; easy to clean"),
            "breed_recommendation": L("Small Breeds, Medium Breeds"),
            "specific_uses_for_product": L("Indoor, Sleeping, Anxiety Relief"),
            "item_length_width_thickness": [{
                "length": {"value": float(s["length"]), "unit": "centimeters"},
                "width": {"value": float(s["width"]), "unit": "centimeters"},
                "thickness": {"value": float(s["height"]), "unit": "centimeters"},
                "marketplace_id": MP}],
            "included_components": L(f"1 x {name_en}"),
            "supplier_declared_has_product_identifier_exemption": N(True),
            "condition_type": N("new_new"),
            "number_of_items": N(1),
            "item_package_dimensions": [{
                "length": {"value": float(s["length"]), "unit": "centimeters"},
                "width": {"value": float(s["width"]), "unit": "centimeters"},
                "height": {"value": float(s["height"]), "unit": "centimeters"},
                "marketplace_id": MP}],
            "item_package_weight": [{"value": float(s["weight"]), "unit": "kilograms", "marketplace_id": MP}],
            "purchasable_offer": [{"currency": "USD", "audience": "ALL",
                                   "our_price": [{"schedule": [{"value_with_tax": price_usd}]}],
                                   "marketplace_id": MP}],
            "list_price": [{"currency": "USD", "value": round(price_usd * 1.7, 2), "marketplace_id": MP}],
            "fulfillment_availability": [{"fulfillment_channel_code": "DEFAULT", "quantity": 199,
                                          "lead_time_to_ship_max_days": 2, "marketplace_id": MP}],
            "merchant_shipping_group": N(SHIP_GROUP),
            "main_product_image_locator": [{"media_location": imgs[0], "marketplace_id": MP}],
        })
        for i, u in enumerate(imgs[1:7], 1):
            a[f"other_product_image_locator_{i}"] = [{"media_location": u, "marketplace_id": MP}]
        tasks.append((s["skuCode"], {"productType": pt, "requirements": "LISTING", "attributes": a},
                      f"子体 {v['color']}"))
    return tasks, variants


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--pt", required=True)
    ap.add_argument("--title", default=None)
    ap.add_argument("--parent-sku", default=None)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--pc", type=int, default=1, help="多件装数量（不足 $20 时用）")
    a = ap.parse_args()

    raw = json.load(open(a.src, encoding="utf-8"))
    spu = json.loads(raw["value"]) if "value" in raw else raw

    name_en = (spu.get("customs") or {}).get("nameEn") or "Pet Product"
    spu["_title"] = a.title or f"{name_en}, Soft Warm Pet Bed for Small Cats and Dogs"
    parent_sku = a.parent_sku or (spu["spuCode"] + "-PARENT")

    s0 = (spu.get("skuList") or [{}])[0]
    cost = float(s0.get("purchasePrice") or 0) * a.pc
    weight = float(s0.get("weight") or 0) * 1000 * a.pc
    pr = price_50_usd(cost, weight)
    price = pr["price_usd"]
    print(f"算价：进价¥{cost}(x{a.pc}) 重量{weight:.0f}g → ${price}（利润率 {pr['real_profit_rate']}%）")
    if price < 20:
        print(f"⚠️ 定价 ${price} < $20，建议加 --pc 2 做多件装")
        return

    tasks, variants = build(spu, a.pt, price, parent_sku)
    auth.set_store("zhangaodi")
    for sku, payload, label in tasks:
        print(f"\n[{label}] SKU={sku} attrs={len(payload['attributes'])}")
        qs = f"marketplaceIds={MP}" + ("&mode=VALIDATION_PREVIEW" if not a.submit else "")
        st, r = auth.request("PUT", f"/listings/2021-08-01/items/{auth.SELLER_ID}/{urllib.parse.quote(sku)}?{qs}", payload)
        status = r.get("status")
        print(f"  HTTP {st} status={status}")
        if status is None:
            print("  RAW:", json.dumps(r, ensure_ascii=False)[:500])
        for i in (r.get("issues") or [])[:5]:
            print(f"   {i.get('severity')} {i.get('code')} {str(i.get('message'))[:90]}")
        time.sleep(1)


if __name__ == "__main__":
    main()
