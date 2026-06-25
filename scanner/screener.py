"""量化筛选器 —— 多模式扫描

支持三种扫描模式:
  1. low_position: 低位潜力股 — 价格在低位, 技术面显示反转迹象
  2. momentum:     追高跟强 — 有上升动能, 但未过度追高
  3. top_gainers:  涨幅排名 — 简单看今日涨幅榜 (原模式)
"""

from __future__ import annotations

import time
from typing import Any

from config import settings
from data.indicators import compute_indicators

# ── 扫描模式 ──
SCAN_MODE_LOW = "low_position"
SCAN_MODE_MOMENTUM = "momentum"
SCAN_MODE_TOPS = "top_gainers"


def screen_market(mode: str = SCAN_MODE_TOPS, max_candidates: int = 30) -> list[dict]:
    """全市场筛选, 根据模式返回候选股

    Args:
        mode: low_position / momentum / top_gainers
        max_candidates: 返回的候选股数量上限

    Returns:
        [{code, name, price, change_pct, ...}]
    """
    print(f"  📡 正在扫描全市场 ({mode})...")

    # 1. 获取全市场行情 (新浪)
    stocks = _fetch_all_stocks()
    if not stocks:
        print("  ❌ 市场数据获取失败")
        return []

    print(f"  📊 全市场 {len(stocks)} 只股票, 正在筛选...")

    if mode == SCAN_MODE_TOPS:
        # 简单涨幅榜
        stocks.sort(key=lambda s: s.get("change_pct", 0), reverse=True)
        return stocks[:max_candidates]

    # 2. 初步过滤 (去掉太便宜的、ST、北交所)
    filtered = _basic_filter(stocks)

    # 3. 缩小候选池 (TOP 80 按成交额)
    filtered.sort(key=lambda s: s.get("turnover", 0), reverse=True)
    pool = filtered[:80]

    print(f"  🔬 正在计算 {len(pool)} 只候选股的技术指标...")

    # 4. 批量下载 K 线 (Baostock 统一登录, 减少开销)
    scored = _score_candidates_batch(pool, mode)

    # 5. 按评分排序
    scored.sort(key=lambda s: s.get("score", 0), reverse=True)

    results = scored[:max_candidates]

    print(f"  ✅ 筛选完成, TOP {len(results)} 如下:\n")
    for r in results[:10]:
        icon = "🔥" if mode == SCAN_MODE_MOMENTUM else "💎"
        print(f"  {icon} {r.get('name','')} ({r.get('code','')}) "
              f"评分:{r.get('score',0):.1f} 涨幅:{r.get('change_pct',0):.1f}% "
              f"RSI:{r.get('rsi','?')} 量比:{r.get('vol_ratio','?')}")

    return results


def _fetch_all_stocks() -> list[dict]:
    """从新浪获取全市场行情"""
    try:
        import akshare as ak

        df = ak.stock_zh_a_spot()
        df = df[~df["代码"].str.startswith("bj")]
        df = df[~df["名称"].str.contains("ST|\\*")]

        stocks = []
        for _, row in df.iterrows():
            stocks.append({
                "code": str(row["代码"]).replace("sh", "").replace("sz", ""),
                "name": str(row["名称"]),
                "price": _f(row.get("最新价", 0)),
                "change_pct": _f(row.get("涨跌幅", 0)),
                "change_amount": _f(row.get("涨跌额", 0)),
                "volume": _f(row.get("成交量", 0)),
                "turnover": _f(row.get("成交额", 0)),
                "open": _f(row.get("今开", 0)),
                "pre_close": _f(row.get("昨收", 0)),
                "high": _f(row.get("最高", 0)),
                "low": _f(row.get("最低", 0)),
            })
        return stocks
    except Exception as e:
        print(f"  ⚠️ 获取行情失败: {e}")
        return []


def _basic_filter(stocks: list[dict]) -> list[dict]:
    """基本过滤: 去掉低价股、成交量太低的"""
    filtered = []
    for s in stocks:
        price = s.get("price", 0)
        turnover = s.get("turnover", 0)
        change = s.get("change_pct", 0)

        # 价格不低于 3 元
        if price < 3:
            continue
        # 成交额不低于 3000 万
        if turnover < 30_000_000:
            continue
        # 去掉涨跌停的 (没有操作空间)
        if change <= -9.5 or change >= 9.5:
            continue
        # 去掉代码非纯数字的 (如 ETF)
        code = s.get("code", "")
        if not code.isdigit():
            continue

        filtered.append(s)
    return filtered


def _score_candidates_batch(stocks: list[dict], mode: str) -> list[dict]:
    """批量打分 (Baostock 统一登录, 减少开销)"""
    results = []
    count = 0

    try:
        import baostock as bs
        import datetime

        bs.login()

        end = datetime.date.today()
        start = end - datetime.timedelta(days=180)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        for s in stocks:
            count += 1
            if count % 20 == 0:
                print(f"    ...已分析 {count}/{len(stocks)}")

            kline = _query_kline_batch(s["code"], bs, start_str, end_str)
            if kline.empty or len(kline) < 20:
                continue

            ind = compute_indicators(kline)
            if "error" in ind:
                continue

            score, signals = _compute_score(s, ind, mode)
            results.append({
                **s, "score": round(score, 1),
                "rsi": ind.get("rsi14", "?"),
                "vol_ratio": ind.get("vol_ratio", "?"),
                "ma_trend": ind.get("ma_trend", ""),
                "macd_bullish": ind.get("macd_bullish", False),
                "macd_golden_cross": ind.get("macd_golden_cross", False),
                "macd_death_cross": ind.get("macd_death_cross", False),
                "rsi_status": ind.get("rsi_status", ""),
                "price_in_bb": ind.get("price_in_bb", ""),
                "near_20d_high": ind.get("near_20d_high", False),
                "high_20d": ind.get("high_20d", 0),
                "low_20d": ind.get("low_20d", 0),
                "ma5": ind.get("ma5", 0),
                "ma20": ind.get("ma20", 0),
                "signals": signals,
            })

        bs.logout()
    except Exception as e:
        print(f"  ⚠️ 批量打分出错: {e}")
        try:
            import baostock as bs
            bs.logout()
        except Exception:
            pass

    return results


