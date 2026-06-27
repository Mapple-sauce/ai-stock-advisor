"""回测优化引擎 —— 快速因子评分回测 + 权重自动调优

包含分红调整: 总收益 = 价差收益 + 持有期间分红

样本集: 覆盖不同板块/市值的 A 股 (非全市场, 但具有代表性)
  - 大型蓝筹: 茅台, 招行, 平安
  - 成长龙头: 宁德时代, 比亚迪, 中际旭创
  - 二线股: 北方华创, 汇川技术, 恒瑞医药
  - 银行股: 平安银行, 招商银行
"""

from __future__ import annotations

import datetime

import pandas as pd
from data.indicators import compute_indicators

# ── 数据缓存 ──
_kline_cache: dict[str, pd.DataFrame] = {}
_div_cache: dict[str, list[dict]] = {}

# ── 代表性样本池 (15只, 覆盖不同板块/市值) ──
TEST_POOL = [
    "600519", "300750", "000001", "300308", "002594",
    "600036", "600276", "002371", "601318", "000333",
    "002415", "601012", "300124", "600030", "688981",
]

# ── 回测日期池 (15个随机月份, 避免过拟合) ──
TEST_DATES = [
    "2024-01-15", "2024-03-18", "2024-06-17", "2024-09-16", "2024-12-16",
    "2025-02-17", "2025-04-14", "2025-06-16", "2025-08-18", "2025-10-20",
    "2025-12-15", "2026-01-12", "2026-03-16", "2026-04-13", "2026-05-18",
]


def _ensure_data(symbols: list[str]) -> None:
    """预加载K线和分红数据"""
    import baostock as bs
    bs.login()

    # 加载K线
    need = [s for s in symbols if s not in _kline_cache]
    if need:
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
                    _kline_cache[s] = df.sort_values("date").reset_index(drop=True)

    # 加载分红 (各年份)
    div_need = [s for s in symbols if s not in _div_cache]
    if div_need:
        _load_all_dividends(div_need)

    bs.logout()


def _load_all_dividends(symbols: list[str]) -> None:
    """加载多只股票多年的分红数据"""
    import baostock as bs

    for s in symbols:
        dividends = []
        for year in ["2022", "2023", "2024", "2025", "2026"]:
            code = _to_bs_code(s)
            rs = bs.query_dividend_data(code, year=year)
            if rs.error_code == "0":
                data = rs.get_data()
                if data is not None and not data.empty:
                    for _, r in data.iterrows():
                        ex_date = str(r.get("dividOperateDate", "")).strip()
                        ps_str = str(r.get("dividCashPsBeforeTax", "0")).strip()
                        if ex_date and ex_date != "None" and ps_str:
                            try:
                                ps = float(ps_str)
                                dividends.append({"ex_date": ex_date, "amount": ps, "year": year})
                            except (ValueError, TypeError):
                                pass
        _div_cache[s] = sorted(dividends, key=lambda d: d["ex_date"])


def _kline_for(symbol: str, as_of: str) -> pd.DataFrame | None:
    """获取指定日期前的K线 (中文列名)"""
    if symbol not in _kline_cache:
        return None
    df = _kline_cache[symbol].copy()
    df = df[df["date"] < as_of]
    if len(df) < 30:
        return None
    return df.tail(60).rename(columns={
        "date": "日期", "open": "开盘", "high": "最高",
        "low": "最低", "close": "收盘", "volume": "成交量", "amount": "成交额",
    }).reset_index(drop=True)


def _total_return(symbol: str, as_of: str, hold_days: int) -> dict | None:
    """获取指定日期后的总收益 = 价差收益 + 分红收益"""
    if symbol not in _kline_cache:
        return None

    df = _kline_cache[symbol].copy()
    fut = df[df["date"] >= as_of]
    if len(fut) < 2:
        return None

    entry = float(fut.iloc[0]["close"])
    if entry <= 0:
        return None

    ei = min(hold_days, len(fut) - 1)
    exit_price = float(fut.iloc[ei]["close"])
    exit_date = str(fut.iloc[ei]["date"])

    # 价差收益
    price_return = (exit_price - entry) / entry * 100

    # 分红收益 (持有期间内的分红)
    div_per_share = 0
    if symbol in _div_cache:
        for d in _div_cache[symbol]:
            if as_of <= d["ex_date"] <= exit_date:
                div_per_share += d["amount"]

    div_return = (div_per_share / entry) * 100 if entry > 0 else 0
    total_ret = price_return + div_return

    return {
        "entry": round(entry, 2),
        "exit": round(exit_price, 2),
        "price_return": round(price_return, 2),
        "div_per_share": round(div_per_share, 3),
        "div_return": round(div_return, 2),
        "return_pct": round(total_ret, 2),
    }


