"""回测引擎 —— 用历史数据检验模型预测准确率

核心逻辑:
  1. 选定一个历史日期 → 获取那之前的数据
  2. 让模型分析并输出建议 + 评分
  3. 对比后续实际走势
  4. 汇总统计: 准确率、盈亏比、相关性
"""

from __future__ import annotations

import datetime
import time
from typing import Any

from backtest.data import get_realtime_quote_as_of, get_kline_as_of, get_actual_return
from data.indicators import compute_indicators
from data.news import get_stock_news


def run_backtest(
    symbols: list[str],
    as_of_date: str,
    hold_days: int = 20,
) -> dict:
    """对多只股票在某个历史日期运行回测

    Args:
        symbols: 股票代码列表
        as_of_date: 回测日期 (YYYY-MM-DD), 模型只使用此日期前的数据
        hold_days: 持有天数, 用于计算后续收益

    Returns:
        {summary: {...}, results: [{...}]}
    """
    print(f"\n{'='*60}")
    print(f"  🔙 回测: {as_of_date} (持有{hold_days}天)")
    print(f"  📊 测试 {len(symbols)} 只股票")
    print(f"{'='*60}")

    results = []
    correct_count = 0
    total_score_return_corr = []

    for i, symbol in enumerate(symbols, 1):
        print(f"\n  [{i}/{len(symbols)}] {symbol} ...")
        result = _backtest_single(symbol, as_of_date, hold_days)
        results.append(result)

        # 打印简要结果
        action = result.get("predicted_action", "?")
        actual = result.get("actual_return_pct", 0)
        correct = result.get("correct", False)
        icon = "✅" if correct else "❌"
        print(f"    {icon} 预测:{action}  实际:{actual:+.2f}%  "
              f"{'正确' if correct else '错误'}")

        if correct:
            correct_count += 1
        score = result.get("predicted_score", 50)
        total_score_return_corr.append((score, actual))

    # 汇总统计
    total = len(results)
    accuracy = round(correct_count / total * 100, 1) if total > 0 else 0

    # 计算 Score-Return 相关性
    correlation = _calc_correlation(total_score_return_corr)

    # 按预测分组统计收益
    buy_returns = [r["actual_return_pct"] for r in results if r.get("predicted_action") in ("强烈推荐", "推荐买入")]
    avoid_returns = [r["actual_return_pct"] for r in results if r.get("predicted_action") in ("回避", "观望")]

    summary = {
        "as_of_date": as_of_date,
        "hold_days": hold_days,
        "total_stocks": total,
        "correct_count": correct_count,
        "accuracy_pct": accuracy,
        "score_return_correlation": correlation,
        "buy_avg_return": round(sum(buy_returns) / len(buy_returns), 2) if buy_returns else 0,
        "buy_count": len(buy_returns),
        "avoid_avg_return": round(sum(avoid_returns) / len(avoid_returns), 2) if avoid_returns else 0,
        "avoid_count": len(avoid_returns),
        "avg_return": round(sum(r["actual_return_pct"] for r in results) / total, 2) if total else 0,
    }

    print(f"\n{'='*60}")
    print(f"  📊 回测结果汇总")
    print(f"  {'='*60}")
    print(f"  总股票数:     {summary['total_stocks']}")
    print(f"  方向正确率:   {summary['accuracy_pct']}%")
    print(f"  Score相关性:  {summary['score_return_correlation']}")
    print(f"  推荐买入平均: {summary['buy_avg_return']:+.2f}% ({summary['buy_count']}只)")
    print(f"  回避/观望平均: {summary['avoid_avg_return']:+.2f}% ({summary['avoid_count']}只)")
    print(f"  全体平均:     {summary['avg_return']:+.2f}%")
    if summary['buy_count'] > 0 and summary['avoid_count'] > 0:
        diff = summary['buy_avg_return'] - summary['avoid_avg_return']
        print(f"  多空差:       {diff:+.2f}%")
    print(f"{'='*60}\n")

    return {"summary": summary, "results": results}