def _query_kline_batch(symbol: str, bs, start_str: str, end_str: str):
    """在已登录的 Baostock session 中查询 K 线"""
    import pandas as pd

    code = symbol.strip()
    if code.isdigit():
        prefix = "sh" if code.startswith(("6", "9")) else "sz"
        bs_code = f"{prefix}.{code}"
    else:
        bs_code = code

    rs = bs.query_history_k_data_plus(
        bs_code, "date,open,high,low,close,volume,amount",
        start_date=start_str, end_date=end_str,
        frequency="d", adjustflag="3",
    )

    if rs.error_code != "0":
        return pd.DataFrame()

    df = rs.get_data()
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.rename(columns={
        "date": "日期", "open": "开盘", "high": "最高",
        "low": "最低", "close": "收盘", "volume": "成交量", "amount": "成交额",
    })
    for col in ["开盘", "最高", "最低", "收盘", "成交量", "成交额"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.tail(60).reset_index(drop=True)


def _compute_score(s: dict, ind: dict, mode: str) -> tuple[float, list[str]]:
    """根据模式计算评分和信号"""
    signals = []
    score = 0.0

    change = abs(s.get("change_pct", 0))
    rsi = ind.get("rsi14", 50)
    vol_ratio = ind.get("vol_ratio", 1.0)
    ma_trend = ind.get("ma_trend", "")
    macd_bullish = ind.get("macd_bullish", False)
    golden_cross = ind.get("macd_golden_cross", False)
    near_high = ind.get("near_20d_high", False)
    price = s.get("price", 0)
    ma20 = ind.get("ma20", 0)
    ma5 = ind.get("ma5", 0)
    macd_hist = ind.get("macd_hist", 0)

    if mode == SCAN_MODE_LOW:
        # ── 低位潜力股评分 ──

        # 价格在 MA20 附近或下方 (回调充分)
        if ma20 > 0:
            dist_from_ma20 = (price - ma20) / ma20 * 100
            if -8 < dist_from_ma20 < 2:
                score += 25
                signals.append(f"价格在MA20附近({dist_from_ma20:.1f}%)")
            elif dist_from_ma20 <= -8:
                score += 15
                signals.append(f"价格低于MA20({dist_from_ma20:.1f}%), 超跌")

        # RSI 适中偏低 (30-50 有反弹空间)
        if 30 <= rsi <= 50:
            score += 20
            signals.append(f"RSI适中偏低({rsi})")
        elif 50 < rsi <= 60:
            score += 10

        # 成交量温和放大 (有资金关注但不过热)
        if 0.8 <= vol_ratio <= 1.8:
            score += 15
            signals.append(f"量能温和({vol_ratio:.1f}x)")
        elif vol_ratio < 0.8:
            score += 5

        # MACD 出现金叉或柱线翻红 (反转信号)
        if golden_cross:
            score += 20
            signals.append("MACD金叉")
        elif macd_bullish and macd_hist > 0:
            score += 15
            signals.append("MACD红柱")

        # 均线空头排列但价格站上MA5 (可能企稳)
        if ma_trend == "空头排列" and price > ma5:
            score += 10
            signals.append("站上MA5")

        # 今日涨幅不大 (还没起飞)
        if -3 <= s.get("change_pct", 0) <= 3:
            score += 10
            signals.append("今日窄幅震荡")

    elif mode == SCAN_MODE_MOMENTUM:
        # ── 追高跟强评分 ──

        # 价格在 MA20 上方 (处于上升趋势)
        if ma20 > 0 and price > ma20 * 1.02:
            score += 20
            signals.append(f"价格在MA20上方")
        elif ma20 > 0 and price > ma20:
            score += 10

        # RSI 偏强但不超买 (50-75)
        if 55 <= rsi <= 75:
            score += 25
            signals.append(f"RSI偏强({rsi})")
        elif 50 <= rsi < 55:
            score += 10
        elif rsi > 75:
            score -= 10  # 超买减分

        # 成交量放大 (有资金推动)
        if vol_ratio >= 1.5:
            score += 20
            signals.append(f"放量{vol_ratio:.1f}x")
        elif vol_ratio >= 1.2:
            score += 15
            signals.append(f"量增{vol_ratio:.1f}x")

        # MACD 多头
        if macd_bullish:
            score += 15
            signals.append("MACD多头")
        if golden_cross:
            score += 15
            signals.append("MACD金叉")

        # 均线多头排列
        if ma_trend == "多头排列":
            score += 15
            signals.append("均线多头排列")

        # 接近20日高点 (突破形态)
        if near_high:
            score += 10
            signals.append("接近20日高点")

        # 涨幅适中 (3-7% 最佳, 还有空间)
        change = s.get("change_pct", 0)
        if 3 <= change <= 7:
            score += 15
            signals.append(f"涨幅适中({change}%)")
        elif 7 < change <= 9:
            score += 5
            signals.append(f"涨幅偏大({change}%)")

        # 换手率适中 (太高的换手可能是出货)
        turnover_rate = s.get("turnover_rate", 0)
        if turnover_rate > 20:
            score -= 10

    return score, signals


def _f(v) -> float:
    try:
        return round(float(v), 2)
    except (ValueError, TypeError):
        return 0.0
