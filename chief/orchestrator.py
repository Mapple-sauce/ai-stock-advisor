"""流程编排器 —— 协调多个 Agent 协作"""

from __future__ import annotations

import time
from typing import Any

from agents.technical import technical_analyst
from agents.fundamental import fundamental_analyst
from agents.sentiment import sentiment_analyst
from agents.risk import risk_analyst
from agents.scanner import market_scanner
from agents.hunter import hunter_agent, build_hunter_prompt
from chief import chief_agent
from data.indicators import compute_indicators
from data.market import get_realtime_quote, get_kline
from data.fundamentals import get_financial_summary, get_valuation_summary
from data.news import get_stock_news
from portfolio.manager import PortfolioManager


class Orchestrator:
    """编排器 —— 协调所有 Agent 的工作流程"""

    def __init__(self):
        self.pm = PortfolioManager()

    # ──────────────────────────────────────────────
    #  买入分析流程
    # ──────────────────────────────────────────────

    def analyze_buy(self, symbol: str) -> dict | None:
        """完整的买入分析: 4个 Agent 并行分析 → Chief 总决策"""
        print(f"\n  {'='*50}")
        print(f"  📈 买入分析: {symbol}")
        print(f"  {'='*50}")

        # 1. 获取数据
        print(f"  [1/6] 获取行情数据...")
        quote = get_realtime_quote(symbol)
        if "error" in quote:
            print(f"  ❌ {quote['error']}")
            return None
        print(f"  ✅ {quote.get('name', '')} @ {quote.get('price', '')} 元")

        print(f"  [2/6] 获取K线 & 计算技术指标...")
        kline = get_kline(symbol)
        indicators = compute_indicators(kline)

        print(f"  [3/6] 获取基本面数据...")
        financial = get_financial_summary(symbol)
        valuation = get_valuation_summary(symbol, quote)

        print(f"  [4/6] 获取新闻舆情...")
        news = get_stock_news(symbol)

        # 2. 构建各 Agent 的输入数据
        tech_input = _build_technical_input(quote, indicators)
        fund_input = _build_fundamental_input(quote, financial, valuation)
        sent_input = _build_sentiment_input(quote, news, indicators)
        risk_input = _build_risk_input(quote, indicators, "buy")

        # 3. 4个 Agent 并行分析 (顺序调用模拟并行)
        print(f"  [5/6] 专家会诊...")
        start = time.time()

        print(f"    → 技术分析师 工作中...")
        tech_report = technical_analyst.call(tech_input)

        print(f"    → 基本面分析师 工作中...")
        fund_report = fundamental_analyst.call(fund_input)

        print(f"    → 舆情分析师 工作中...")
        sent_report = sentiment_analyst.call(sent_input)

        print(f"    → 风控分析师 工作中...")
        risk_report = risk_analyst.call(risk_input)

        elapsed = time.time() - start
        print(f"    ✅ 4位专家耗时 {elapsed:.1f}秒")

        # 4. Chief Agent 总决策
        print(f"  [6/6] 首席投资官 综合评估中...")
        try:
            decision = chief_agent.decide_buy(
                stock_info=quote,
                technical=tech_report,
                fundamental=fund_report,
                sentiment=sent_report,
                risk=risk_report,
            )

            result = {
                "code": symbol,
                "name": quote.get("name", ""),
                "price": quote.get("price", ""),
                "change_pct": quote.get("change_pct", ""),
                "technical_report": tech_report,
                "fundamental_report": fund_report,
                "sentiment_report": sent_report,
                "risk_report": risk_report,
                "decision": decision,
                "decision_score": decision.get("final_score", 0),
                "decision_action": decision.get("action", ""),
            }
            print(f"  ✅ 首席决策: {decision.get('action', '')} "
                  f"(评分: {decision.get('final_score', '')})")
            return result

        except Exception as e:
            print(f"  ❌ 首席决策失败: {e}")
            return None

    # ──────────────────────────────────────────────
    #  卖出分析流程
    # ──────────────────────────────────────────────

    def analyze_sell(self, holding: dict) -> dict | None:
        """完整的卖出分析: 3个 Agent 分析 → Chief 总决策"""
        symbol = holding["symbol"]
        print(f"\n  {'='*50}")
        print(f"  📉 卖出分析: {symbol}")
        print(f"  {'='*50}")

        # 1. 获取最新数据
        print(f"  [1/5] 获取最新行情...")
        quote = get_realtime_quote(symbol)
        if "error" in quote:
            print(f"  ❌ {quote['error']}")
            return None

        # 更新持仓价格
        current_price = quote.get("price", 0)
        self.pm.update_price(symbol, current_price)
        holding["current_price"] = current_price
        holding["pnl_pct"] = ((current_price - holding["cost_price"]) / holding["cost_price"] * 100) if holding["cost_price"] else 0

        print(f"  ✅ {holding.get('name', '')} 当前 {current_price} 元, "
              f"盈亏: {holding.get('pnl_pct', 0):.2f}%")

        print(f"  [2/5] 获取K线 & 计算技术指标...")
        kline = get_kline(symbol)
        indicators = compute_indicators(kline)

        print(f"  [3/5] 获取新闻舆情...")
        news = get_stock_news(symbol)

        # 2. Agent 输入
        tech_input = _build_technical_input(quote, indicators, is_sell=True)
        sent_input = _build_sentiment_input(quote, news, indicators)
        risk_input = _build_risk_input(quote, indicators, "sell", holding)

        # 3. Agent 分析
        print(f"  [4/5] 专家会诊...")
        start = time.time()

        print(f"    → 技术分析师 工作中...")
        tech_report = technical_analyst.call(tech_input)

        print(f"    → 舆情分析师 工作中...")
        sent_report = sentiment_analyst.call(sent_input)

        print(f"    → 风控分析师 工作中...")
        risk_report = risk_analyst.call(risk_input)

        elapsed = time.time() - start
        print(f"    ✅ 3位专家耗时 {elapsed:.1f}秒")

        # 4. Chief 决策
        print(f"  [5/5] 首席投资官 评估中...")
        try:
            decision = chief_agent.decide_sell(
                holding_info=holding,
                technical=tech_report,
                sentiment=sent_report,
                risk=risk_report,
            )
            result = {
                "code": symbol,
                "name": quote.get("name", ""),
                "price": current_price,
                "cost_price": holding["cost_price"],
                "pnl_pct": holding.get("pnl_pct", 0),
                "technical_report": tech_report,
                "sentiment_report": sent_report,
                "risk_report": risk_report,
                "decision": decision,
                "decision_score": decision.get("final_score", 0),
                "decision_action": decision.get("action", ""),
            }
            print(f"  ✅ 首席决策: {decision.get('action', '')} "
                  f"(评分: {decision.get('final_score', '')})")
            return result
        except Exception as e:
            print(f"  ❌ 首席决策失败: {e}")
            return None

    # ──────────────────────────────────────────────
    #  市场扫描流程
    # ──────────────────────────────────────────────

    def scan_market(self, candidates: list[dict], mode: str = "top_gainers") -> str:
        """AI 扫描精选"""
        top_n = 5

        # 根据模式调整描述
        mode_labels = {
            "low_position": "💎 低位潜力股",
            "momentum": "🔥 追高跟强",
            "top_gainers": "📈 今日涨幅榜",
        }
        mode_label = mode_labels.get(mode, "📈 扫描")

        text = "\n".join(
            f"- {s.get('name','')}({s['code']}) 涨幅:{s.get('change_pct',0)}% "
            f"评分:{s.get('score','?')} RSI:{s.get('rsi','?')} "
            f"信号:{','.join(s.get('signals',[]))}"
            for s in candidates[:15]
        )

        prompt = (
            f"## 扫描模式: {mode_label}\n\n"
            f"### 候选股票\n{text}\n\n"
            f"请从以上候选股票中精选最值得关注的 {top_n} 只, "
            f"结合每个股票的技术评分和信号给出理由。"
        )
        report = market_scanner.call(prompt)
        return report

    # ──────────────────────────────────────────────
    #  低位挖掘流程 (Hunter Agent 深度分析)
    # ──────────────────────────────────────────────

    def hunter_deep_dive(self, candidates: list[dict]) -> str:
        """Hunter 深度挖掘: 对候选股逐一分析 + 综合排名

        工作流:
          1. 全市场扫雷 → 量化初筛 (已完成, 由调用方执行)
          2. AI 深度挖掘 → 对 TOP 10 逐一分析
          3. 精选排名 → Hunter 输出最终榜单
        """
        print(f"\n  🔬 低位挖掘 Agent 开始深度分析...")

        top = sorted(candidates, key=lambda s: s.get("score", 0), reverse=True)[:10]
        print(f"  📋 选取 TOP {len(top)} 进行深度分析\n")

        deep_reports = []
        for i, s in enumerate(top, 1):
            name = s.get("name", "")
            code = s.get("code", "")
            print(f"    [{i}/{len(top)}] 🕵️ 分析 {name} ({code})...")

            prompt = build_hunter_prompt(
                symbol=code, name=name,
                price=s.get("price", 0), change_pct=s.get("change_pct", 0),
                ind={
                    "ma5": s.get("ma5"), "ma10": s.get("ma10"), "ma20": s.get("ma20"),
                    "ma_trend": s.get("ma_trend"), "rsi14": s.get("rsi"),
                    "rsi_status": s.get("rsi_status"),
                    "macd_dif": s.get("macd_dif"), "macd_dea": s.get("macd_dea"),
                    "macd_hist": s.get("macd_hist"), "macd_bullish": s.get("macd_bullish"),
                    "macd_golden_cross": s.get("macd_golden_cross"),
                    "kdj_k": s.get("kdj_k"), "kdj_d": s.get("kdj_d"), "kdj_j": s.get("kdj_j"),
                    "bb_upper": s.get("bb_upper"), "bb_mid": s.get("bb_mid"),
                    "bb_lower": s.get("bb_lower"), "price_in_bb": s.get("price_in_bb"),
                    "vol_ratio": s.get("vol_ratio"), "vol_status": s.get("vol_status"),
                    "high_20d": s.get("high_20d"), "low_20d": s.get("low_20d"),
                    "near_20d_high": s.get("near_20d_high"),
                },
                signals=s.get("signals", []),
                turnover=s.get("turnover", 0),
            )

            try:
                report = hunter_agent.call(prompt)
                deep_reports.append((name, code, report))
                print(f"    ✅ 完成")
            except Exception as e:
                print(f"    ❌ 失败: {e}")

        # 汇总报告
        lines = [
            f"# 💎 AI 低位挖掘深度报告",
            f"**日期**: {time.strftime('%Y-%m-%d')}",
            f"**扫描股票数**: {len(candidates)}",
            f"**深度分析数**: {len(deep_reports)}",
            "", "---", "",
        ]

        # 综合排名
        summary_prompt = "以下是对各只候选股票的深度分析结果，请对它们进行综合排名：\n\n"
        for name, code, report in deep_reports:
            short = (report or "分析失败")[:300].replace("#", "").strip()
            summary_prompt += f"**{name} ({code})**:\n{short}\n\n"

        summary_prompt += (
            "请按推荐程度从高到低排序，输出格式:\n"
            "| 排名 | 股票 | 评级 | 核心逻辑 | 风险收益比 |\n"
            "|:---:|:---:|:---:|:---|:---:|\n"
            "| 🥇 | xxx | ⭐⭐⭐ | ... | 好 |\n"
        )

        print(f"\n  📊 Hunter 综合排名中...")
        try:
            ranking = hunter_agent.call(summary_prompt)
            lines.append("## 📊 最终精选排名\n")
            lines.append(ranking)
            lines.append("")
        except Exception as e:
            print(f"  ⚠️ 排名生成失败: {e}")

        lines.append("---\n## 📋 详细分析\n")
        for name, code, report in deep_reports:
            lines.append(f"### {name} ({code})\n")
            lines.append(report or "*(分析失败)*")
            lines.append("---\n")

        lines.append("\n*报告由 AI Hunter Agent 自动生成, 仅供参考*")
        return "\n".join(lines)


