"""量化筛选器 —— 多模式多因子评分系统

评分体系参考:
  - Barra CNE6 风格因子框架 (8大类因子)
  - AlphaSift 多因子评分体系
  - A股市场本土化调整 (快轮动、政策敏感)

因子权重设计原则:
  1. 技术面 > 基本面 > 资金面 > 舆情 (A股特征)
  2. 每类因子内再按预测能力加权
  3. 不同扫描模式使用不同的权重矩阵
"""

from __future__ import annotations

from typing import Any

from config import settings

# ── 扫描模式 ──
SCAN_MODE_LOW = "low_position"      # 低位潜力股
SCAN_MODE_MOMENTUM = "momentum"     # 追高跟强
SCAN_MODE_TOPS = "top_gainers"      # 涨幅榜

# ════════════════════════════════════════════════════════════
#  多因子权重矩阵 (Barra CNE6 本土化版)
# ════════════════════════════════════════════════════════════

# 每个因子: (权重, 名称, 说明)
# 权重 = 该因子在整个评分中的占比 (满分为1.0)
# factor_score 返回 -1.0 ~ +1.0, 最终得分 = weight * 100 * factor_score

# ── 低位潜力模式权重 ──
WEIGHTS_LOW = {
    # Barra Momentum - 反转/动量子因子
    "ma_trend":       (0.14, "均线趋势", "多头/空头/缠绕, 最核心的趋势判断"),
    "macd_signal":    (0.10, "MACD信号", "金叉/死叉/柱线方向, 动量反转信号"),
    "rsi_position":   (0.08, "RSI位置", "超买超卖区间, 判断回调是否充分"),
    "volume_ratio":   (0.10, "量价关系", "放量/缩量/正常, 量价配合情况"),
    "bb_position":    (0.05, "布林位置", "股价在布林带中的位置"),
    "kdj_signal":     (0.05, "KDJ信号", "KDJ金叉/死叉, 辅助信号"),
    "price_position": (0.08, "价格位置", "相对MA20/MA60的位置, 回调深度"),
    # 附加因子
    "near_high_low":  (0.06, "高低位置", "接近20日高/低点, 突破/触底判断"),
    "daily_change":   (0.04, "当日涨幅", "当日涨跌幅范围"),
    # Barra Quality - 质量因子 (通过技术面反映)
    "ma5_stability":  (0.05, "MA5支撑", "价格在MA5上方/下方, 短期企稳判断"),
}

# ── 追高跟强模式权重 ──
WEIGHTS_MOMENTUM = {
    "ma_trend":       (0.15, "均线趋势", "多头排列是最核心的信号"),
    "macd_signal":    (0.12, "MACD信号", "MACD多头+金叉=强做多信号"),
    "rsi_position":   (0.10, "RSI位置", "55-75最佳, 太超买要警惕"),
    "volume_ratio":   (0.12, "量价关系", "放量突破是追高的核心逻辑"),
    "bb_position":    (0.06, "布林位置", "沿上轨运行 = 强势"),
    "kdj_signal":     (0.05, "KDJ信号", "KDJ高位钝化 = 强势持续"),
    "price_position": (0.07, "价格位置", "在MA20上方, 偏离度适中"),
    "near_high_low":  (0.08, "高低位置", "接近20日高点=突破形态"),
    "daily_change":   (0.10, "当日涨幅", "3-7%最佳追高区间"),
    "turnover_rate":  (0.05, "换手率", "换手率适中不拥堵"),
}

# ════════════════════════════════════════════════════════════
#  因子评分函数
#  每个因子返回 (-1.0, +1.0) 的分数和信号文字
# ════════════════════════════════════════════════════════════


def score_ma_trend(ind: dict, mode: str) -> tuple[float, str]:
    """均线趋势因子 — 权重最高 (14-15%)

    判断依据: MA5/MA10/MA20 排列关系
    +1.0: 多头排列, MA5>MA10>MA20 发散向上
    -1.0: 空头排列, MA5<MA10<MA20 发散向下
    """
    trend = ind.get("ma_trend", "")
    ma5 = ind.get("ma5", 0)
    ma10 = ind.get("ma10", 0)
    ma20 = ind.get("ma20", 0)

    if trend == "多头排列":
        # 进一步判断发散程度
        spread = (ma5 - ma20) / ma20 * 100 if ma20 > 0 else 0
        if spread > 3:
            return 1.0, f"多头排列, 均线发散({spread:.1f}%)"
        elif spread > 1:
            return 0.7, f"多头排列, 均线向上"
        else:
            return 0.5, "均线刚形成多头"
    elif trend == "空头排列":
        spread = (ma20 - ma5) / ma20 * 100 if ma20 > 0 else 0
        if mode == SCAN_MODE_LOW:
            # 低位模式: 空头排列但如果站上MA5, 可能是反转
            return -0.3, f"空头排列, 关注是否企稳"
        else:
            return -0.8, f"空头排列, 均线发散(-{spread:.1f}%)"
    else:
        return 0.0, "均线缠绕/整理"


