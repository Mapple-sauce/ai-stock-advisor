"""技术指标计算"""

from __future__ import annotations

import pandas as pd


def compute_indicators(df: pd.DataFrame) -> dict:
    """从 K 线数据计算技术指标"""
    if df is None or df.empty or len(df) < 10:
        return {"error": "数据不足"}

    close = df["收盘"].astype(float)
    high = df["最高"].astype(float)
    low = df["最低"].astype(float)
    volume = df["成交量"].astype(float)

    # ── 均线 ──
    ma5 = close.rolling(5).mean().iloc[-1]
    ma10 = close.rolling(10).mean().iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None
    latest_close = close.iloc[-1]

    # ── MACD ──
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    macd_hist = (dif - dea).iloc[-1]
    macd_dif = dif.iloc[-1]
    macd_dea = dea.iloc[-1]
    macd_bullish = macd_hist > 0  # 红柱
    macd_golden_cross = dif.iloc[-2] < dea.iloc[-2] and dif.iloc[-1] > dea.iloc[-1]
    macd_death_cross = dif.iloc[-2] > dea.iloc[-2] and dif.iloc[-1] < dea.iloc[-1]

    # ── RSI ──
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi14 = (100 - 100 / (1 + rs)).iloc[-1]

    # ── KDJ ──
    low_9 = low.rolling(9).min()
    high_9 = high.rolling(9).max()
    rsv = (close - low_9) / (high_9 - low_9).replace(0, float("nan")) * 100
    k = rsv.ewm(com=2).mean().iloc[-1]
    d = k if pd.isna(k) else (rsv.ewm(com=2).mean().ewm(com=2).mean().iloc[-1])
    j = 3 * k - 2 * d if not pd.isna(k) and not pd.isna(d) else 50

    # ── 布林带 ──
    bb_mid = close.rolling(20).mean().iloc[-1]
    bb_std = close.rolling(20).std().iloc[-1]
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    # ── 量价分析 ──
    vol_ma5 = volume.rolling(5).mean().iloc[-1]
    vol_ma20 = volume.rolling(20).mean().iloc[-1]
    vol_ratio = latest_close / vol_ma20 if vol_ma20 > 0 else 1.0
    price_position = (latest_close - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5

    # ── 走势形态 ──
    high_20 = high.tail(20).max()
    low_20 = low.tail(20).min()
    near_high = (latest_close / high_20) > 0.95

    return {
        "price": round(latest_close, 2),
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2),
        "ma20": round(ma20, 2),
        "ma60": round(ma60, 2) if ma60 else None,
        "ma_trend": "多头排列" if ma5 > ma10 > ma20 else "空头排列" if ma5 < ma10 < ma20 else "缠绕/整理",
        "macd_dif": round(macd_dif, 4),
        "macd_dea": round(macd_dea, 4),
        "macd_hist": round(macd_hist, 4),
        "macd_bullish": bool(macd_bullish),
        "macd_golden_cross": bool(macd_golden_cross),
        "macd_death_cross": bool(macd_death_cross),
        "rsi14": round(rsi14, 2),
        "rsi_status": "超买" if rsi14 > 80 else "超卖" if rsi14 < 20 else "正常",
        "kdj_k": round(k, 2),
        "kdj_d": round(d, 2),
        "kdj_j": round(j, 2),
        "bb_upper": round(bb_upper, 2),
        "bb_mid": round(bb_mid, 2),
        "bb_lower": round(bb_lower, 2),
        "price_in_bb": "上轨附近" if price_position > 0.8 else "下轨附近" if price_position < 0.2 else "中轨附近",
        "vol_ratio": round(vol_ratio, 2),
        "vol_status": "放量" if vol_ratio > 1.5 else "缩量" if vol_ratio < 0.6 else "正常",
        "near_20d_high": bool(near_high),
        "high_20d": round(high_20, 2),
        "low_20d": round(low_20, 2),
    }
