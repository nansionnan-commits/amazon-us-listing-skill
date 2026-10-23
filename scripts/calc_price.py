# -*- coding: utf-8 -*-
"""美国 · 云途专线 · 利润率 50% 定价计算器

逻辑完全复刻老板算价表《1008普货.xlsx》：
  - 进货成本(A) + 包装费(I=1) + 运费 = 产品成本
  - 运费(云途美国) = 单价(RMB/KG) × 重量(KG) + 挂号费(RMB/票)
  - 利润 = 定价 × 佣金比例(0.85) − 产品成本
  - 利润率 = 利润 / 定价
  - 利润率 50% ⇒ 定价 = 产品成本 / (0.85 − 0.5) = 产品成本 / 0.35
  - 美元定价 = 定价(CNY) / 汇率(6.7367)

用法：
  python calc_price.py 12 300        # 进货12元，300g
"""
import math
import sys

USD_RATE = 6.7367          # 美元汇率（表 r8c17）
COMMISSION = 0.85          # 卖家实得比例（=1−平台15%佣金，表 H4）
TARGET_PROFIT = 0.50       # 目标利润率 50%
PACKING_FEE = 1.0          # 包装费（表 I4）
FREIGHT_CNY = 99.99        # 预留：MX 等站运费，美国不用


def to_dot99(x):
    """向上取到 .99（利润略提升）。23.24 → 23.99；23.99 → 23.99；24.01 → 24.99"""
    return round(math.ceil(x) - 0.01, 2)

# 云途专线挂号（普货）· 美国 费率表：[(重量上限g, 单价RMB/KG, 挂号费RMB/票)]
YUNTU_US = [
    (100,   84, 23),
    (200,   79, 21),
    (450,   76, 19),
    (700,   75, 19),
    (2000,  74, 12),
    (30000, 69, 12),
]


def yuntu_us_freight(weight_g):
    """云途美国运费（RMB）。weight_g 单位克。"""
    for cap, unit, reg in YUNTU_US:
        if weight_g <= cap:
            return unit * weight_g / 1000.0 + reg
    return 69 * weight_g / 1000.0 + 12


def price_50_usd(purchase_cny, weight_g):
    """利润率 50% 时的美元定价（不含运费，即 listing 的 our_price 基准）。"""
    freight = yuntu_us_freight(weight_g)
    cost = purchase_cny + PACKING_FEE + freight
    price_cny = cost / (COMMISSION - TARGET_PROFIT)   # /0.35
    price_usd = price_cny / USD_RATE
    final_usd = to_dot99(price_usd)
    # 用最终定价反算实际利润率（.99 上取后利润率会略高于 50%）
    final_cny = final_usd * USD_RATE
    real_profit = (final_cny * COMMISSION - cost) / final_cny
    return {
        "purchase_cny": purchase_cny,
        "weight_g": weight_g,
        "freight_rmb": round(freight, 2),
        "cost_rmb": round(cost, 2),
        "price_cny": round(price_cny, 2),
        "price_usd_raw": round(price_usd, 2),
        "price_usd": final_usd,
        "real_profit_rate": round(real_profit * 100, 2),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    a = float(sys.argv[1])
    w = float(sys.argv[2])
    r = price_50_usd(a, w)
    print("进货成本 CNY:", r["purchase_cny"])
    print("重量 g       :", r["weight_g"])
    print("云途运费 RMB :", r["freight_rmb"])
    print("产品成本 RMB :", r["cost_rmb"])
    print("定价 CNY(50%):", r["price_cny"])
    print("美元定价原始 : $", r["price_usd_raw"])
    print("美元定价 .99 : $", r["price_usd"], "  实际利润率:", r["real_profit_rate"], "%")