def score_macd_signal(ind: dict, mode: str) -> tuple[float, str]:
    """MACD 信号因子 — 权重 10-12%

    +1.0: 零轴上方金叉 (最强做多)
    -1.0: 零轴下方死叉 (最强做空)
    """
    golden = ind.get("macd_golden_cross", False)
    death = ind.get("macd_death_cross", False)
    bullish = ind.get("macd_bullish", False)
    hist = ind.get("macd_hist", 0)
    dif = ind.get("macd_dif", 0)
    dea = ind.get("macd_dea", 0)

    if golden:
        return 1.0, "MACD金叉(强烈做多)"
    if death:
        return -1.0, "MACD死叉(强烈做空)"

    if bullish:
        if hist > 0 and dif > 0:
            return 0.7, "MACD多头, 零轴上方"
        elif hist > 0:
            return 0.5, "MACD红柱, 零轴下方待确认"
        else:
            return 0.3, "MACD偏多"

    if not bullish and hist < 0:
        if dif < 0 and dea < 0:
            return -0.7, "MACD空头, 零轴下方"
        else:
            return -0.5, "MACD绿柱"
    return 0.0, "MACD中性"


def score_rsi_position(ind: dict, mode: str) -> tuple[float, str]:
    """RSI 位置因子 — 权重 8-10%

    不同模式下评分规则不同:
    低位模式: 30-50最好 (超卖回升)
    追高模式: 55-75最好 (偏强未超买)
    """
    rsi = ind.get("rsi14", 50)
    status = ind.get("rsi_status", "正常")

    if mode == SCAN_MODE_LOW:
        # 低位模式: 找超卖回升
        if 30 <= rsi <= 50:
            norm = (rsi - 30) / 20  # 0 -> 1
            return 0.5 + norm * 0.5, f"RSI{rsi:.0f}, 超卖回升区间"
        elif 50 < rsi <= 60:
            return 0.3, f"RSI{rsi:.0f}, 中性偏强"
        elif rsi < 30:
            return 0.0, f"RSI{rsi:.0f}, 超卖区(仍在探底)"
        elif rsi > 70:
            return -0.3, f"RSI{rsi:.0f}, 偏高(注意回调)"
        return 0.2, f"RSI{rsi:.0f}"
    else:
        # 追高模式: 找偏强不超买
        if 55 <= rsi <= 75:
            return 0.8, f"RSI{rsi:.0f}, 偏强持续区间"
        elif 50 <= rsi < 55:
            return 0.3, f"RSI{rsi:.0f}, 中性偏强"
        elif 75 < rsi <= 85:
            return -0.2, f"RSI{rsi:.0f}, 偏超买"
        elif rsi > 85:
            return -0.6, f"RSI{rsi:.0f}, 严重超买"
        elif rsi < 40:
            return -0.4, f"RSI{rsi:.0f}, 偏弱"
        return 0.0, f"RSI{rsi:.0f}"


def score_volume_ratio(ind: dict, mode: str) -> tuple[float, str]:
    """量价关系因子 — 权重 10-12%

    A股最有效的因子之一:
    低位模式: 温和放量最好 (0.8-1.8x)
    追高模式: 明显放量最好 (1.5x+)
    """
    vol_ratio = ind.get("vol_ratio", 1.0)
    vol_status = ind.get("vol_status", "正常")

    if mode == SCAN_MODE_LOW:
        if 0.8 <= vol_ratio <= 1.5:
            return 0.8, f"量比{vol_ratio:.1f}x, 温和放量(标准)"
        elif 1.5 < vol_ratio <= 2.0:
            return 0.5, f"量比{vol_ratio:.1f}x, 温和放量"
        elif 0.5 <= vol_ratio < 0.8:
            return 0.2, f"量比{vol_ratio:.1f}x, 缩量(可能筑底)"
        elif vol_ratio < 0.5:
            return -0.2, f"量比{vol_ratio:.1f}x, 严重缩量"
        else:
            return -0.3, f"量比{vol_ratio:.1f}x, 放量过大(警惕)"
    else:
        if vol_ratio >= 2.0:
            return 1.0, f"量比{vol_ratio:.1f}x, 显著放量"
        elif 1.5 <= vol_ratio < 2.0:
            return 0.8, f"量比{vol_ratio:.1f}x, 明显放量"
        elif 1.2 <= vol_ratio < 1.5:
            return 0.5, f"量比{vol_ratio:.1f}x, 温和放量"
        elif 0.8 <= vol_ratio < 1.2:
            return 0.0, f"量比{vol_ratio:.1f}x, 正常"
        else:
            return -0.3, f"量比{vol_ratio:.1f}x, 缩量"


