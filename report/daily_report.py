"""Daily PDF Report Generator — with sentiment aggregation"""

from __future__ import annotations

import datetime

from config import settings
from data.market import get_realtime_quote, get_kline
from data.indicators import compute_indicators
from data.sentiment import collect_sentiment, get_market_news_snapshot
from report.pdf_report import generate_daily_report
from scanner.sectors import get_sector, get_sector_weighted_score

FOCUS_SECTORS = {
    "AI": ["300308", "688981", "002371", "300782", "688041"],
    "Robot": ["688017", "300124", "601689", "002050", "603728"],
    "Consumer": ["600519", "000333", "600887"],
    "Finance": ["601318", "600036", "600030"],
    "Medical": ["600276", "300760", "000538"],
    "New Energy": ["300750", "002594", "601012"],
}

STOCKS = {
    "002384": {"name": "Dongshan Prec", "entry": "240-250", "reason": "Lowest PE AI", "group": "AI", "prio": "A"},
    "300394": {"name": "Tianfu Comm", "entry": "310-342", "reason": "CPO leader RSI30", "group": "AI", "prio": "A"},
    "600183": {"name": "Shengyi Tech", "entry": "157-165", "reason": "CCL hike play", "group": "AI", "prio": "B"},
    "002916": {"name": "Shennan Circ", "entry": "410-420", "reason": "IC substrate", "group": "AI", "prio": "B"},
    "002463": {"name": "WUS PCB", "entry": "142-145", "reason": "Low PE PCB", "group": "AI", "prio": "A"},
    "601689": {"name": "Tuopu Group", "entry": "52-56", "reason": "RSI20 oversold", "group": "Robot", "prio": "A"},
    "300124": {"name": "Inovance", "entry": "64-67", "reason": "Servo RSI31", "group": "Robot", "prio": "A"},
    "002050": {"name": "Sanhua", "entry": "41-44", "reason": "Rotary+thermal", "group": "Robot", "prio": "B"},
    "603662": {"name": "Keli Sensing", "entry": "64-65", "reason": "Torque sensor", "group": "Robot", "prio": "B"},
    "688322": {"name": "Orbbec", "entry": "115-123", "reason": "3D vision", "group": "Robot", "prio": "B"},
}


def run_daily_report(output_dir: str = "reports") -> str:
    print(f"\n{'='*50}")
    print(f"  Generating daily report [{datetime.date.today()}]")
    print(f"{'='*50}\n")

    # 1. Market
    print("  [1/5] Market data...")
    indices = []
    for code, name in [("sh000001","Shanghai"),("sz399001","Shenzhen"),("sz399006","ChiNext")]:
        q = get_realtime_quote(code)
        if "error" not in q:
            indices.append({"name": name, "price": q.get("price",0), "change_pct": q.get("change_pct",0), "score": 50})

    # 2. Sectors
    print("  [2/5] Sectors...")
    views = {"AI":"High growth","Robot":"Oversold","Consumer":"Weak","Finance":"Neutral","Medical":"Recovering","New Energy":"Cyclical"}
    sectors = []
    for name, codes in FOCUS_SECTORS.items():
        scores = []
        for code in codes[:3]:
            q = get_realtime_quote(code)
            if "error" in q: continue
            k = get_kline(code, 60)
            if k.empty: continue
            ind = compute_indicators(k)
            if "error" in ind: continue
            sc = get_sector_weighted_score(q["price"], ind, "low_position", get_sector(code))
            scores.append(sc)
        avg = sum(scores)/len(scores) if scores else 50
        sectors.append({"name": name, "score": avg, "spread": avg-50, "direction": "Bull" if avg>50 else "Bear", "view": views.get(name,"")})
        print(f"    {name}: {avg:.0f}/100")

    # 3. Stocks
    print("  [3/5] Stocks...")
    stocks = []
    for code, ref in STOCKS.items():
        q = get_realtime_quote(code)
        if "error" in q: continue
        price = q.get("price", 0)
        k = get_kline(code, 60)
        if k.empty: continue
        ind = compute_indicators(k)
        if "error" in ind: continue
        sc = get_sector_weighted_score(price, ind, "low_position", get_sector(code))
        rsi = ind.get("rsi14", 50)
        trend = ind.get("ma_trend", "")
        signal = "Strong" if sc >= 65 else "Neutral" if sc >= 50 else "Weak"
        action = "Watch" if sc >= 65 else "Hold" if sc >= 50 else "Avoid"
        stocks.append({"code":code,"name":ref["name"],"price":price,"score":sc,"rsi":rsi,"trend":trend,"signal":signal,"action":action,"entry_ref":ref["entry"],"reason":ref["reason"],"sector_group":ref["group"],"priority":ref["prio"]})
        print(f"    {ref['name']}({code}): {sc:.0f}/100")

    # 4. Sentiment
    print("  [4/5] Sentiment...")
    market_news = get_market_news_snapshot(6)
    sentiments = {}
    for code in list(STOCKS.keys())[:6]:
        sent = collect_sentiment(code, STOCKS[code]["name"], max_sources=2)
        if sent["total_items"] > 0:
            sentiments[code] = sent
    print(f"    collected {len(sentiments)} stock sentiments, {len(market_news)} market news")

    # 5. PDF
    print("  [5/5] PDF...")
    pdf = generate_daily_report(
        market_summary={"indices":indices,"outlook":"Structural divergence. AI chain strong, Robot oversold."},
        sector_analysis=sectors,
        stock_analysis=stocks,
        market_news=market_news,
        sentiments=sentiments,
        output_dir=output_dir,
    )
    print(f"\n  Done! PDF: {pdf}")
    return pdf