def _backtest_single(symbol: str, as_of_date: str, hold_days: int) -> dict:
    """对单只股票在某个日期运行回测"""
    result = {
        "code": symbol,
        "as_of_date": as_of_date,
        "predicted_action": "?",
        "predicted_score": 50,
        "predicted_reason": "",
    }

    # 1. 获取当时的行情 (模拟)
    quote = get_realtime_quote_as_of(symbol, as_of_date)
    if "error" in quote:
        result["error"] = quote["error"]
        result["actual_return_pct"] = 0
        result["correct"] = False
        return result

    result["name"] = quote.get("name", symbol)
    result["price_at_test"] = quote.get("price", 0)

    # 2. 获取当时的 K 线
    kline = get_kline_as_of(symbol, as_of_date, count=120)
    if kline.empty or len(kline) < 20:
        result["error"] = "K线数据不足"
        result["actual_return_pct"] = 0
        result["correct"] = False
        return result

    ind = compute_indicators(kline)
    result["rsi"] = ind.get("rsi14", "?")
    result["ma_trend"] = ind.get("ma_trend", "")

    # 3. 获取当时的新闻
    news = get_stock_news(symbol)

    # 4. 构建技术分析输入，让模型判断
    from agents.technical import technical_analyst
    from agents.risk import risk_analyst
    from chief import chief_agent

    # 构建技术分析输入
    tech_input = _build_tech_input(quote, ind)
    try:
        tech_report = technical_analyst.call(tech_input)
    except Exception as e:
        result["error"] = f"技术分析失败: {e}"
        result["actual_return_pct"] = 0
        result["correct"] = False
        return result

    # 风控分析
    risk_input = _build_risk_input(quote, ind)
    try:
        risk_report = risk_analyst.call(risk_input)
    except Exception as e:
        risk_report = f"(分析失败: {e})"

    # Chief 决策
    try:
        decision = chief_agent.decide_buy(
            stock_info=quote,
            technical=tech_report,
            fundamental="(回测模式: 基本面分析跳过)",
            sentiment=f"(回测模式: 新闻{len(news)}条)",
            risk=risk_report,
        )
    except Exception as e:
        result["error"] = f"决策失败: {e}"
        result["actual_return_pct"] = 0
        result["correct"] = False
        return result

    result["predicted_action"] = decision.get("action", "?")
    result["predicted_score"] = decision.get("final_score", 50)
    result["predicted_reason"] = decision.get("key_reason", "")
    result["position"] = decision.get("position_suggestion", "")

    # 5. 获取实际走势
    actual = get_actual_return(symbol, as_of_date, hold_days)
    if "error" in actual:
        result["error"] = actual["error"]
        result["actual_return_pct"] = 0
        result["correct"] = False
        return result

    result["entry_price"] = actual.get("entry_price", 0)
    result["exit_price"] = actual.get("exit_price", 0)
    result["actual_return_pct"] = actual.get("return_pct", 0)
    result["actual_high_pct"] = actual.get("high_pct", 0)
    result["actual_low_pct"] = actual.get("low_pct", 0)
    result["days_in_data"] = actual.get("days_in_data", 0)

    # 6. 判断预测是否正确
    # 买入/强烈推荐 -> 股价上涨算正确
    # 回避 -> 股价下跌算正确
    # 观望 -> 没有明确方向, 中性
    action = result["predicted_action"]
    ret = result["actual_return_pct"]

    if action in ("强烈推荐", "推荐买入"):
        result["correct"] = ret > 0
    elif action in ("回避",):
        result["correct"] = ret < 0
    else:
        # 观望: 不涨不跌 (涨跌幅 < 3%) 算正确
        result["correct"] = abs(ret) < 3

    return result