def score_bb_position(ind: dict, mode: str) -> tuple[float, str]:
    """布林带位置因子 — 权重 5-6%"""
    pos = ind.get("price_in_bb", "中轨附近")

    if mode == SCAN_MODE_LOW:
        if "下轨" in pos:
            return 0.5, "布林下轨附近(超卖)"
        elif "中轨" in pos:
            return 0.3, "布林中轨(中性)"
        elif "上轨" in pos:
            return -0.3, "布林上轨附近(偏高)"
    else:
        if "上轨" in pos:
            return 0.6, "布林上轨(强势)"
        elif "中轨" in pos:
            return 0.2, "布林中轨"
        elif "下轨" in pos:
            return -0.3, "布林下轨(弱势)"
    return 0.0, "布林位置中性"


def score_kdj_signal(ind: dict, mode: str) -> tuple[float, str]:
    """KDJ 信号因子 — 权重 5%"""
    k = ind.get("kdj_k", 50)
    d = ind.get("kdj_d", 50)
    j = ind.get("kdj_j", 50)

    if mode == SCAN_MODE_LOW:
        if k < 30 and d < 30:
            return 0.5, "KDJ低位(超卖)"
        elif 30 <= k <= 60:
            return 0.3, "KDJ中性"
        elif k > 80:
            return -0.3, "KDJ高位(超买)"
    else:
        if k > d and k > 60:
            return 0.5, "KDJ金叉向上"
        elif 40 <= k <= 80:
            return 0.2, "KDJ中性偏强"
        elif k < 20:
            return -0.3, "KDJ低位"
    return 0.0, "KDJ中性"


def score_price_position(ind: dict, mode: str, price: float) -> tuple[float, str]:
    """价格位置因子 — 相对均线位置 权重 7-8%"""
    ma20 = ind.get("ma20", 0)
    ma60 = ind.get("ma60", 0)
    if ma20 == 0:
        return 0.0, "无MA20"

    dist = (price - ma20) / ma20 * 100

    if mode == SCAN_MODE_LOW:
        if -5 <= dist <= 2:
            return 0.9, f"在MA20附近({dist:+.1f}%)"
        elif -10 <= dist < -5:
            return 0.6, f"稍低于MA20({dist:+.1f}%), 回调充分"
        elif dist < -10 and ma60 > 0 and price > ma60:
            return 0.4, f"大幅低于MA20但高于MA60"
        elif dist < -10:
            return 0.2, f"深度低于MA20({dist:+.1f}%)"
        elif 2 < dist <= 10:
            return 0.3, f"稍高于MA20({dist:+.1f}%)"
        else:
            return -0.2, f"远离MA20({dist:+.1f}%)"
    else:
        if 2 <= dist <= 15:
            return 0.8, f"在MA20上方({dist:+.1f}%), 趋势健康"
        elif 0 <= dist < 2:
            return 0.3, f"刚站上MA20({dist:+.1f}%)"
        elif 15 < dist <= 30:
            return 0.4, f"大幅高于MA20({dist:+.1f}%), 注意回调"
        elif dist > 30:
            return -0.3, f"严重偏离MA20({dist:+.1f}%), 警惕"
        else:
            return -0.5, f"低于MA20({dist:+.1f}%), 偏弱"
    return 0.0, "中性"


