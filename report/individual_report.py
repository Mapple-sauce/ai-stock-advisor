"""个股深度分析 PDF 报告生成器

基于 StockReport(FPDF) 基类，生成带图表的个股深度分析报告。
"""

from __future__ import annotations

import datetime
from pathlib import Path

import numpy as np

from report.pdf_report import StockReport, C1, C2, CG, CR, CY, CGR, CLB, CW, CB

_MAX_CHART_WIDTH = 175


def generate_individual_report(result: dict, output_dir: str = "reports") -> str:
    """生成个股深度分析 PDF 报告"""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    symbol = result.get("symbol", "unknown")
    name = result.get("name", symbol)
    today = datetime.date.today()
    filename = out_path / f"{name}_{symbol}_{today.strftime('%Y%m%d')}.pdf"

    if result.get("status") == "error":
        _generate_error_report(result, filename)
        return str(filename)

    pdf = StockReport()

    # ── 封面 ──
    pdf.cover(
        title=f"{name} ({symbol})",
        subtitle="个股深度分析报告 — AI Stock Advisor",
    )
    pdf.ln(-15)
    pdf.set_font(*pdf._ft("", 8))
    pdf.set_text_color(*CGR)
    pdf.cell(0, 6, "📖 指标不懂？见配套手册: 投资指标参考手册.pdf", align="C", new_x="LMARGIN", new_y="NEXT")

    # ── 目录 ──
    pdf.add_page()
    pdf.h1("目录 CONTENTS")
    for item in [
        "1. 核心指标一览",
        "2. 收益与风险分析",
        "3. 价格走势图",
        "4. 技术指标分析",
        "5. 最大回撤分析",
        "6. AI 综合研判",
        "7. 行业与供应链分析",
        "8. 财报深度分析",
        "9. 投资建议",
        "10. 风险提示",
    ]:
        pdf.set_font(*pdf._ft("", 11))
        pdf.set_text_color(*C1)
        pdf.cell(0, 8, f"    {item}", new_x="LMARGIN", new_y="NEXT")

    # ── 1 ──
    pdf.add_page()
    pdf.h1("1. 核心指标一览 Key Metrics")
    _add_metrics_table(pdf, result)

    # ── 2 ──
    pdf.h1("2. 收益与风险分析 Performance & Risk")
    _add_performance_risk(pdf, result)

    # ── 3 ──
    pdf.add_page()
    pdf.h1("3. 价格走势图 Price Chart")
    _add_chart(pdf, result, "price", "价格走势（含均线/成交量/回撤/RSI）")

    # ── 4 ──
    pdf.h1("4. 技术指标分析 Technical Analysis")
    _add_chart(pdf, result, "technical", "布林带 + MACD + KDJ")
    _add_technical_summary(pdf, result)

    # ── 5 ──
    pdf.add_page()
    pdf.h1("5. 最大回撤分析 Drawdown Analysis")
    _add_chart(pdf, result, "drawdown", "历史回撤曲线")
    _add_drawdown_details(pdf, result)

    # ── 新闻时间线（如果有） ──
    if "news" in result.get("chart_paths", {}):
        pdf.h1("新闻时间线 News Timeline")
        _add_chart(pdf, result, "news", "股价走势 + 新闻事件标注")
        _add_news_summary(pdf, result)

    # ── 6 ──
    pdf.add_page()
    pdf.h1("6. AI 综合研判 AI Analysis")
    _add_ai_analysis(pdf, result)

    # ── 7: 行业与供应链分析 ──
    pdf.add_page()
    pdf.h1("7. 行业与供应链分析 Industry & Supply Chain")
    _add_industry_analysis(pdf, result)

    # ── 8: 财报深度分析 ──
    pdf.h1("8. 财报深度分析 Financial Deep Dive")
    _add_financial_deep_dive(pdf, result)

    # ── 9 ──
    pdf.add_page()
    pdf.h1("9. 投资建议 Investment Recommendation")
    _add_investment_advice(pdf, result)

    # ── 10 ──
    pdf.h1("10. 风险提示 Risk Disclaimer")
    _add_disclaimer(pdf)

    pdf.output(str(filename))
    print(f"\n  ✅ PDF 报告已保存: {filename}")
    return str(filename)