# ──────────────────────────────────────────────
#  Agent 输入构建函数
# ──────────────────────────────────────────────

def _build_technical_input(quote: dict, ind: dict, is_sell: bool = False) -> str:
    lines = [
        f"股票: {quote.get('name', '')} ({quote.get('code', '')})",
        f"当前价格: {ind.get('price', quote.get('price', 'N/A'))} 元",
        f"今日涨幅: {quote.get('change_pct', '')}%",
        f"",
        f"=== 技术指标 ===",
        f"均线: MA5={ind.get('ma5')} MA10={ind.get('ma10')} MA20={ind.get('ma20')}",
        f"均线趋势: {ind.get('ma_trend', 'N/A')}",
        f"",
        f"MACD: DIF={ind.get('macd_dif')} DEA={ind.get('macd_dea')} 柱={ind.get('macd_hist')}",
        f"MACD金叉: {ind.get('macd_golden_cross')}  死叉: {ind.get('macd_death_cross')}  多头: {ind.get('macd_bullish')}",
        f"",
        f"RSI(14): {ind.get('rsi14')} ({ind.get('rsi_status')})",
        f"KDJ: K={ind.get('kdj_k')} D={ind.get('kdj_d')} J={ind.get('kdj_j')}",
        f"",
        f"布林带: 上={ind.get('bb_upper')} 中={ind.get('bb_mid')} 下={ind.get('bb_lower')}",
        f"股价位置: {ind.get('price_in_bb')}",
        f"",
        f"成交量: 量比={ind.get('vol_ratio')} ({ind.get('vol_status')})",
        f"20日高/低: {ind.get('high_20d')} / {ind.get('low_20d')}",
        f"接近20日高点: {ind.get('near_20d_high')}",
    ]
    if is_sell:
        lines += [
            f"",
            f"⚠️ 这是**持仓卖出分析**, 请重点判断趋势是否走坏, 是否出现卖出信号。",
        ]
    return "\n".join(str(x) for x in lines)