def score_near_high_low(ind: dict, mode: str) -> tuple[float, str]:
    """高低位置因子 — 权重 6-8%

    A股特色: 突破前高vs触底反弹
    """
    near_high = ind.get("near_20d_high", False)
    high_20d = ind.get("high_20d", 0)
    low_20d = ind.get("low_20d", 0)
    price = ind.get("price", 0)

    if mode == SCAN_MODE_LOW:
        # 低位模式: 接近20日低点但不再创新低 = 触底
        if low_20d > 0 and price > 0:
            dist_to_low = (price - low_20d) / low_20d * 100
            if dist_to_low < 2:
                return 0.6, f"接近20日低点(距{high_20d:.1f}), 关注支撑"
            elif dist_to_low < 5:
                return 0.3, "在20日低点附近"
        if near_high:
            return -0.2, "接近20日高点(低位反弹?)"
        return 0.0, f"20日区间中部"
    else:
        if near_high:
            return 0.8, "接近20日高点(突破形态)"
        elif high_20d > 0 and price > 0:
            dist = (high_20d - price) / high_20d * 100
            if dist < 5:
                return 0.5, f"距20日高{high_20d:.1f}仅{dist:.1f}%"
        return 0.0, "未触及20日高点"


def score_daily_change(ind: dict, s: dict, mode: str) -> tuple[float, str]:
    """当日涨幅因子 — 权重 4-10%

    低位模式: 窄幅震荡(-3%~+3%)最好 (还没起飞)
    追高模式: 3%-7%最佳 (有空间继续追)
    """
    change = s.get("change_pct", 0)

    if mode == SCAN_MODE_LOW:
        if -3 <= change <= 3:
            return 0.7, f"当日{change:+.1f}%, 窄幅(企稳)"
        elif -5 <= change < -3:
            return 0.3, f"当日{change:+.1f}%, 偏弱"
        elif 3 < change <= 5:
            return 0.2, f"当日{change:+.1f}%, 小涨"
        else:
            return -0.3, f"当日{change:+.1f}%, 波动过大"
    else:
        if 3 <= change <= 7:
            return 1.0, f"当日{change:+.1f}%, 理想追高区间"
        elif 1 <= change < 3:
            return 0.4, f"当日{change:+.1f}%, 小涨"
        elif 7 < change <= 9.5:
            return 0.3, f"当日{change:+.1f}%, 偏高"
        elif change < -2:
            return -0.5, f"当日{change:+.1f}%, 下跌"
        elif change > 9.5:
            return -0.8, f"当日{change:+.1f}%, 涨封板(买不进)"
        return 0.1, f"当日{change:+.1f}%"


def score_ma5_stability(ind: dict, mode: str) -> tuple[float, str]:
    """MA5 短期支撑因子 — 权重 5%

    A股特色: MA5是短期生命线
    """
    price = ind.get("price", 0)
    ma5 = ind.get("ma5", 0)
    if ma5 == 0:
        return 0.0, ""

    if price >= ma5:
        dist = (price - ma5) / ma5 * 100
        if dist < 3:
            return 0.6, f"站上MA5, 短期支撑有效"
        else:
            return 0.3, f"在MA5上方({dist:.1f}%)"
    else:
        dist = (ma5 - price) / ma5 * 100
        if dist < 3:
            return -0.2, f"略低于MA5({dist:.1f}%), 关注"
        else:
            return -0.5, f"跌破MA5({dist:.1f}%), 短期走弱"


# ════════════════════════════════════════════════════════════
#  评分引擎
# ════════════════════════════════════════════════════════════