def backtest_factor_weights(
    symbols: list[str], dates: list[str],
    weights: dict, mode: str = "low_position", hold_days: int = 20,
    include_dividends: bool = True,
) -> dict:
    """回测一组权重配置 (含分红调整)"""
    _ensure_data(symbols)

    total = correct = 0
    buy_ret, avoid_ret, pairs, details = [], [], [], []

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

            fut = _total_return(sym, date, hold_days)
            if fut is None:
                continue

            score = _score_fast(entry, ind, weights, mode)

            if score >= 68:
                act = "买入"
            elif score >= 58:
                act = "建议关注"
            elif score >= 45:
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
            details.append({
                "symbol": sym, "date": date, "score": round(score, 1),
                "action": act, "total_return": ret, "price_return": fut["price_return"],
                "div_return": fut["div_return"], "correct": ok,
            })

    if total == 0:
        return {"error": "无有效测试"}

    ba = sum(buy_ret) / len(buy_ret) if buy_ret else 0
    aa = sum(avoid_ret) / len(avoid_ret) if avoid_ret else 0

    # 分红影响统计
    total_div = sum(f["div_return"] for f in details)

    return {
        "total_tests": total,
        "correct_count": correct,
        "accuracy_pct": round(correct / total * 100, 1),
        "buy_avg_return": round(ba, 2),
        "buy_count": len(buy_ret),
        "avoid_avg_return": round(aa, 2),
        "avoid_count": len(avoid_ret),
        "spread": round(ba - aa, 2),
        "score_correlation": _corr(pairs),
        "avg_return": round(sum(r for _, r in pairs) / total, 2),
        "avg_div_return": round(total_div / total, 2) if total else 0,
        "mode": mode,
    }


def score_config(result: dict) -> float:
    """综合评分一个配置的好坏"""
    if "error" in result:
        return -999
    acc = result.get("accuracy_pct", 0)
    spread = result.get("spread", 0)
    total = result.get("total_tests", 0)
    if total < 30:
        return -500
    acc_score = (acc - 45) * 0.5
    spread_score = spread * 1.0
    corr = result.get("score_correlation", 0) * 20
    size_bonus = min(total / 100, 1.0)
    return round(acc_score + spread_score + corr + size_bonus, 2)


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
    raw = (ws / tw + 50) if tw else 50
    return max(0, min(100, 100 - raw))


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
    if any(s.startswith(p) for p in ("sh.", "sz.", "bj.")):
        return s
    if any(s.startswith(p) for p in ("sh", "sz", "bj")):
        return f"{s[:2]}.{s[2:]}"
    if s.isdigit():
        return f"{'sh' if s.startswith(('6', '9')) else 'sz'}.{s}"
    return s