def _build_fundamental_input(quote: dict, financial: dict, valuation: dict) -> str:
    lines = [
        f"股票: {quote.get('name', '')} ({quote.get('code', '')})",
        f"价格: {quote.get('price', '')} 元",
        f"总市值: {_fmt_num(quote.get('market_cap', 0))}",
        f"",
        f"=== 估值 ===",
        f"动态PE: {valuation.get('pe', 'N/A')}",
    ]
    if financial:
        lines += [
            f"",
            f"=== 财务数据 (最新报告期: {financial.get('report_date', '')}) ===",
            f"营业收入: {_fmt_num(financial.get('revenue', 0))}",
            f"营收同比: {financial.get('revenue_yoy', 'N/A')}%",
            f"净利润: {_fmt_num(financial.get('net_profit', 0))}",
            f"利润同比: {financial.get('profit_yoy', 'N/A')}%",
        ]
    return "\n".join(lines)


def _build_sentiment_input(quote: dict, news: list[dict], ind: dict) -> str:
    lines = [
        f"股票: {quote.get('name', '')} ({quote.get('code', '')})",
        f"当前价格: {quote.get('price', '')} 元",
        f"今日涨幅: {quote.get('change_pct', '')}%",
        f"换手率: {quote.get('turnover_rate', '')}%",
        f"当日振幅: {quote.get('amplitude', '')}%",
        f"",
        f"=== 技术情绪参考 ===",
        f"RSI: {ind.get('rsi14')} ({ind.get('rsi_status')})  — 超买=可能过热, 超卖=可能恐慌过度",
        f"量价: {ind.get('vol_status')} 量比={ind.get('vol_ratio')}",
        f"",
        f"=== 近期新闻 ===",
    ]
    if news:
        for n in news:
            lines.append(f"- [{n.get('time', '')}] {n.get('title', '')}")
    else:
        lines.append("(暂无新闻数据)")
    return "\n".join(lines)