# ════════════════════════════════════════════════


def _add_metrics_table(pdf: StockReport, result: dict):
    """核心指标表格"""
    summary = result.get("summary_table", [])
    if not summary:
        pdf.p("指标数据不可用")
        return

    pdf.set_font(*pdf._ft("B", 9))
    pdf.set_fill_color(*C1)
    pdf.set_text_color(*CW)
    col_w = [40, 55, 40, 55]
    for i, h in enumerate(["指标", "数值", "指标", "数值"]):
        pdf.cell(col_w[i], 7, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font(*pdf._ft("", 8.5))
    for row_idx, row in enumerate(summary[1:], 1):
        pdf.set_fill_color(*CLB) if row_idx % 2 == 0 else pdf.set_fill_color(*CW)
        pdf.set_text_color(*CB)
        for i, cell_text in enumerate(row):
            pdf.cell(col_w[i], 6, str(cell_text), border=1, fill=True, align="C")
        pdf.ln()
    pdf.ln(4)


def _add_performance_risk(pdf: StockReport, result: dict):
    """收益与风险详细分析"""
    metrics = result.get("metrics", {})

    pdf.h2("收益表现")
    for label, val in [
        ("近 1 月", metrics.get("return_1m")),
        ("近 3 月", metrics.get("return_3m")),
        ("近 6 月", metrics.get("return_6m")),
        ("近 1 年", metrics.get("return_1y")),
        ("年初至今", metrics.get("ytd_return")),
    ]:
        if val is not None:
            color = CG if isinstance(val, (int, float)) and val >= 0 else CR
            txt = f"  {label}: {val:+.2f}%" if isinstance(val, (int, float)) else f"  {label}: {val}"
            pdf.p_color(txt, color)

    pdf.h2("风险指标")
    for label, val in [
        ("年化波动率", f"{metrics.get('volatility_1y', 'N/A')}%"),
        ("最大回撤", f"{metrics.get('max_drawdown', {}).get('max_dd_pct', 'N/A')}%"),
        ("当前回撤", f"{metrics.get('current_drawdown', 'N/A')}%"),
        ("夏普比率", str(metrics.get("sharpe_ratio", "N/A"))),
        ("卡玛比率", str(metrics.get("calmar_ratio", "N/A"))),
        ("盈亏比", str(metrics.get("win_loss_ratio", {}).get("win_loss_ratio", "N/A"))),
    ]:
        pdf.p(f"  {label}: {val}")

    wlr = metrics.get("win_loss_ratio", {})
    pdf.p(f"  上涨概率: {wlr.get('win_rate', 'N/A')}%"
          f" (平均涨 {wlr.get('avg_win_pct', 'N/A')}% / 跌 {wlr.get('avg_loss_pct', 'N/A')}%)")


def _add_chart(pdf: StockReport, result: dict, chart_type: str, caption: str):
    """嵌入图表"""
    chart_paths = result.get("chart_paths", {})
    path = chart_paths.get(chart_type)
    if path and Path(path).exists():
        pdf.ln(2)
        try:
            pdf.image(path, x=15, w=_MAX_CHART_WIDTH)
            pdf.ln(2)
            pdf.set_font(*pdf._ft("", 8))
            pdf.set_text_color(*CGR)
            pdf.cell(0, 6, caption, align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        except Exception as e:
            pdf.p_color(f"[图表加载失败: {e}]", CR)
    else:
        pdf.p_color(f"[图表 {chart_type} 不可用]", CGR)


def _add_technical_summary(pdf: StockReport, result: dict):
    """技术面简析"""
    tech_text = result.get("analysis", {}).get("technical_analysis", "")
    if tech_text:
        pdf.h2("技术面简析")
        pdf.p(tech_text)


def _add_drawdown_details(pdf: StockReport, result: dict):
    """回撤详情"""
    dd = result.get("metrics", {}).get("max_drawdown", {})
    if dd:
        for line in [
            f"  最高点价格: {dd.get('peak_price', 'N/A')} 元",
            f"  最低点价格: {dd.get('trough_price', 'N/A')} 元",
            f"  最大回撤幅度: {dd.get('max_dd_pct', 'N/A')}%",
            f"  回撤持续天数: {dd.get('duration_days', 'N/A')} 天",
        ]:
            pdf.p(line)

    current_dd = result.get("metrics", {}).get("current_drawdown")
    if current_dd is not None:
        color = CG if current_dd > -5 else CY if current_dd > -15 else CR
        pdf.p_color(f"  当前距前高回撤: {current_dd:+.2f}%", color)


def _add_news_summary(pdf: StockReport, result: dict):
    """消息面"""
    sentiment = result.get("analysis", {}).get("news_sentiment", "")
    if sentiment:
        pdf.h2("消息面简析")
        pdf.p(sentiment)

    news = result.get("news", [])
    if news:
        pdf.h2("近期重要新闻")
        for n in news[:8]:
            t = str(n.get("title", ""))
            tm = str(n.get("time", ""))[:10]
            if t:
                pdf.p(f"  [{tm}] {t}")


def _add_ai_analysis(pdf: StockReport, result: dict):
    """AI 研判"""
    analysis = result.get("analysis", {})
    if not analysis:
        pdf.p("AI 分析数据不可用")
        return

    # score is now 1-100 (percentile)
    score = analysis.get("score", 50)
    if isinstance(score, (int, float)):
        _draw_score_bar(pdf, "综合评分", int(score))
    else:
        _draw_score_bar(pdf, "综合评分", 50)

    for section, key in [
        ("核心观点", "summary"),
        ("技术面分析", "technical_analysis"),
        ("基本面分析", "fundamental_analysis"),
        ("新闻情绪分析", "news_sentiment"),
        ("风险评估", "risk_assessment"),
        ("后市展望", "outlook"),
    ]:
        text = analysis.get(key, "")
        if text:
            pdf.h2(section)
            pdf.p(text)


def _add_industry_analysis(pdf: StockReport, result: dict):
    """行业与供应链分析"""
    sector = result.get("sector", "")
    sector_data = result.get("sector_performance", {})
    ranking = result.get("industry_ranking", {})
    supply_chain = result.get("supply_chain_context", {})

    # 板块总览
    if sector:
        pdf.h2(f"所属板块: {sector}")
        if "error" not in sector_data:
            pdf.p(f"  近1日: {sector_data.get('change_1d', '?')}% | "
                  f"成交额: {sector_data.get('volume', '?')}亿 | "
                  f"上涨/下跌: {sector_data.get('leader_count', '?')}/{sector_data.get('laggard_count', '?')}")
            if sector_data.get("top_gainers"):
                gainers = ", ".join(f"{s['name']}({s['change_pct']:+.1f}%)" for s in sector_data["top_gainers"][:3])
                pdf.p(f"  板块领涨: {gainers}")
        pdf.p("")

    # 行业排名
    if ranking and ranking.get("total_peers", 0) > 0:
        pdf.h2("行业排名")
        pdf.p(f"  可比公司: {ranking['total_peers']}家")
        pdf.p(f"  市值排名: {ranking.get('market_cap_rank', 'N/A')} (行业中位数市值 {ranking.get('market_cap_median', 0)/1e8:.1f}亿)")
        pdf.p(f"  PE排名: {ranking.get('pe_rank', 'N/A')} (行业中位数PE {ranking.get('pe_median', '?')})")
        pdf.p("")

    # 板块分析AI报告
    analysis_sector = result.get("analysis_sector")
    if analysis_sector:
        pdf.h2("7a. 行业板块分析")
        pdf.p(analysis_sector[:1000])  # 截取避免过长

    # 行业地位报告
    analysis_position = result.get("analysis_position")
    if analysis_position:
        pdf.h2("7b. 行业地位分析")
        pdf.p(analysis_position[:1000])

    # 供应链报告
    analysis_supply = result.get("analysis_supply_chain")
    if analysis_supply:
        pdf.h2("7c. 供应链分析")
        pdf.p(analysis_supply[:1000])

    if not any([analysis_sector, analysis_position, analysis_supply]):
        pdf.p("行业分析数据暂不可用")


def _add_financial_deep_dive(pdf: StockReport, result: dict):
    """财报深度分析"""
    financial = result.get("financial", {})
    if "error" in financial or not financial:
        pdf.p("财报数据暂不可用")
        return

    # 当前指标
    pdf.h2("最新财务指标")
    items = [
        ("营业收入", f"{financial.get('revenue', 0)/1e8:.1f}亿" if financial.get('revenue') else "N/A"),
        ("营收同比", f"{financial.get('revenue_yoy', 'N/A')}%"),
        ("净利润", f"{financial.get('net_profit', 0)/1e8:.1f}亿" if financial.get('net_profit') else "N/A"),
        ("净利润同比", f"{financial.get('profit_yoy', 'N/A')}%"),
    ]
    if financial.get("roe"):
        items.append(("ROE", f"{financial['roe']}%"))
    if financial.get("debt_ratio"):
        items.append(("资产负债率", f"{financial['debt_ratio']}%"))
    if financial.get("operating_cashflow"):
        items.append(("经营现金流", f"{financial['operating_cashflow']/1e8:.1f}亿"))
    if financial.get("rd_ratio"):
        items.append(("研发占比", f"{financial['rd_ratio']}%"))

    # 2列显示
    pdf.set_font(*pdf._ft("B", 9))
    pdf.set_fill_color(*C1)
    pdf.set_text_color(*CW)
    col_w = [40, 55, 40, 55]
    for i, h in enumerate(["指标", "数值", "指标", "数值"]):
        pdf.cell(col_w[i], 7, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font(*pdf._ft("", 8.5))
    for row_idx in range(0, len(items), 2):
        pdf.set_fill_color(*CLB) if (row_idx // 2) % 2 == 0 else pdf.set_fill_color(*CW)
        pdf.set_text_color(*CB)
        for j in range(2):
            idx = row_idx + j
            if idx < len(items):
                pdf.cell(col_w[0], 6, items[idx][0], border=1, fill=True, align="C")
                pdf.cell(col_w[1], 6, str(items[idx][1]), border=1, fill=True, align="C")
            else:
                pdf.cell(col_w[0] + col_w[1], 6, "", border=1, fill=True, align="C")
        pdf.ln()
    pdf.ln(4)

    # 近4个季度趋势
    quarters = financial.get("quarters", [])
    if len(quarters) >= 2:
        pdf.h2("近4个季度营收与利润趋势")
        pdf.table(
            ["报告期", "营收同比", "利润同比", "毛利率", "净利率"],
            [
                [
                    q.get("report_date", "")[-7:],
                    f"{q.get('revenue_yoy', 0):+.1f}%",
                    f"{q.get('profit_yoy', 0):+.1f}%",
                    f"{q.get('gross_margin', 0):.1f}%",
                    f"{q.get('net_margin', 0):.1f}%",
                ]
                for q in quarters
            ],
            [38, 38, 38, 38, 38],
        )

        # 趋势判断
        rev_trends = [q.get("revenue_yoy", 0) for q in quarters]
        profit_trends = [q.get("profit_yoy", 0) for q in quarters]
        avg_rev = sum(rev_trends) / len(rev_trends)
        avg_profit = sum(profit_trends) / len(profit_trends)

        if avg_rev > 15 and avg_profit > 15:
            pdf.p_color("  📈 营收和利润持续高增长 (>15%)，成长性优秀", CG)
        elif avg_rev > 5 and avg_profit > 5:
            pdf.p_color("  📈 营收和利润稳步增长，经营状况良好", CG)
        elif avg_rev < -5 and avg_profit < -5:
            pdf.p_color("  📉 营收和利润双降，需警惕基本面恶化", CR)
        elif avg_profit < avg_rev:
            pdf.p_color("  🟡 利润增速低于营收增速，关注利润率变化", CY)
        else:
            pdf.p_color("  🟡 业绩增长平稳，关注后续季度变化", CY)

    # 报告日期
    if financial.get("report_date"):
        pdf.p(f"  数据截止: {financial['report_date']}")


def _add_investment_advice(pdf: StockReport, result: dict):
    """投资建议 + 价格预测 + 买卖点"""
    analysis = result.get("analysis", {})
    metrics = result.get("metrics", {})

    rating = analysis.get("rating", "中性观望")
    score = analysis.get("score", 50)
    confidence = analysis.get("confidence", "中")
    theme = analysis.get("investment_theme", "")
    position = analysis.get("position_suggestion", "")
    levels = analysis.get("key_levels", {})
    risks = analysis.get("risks_to_watch", [])

    rating_color = CG if rating in ("强烈推荐", "推荐买入") else CY if rating == "中性观望" else CR
    pdf.p_color(f"投资评级: {rating}  (评分: {score}/100, 置信度: {confidence})", rating_color)

    # ── 价格预测 ──
    _add_price_prediction(pdf, result)

    if theme:
        pdf.h2("核心投资逻辑")
        pdf.p(theme)

    if levels:
        pdf.h2("关键价位")
        pdf.p(f"  支撑位: {levels.get('support', 'N/A')}")
        pdf.p(f"  阻力位: {levels.get('resistance', 'N/A')}")
        stop_loss = levels.get("stop_loss")
        if stop_loss:
            pdf.p_color(f"  建议止损: {stop_loss} 元", CR)

    if position:
        pdf.h2("仓位建议")
        bar_color = CG if "重仓" in position else CY if "半仓" in position else CGR
        pdf.p_color(f"  建议仓位: {position}", bar_color)

    if risks:
        pdf.h2("关注风险")
        for r in risks:
            pdf.p_color(f"  ⚠️ {r}", CR)

    sr = metrics.get("support_resistance", {})
    if sr:
        pdf.h2("技术面关键位")
        supports = sr.get("supports", [])
        resistances = sr.get("resistances", [])
        if supports:
            pdf.p("支撑位 (由近到远): " + " → ".join(f"{s['name']}({s['price']})" for s in supports))
        if resistances:
            pdf.p("阻力位 (由近到远): " + " → ".join(f"{r['name']}({r['price']})" for r in resistances))


def _add_disclaimer(pdf: StockReport):
    """风险提示"""
    for w in [
        "1. 本报告由 AI 模型自动生成，仅供参考，不构成投资建议。",
        "2. 技术分析基于历史数据，历史表现不代表未来收益。",
        "3. 模型准确率约 60-65%，存在 35-40% 的误差空间。",
        "4. 请结合基本面分析、政策分析等做出综合判断。",
        "5. 股市有风险，投资需谨慎，请注意仓位控制。",
        f"6. 报告生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]:
        pdf.set_font(*pdf._ft("", 9.5))
        pdf.set_text_color(*CGR)
        pdf.cell(0, 8, w, new_x="LMARGIN", new_y="NEXT")


def _generate_error_report(result: dict, filename: Path):
    """错误报告"""
    pdf = StockReport()
    pdf.cover(
        title=f"{result.get('name', '?')} ({result.get('symbol', '?')})",
        subtitle="分析失败",
    )
    pdf.add_page()
    pdf.h1("错误信息")
    pdf.p_color(f"分析失败: {result.get('error', '未知错误')}", CR)
    pdf.output(str(filename))
    print(f"\n  ⚠️ 错误报告已保存: {filename}")


def _add_price_prediction(pdf: StockReport, result: dict):
    """基于历史波动率的统计价格预测 + 买卖点建议"""
    price = result.get("price", 0)
    metrics = result.get("metrics", {})
    volatility = metrics.get("volatility_1y", 30)
    analysis = result.get("analysis", {})
    levels = analysis.get("key_levels", {})

    if not price or float(price) <= 0:
        return

    price_f = float(price)
    daily_vol = (volatility / 100) / np.sqrt(252) if volatility else 0.03

    def simulate(days):
        np.random.seed(42)
        paths = np.zeros((5000, days + 1))
        paths[:, 0] = price_f
        for d in range(days):
            paths[:, d + 1] = paths[:, d] * (1 + np.random.normal(0, daily_vol, 5000))
        f = paths[:, -1]
        return {"median": float(np.median(f)), "p25": float(np.percentile(f, 25)),
                "p75": float(np.percentile(f, 75))}

    pred_1w = simulate(5)
    pred_1m = simulate(21)

    pdf.h2("📈 价格预测区间（波动率模型）")
    pdf.p("基于历史波动率的统计模拟，非精确预测。")

    for period, p in [("未来 1 周", pred_1w), ("未来 1 月", pred_1m)]:
        pdf.p(f"  {period}: {p['p25']:.2f} ~ {p['median']:.2f} ~ {p['p75']:.2f} 元")

    pdf.h2("💰 买卖参考建议")
    score = float(analysis.get("score", 50))
    support = levels.get("support", "")
    resistance = levels.get("resistance", "")
    stop_loss = levels.get("stop_loss", "")

    buy_high = pred_1w["median"] * 0.98
    sell_low = pred_1w["median"] * 1.02

    if score >= 65:
        pdf.p_color(f"  🟢 买入区间: 不高于 {buy_high:.2f} 元", CG)
        pdf.p_color(f"  🔴 卖出区间: 不低于 {sell_low:.2f} 元", CR)
    else:
        pdf.p_color(f"  🟡 当前评分偏低({score:.0f}/100), 建议观望", CY)
        if buy_high > price_f * 0.95:
            pdf.p(f"  若想介入, 建议等回落到 {price_f*0.95:.2f} 元以下")

    if support: pdf.p(f"  📊 参考支撑: {support}")
    if resistance: pdf.p(f"  📊 参考阻力: {resistance}")
    if stop_loss: pdf.p_color(f"  ⛔ 止损位: {stop_loss}", CR)

    pdf.h2("📋 策略建议")
    is_oversold = isinstance(metrics.get("return_1m"), (int, float)) and metrics["return_1m"] < -15
    if score >= 70:
        pdf.p_color("  当前策略: 积极布局 ✅", CG)
        pdf.p("  评分较高，建议逢低分批建仓，分 2-3 次买入")
        pdf.p("  持有周期: 中线 1-3 个月")
        pdf.p_color("  建议仓位: 半仓~7成", CY)
    elif score >= 50:
        pdf.p_color("  当前策略: 中性观望 🟡", CY)
        pdf.p("  评分中等，方向不明，等待评分升至 70+ 或跌至超卖区")
        pdf.p_color("  建议仓位: 轻仓~半仓", CY)
    elif is_oversold:
        pdf.p_color("  当前策略: 左侧关注 ⚠️", CY)
        pdf.p("  已超跌，可能是底部区域，但需严格止损")
        pdf.p_color("  建议仓位: 1~2成试探仓", CR)
    else:
        pdf.p_color("  当前策略: 回避 🔴", CR)
        pdf.p("  技术面较弱，不建议买入，持有者注意止损")
        pdf.p_color("  建议仓位: 空仓观望", CR)


def _draw_score_bar(pdf: StockReport, label: str, score: int, max_score: int = 100):
    """绘制简易评分条（百分制）"""
    pdf.ln(4)
    pdf.set_font(*pdf._ft("B", 10))
    pdf.set_text_color(*CB)
    pdf.cell(190, 8, f"  {label}: {score}/{max_score}", new_x="LMARGIN", new_y="NEXT")

    pct = min(score / max_score, 1.0)
    pdf.set_line_width(0)
    # 背景
    pdf.set_fill_color(*CLB)
    pdf.rect(15, pdf.get_y(), 170, 8, style="F")
    # 填充
    bar_color = CG if pct >= 0.6 else CY if pct >= 0.4 else CR
    pdf.set_fill_color(*bar_color)
    pdf.rect(15, pdf.get_y(), max(1, 170 * pct), 8, style="F")
    # 文字
    pdf.set_xy(15, pdf.get_y())
    pdf.set_font(*pdf._ft("B", 8))
    pdf.set_text_color(*CW)
    pdf.cell(170, 8, f"{score}/{max_score}", align="C")
    pdf.ln(12)