def find_optimal_weights(
    symbols: list[str] | None = None,
    mode: str = "low_position",
    lookback_months: int = 6,
    hold_days: int = 20,
    iterations: int = 20000,
) -> dict:
    """自动寻优：在最近N个月的数据上找到最优权重组合

    算法:
      1. 筛选最近 N 个月的回测日期
      2. 随机生成 20000 组权重配置 (Dirichlet 分布)
      3. 用 score_config() 评分选出最优权重
      4. 返回最优权重 + 准确率 + 多空差

    Returns:
        {"weights": {因子: (w, name, note), ...},
         "accuracy_pct": 准确率,
         "spread": 多空差,
         "total_tests": 测试次数}
    """
    if symbols is None:
        symbols = TEST_POOL[:10]

    # 筛选最近 N 个月的日期
    cutoff = datetime.date.today()
    cutoff = cutoff.replace(day=1)
    for _ in range(lookback_months):
        cutoff -= datetime.timedelta(days=30)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    recent_dates = [d for d in TEST_DATES if d >= cutoff_str][:8]
    if len(recent_dates) < 3:
        recent_dates = TEST_DATES[-6:]  # 兜底: 用最近6个
    
    weights_keys = [
        "ma_trend", "macd_signal", "rsi_position", "volume_ratio",
        "bb_position", "kdj_signal", "price_position", "near_high_low",
        "daily_change", "ma5_stability",
    ]
    factor_names = {
        "ma_trend": "均线趋势", "macd_signal": "MACD信号", "rsi_position": "RSI位置",
        "volume_ratio": "量价关系", "bb_position": "布林位置", "kdj_signal": "KDJ信号",
        "price_position": "价格位置", "near_high_low": "高低位置",
        "daily_change": "当日涨幅", "ma5_stability": "MA5支撑",
    }

    # 加载数据
    _ensure_data(symbols)

    # 预计算所有股票在所有日期上的因子分数 (加速)
    cache = {}  # {(sym, date): factor_scores_dict}
    for sym in symbols:
        for date in recent_dates:
            kdf = _kline_for(sym, date)
            if kdf is None:
                continue
            ind = compute_indicators(kdf)
            if "error" in ind:
                continue
            entry = float(kdf.iloc[-1]["收盘"])
            fut = _total_return(sym, date, hold_days)
            if fut is None:
                continue
            # 预计算因子分
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
                "price_position": score_price_position(ind, mode, entry)[0],
                "near_high_low": score_near_high_low(ind, mode)[0],
                "daily_change": score_daily_change(ind, {"price": entry, "change_pct": 0}, mode)[0],
                "ma5_stability": score_ma5_stability(ind, mode)[0],
            }
            cache[(sym, date)] = (fs, fut["return_pct"])

    if not cache:
        return {"error": "No data available"}

    print(f"   已预计算 {len(cache)} 组因子数据, 开始搜索最优配置...")

    # 随机搜索: Dirichlet 分布生成随机权重
    import random
    seed = 42
    random.seed(seed)

    best_score = -999
    best_weights = None
    best_result = None
    total_data = list(cache.values())

    REPORT_INTERVAL = max(1, iterations // 20)

    for i in range(iterations):
        # 用 Dirichlet 分布生成随机权重 (所有权重和为1)
        raw_ws = [random.expovariate(1) for _ in weights_keys]
        total_w = sum(raw_ws)
        ws = [w / total_w for w in raw_ws]

        # 计算评分
        correct = 0
        total = 0
        buy_ret, avoid_ret = [], []
        for fs, ret in total_data:
            tw = 0
            ws_total = 0
            for w, key in zip(ws, weights_keys):
                if key in fs:
                    ws_total += w * fs[key] * 100
                    tw += w
            raw = (ws_total / tw + 50) if tw else 50
            score = max(0, min(100, 100 - raw))

            if score >= 68:
                act = "买入"
            elif score >= 58:
                act = "建议关注"
            elif score >= 45:
                act = "观望"
            else:
                act = "回避"

            total += 1
            if (act in ("买入", "建议关注") and ret > 0) or (act == "回避" and ret < 0) or (act == "观望" and abs(ret) < 3):
                correct += 1

        acc = correct / total * 100
        # 简单评分: 准确率 - 50 + 多空差/5
        sc = (acc - 50)

        if sc > best_score:
            best_score = sc
            best_weights = {k: (w, factor_names.get(k, k), "") for k, w in zip(weights_keys, ws)}
            best_result = {"accuracy_pct": round(acc, 1), "total_tests": total}

        if (i + 1) % REPORT_INTERVAL == 0:
            print(f"     进度 {i+1}/{iterations}  当前最优: 准确率 {best_result['accuracy_pct']}%")

    # 用最优权重跑一次完整回测
    final_weights = {f: (w, name, note) for f, (w, name, note) in best_weights.items()}
    
    # 验证
    verify_total = 0
    verify_correct = 0
    verify_buy, verify_avoid = [], []
    for fs, ret in total_data:
        tw = ws_v = 0
        for f, (w, _, _) in final_weights.items():
            if f in fs:
                ws_v += w * fs[f] * 100
                tw += w
        raw = (ws_v / tw + 50) if tw else 50
        score = max(0, min(100, 100 - raw))
        
        if score >= 68: act = "买入"
        elif score >= 58: act = "建议关注"
        elif score >= 45: act = "观望"
        else: act = "回避"
        
        verify_total += 1
        if (act in ("买入","建议关注") and ret > 0) or (act == "回避" and ret < 0) or (act == "观望" and abs(ret) < 3):
            verify_correct += 1
        if act in ("买入","建议关注"):
            verify_buy.append(ret)
        elif act == "回避":
            verify_avoid.append(ret)

    ba = sum(verify_buy)/len(verify_buy) if verify_buy else 0
    aa = sum(verify_avoid)/len(verify_avoid) if verify_avoid else 0

    return {
        "weights": final_weights,
        "accuracy_pct": round(verify_correct / verify_total * 100, 1),
        "spread": round(ba - aa, 2),
        "total_tests": verify_total,
        "buy_count": len(verify_buy),
        "avoid_count": len(verify_avoid),
        "buy_avg_return": round(ba, 2),
        "avoid_avg_return": round(aa, 2),
        "lookback_months": lookback_months,
        "iterations": iterations,
    }
