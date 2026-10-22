# -*- coding: utf-8 -*-
import sys, json, time, urllib.parse, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth
auth.set_store("zhangaodi")
sku = "MGB-1PC-BLK"
for i in range(15):
    time.sleep(60)
    q = urllib.parse.urlencode({"marketplaceIds": auth.US, "includedData": "summaries,offers,fulfillmentAvailability"})
    st, r = auth.request("GET", f"/listings/2021-08-01/items/{auth.SELLER_ID}/{urllib.parse.quote(sku)}?{q}")
    if st != 200:
        print(f"[{i+1}] HTTP {st}"); continue
    s = (r.get("summaries") or [{}])[0]
    asin = s.get("asin")
    status = s.get("status") or []
    print(f"[{i+1}] ASIN={asin} status={status} title={(s.get('itemName') or '')[:40]}")
    if asin:
        off = (r.get("offers") or [{}])[0]
        fa = (r.get("fulfillmentAvailability") or [{}])[0]
        print("  ✅ 生成成功！")
        print("  ASIN:", asin)
        print("  价格:", (off.get("price") or {}).get("amount"), (off.get("price") or {}).get("currency"))
        print("  库存:", fa.get("quantity"))
        print("  主图:", ((s.get("mainImage") or {}).get("link") or "")[:90])
        json.dump({"sku": sku, "asin": asin, "status": status,
                   "title": s.get("itemName"),
                   "price": (off.get("price") or {}).get("amount"),
                   "qty": fa.get("quantity")},
                  open("_result_544.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        break
else:
    print("⏱️ 15 分钟仍未生成 ASIN，建议后台核查")