def _compute_score(s: dict, ind: dict, mode: str) -> tuple[float, list[str]]:
    """综合多因子评分 — 参考 Barra 多因子模型

    计算流程:
      1. 对每个因子计算 -1.0 ~ +1.0 的分数
      2. 乘以因子权重
      3. 加权求和得到总分 (-100 ~ +100)
      4. 归一化到 0 ~ 100 输出
    """
    price = s.get("price", 0)
    signals = []

    if mode == SCAN_MODE_LOW:
        weights = WEIGHTS_LOW
    elif mode == SCAN_MODE_MOMENTUM:
        weights = WEIGHTS_MOMENTUM
    else:
        return 50, ["涨幅榜模式不下发评分"]

    # 计算每个因子得分
    factor_scores = {}

    # 1. 均线趋势
    val, sig = score_ma_trend(ind, mode)
    factor_scores["ma_trend"] = val
    signals.append(sig)

    # 2. MACD信号
    val, sig = score_macd_signal(ind, mode)
    factor_scores["macd_signal"] = val
    signals.append(sig)

    # 3. RSI位置
    val, sig = score_rsi_position(ind, mode)
    factor_scores["rsi_position"] = val
    signals.append(sig)

    # 4. 量价关系
    val, sig = score_volume_ratio(ind, mode)
    factor_scores["volume_ratio"] = val
    signals.append(sig)

    # 5. 布林位置
    val, sig = score_bb_position(ind, mode)
    factor_scores["bb_position"] = val
    signals.append(sig)

    # 6. KDJ信号
    val, sig = score_kdj_signal(ind, mode)
    factor_scores["kdj_signal"] = val
    signals.append(sig)

    # 7. 价格位置
    val, sig = score_price_position(ind, mode, price)
    factor_scores["price_position"] = val
    signals.append(sig)

    # 8. 高低位置
    val, sig = score_near_high_low(ind, mode)
    factor_scores["near_high_low"] = val
    signals.append(sig)

    # 9. 当日涨幅
    val, sig = score_daily_change(ind, s, mode)
    factor_scores["daily_change"] = val
    signals.append(sig)

    # 10. MA5支撑 (仅低位模式)
    if mode == SCAN_MODE_LOW:
        val, sig = score_ma5_stability(ind, mode)
        factor_scores["ma5_stability"] = val
        if sig:
            signals.append(sig)

    # 加权总分
    total_weight = 0
    weighted_score = 0
    for factor, (weight, name, desc) in weights.items():
        if factor in factor_scores:
            fscore = factor_scores[factor]
            weighted_score += weight * fscore * 100
            total_weight += weight

    # 归一化到 0-100
    if total_weight > 0:
        final_score = (weighted_score / total_weight) + 50
    else:
        final_score = 50

    final_score = max(0, min(100, final_score))

    # 过滤无用信号
    signals = [s for s in signals if s and s not in ("KDJ中性", "布林位置中性", "中性")]

    return final_score, signals


# ════════════════════════════════════════════════════════════
#  市场扫描入口
# ════════════════════════════════════════════════════════════

def screen_market(mode: str = SCAN_MODE_TOPS, max_candidates: int = 30) -> list[dict]:
    """全市场筛选, 根据模式返回候选股"""
    print(f"  📡 正在扫描全市场 ({mode})...")

    stocks = _fetch_all_stocks()
    if not stocks:
        print("  ❌ 市场数据获取失败")
        return []

    print(f"  📊 全市场 {len(stocks)} 只股票, 正在筛选...")

    if mode == SCAN_MODE_TOPS:
        stocks.sort(key=lambda s: s.get("change_pct", 0), reverse=True)
        return stocks[:max_candidates]

    filtered = _basic_filter(stocks)
    filtered.sort(key=lambda s: s.get("turnover", 0), reverse=True)
    pool = filtered[:80]

    print(f"  🔬 正在计算 {len(pool)} 只候选股的技术指标...")

    scored = _score_candidates_batch(pool, mode)
    scored.sort(key=lambda s: s.get("score", 0), reverse=True)

    results = scored[:max_candidates]

    print(f"  ✅ 筛选完成, TOP {len(results)} 如下:\n")
    for r in results[:10]:
        icon = "🔥" if mode == SCAN_MODE_MOMENTUM else "💎"
        print(f"  {icon} {r.get('name','')} ({r.get('code','')}) "
              f"评分:{r.get('score',0):.1f} 涨幅:{r.get('change_pct',0):.1f}% "
              f"RSI:{r.get('rsi','?')} 量比:{r.get('vol_ratio','?')}")

    return results


# ════════════════════════════════════════════════════════════
#  以下函数保持与之前一致
# ════════════════════════════════════════════════════════════

def _fetch_all_stocks() -> list[dict]:
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
    filtered = []
    for s in stocks:
        price = s.get("price", 0)
        turnover = s.get("turnover", 0)
        change = s.get("change_pct", 0)
        code = s.get("code", "")
        if price < 3:
            continue
        if turnover < 30_000_000:
            continue
        if change <= -9.5 or change >= 9.5:
            continue
        if not code.isdigit():
            continue
        filtered.append(s)
    return filtered


def _score_candidates_batch(stocks: list[dict], mode: str) -> list[dict]:
    results = []
    count = 0
    try:
        import baostock as bs
        import datetime
        import pandas as pd

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

            from data.indicators import compute_indicators
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


def _f(v) -> float:
    try:
        return round(float(v), 2)
    except (ValueError, TypeError):
        return 0.0
