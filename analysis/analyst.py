"""StockAnalyst Agent —— 个股深度分析

架构:
  1. 数据采集（行情/K线/技术/财务/新闻/资金流 + 行业/板块数据）
  2. 图表生成
  3. 并行 AI 分析（主分析 + 板块分析 + 行业地位 + 供应链）
  4. 结果汇总
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
#  分析报告输出 Schema（百分制 1-100）
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
            "description": "综合评分 1-100 分（百分制, 越高越好）",
            "minimum": 1,
            "maximum": 100,
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
    """个股深度分析 Agent"""

    def system_prompt(self) -> str:
        return f"""你是一位拥有 15 年经验的资深股票分析师（卖方研究所首席分析师级别）。

你的分析框架（自上而下）：
1. **市场背景** — 当前市场风格和板块所处阶段
2. **技术面** — 趋势、动量、量价关系、关键支撑阻力
3. **基本面** — 估值水平、盈利能力、成长性、财务健康度
4. **资金面** — 主力资金流向、成交量能
5. **新闻情绪** — 近期消息面整体评价
6. **风险评估** — 下行空间、关键风险因素
7. **后市展望** — 未来 1-3 个月的走势判断

评分尺度参考（百分制 1-100）：
- 85-100 → 强烈推荐: 技术面多头+基本面优秀+资金流入+情绪正面
- 65-84  → 推荐买入: 整体偏多, 少量瑕疵
- 45-64  → 中性观望: 多空均衡, 等待触发因素
- 25-44  → 谨慎回避: 偏弱, 多个风险点
- 1-24   → 回避: 技术面/基本面明显恶化

分析原则：
- 客观中立，既不盲目看多也不刻意看空
- 明确指出技术面和基本面的核心矛盾
- 风险提示要具体，不止是泛泛而谈
- 给出明确的支撑位和阻力位判断
- 评级要与风险收益比匹配

