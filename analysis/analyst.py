"""StockAnalyst Agent —— 个股深度分析

职责:
  1. 采集个股全维度数据（行情/技术/财务/新闻/资金）
  2. 计算核心指标（metrics.py）
  3. 生成图表（charts.py）
  4. 调用 LLM 综合分析
  5. 输出结构化分析报告（含文字分析和数值指标）
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from agents.base import BaseAgent
from config import settings
from data.fundamentals import get_financial_summary, get_valuation_summary
from data.indicators import compute_indicators
from data.market import get_kline, get_realtime_quote
from data.news import get_stock_news

from analysis.metrics import compute_all_metrics
from analysis.charts import generate_all_charts

# ════════════════════════════════════════════════════════════
#  分析报告输出 Schema
# ════════════════════════════════════════════════════════════

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "一句话投资结论"},
        "rating": {
            "type": "string",
            "enum": ["强烈推荐", "推荐买入", "中性观望", "谨慎回避"],
            "description": "投资评级",
        },
        "score": {
            "type": "number",
            "description": "综合评分 1-10",
            "minimum": 1,
            "maximum": 10,
        },
        "confidence": {
            "type": "string",
            "enum": ["高", "中", "低"],
            "description": "分析置信度",
        },
        "technical_analysis": {
            "type": "string",
            "description": "技术面分析（趋势/动量/量价/支撑阻力）",
        },
        "fundamental_analysis": {
            "type": "string",
            "description": "基本面分析（估值/盈利/成长/财务健康）",
        },
        "news_sentiment": {
            "type": "string",
            "description": "新闻情绪综述（近期消息面整体评价）",
        },
        "risk_assessment": {
            "type": "string",
            "description": "风险评估（下行风险/关键风险因素）",
        },
        "outlook": {
            "type": "string",
            "description": "后市展望（1-3个月走势判断）",
        },
        "key_levels": {
            "type": "object",
            "properties": {
                "support": {"type": "string", "description": "关键支撑位"},
                "resistance": {"type": "string", "description": "关键阻力位"},
                "stop_loss": {"type": "number", "description": "建议止损价"},
            },
            "required": ["support", "resistance"],
        },
        "position_suggestion": {
            "type": "string",
            "enum": ["轻仓(1-2成)", "半仓(3-5成)", "重仓(6-8成)", "空仓"],
            "description": "建议仓位",
        },
        "investment_theme": {
            "type": "string",
            "description": "核心投资逻辑/故事（一句话）",
        },
        "risks_to_watch": {
            "type": "array",
            "items": {"type": "string"},
            "description": "需要关注的风险点列表",
        },
    },
    "required": [
        "summary", "rating", "score", "confidence",
        "technical_analysis", "news_sentiment", "risk_assessment", "outlook",
    ],
}


class StockAnalyst(BaseAgent):
    """个股深度分析 Agent —— 卖方分析师级别"""

    def system_prompt(self) -> str:
        return """你是一位拥有 15 年经验的资深股票分析师（卖方研究所首席分析师级别）。

你的分析框架（自上而下）：
1. **市场背景** — 当前市场风格和板块所处阶段
2. **技术面** — 趋势、动量、量价关系、关键支撑阻力
3. **基本面** — 估值水平、盈利能力、成长性、财务健康度
4. **资金面** — 主力资金流向、成交量能
5. **新闻情绪** — 近期消息面整体评价
6. **风险评估** — 下行空间、关键风险因素
7. **后市展望** — 未来 1-3 个月的走势判断

分析原则：
- 客观中立，既不盲目看多也不刻意看空
- 明确指出技术面和基本面的核心矛盾
- 风险提示要具体，不止是泛泛而谈
- 给出明确的支撑位和阻力位判断
- 评级要与风险收益比匹配

