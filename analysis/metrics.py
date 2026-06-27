"""个股核心指标计算 —— 最大回撤、夏普比率、波动率、收益表现等

所有函数接收 pandas DataFrame（含日期/收盘/最高/最低列）或 numpy 数组，
纯数学计算，无外部网络依赖。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_all_metrics(df: pd.DataFrame) -> dict:
    """从 K 线数据计算个股全维度指标

    Args:
        df: 包含 日期/收盘/最高/最低/成交量 列的 DataFrame

    Returns:
        包含收益率、风险、技术指标的综合字典
    """
    if df is None or df.empty or len(df) < 20:
        return {"error": "数据不足，至少需要 20 个交易日"}

    # 提取核心序列
    close = df["收盘"].values.astype(float)
    high = df["最高"].values.astype(float)
    low = df["最低"].values.astype(float)
    volume = df["成交量"].values.astype(float) if "成交量" in df.columns else None
    dates = df["日期"].values if "日期" in df.columns else None
    n = len(close)

    # 日收益率
    daily_returns = np.diff(close) / close[:-1]

    # 交易天数常量
    TRADING_DAYS = 252

    # ── 收益表现 ──
    idx = {d: i for i, d in enumerate(dates)} if dates is not None else {}
    result = {
        "return_1m": _period_return(close, 21),
        "return_3m": _period_return(close, 63),
        "return_6m": _period_return(close, 126),
        "return_1y": _period_return(close, 252),
        "ytd_return": _ytd_return(close, dates),
        "cagr_3y": _cagr(close, 3 * TRADING_DAYS) if n >= 3 * TRADING_DAYS else None,
    }

    # ── 风险指标 ──
    dd = _max_drawdown(close)
    result.update({
        "max_drawdown": dd,
        "current_drawdown": _current_drawdown(close),
    })

    # 波动率
    if len(daily_returns) >= 30:
        vol_30d = np.std(daily_returns[-30:]) * np.sqrt(TRADING_DAYS) * 100
        result["volatility_30d"] = round(vol_30d, 2)
    else:
        result["volatility_30d"] = None

    if len(daily_returns) >= 252:
        vol_1y = np.std(daily_returns[-252:]) * np.sqrt(TRADING_DAYS) * 100
        result["volatility_1y"] = round(vol_1y, 2)
    else:
        vol_all = np.std(daily_returns) * np.sqrt(TRADING_DAYS) * 100
        result["volatility_1y"] = round(vol_all, 2) if len(daily_returns) > 20 else None

    # 夏普比率 (假设无风险利率 2%)
    rf = 0.02
    if len(daily_returns) >= 252:
        excess = daily_returns[-252:] - rf / TRADING_DAYS
        sharpe = np.mean(excess) / np.std(excess) * np.sqrt(TRADING_DAYS) if np.std(excess) > 0 else 0
        result["sharpe_ratio"] = round(sharpe, 2)
    else:
        excess = daily_returns - rf / TRADING_DAYS
        sharpe = np.mean(excess) / np.std(excess) * np.sqrt(TRADING_DAYS) if np.std(excess) > 0 else 0
        result["sharpe_ratio"] = round(sharpe, 2) if len(daily_returns) > 20 else None

    # 卡玛比率
    cagr_3y = result.get("cagr_3y")
    if cagr_3y is None:
        total_ret = (close[-1] / close[0] - 1) * 100
        cagr_val = total_ret / (n / TRADING_DAYS) if n > 0 else None
    else:
        cagr_val = cagr_3y
    mdd_val = abs(dd.get("max_dd_pct", 1))
    result["calmar_ratio"] = round(cagr_val / mdd_val, 2) if mdd_val > 0 else None

    # 索提诺比率 (只考虑下行波动)
    if len(daily_returns) >= 21:
        downside = daily_returns[daily_returns < 0]
        downside_std = np.std(downside) * np.sqrt(TRADING_DAYS) if len(downside) > 0 else 0.01
        total_ret_pct = (close[-1] / close[0] - 1) * 100
        annual_return = total_ret_pct / (n / TRADING_DAYS) / 100
        sortino = (annual_return - rf) / downside_std if downside_std > 0 else 0
        result["sortino_ratio"] = round(sortino, 2)
    else:
        result["sortino_ratio"] = None

    # ── 均线位置 ──
    ma_pos = {}
    for period in [5, 10, 20, 60, 120, 250]:
        if n >= period:
            ma_val = np.mean(close[-period:])
            dist = (close[-1] - ma_val) / ma_val * 100
            ma_pos[f"ma{period}"] = {
                "value": round(ma_val, 2),
                "distance_pct": round(dist, 2),
                "above": dist > 0,
            }
        else:
            ma_pos[f"ma{period}"] = None
    result["ma_position"] = ma_pos

    # ATR (平均真实波幅)
    result["atr14"] = _atr(high, low, close, 14)

    # 支撑/阻力位
    result["support_resistance"] = _support_resistance(high, low, close)

    # 盈亏比 (过去 1 年涨幅 vs 跌幅)
    result["win_loss_ratio"] = _win_loss_ratio(daily_returns)

    # 成交量分析
    if volume is not None and n >= 20:
        vol_ma20 = np.mean(volume[-20:])
        vol_ma5 = np.mean(volume[-5:]) if n >= 5 else vol_ma20
        result["volume_ratio_5_20"] = round(vol_ma5 / vol_ma20, 2) if vol_ma20 > 0 else 1.0
    else:
        result["volume_ratio_5_20"] = None

    # 价格位置 (52周高/低位)
    if n >= 252:
        high_52w = np.max(close[-252:])
        low_52w = np.min(close[-252:])
    else:
        high_52w = np.max(close)
        low_52w = np.min(close)
    pos_52w = (close[-1] - low_52w) / (high_52w - low_52w) * 100 if high_52w > low_52w else 50
    result["position_52w_pct"] = round(pos_52w, 1)
    result["high_52w"] = round(high_52w, 2)
    result["low_52w"] = round(low_52w, 2)

    return result


# ════════════════════════════════════════════════════════════
#  内部辅助函数
# ════════════════════════════════════════════════════════════


def _period_return(close: np.ndarray, days: int) -> float | None:
    """计算最近 days 个交易日的累计收益率（%）"""
    if len(close) <= days:
        return None
    ret = (close[-1] / close[-(days + 1)] - 1) * 100
    return round(ret, 2)


def _ytd_return(close: np.ndarray, dates: np.ndarray) -> float | None:
    """年初至今收益率（%）"""
    if dates is None or len(dates) != len(close):
        return None
    try:
        # 找今年第一个交易日
        year = str(dates[-1])[:4]
        ytd_indices = [i for i, d in enumerate(dates) if str(d)[:4] == year]
        if not ytd_indices or len(dates) - ytd_indices[0] < 2:
            return None
        first_idx = ytd_indices[0]
        ret = (close[-1] / close[first_idx] - 1) * 100
        return round(ret, 2)
    except Exception:
        return None


def _cagr(close: np.ndarray, trading_days: int) -> float | None:
    """年化复合收益率（%）"""
    if len(close) < trading_days + 1:
        return None
    years = trading_days / 252
    total_ret = close[-1] / close[-(trading_days + 1)] - 1
    cagr = (pow(1 + total_ret, 1 / years) - 1) * 100
    return round(cagr, 2)


def _max_drawdown(close: np.ndarray) -> dict:
    """最大回撤计算

    返回:
        max_dd_pct: 最大回撤百分比 (如 -45.2)
        peak_price: 最高点价格
        trough_price: 最低点价格
        duration_days: 最大回撤持续天数
    """
    peak = np.maximum.accumulate(close)
    drawdown = (close - peak) / peak * 100

    max_dd_idx = np.argmin(drawdown)
    max_dd = drawdown[max_dd_idx]
    peak_idx = np.argmax(close[:max_dd_idx + 1])

    # 持续时间：从峰值到恢复超过原峰值的天数
    duration = 0
    for i in range(max_dd_idx, len(close)):
        if close[i] >= close[peak_idx]:
            duration = i - peak_idx
            break
    else:
        duration = len(close) - peak_idx  # 尚未恢复

    return {
        "max_dd_pct": round(max_dd, 2),
        "peak_price": round(float(close[peak_idx]), 2),
        "trough_price": round(float(close[max_dd_idx]), 2),
        "duration_days": duration,
    }


def _current_drawdown(close: np.ndarray) -> float:
    """当前回撤（距最近高点）%"""
    peak_since = np.max(close[-252:]) if len(close) >= 252 else np.max(close)
    dd = (close[-1] - peak_since) / peak_since * 100
    return round(dd, 2)


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float | None:
    """平均真实波幅 (ATR)"""
    if len(close) < period + 1:
        return None
    tr = np.zeros(len(close) - 1)
    for i in range(1, len(close)):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i - 1] = max(hl, hc, lc)
    atr_val = np.mean(tr[-period:])
    return round(atr_val, 2)


def _support_resistance(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> dict:
    """关键支撑位和阻力位

    使用过去 252 个交易日（或全部可用数据）中的密集成交区
    """
    n = min(252, len(close))
    recent_high = np.max(high[-n:])
    recent_low = np.min(low[-n:])
    current = close[-1]

    # 支撑位：近期低点、MA60、MA120
    supports = []
    for level in [
        ("近期低点", recent_low),
        ("MA60", np.mean(close[-60:]) if len(close) >= 60 else None),
        ("MA120", np.mean(close[-120:]) if len(close) >= 120 else None),
        ("MA250", np.mean(close[-250:]) if len(close) >= 250 else None),
    ]:
        if level[1] is not None and level[1] < current:
            supports.append({"name": level[0], "price": round(level[1], 2)})

    # 阻力位：近期高点、MA60以上
    resistances = []
    for level in [
        ("近期高点", recent_high),
        ("MA60", np.mean(close[-60:]) if len(close) >= 60 else None),
        ("MA120", np.mean(close[-120:]) if len(close) >= 120 else None),
    ]:
        if level[1] is not None and level[1] > current:
            resistances.append({"name": level[0], "price": round(level[1], 2)})

    # 按价格排序
    supports.sort(key=lambda x: x["price"], reverse=True)
    resistances.sort(key=lambda x: x["price"])

    return {
        "supports": supports[:3],
        "resistances": resistances[:3],
        "recent_high": round(recent_high, 2),
        "recent_low": round(recent_low, 2),
    }


def _win_loss_ratio(daily_returns: np.ndarray) -> dict:
    """盈亏比统计

    返回:
        win_rate: 上涨交易日占比
        avg_win: 平均涨幅
        avg_loss: 平均跌幅
        win_loss_ratio: 盈亏比
    """
    if len(daily_returns) == 0:
        return {"win_rate": 0, "win_loss_ratio": 0}

    wins = daily_returns[daily_returns > 0]
    losses = daily_returns[daily_returns < 0]

    win_rate = len(wins) / len(daily_returns) * 100 if len(daily_returns) > 0 else 0
    avg_win = np.mean(wins) * 100 if len(wins) > 0 else 0
    avg_loss = abs(np.mean(losses)) * 100 if len(losses) > 0 else 1
    wl_ratio = avg_win / avg_loss if avg_loss > 0 else 0

    return {
        "win_rate": round(win_rate, 1),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "win_loss_ratio": round(wl_ratio, 2),
    }