def _build_risk_input(quote: dict, ind: dict, mode: str = "buy", holding: dict | None = None) -> str:
    lines = [
        f"股票: {quote.get('name', '')} ({quote.get('code', '')})",
        f"价格: {ind.get('price', quote.get('price', ''))} 元",
        f"今日涨幅: {quote.get('change_pct', '')}%",
        f"振幅: {quote.get('amplitude', '')}%",
        f"换手率: {quote.get('turnover_rate', '')}%",
        f"",
        f"=== 技术风险指标 ===",
        f"均线趋势: {ind.get('ma_trend')}",
        f"RSI: {ind.get('rsi14')} ({ind.get('rsi_status')})",
        f"MACD: {'金叉做多' if ind.get('macd_golden_cross') else '死叉做空' if ind.get('macd_death_cross') else '正常'}",
        f"股价: {ind.get('price_in_bb')}",
        f"量价: {ind.get('vol_status')}",
        f"20日高低: {ind.get('high_20d')}/{ind.get('low_20d')}",
        f"",
        f"20日最高: {ind.get('high_20d')}  20日最低: {ind.get('low_20d')}",
    ]
    if holding:
        lines += [
            f"",
            f"=== 持仓风险 ===",
            f"成本价: {holding.get('cost_price', 'N/A')}",
            f"当前盈亏: {holding.get('pnl_pct', 0):.2f}%",
        ]
    lines.append(f"\n分析模式: {'买入风险评估' if mode == 'buy' else '持仓卖出风险评估'}")
    if mode == "buy":
        lines.append("重点关注: 该股票买入后面临的下行风险")
    else:
        lines.append("重点关注: 是否应该继续持有, 还是止损/止盈卖出")
    return "\n".join(lines)


def _fmt_num(num: float) -> str:
    """格式化大数字"""
    if num >= 1e12:
        return f"{num/1e12:.2f}万亿"
    if num >= 1e8:
        return f"{num/1e8:.2f}亿"
    if num >= 1e4:
        return f"{num/1e4:.2f}万"
    return str(num)