输出必须严格遵循指定的 JSON 格式，不要添加额外文字。"""

    def analyze(self, symbol: str, name: str = "") -> dict:
        """完整的个股深度分析（含并行行业Agent）"""
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

        metrics = compute_all_metrics(kline)
        result["metrics"] = metrics
        print(f"  ✅ 核心指标: 回撤({metrics.get('max_drawdown', {}).get('max_dd_pct', '?')}%) "
              f"夏普({metrics.get('sharpe_ratio', '?')})")

        financial = get_financial_summary(symbol)
        valuation = get_valuation_summary(symbol, quote)
        result["financial"] = financial
        result["valuation"] = valuation

        fin_detail = ""
        if "error" not in financial:
            fin_detail = f"营收{financial.get('revenue_yoy','')}% 利润{financial.get('profit_yoy','')}%"
            if financial.get("roe"):
                fin_detail += f" ROE={financial.get('roe','')}%"
        print(f"  ✅ 基本面: PE={valuation.get('pe', '?')} ({fin_detail})")

        news = get_stock_news(symbol, max_results=10)
        result["news"] = news
        print(f"  ✅ 新闻: {len(news)} 条")

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

        # ── 1.5 行业数据采集 ──
        print(f"\n  🏭 行业数据采集")
        print(f"  {'─'*40}")
        from analysis.industry import get_sector_performance, get_industry_peers, \
            get_industry_ranking, get_supply_chain_context
        from scanner.sectors import get_sector, get_industry_name

        sector = get_sector(symbol)
        industry_name = get_industry_name(symbol)
        result["sector"] = sector
        result["industry_name"] = industry_name

        if sector:
            print(f"  ✅ 所属板块: {sector}")
            if industry_name:
                print(f"  ✅ 所属行业: {industry_name}")

        sector_data = get_sector_performance(sector)
        result["sector_performance"] = sector_data
        if "error" not in sector_data:
            print(f"  ✅ 板块涨跌: {sector_data.get('change_1d', '?')}% (1日)")

        peers = get_industry_peers(symbol)
        result["industry_peers"] = peers[:10]
        print(f"  ✅ 同业可比: {len(peers)} 家")

        ranking = get_industry_ranking(symbol, peers)
        result["industry_ranking"] = ranking
        if ranking.get("total_peers", 0) > 0:
            print(f"  ✅ 行业排名: 市值 {ranking.get('market_cap_rank', 'N/A')}")

        supply_chain = get_supply_chain_context(sector, industry_name)
        result["supply_chain_context"] = supply_chain
        print(f"  ✅ 供应链: 上游{len(supply_chain.get('upstream_sectors',[]))}个环节")

        # ── 2. 生成图表 ──
        print(f"\n  🎨 图表生成阶段")
        chart_paths = generate_all_charts(kline, symbol, stock_name, news)
        result["chart_paths"] = chart_paths
        for ctype, path in chart_paths.items():
            print(f"  ✅ {ctype}: {Path(path).name}")

        # ── 3. 构建 LLM 输入 ──
        print(f"\n  🤖 并行 AI 深度分析阶段")
        print(f"  {'─'*40}")

        # 3a: 主分析
        main_input = self._build_llm_input(
            name=stock_name, symbol=symbol,
            quote=quote, indicators=indicators,
            metrics=metrics, financial=financial,
            valuation=valuation, news=news,
            money_flow=result.get("money_flow", {}),
            sector=sector, sector_data=sector_data,
            ranking=ranking, supply_chain=supply_chain,
        )

        # 3b: 板块分析
        sector_prompt = self._build_sector_prompt(sector, sector_data, industry_name)
        # 3c: 行业地位
        position_prompt = self._build_position_prompt(stock_name, symbol, sector, ranking, peers[:5])
        # 3d: 供应链
        supply_prompt = self._build_supply_prompt(stock_name, sector, supply_chain)

        # ── 4. 并行 AI 分析 ──
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from agents.sector import sector_analyst
        from agents.industry_position import industry_position_analyst
        from agents.supply_chain import supply_chain_analyst

        agents_list = [
            ("main", self, main_input, True),
            ("sector", sector_analyst, sector_prompt, False),
            ("position", industry_position_analyst, position_prompt, False),
            ("supply_chain", supply_chain_analyst, supply_prompt, False),
        ]

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_map = {}
            for agent_name, agent_obj, prompt, structured in agents_list:
                if structured:
                    f = executor.submit(agent_obj.call_structured, prompt, ANALYSIS_SCHEMA)
                else:
                    f = executor.submit(agent_obj.call, prompt)
                future_map[f] = agent_name

            for future in as_completed(future_map):
                aname = future_map[future]
                try:
                    res = future.result()
                    result[f"analysis_{aname}"] = res
                    print(f"  ✅ {aname} 分析完成")
                except Exception as e:
                    result[f"analysis_{aname}"] = None
                    result[f"analysis_{aname}_error"] = str(e)
                    print(f"  ⚠️ {aname} 分析异常: {e}")

        # 兼容旧接口: analysis 字段指向主分析结果
        result["analysis"] = result.get("analysis_main") or result.get("analysis", {})

        # ── 5. 汇总信息 ──
        result["summary_table"] = self._build_summary_table(
            quote, indicators, metrics, result.get("analysis", {})
        )

        score = result.get("analysis", {}).get("score", "?")
        rating = result.get("analysis", {}).get("rating", "?")
        print(f"\n  📊 分析完成: {stock_name} ({symbol}) — 评分 {score}/100, 评级 {rating}")
        return result

    # ════════════════════════════════════════════════════════════
    #  Prompt 构建
    # ════════════════════════════════════════════════════════════

    def _build_llm_input(
        self, name: str, symbol: str,
        quote: dict, indicators: dict,
        metrics: dict, financial: dict,
        valuation: dict, news: list[dict],
        money_flow: dict,
        sector: str = "", sector_data: dict | None = None,
        ranking: dict | None = None, supply_chain: dict | None = None,
    ) -> str:
        """构建主 LLM 分析输入"""
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
            "",
        ]
        if sector:
            lines.append(f"所属行业板块: {sector}")
            if sector_data and "error" not in sector_data:
                lines.append(f"板块近1日涨幅: {sector_data.get('change_1d', '?')}%")
                lines.append(f"板块领涨股: {', '.join(s.get('name','') for s in sector_data.get('top_gainers',[])[:3])}")
            if ranking and ranking.get("total_peers", 0) > 0:
                lines.append(f"行业市值排名: {ranking.get('market_cap_rank', 'N/A')}")
                lines.append(f"行业中位数 PE: {ranking.get('pe_median', '?')}")
        lines.append("")

        # 技术指标
        lines.append("### 技术指标")
        lines.append(f"均线: MA5={indicators.get('ma5','')} MA10={indicators.get('ma10','')} MA20={indicators.get('ma20','')} MA60={indicators.get('ma60','')}")
        lines.append(f"均线趋势: {indicators.get('ma_trend', 'N/A')}")
        lines.append(f"MACD: DIF={indicators.get('macd_dif','')}/DEA={indicators.get('macd_dea','')}, {'多头' if indicators.get('macd_bullish') else '空头'}")
        lines.append(f"RSI(14): {indicators.get('rsi14','')} ({indicators.get('rsi_status','')})")
        lines.append(f"布林带: 在{indicators.get('price_in_bb','中轨')}")
        lines.append(f"量比: {indicators.get('vol_ratio','')} ({indicators.get('vol_status','')})")
        lines.append("")

        # 风险指标
        lines.append("### 风险指标")
        dd = metrics.get("max_drawdown", {})
        lines.append(f"最大回撤: {dd.get('max_dd_pct', 'N/A')}% (持续{dd.get('duration_days', '?')}天)")
        lines.append(f"当前回撤: {metrics.get('current_drawdown', 'N/A')}%")
        lines.append(f"波动率(年化): {metrics.get('volatility_1y', 'N/A')}%")
        lines.append(f"夏普比率: {metrics.get('sharpe_ratio', 'N/A')}")
        lines.append(f"上涨概率: {metrics.get('win_loss_ratio', {}).get('win_rate', 'N/A')}%")
        lines.append(f"盈亏比: {metrics.get('win_loss_ratio', {}).get('win_loss_ratio', 'N/A')}")
        lines.append("")

        # 收益
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
            lines.append(f"资金趋势: {money_flow.get('flow_trend', 'N/A')} (近5日{money_flow.get('up_days_5', '?')}天流入)")
            lines.append("")

        # 基本面
        if financial and "error" not in financial:
            lines.append("### 财务数据")
            lines.append(f"营业收入: {self._fmt_cap(financial.get('revenue', 0))} (同比{financial.get('revenue_yoy', 'N/A')}%)")
            lines.append(f"净利润: {self._fmt_cap(financial.get('net_profit', 0))} (同比{financial.get('profit_yoy', 'N/A')}%)")
            if financial.get("roe"):
                lines.append(f"ROE: {financial.get('roe')}%")
            if financial.get("debt_ratio"):
                lines.append(f"资产负债率: {financial.get('debt_ratio')}%")
            lines.append("")
            # 近4个季度趋势
            quarters = financial.get("quarters", [])
            if len(quarters) >= 2:
                lines.append("### 近4个季度营收/利润趋势")
                for q in quarters:
                    lines.append(f"  {q.get('report_date','')}: 营收{q.get('revenue_yoy','?'):+.1f}% / 利润{q.get('profit_yoy','?'):+.1f}% / 毛利率{q.get('gross_margin','?')}%")
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
            lines.append("(暂无)")
            lines.append("")

        lines.append("请根据以上数据，给出综合投资评级和详细分析（百分制 1-100分）。")
        lines.append("评分尺度: 85+强烈推荐/65+推荐买入/45+中性观望/25+谨慎回避/1-24回避")
        return "\n".join(str(x) for x in lines)

    def _build_sector_prompt(self, sector: str, sector_data: dict, industry_name: str) -> str:
        """板块分析 prompt"""
        lines = [
            f"## 行业板块分析: {sector}",
            f"分析日期: {datetime.date.today().strftime('%Y-%m-%d')}",
            "",
            "### 板块近期表现",
        ]
        if "error" not in sector_data:
            lines.append(f"近1日涨幅: {sector_data.get('change_1d', 'N/A')}%")
            lines.append(f"板块成交额: {sector_data.get('volume', 'N/A')}亿")
            lines.append(f"上涨/下跌家数: {sector_data.get('leader_count', '?')}/{sector_data.get('laggard_count', '?')}")
            lines.append("")
            lines.append("### 板块领涨股")
            for s in sector_data.get("top_gainers", [])[:5]:
                lines.append(f"- {s.get('name','')} ({s.get('change_pct','?')}%)")
            lines.append("")
            lines.append("### 板块领跌股")
            for s in sector_data.get("top_losers", [])[:3]:
                lines.append(f"- {s.get('name','')} ({s.get('change_pct','?')}%)")
        else:
            lines.append("(板块指数数据暂不可用)")
        lines.append("")
        lines.append("请分析该板块的整体情况、驱动因素和未来展望。")
        return "\n".join(lines)

    def _build_position_prompt(self, name: str, symbol: str, sector: str, ranking: dict, peers: list) -> str:
        """行业地位分析 prompt"""
        lines = [
            f"## 行业地位分析: {name} ({symbol})",
            f"所属行业: {sector}",
            f"分析日期: {datetime.date.today().strftime('%Y-%m-%d')}",
            "",
            "### 同行对比数据",
        ]
        if ranking and ranking.get("total_peers", 0) > 0:
            lines.append(f"可比公司总数: {ranking['total_peers']}家")
            lines.append(f"市值排名: {ranking.get('market_cap_rank', 'N/A')} (市值{self._fmt_cap(ranking.get('market_cap',0))})")
            lines.append(f"行业中位数PE: {ranking.get('pe_median', 'N/A')} (本股PE: {ranking.get('pe', '?')})")
            lines.append("")
            lines.append("### 主要竞争对手")
            for p in peers:
                mc = self._fmt_cap(p.get("market_cap", 0) * 1e8)
                lines.append(f"- {p.get('name','')}({p.get('symbol','')}) {mc} PE{p.get('pe','?')} 涨幅{p.get('change_pct','?')}%")
        else:
            lines.append("(暂无行业对比数据)")
        lines.append("")
        lines.append("请分析该股票在行业中的竞争地位、估值水平和优劣势。")
        return "\n".join(lines)

    def _build_supply_prompt(self, name: str, sector: str, supply_chain: dict) -> str:
        """供应链分析 prompt"""
        lines = [
            f"## 供应链分析: {name}",
            f"所属板块: {sector}",
            f"分析日期: {datetime.date.today().strftime('%Y-%m-%d')}",
            "",
        ]
        if supply_chain and "error" not in supply_chain:
            if supply_chain.get("upstream_sectors"):
                lines.append("### 上游行业")
                for u in supply_chain["upstream_sectors"]:
                    lines.append(f"- {u}")
            if supply_chain.get("downstream_sectors"):
                lines.append("")
                lines.append("### 下游行业")
                for d in supply_chain["downstream_sectors"]:
                    lines.append(f"- {d}")
            if supply_chain.get("typical_risks"):
                lines.append("")
                lines.append("### 常见供应链风险")
                for r in supply_chain["typical_risks"]:
                    lines.append(f"- {r}")
        else:
            lines.append(f"所属板块: {sector}")
        lines.append("")
        lines.append("请分析该公司的供应链结构、上下游依赖度、以及潜在风险。")
        return "\n".join(lines)

    # ════════════════════════════════════════════════════════════
    #  辅助方法
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def _build_summary_table(quote: dict, ind: dict, metrics: dict, analysis: dict) -> list[list]:
        """核心指标摘要表"""
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
            ["综合评分", f"{score}/100", "投资评级", rating],
            ["置信度", confidence, "收盘价", f"{quote.get('price', '?')} 元"],
            ["今日涨幅", f"{quote.get('change_pct', 0):+.2f}%", "最大回撤", mdd_str],
            ["近1月收益", ret_1m_str, "近1年收益", ret_1y_str],
            ["年化波动率", vol_str, "夏普比率", str(sharpe)],
            ["均线趋势", ind.get("ma_trend", "N/A"), "RSI(14)", str(ind.get("rsi14", "?"))],
        ]

    @staticmethod
    def _fmt_cap(num: float) -> str:
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
