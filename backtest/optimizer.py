"""回测优化引擎 —— 快速因子评分回测 + 权重自动调优

不调 AI API, 只用量化因子评分 (免费、快速)
支持随机抽取历史时间段, 避免过拟合
"""

from __future__ import annotations

import datetime

import pandas as pd
from data.indicators import compute_indicators

_cache: dict[str, pd.DataFrame] = {}


def _ensure_data(symbols: list[str]) -> None:
    """批量预加载所有股票的K线数据 (缓存)"""
    import baostock as bs

    need = [s for s in symbols if s not in _cache]
    if not need:
        return

    bs.login()
    end = datetime.date.today()
    start = end - datetime.timedelta(days=700)

    for s in need:
        code = _to_bs_code(s)
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume,amount",
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            frequency="d", adjustflag="3",
        )
        if rs.error_code == "0":
            df = rs.get_data()
            if df is not None and not df.empty:
                for col in ["open", "high", "low", "close", "volume", "amount"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.sort_values("date").reset_index(drop=True)
                _cache[s] = df

    bs.logout()


def _kline_for(symbol: str, as_of: str) -> pd.DataFrame | None:
    """获取指定日期前的K线 (已转为中文列名给 indicators.py)"""
    if symbol not in _cache:
        return None
    df = _cache[symbol].copy()
    df = df[df["date"] < as_of]
    if len(df) < 30:
        return None
    df = df.tail(60).rename(columns={
        "date": "日期", "open": "开盘", "high": "最高",
        "low": "最低", "close": "收盘", "volume": "成交量", "amount": "成交额",
    }).reset_index(drop=True)
    return df


def _future_return(symbol: str, as_of: str, hold_days: int) -> dict | None:
    """获取指定日期后的实际涨跌幅"""
    if symbol not in _cache:
        return None
    df = _cache[symbol].copy()
    fut = df[df["date"] >= as_of]
    if len(fut) < 2:
        return None
    entry = float(fut.iloc[0]["close"])
    if entry <= 0:
        return None
    ei = min(hold_days, len(fut) - 1)
    exit_price = float(fut.iloc[ei]["close"])
    ret = (exit_price - entry) / entry * 100
    return {"entry": round(entry, 2), "exit": round(exit_price, 2),
            "return_pct": round(ret, 2)}


def backtest_factor_weights(
    symbols: list[str], dates: list[str],
    weights: dict, mode: str = "low_position", hold_days: int = 20,
) -> dict:
    """回测一组权重配置"""
    _ensure_data(symbols)

    total = correct = 0
    buy_ret, avoid_ret, pairs = [], [], []

    for date in dates:
        for sym in symbols:
            kdf = _kline_for(sym, date)
            if kdf is None:
                continue
            ind = compute_indicators(kdf)
            if "error" in ind:
                continue
            entry = float(kdf.iloc[-1]["收盘"])
            if entry <= 0:
                continue

            fut = _future_return(sym, date, hold_days)
            if fut is None:
                continue

            score = _score_fast(entry, ind, weights, mode)

            if score >= 64:
                act = "买入"
            elif score >= 54:
                act = "建议关注"
            elif score >= 40:
                act = "观望"
            else:
                act = "回避"

            ret = fut["return_pct"]
            if act in ("买入", "建议关注"):
                ok = ret > 0
            elif act == "回避":
                ok = ret < 0
            else:
                ok = abs(ret) < 3

            total += 1
            if ok:
                correct += 1
            pairs.append((score, ret))
            if act in ("买入", "建议关注"):
                buy_ret.append(ret)
            elif act == "回避":
                avoid_ret.append(ret)

    if total == 0:
        return {"error": "无有效测试"}

    ba = sum(buy_ret) / len(buy_ret) if buy_ret else 0
    aa = sum(avoid_ret) / len(avoid_ret) if avoid_ret else 0

    return {
        "total_tests": total, "correct_count": correct,
        "accuracy_pct": round(correct / total * 100, 1),
        "buy_avg_return": round(ba, 2), "buy_count": len(buy_ret),
        "avoid_avg_return": round(aa, 2), "avoid_count": len(avoid_ret),
        "spread": round(ba - aa, 2),
        "score_correlation": _corr(pairs),
        "avg_return": round(sum(r for _, r in pairs) / total, 2),
    }


def _score_fast(price: float, ind: dict, weights: dict, mode: str) -> float:
    from scanner.screener import (
        score_ma_trend, score_macd_signal, score_rsi_position,
        score_volume_ratio, score_bb_position, score_kdj_signal,
        score_price_position, score_near_high_low, score_daily_change,
        score_ma5_stability,
    )
    fs = {
        "ma_trend": score_ma_trend(ind, mode)[0],
        "macd_signal": score_macd_signal(ind, mode)[0],
        "rsi_position": score_rsi_position(ind, mode)[0],
        "volume_ratio": score_volume_ratio(ind, mode)[0],
        "bb_position": score_bb_position(ind, mode)[0],
        "kdj_signal": score_kdj_signal(ind, mode)[0],
        "price_position": score_price_position(ind, mode, price)[0],
        "near_high_low": score_near_high_low(ind, mode)[0],
        "daily_change": score_daily_change(ind, {"price": price, "change_pct": 0}, mode)[0],
    }
    if mode == "low_position":
        fs["ma5_stability"] = score_ma5_stability(ind, mode)[0]

    tw = ws = 0
    for f, (w, _, _) in weights.items():
        if f in fs:
            ws += w * fs[f] * 100
            tw += w
    return max(0, min(100, (ws / tw + 50))) if tw else 50


def _corr(pairs: list) -> float:
    if len(pairs) < 3:
        return 0
    import math
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxy = sum(x * y for x, y in pairs)
    sxx = sum(x * x for x in xs)
    syy = sum(y * y for y in ys)
    d = math.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy))
    return round((n * sxy - sx * sy) / d, 3) if d else 0


def _to_bs_code(symbol: str) -> str:
    s = symbol.strip()
    if s.startswith(("sh.", "sz.", "bj.")):
        return s
    if any(s.startswith(p) for p in ("sh", "sz", "bj")):
        return f"{s[:2]}.{s[2:]}"
    if s.isdigit():
        return f"{'sh' if s.startswith(('6', '9')) else 'sz'}.{s}"
    return s