def run_multi_backtest(
    symbols: list[str],
    dates: list[str],
    hold_days: int = 20,
) -> dict:
    """多时间点多只股票综合回测

    返回所有回测的综合统计
    """
    all_summaries = []
    all_results = []

    for date in dates:
        r = run_backtest(symbols, date, hold_days)
        all_summaries.append(r["summary"])
        all_results.extend(r["results"])

    # 综合统计
    total = len(all_results)
    correct = sum(1 for r in all_results if r.get("correct"))
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    buy_returns = [r["actual_return_pct"] for r in all_results
                   if r.get("predicted_action") in ("强烈推荐", "推荐买入")]
    avoid_returns = [r["actual_return_pct"] for r in all_results
                     if r.get("predicted_action") in ("回避",)]

    correlations = [s.get("score_return_correlation", 0) for s in all_summaries]
    avg_corr = round(sum(correlations) / len(correlations), 3) if correlations else 0

    summary = {
        "total_tests": total,
        "total_dates": len(dates),
        "correct_count": correct,
        "accuracy_pct": accuracy,
        "avg_score_correlation": avg_corr,
        "buy_avg_return": round(sum(buy_returns) / len(buy_returns), 2) if buy_returns else 0,
        "buy_count": len(buy_returns),
        "avoid_avg_return": round(sum(avoid_returns) / len(avoid_returns), 2) if avoid_returns else 0,
        "avoid_count": len(avoid_returns),
        "overall_avg_return": round(sum(r["actual_return_pct"] for r in all_results) / total, 2) if total else 0,
    }

    # 按日期列出
    print(f"\n{'█'*60}")
    print(f"  📊 综合回测报告 ({len(dates)}个时间点 x {len(symbols)}只股票)")
    print(f"{'█'*60}")
    print(f"  总测试次数:   {summary['total_tests']}")
    print(f"  方向正确率:   {summary['accuracy_pct']}%")
    print(f"  Score相关性:  {summary['avg_score_correlation']}")
    print(f"  买入收益avg:  {summary['buy_avg_return']:+.2f}% ({summary['buy_count']}次)")
    print(f"  回避收益avg:  {summary['avoid_avg_return']:+.2f}% ({summary['avoid_count']}次)")
    if summary['buy_count'] > 0 and summary['avoid_count'] > 0:
        print(f"  多空差:       {summary['buy_avg_return'] - summary['avoid_avg_return']:+.2f}%")
    print(f"  全体收益avg:  {summary['overall_avg_return']:+.2f}%")
    print()

    # 按日期展示
    print(f"{'日期':<14} {'正确率':<10} {'买入收益':<12} {'回避收益':<12} {'测试数':<8}")
    print(f"{'─'*56}")
    for s in sorted(all_summaries, key=lambda x: x["as_of_date"]):
        print(f"{s['as_of_date']:<14} {s['accuracy_pct']:<10}% "
              f"{s['buy_avg_return']:<+11.2f}% {s['avoid_avg_return']:<+11.2f}% "
              f"{s['total_stocks']:<8}")

    return {"summary": summary, "by_date": all_summaries, "all_results": all_results}


def _build_tech_input(quote: dict, ind: dict) -> str:
    return (
        f"(回测模式) 当前日期: {quote.get('_as_of_date', '?')}\n\n"
        f"股票: {quote.get('name', '')} ({quote.get('code', '')})\n"
        f"收盘价: {ind.get('price', quote.get('price', 'N/A'))} 元\n"
        f"\n"
        f"=== 技术指标 ===\n"
        f"均线: MA5={ind.get('ma5')} MA10={ind.get('ma10')} MA20={ind.get('ma20')}\n"
        f"均线趋势: {ind.get('ma_trend', 'N/A')}\n"
        f"MACD: DIF={ind.get('macd_dif')} DEA={ind.get('macd_dea')} 柱={ind.get('macd_hist')}\n"
        f"MACD金叉: {ind.get('macd_golden_cross')}  多头: {ind.get('macd_bullish')}\n"
        f"RSI(14): {ind.get('rsi14')} ({ind.get('rsi_status')})\n"
        f"KDJ: K={ind.get('kdj_k')} D={ind.get('kdj_d')} J={ind.get('kdj_j')}\n"
        f"布林带: 上={ind.get('bb_upper')} 中={ind.get('bb_mid')} 下={ind.get('bb_lower')}\n"
        f"股价位置: {ind.get('price_in_bb')}\n"
        f"量比: {ind.get('vol_ratio')} ({ind.get('vol_status')})\n"
        f"20日高/低: {ind.get('high_20d')} / {ind.get('low_20d')}\n"
    )


def _build_risk_input(quote: dict, ind: dict) -> str:
    return (
        f"(回测模式) 当前日期: {quote.get('_as_of_date', '?')}\n\n"
        f"股票: {quote.get('name', '')} ({quote.get('code', '')})\n"
        f"价格: {ind.get('price', '')} 元\n"
        f"\n"
        f"均线趋势: {ind.get('ma_trend')}\n"
        f"RSI: {ind.get('rsi14')} ({ind.get('rsi_status')})\n"
        f"MACD: {'多头' if ind.get('macd_bullish') else '空头/调整'}\n"
        f"股价: {ind.get('price_in_bb')}\n"
        f"量价: {ind.get('vol_status')}\n"
        f"20日高低: {ind.get('high_20d')}/{ind.get('low_20d')}\n"
    )


def _calc_correlation(pairs: list[tuple[float, float]]) -> float:
    """计算 Score 与实际收益的 Pearson 相关性"""
    if len(pairs) < 3:
        return 0
    import math
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    n = len(xs)
    sx = sum(xs); sy = sum(ys)
    sxy = sum(x * y for x, y in pairs)
    sxx = sum(x * x for x in xs)
    syy = sum(y * y for y in ys)
    denom = math.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy))
    if denom == 0:
        return 0
    r = (n * sxy - sx * sy) / denom
    return round(r, 3)
