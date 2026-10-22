#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US Listing 生成器（模板驱动）

用法：
  # 只生成 JSON，不提交
  python build_us_listing.py --input _product_544.json --out _listing_544.json

  # 生成 + VALIDATION_PREVIEW 校验（不真正创建，安全）
  python build_us_listing.py --input _product_544.json --validate

  # 正式提交（PAUSED 状态，不产生流量）
  python build_us_listing.py --input _product_544.json --submit
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import auth  # noqa: E402

MP = "ATVPDKIKX0DER"          # US
TEMPLATE_PATH = os.path.join(HERE, "_listing_template.json")
SHIPPING_GROUP = "a08cfb00-f40d-4cbd-a231-51d5f48f37d9"


def L(v):
    """标准 language_tag 包装"""
    return [{"language_tag": "en_US", "value": v, "marketplace_id": MP}]


def build(p):
    """从产品定义 p 生成完整 listing payload"""
    attrs = {
        "brand": L(p["brand"]),
        "item_name": L(p["title"]),
        "bullet_point": [{"language_tag": "en_US", "value": b, "marketplace_id": MP}
                         for b in p["bullets"]],
        "product_description": L(p["description"]),
        "item_type_keyword": L(p["item_type_keyword"]),
        "condition_type": [{"value": "new_new", "marketplace_id": MP}],
        # PT schema required（HARDWARE_HANDLE 必须）
        "country_of_origin": [{"value": p.get("country_of_origin", "CN"), "marketplace_id": MP}],
        "supplier_declared_dg_hz_regulation": [{"value": p.get("dg_regulation", "not_applicable"), "marketplace_id": MP}],
        "model_number": [{"value": p.get("model_number", p["sku"]), "marketplace_id": MP}],
        "model_name": L(p.get("model_name", p["title"].split(",")[0])),
        "manufacturer": L(p.get("manufacturer", p["brand"])),
        "included_components": L(p.get("included_components",
                                     "1 x Motorcycle Passenger Grab Handle Belt")),
        "handle": [{
            "material": [{"language_tag": "en_US", "value": p.get("handle_material", "Plastic")}],
            "type": [{"language_tag": "en_US", "value": p.get("handle_type", "Molded Grip Handle")}],
            "marketplace_id": MP,
        }],
        # 产品实际长宽（单位只能是 inches）
        "item_length_width": [{
            "length": {"value": p["item_lw"]["length"], "unit": "inches"},
            "width": {"value": p["item_lw"]["width"], "unit": "inches"},
            "marketplace_id": MP,
        }],
        "color": L(p.get("color", "Black")),
        "size": L(p.get("size", "One Size")),
        "material": L(p.get("material", "Nylon")),
        "number_of_items": [{"value": p.get("number_of_items", 1), "marketplace_id": MP}],

        # 主图 / 副图
        "main_product_image_locator": [{"media_location": p["images"]["main"], "marketplace_id": MP}],

        # UPC 豁免（本店已开）
        "supplier_declared_has_product_identifier_exemption": [{"value": True, "marketplace_id": MP}],

        # 价格
        "purchasable_offer": [{
            "currency": "USD",
            "audience": "ALL",
            "our_price": [{"schedule": [{"value_with_tax": p["price"]}]}],
            "marketplace_id": MP,
        }],
        "list_price": [{"currency": "USD", "value": p["list_price"], "marketplace_id": MP}],

        # 库存与发货
        "fulfillment_availability": [{
            "fulfillment_channel_code": "DEFAULT",
            "quantity": p.get("quantity", 999),
            "lead_time_to_ship_max_days": p.get("lead_time", 2),
        }],
        "merchant_shipping_group": [{"value": p.get("shipping_group", SHIPPING_GROUP), "marketplace_id": MP}],

        # 包装尺寸（cm）与重量（kg）
        "item_package_dimensions": [{
            "length": {"value": p["pkg"]["l"], "unit": "centimeters"},
            "width": {"value": p["pkg"]["w"], "unit": "centimeters"},
            "height": {"value": p["pkg"]["h"], "unit": "centimeters"},
            "marketplace_id": MP,
        }],
        "item_package_weight": [{
            "value": p["weight_kg"], "unit": "kilograms", "marketplace_id": MP,
        }],
        "item_package_quantity": [{"value": 1, "marketplace_id": MP}],
        "number_of_boxes": [{"value": 1, "marketplace_id": MP}],
    }

    # 副图 1..6
    for i, url in enumerate(p["images"].get("others", [])[:8], 1):
        attrs[f"other_product_image_locator_{i}"] = [{"media_location": url, "marketplace_id": MP}]

    # 单款：不设 parentage_level / variation_theme / child_parent_sku_relationship

    payload = {
        "productType": p["product_type"],
        "requirements": "LISTING",
        "attributes": attrs,
    }
    return payload


def submit(sku, payload, mode=None):
    """mode=None 正式提交；mode=VALIDATION_PREVIEW 只校验"""
    qs = {"marketplaceIds": MP}
    if mode:
        qs["mode"] = mode
    path = f"/listings/2021-08-01/items/{auth.SELLER_ID}/{urllib.parse.quote(sku)}?{urllib.parse.urlencode(qs)}"
    return auth.request("PUT", path, body=payload)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--validate", action="store_true", help="VALIDATION_PREVIEW 校验，不创建")
    ap.add_argument("--submit", action="store_true", help="正式提交")
    args = ap.parse_args()

    p = json.load(open(args.input, encoding="utf-8"))
    payload = build(p)

    out = args.out or os.path.join(HERE, f"_listing_{p['sku']}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"✅ 已生成 {out}")
    print(f"   productType={p['product_type']} | 属性 {len(payload['attributes'])} 个")

    if not (args.validate or args.submit):
        return 0

    auth.set_store(p.get("store", "zhangaodi"))

    if args.validate:
        print("\n🔍 VALIDATION_PREVIEW（只校验，不创建）...")
        st, r = submit(p["sku"], payload, mode="VALIDATION_PREVIEW")
        print(f"HTTP {st}")
        print(json.dumps(r, ensure_ascii=False, indent=1)[:3000])
        return 0

    print("\n📤 正式提交...")
    st, r = submit(p["sku"], payload)
    print(f"HTTP {st}")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