输出必须严格遵循指定的 JSON 格式，不要添加额外文字。"""

    def analyze(self, symbol: str, name: str = "") -> dict:
        """完整的个股深度分析流程

        Args:
            symbol: 股票代码（如 "002594"）
            name: 股票名称（可选，自动获取）

        Returns:
            包含所有分析数据和 LLM 分析结果的结构化字典
        """
        result = {
            "symbol": symbol,
            "name": name,
            "analysis_date": datetime.date.today().strftime("%Y-%m-%d"),
            "status": "success",
        }

        # ── 1. 数据采集 ──
        print(f"\n  📡 数据采集阶段")
        print(f"  {'─'*40}")

        quote = get_realtime_quote(symbol)
        if "error" in quote:
            result["status"] = "error"
            result["error"] = f"行情获取失败: {quote['error']}"
            return result

        stock_name = quote.get("name", name or symbol)
        result["name"] = stock_name
        result["quote"] = quote
        print(f"  ✅ 行情: {stock_name} @ {quote.get('price', '?')} 元")

        kline = get_kline(symbol)
        if kline is None or kline.empty or len(kline) < 20:
            result["status"] = "error"
            result["error"] = "K线数据不足（至少需要20个交易日）"
            return result
        print(f"  ✅ K线: {len(kline)} 个交易日")

        indicators = compute_indicators(kline)
        if "error" in indicators:
            result["status"] = "error"
            result["error"] = f"指标计算失败: {indicators['error']}"
            return result
        print(f"  ✅ 技术指标: 均线/RIS/MACD/布林/KDJ 计算完成")

        # 核心指标
        metrics = compute_all_metrics(kline)
        result["metrics"] = metrics
        print(f"  ✅ 核心指标: 回撤({metrics.get('max_drawdown', {}).get('max_dd_pct', '?')}%) "
              f"夏普({metrics.get('sharpe_ratio', '?')})")

        # 基本面
        financial = get_financial_summary(symbol)
        valuation = get_valuation_summary(symbol, quote)
        result["financial"] = financial
        result["valuation"] = valuation
        print(f"  ✅ 基本面: PE={valuation.get('pe', '?')}")

        # 新闻
        news = get_stock_news(symbol, max_results=10)
        result["news"] = news
        print(f"  ✅ 新闻: {len(news)} 条")

        # 资金流向
        try:
            from data.money_flow import get_money_flow
            money_flow = get_money_flow(symbol)
            result["money_flow"] = money_flow
            if money_flow:
                print(f"  ✅ 资金流向: 主力净流入 {money_flow.get('main_net_inflow', '?')} 亿")
            else:
                print(f"  ⚠️ 资金流向: 数据不可用")
        except Exception:
            result["money_flow"] = {}
            print(f"  ⚠️ 资金流向: 获取失败")

        # ── 2. 生成图表 ──
        print(f"\n  🎨 图表生成阶段")
        chart_paths = generate_all_charts(kline, symbol, stock_name, news)
        result["chart_paths"] = chart_paths
        for ctype, path in chart_paths.items():
            print(f"  ✅ {ctype}: {Path(path).name}")

        # ── 3. 构建 LLM 输入 ──
        print(f"\n  🤖 AI 深度分析阶段")

        llm_input = self._build_llm_input(
            name=stock_name, symbol=symbol,
            quote=quote, indicators=indicators,
            metrics=metrics, financial=financial,
            valuation=valuation, news=news,
            money_flow=result.get("money_flow", {}),
        )

        # ── 4. LLM 分析 ──
        try:
            analysis = self.call_structured(llm_input, ANALYSIS_SCHEMA)
            result["analysis"] = analysis
            print(f"  ✅ AI 分析完成: 评分 {analysis.get('score', '?')}/10, "
                  f"评级 {analysis.get('rating', '?')}")
        except Exception as e:
            result["analysis"] = {
                "summary": f"AI 分析失败: {str(e)}",
                "rating": "中性观望",
                "score": 5,
                "confidence": "低",
            }
            result["analysis_error"] = str(e)
            print(f"  ⚠️ AI 分析异常: {e}")

        # ── 5. 汇总信息 ──
        result["summary_table"] = self._build_summary_table(
            quote, indicators, metrics, result.get("analysis", {})
        )

        print(f"\n  📊 分析完成: {stock_name} ({symbol})")
        return result

    # ════════════════════════════════════════════════════════════
    #  内部辅助
    # ════════════════════════════════════════════════════════════

    def _build_llm_input(
        self, name: str, symbol: str,
        quote: dict, indicators: dict,
        metrics: dict, financial: dict,
        valuation: dict, news: list[dict],
        money_flow: dict,
    ) -> str:
        """构建 LLM 分析输入（含所有数据摘要）"""
        price = quote.get("price", "?")
        change = quote.get("change_pct", 0)

        lines = [
            f"## 个股深度分析: {name} ({symbol})",
            f"分析日期: {datetime.date.today().strftime('%Y-%m-%d')}",
            "",
            "### 市场数据",
            f"当前价格: {price} 元",
            f"今日涨幅: {change:+.2f}%" if isinstance(change, (int, float)) else f"今日涨幅: {change}%",
            f"总市值: {self._fmt_cap(quote.get('market_cap', 0))}",
            f"换手率: {quote.get('turnover_rate', '')}%",
            f"所属板块: {quote.get('sector', 'N/A')}",
            "",
            "### 技术指标",
            f"均线: MA5={indicators.get('ma5','')} MA10={indicators.get('ma10','')} MA20={indicators.get('ma20','')} MA60={indicators.get('ma60','')}",
            f"均线趋势: {indicators.get('ma_trend', 'N/A')}",
            f"MACD: DIF={indicators.get('macd_dif','')} DEA={indicators.get('macd_dea','')} 柱线={indicators.get('macd_hist','')}",
            f"MACD状态: {'多头' if indicators.get('macd_bullish') else '空头'}, "
            f"{'金叉' if indicators.get('macd_golden_cross') else '死叉' if indicators.get('macd_death_cross') else '无交叉'}",
            f"RSI(14): {indicators.get('rsi14','')} ({indicators.get('rsi_status','')})",
            f"布林带: 股价在{indicators.get('price_in_bb','中轨')}",
            f"量价: 量比={indicators.get('vol_ratio','')} ({indicators.get('vol_status','')})",
            "",
            "### 风险指标",
        ]

        dd = metrics.get("max_drawdown", {})
        lines.append(f"最大回撤: {dd.get('max_dd_pct', 'N/A')}% (持续{dd.get('duration_days', '?')}天)")
        lines.append(f"当前回撤: {metrics.get('current_drawdown', 'N/A')}%")
        lines.append(f"波动率(年化): {metrics.get('volatility_1y', 'N/A')}%")
        lines.append(f"夏普比率: {metrics.get('sharpe_ratio', 'N/A')}")
        lines.append(f"卡玛比率: {metrics.get('calmar_ratio', 'N/A')}")
        lines.append(f"盈亏比: {metrics.get('win_loss_ratio', {}).get('win_loss_ratio', 'N/A')}")
        lines.append(f"上涨概率: {metrics.get('win_loss_ratio', {}).get('win_rate', 'N/A')}%")
        lines.append("")

        # 收益表现
        lines.append("### 收益表现")
        for period, label in [("return_1m", "近1月"), ("return_3m", "近3月"),
                               ("return_6m", "近6月"), ("return_1y", "近1年"),
                               ("ytd_return", "年初至今")]:
            val = metrics.get(period)
            if val is not None:
                lines.append(f"{label}: {val:+.2f}%" if isinstance(val, (int, float)) else f"{label}: {val}")
        lines.append("")

        # 支撑阻力
        sr = metrics.get("support_resistance", {})
        if sr:
            supports = sr.get("supports", [])
            resistances = sr.get("resistances", [])
            if supports:
                items = [f"{s['name']}={s['price']}" for s in supports]
                lines.append(f"支撑位: {', '.join(items)}")
            if resistances:
                items = [f"{r['name']}={r['price']}" for r in resistances]
                lines.append(f"阻力位: {', '.join(items)}")
            lines.append("")

        # 资金流向
        if money_flow:
            lines.append("### 资金流向")
            lines.append(f"主力净流入: {money_flow.get('main_net_inflow', 'N/A')} 亿")
            lines.append(f"主力净流入率: {money_flow.get('main_inflow_ratio', 'N/A')}%")
            lines.append(f"超大单净流入: {money_flow.get('super_large_net', 'N/A')} 亿")
            lines.append(f"大单净流入: {money_flow.get('large_net', 'N/A')} 亿")
            lines.append(f"资金趋势: {money_flow.get('flow_trend', 'N/A')} (近5日{money_flow.get('up_days_5', '?')}天流入/{money_flow.get('down_days_5', '?')}天流出)")
            lines.append("")

        # 基本面
        if financial and "error" not in financial:
            lines.append("### 财务数据")
            lines.append(f"营业收入: {self._fmt_cap(financial.get('revenue', 0))}")
            lines.append(f"营收同比: {financial.get('revenue_yoy', 'N/A')}%")
            lines.append(f"净利润: {self._fmt_cap(financial.get('net_profit', 0))}")
            lines.append(f"利润同比: {financial.get('profit_yoy', 'N/A')}%")
            lines.append(f"报告期: {financial.get('report_date', 'N/A')}")
            lines.append("")

        # 估值
        if valuation and "error" not in valuation:
            pe = valuation.get("pe", 0)
            mc = valuation.get("market_cap", 0)
            lines.append(f"PE: {pe}" if pe else "PE: N/A")
            lines.append(f"总市值: {self._fmt_cap(mc)}")
            lines.append("")

        # 新闻
        if news:
            lines.append("### 近期新闻")
            for n in news:
                t = n.get("title", "")
                tm = str(n.get("time", ""))[:10]
                if t:
                    lines.append(f"- [{tm}] {t}")
            lines.append("")
        else:
            lines.append("### 近期新闻")
            lines.append("(暂无新闻数据)")
            lines.append("")

        lines.append("请根据以上数据，给出综合投资评级和详细分析。")
        lines.append("重点关注: 技术面与基本面的匹配度、当前风险收益比、关键驱动因素。")

        return "\n".join(str(x) for x in lines)

    @staticmethod
    def _build_summary_table(quote: dict, ind: dict, metrics: dict, analysis: dict) -> list[list]:
        """构建核心指标摘要表（用于 PDF 报告）"""
        mdd = metrics.get("max_drawdown", {}).get("max_dd_pct", "N/A")
        mdd_str = f"{mdd}%" if isinstance(mdd, (int, float)) else str(mdd)

        vol = metrics.get("volatility_1y", "N/A")
        vol_str = f"{vol}%" if isinstance(vol, (int, float)) else str(vol)

        sharpe = metrics.get("sharpe_ratio", "N/A")
        ret_1m = metrics.get("return_1m", "N/A")
        ret_1m_str = f"{ret_1m:+.1f}%" if isinstance(ret_1m, (int, float)) else str(ret_1m)
        ret_1y = metrics.get("return_1y", "N/A")
        ret_1y_str = f"{ret_1y:+.1f}%" if isinstance(ret_1y, (int, float)) else str(ret_1y)

        score = analysis.get("score", "?")
        rating = analysis.get("rating", "?")
        confidence = analysis.get("confidence", "?")

        return [
            ["指标", "数值", "指标", "数值"],
            ["综合评分", f"{score}/10", "投资评级", rating],
            ["置信度", confidence, "收盘价", f"{quote.get('price', '?')} 元"],
            ["今日涨幅", f"{quote.get('change_pct', 0):+.2f}%", "最大回撤", mdd_str],
            ["近1月收益", ret_1m_str, "近1年收益", ret_1y_str],
            ["年化波动率", vol_str, "夏普比率", str(sharpe)],
            ["均线趋势", ind.get("ma_trend", "N/A"), "RSI(14)", str(ind.get("rsi14", "?"))],
        ]

    @staticmethod
    def _fmt_cap(num: float) -> str:
        """格式化大数字"""
        try:
            num = float(num)
            if num >= 1e12:
                return f"{num/1e12:.2f}万亿"
            if num >= 1e8:
                return f"{num/1e8:.2f}亿"
            if num >= 1e4:
                return f"{num/1e4:.2f}万"
            return str(round(num, 2))
        except (ValueError, TypeError):
            return str(num)


# ── 单例 ──
stock_analyst = StockAnalyst("analyst", temperature=0.05)
