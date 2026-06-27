"""个股深度分析 PDF 报告生成器

基于现有的 StockReport(FPDF) 基类，生成带图表的个股深度分析报告。
"""

from __future__ import annotations

import datetime
from pathlib import Path

from report.pdf_report import StockReport, C1, C2, CG, CR, CY, CGR, CLB, CW, CB

# ── 常量 ──
_MAX_CHART_WIDTH = 175  # mm, A4 边距内


def generate_individual_report(result: dict, output_dir: str = "reports") -> str:
    """生成个股深度分析 PDF 报告

    Args:
        result: StockAnalyst.analyze() 返回的结构化结果
        output_dir: 输出目录

    Returns:
        PDF 文件路径
    """
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
    pdf.add_cover(
        title=f"{name} ({symbol})",
        subtitle="个股深度分析报告 — AI Stock Advisor",
    )

    # ── 目录 ──
    pdf.add_page()
    pdf.add_section("目录 CONTENTS")
    toc_items = [
        "1. 核心指标一览 Key Metrics",
        "2. 收益与风险分析 Performance & Risk",
        "3. 价格走势图 Price Chart",
        "4. 技术指标分析 Technical Analysis Chart",
        "5. 最大回撤分析 Drawdown Analysis",
        "6. AI 综合研判 AI Analysis",
        "7. 投资建议 Investment Recommendation",
        "8. 风险提示 Risk Disclaimer",
    ]
    for item in toc_items:
        pdf.set_font(*pdf._ft("", 11))
        pdf.set_text_color(*C1)
        pdf.cell(0, 8, f"    {item}", new_x="LMARGIN", new_y="NEXT")

    # ── 1. 核心指标一览 ──
    pdf.add_page()
    pdf.add_section("1. 核心指标一览 Key Metrics")
    _add_metrics_table(pdf, result)

    # ── 2. 收益与风险分析 ──
    pdf.add_section("2. 收益与风险分析 Performance & Risk")
    _add_performance_risk(pdf, result)

    # ── 3. 价格走势图 ──
    pdf.add_page()
    pdf.add_section("3. 价格走势图 Price Chart")
    _add_chart(pdf, result, "price", "价格走势（含均线/成交量/回撤/RSI）")

    # ── 4. 技术指标图 ──
    pdf.add_section("4. 技术指标分析 Technical Analysis")
    _add_chart(pdf, result, "technical", "布林带 + MACD + KDJ")
    _add_technical_summary(pdf, result)

    # ── 5. 最大回撤图 ──
    pdf.add_page()
    pdf.add_section("5. 最大回撤分析 Drawdown Analysis")
    _add_chart(pdf, result, "drawdown", "历史回撤曲线")
    _add_drawdown_details(pdf, result)

    # ── 新闻时间线（如果有） ──
    if "news" in result.get("chart_paths", {}):
        pdf.add_section("新闻时间线 News Timeline")
        _add_chart(pdf, result, "news", "股价走势 + 新闻事件标注")
        _add_news_summary(pdf, result)

    # ── 6. AI 综合研判 ──
    pdf.add_page()
    pdf.add_section("6. AI 综合研判 AI Analysis")
    _add_ai_analysis(pdf, result)

    # ── 7. 投资建议 ──
    pdf.add_section("7. 投资建议 Investment Recommendation")
    _add_investment_advice(pdf, result)

    # ── 8. 风险提示 ──
    pdf.add_section("8. 风险提示 Risk Disclaimer")
    _add_disclaimer(pdf)

    pdf.output(str(filename))
    print(f"\n  ✅ PDF 报告已保存: {filename}")
    return str(filename)


# ════════════════════════════════════════════════════════════
#  内部构建函数
# ════════════════════════════════════════════════════════════


def _add_metrics_table(pdf: StockReport, result: dict):
    """核心指标表格"""
    summary = result.get("summary_table", [])
    if not summary:
        pdf.add_text("指标数据不可用")
        return

    # 表头
    pdf.set_font(*pdf._ft("B", 9))
    pdf.set_fill_color(*C1)
    pdf.set_text_color(*CW)
    col_w = [40, 55, 40, 55]
    for i, h in enumerate(["指标", "数值", "指标", "数值"]):
        pdf.cell(col_w[i], 7, h, border=1, fill=True, align="C")
    pdf.ln()

    # 数据行（跳过第一行标题行）
    pdf.set_font(*pdf._ft("", 8.5))
    for row_idx, row in enumerate(summary[1:], 1):
        if row_idx % 2 == 0:
            pdf.set_fill_color(*CLB)
        else:
            pdf.set_fill_color(*CW)
        pdf.set_text_color(*CB)

        for i, cell_text in enumerate(row):
            pdf.cell(col_w[i], 6, str(cell_text), border=1, fill=True, align="C")
        pdf.ln()

    pdf.ln(4)


def _add_performance_risk(pdf: StockReport, result: dict):
    """收益与风险详细分析"""
    metrics = result.get("metrics", {})

    # 收益
    pdf.add_sub("收益表现")
    returns = [
        ("近 1 月", metrics.get("return_1m")),
        ("近 3 月", metrics.get("return_3m")),
        ("近 6 月", metrics.get("return_6m")),
        ("近 1 年", metrics.get("return_1y")),
        ("年初至今", metrics.get("ytd_return")),
    ]
    for label, val in returns:
        if val is not None:
            color = CG if isinstance(val, (int, float)) and val >= 0 else CR
            txt = f"  {label}: {val:+.2f}%" if isinstance(val, (int, float)) else f"  {label}: {val}"
            pdf.add_text_color(txt, color)

    # 风险
    pdf.add_sub("风险指标")
    risk_items = [
        ("年化波动率", f"{metrics.get('volatility_1y', 'N/A')}%"),
        ("最大回撤", f"{metrics.get('max_drawdown', {}).get('max_dd_pct', 'N/A')}%"),
        ("当前回撤", f"{metrics.get('current_drawdown', 'N/A')}%"),
        ("夏普比率", str(metrics.get("sharpe_ratio", "N/A"))),
        ("卡玛比率", str(metrics.get("calmar_ratio", "N/A"))),
        ("盈亏比", str(metrics.get("win_loss_ratio", {}).get("win_loss_ratio", "N/A"))),
    ]
    for label, val in risk_items:
        pdf.add_text(f"  {label}: {val}")

    wlr = metrics.get("win_loss_ratio", {})
    pdf.add_text(f"  上涨概率: {wlr.get('win_rate', 'N/A')}%"
                 f" (平均涨 {wlr.get('avg_win_pct', 'N/A')}% / 跌 {wlr.get('avg_loss_pct', 'N/A')}%)")


def _add_chart(pdf: StockReport, result: dict, chart_type: str, caption: str):
    """从 result 中获取图表路径并嵌入 PDF"""
    chart_paths = result.get("chart_paths", {})
    path = chart_paths.get(chart_type)
    if path and Path(path).exists():
        pdf.ln(2)
        try:
            pdf.image(path, x=15, w=_MAX_CHART_WIDTH)
            pdf.ln(2)
            pdf.set_font(*pdf._ft("I", 8))
            pdf.set_text_color(*CGR)
            pdf.cell(0, 6, caption, align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        except Exception as e:
            pdf.add_text_color(f"[图表加载失败: {e}]", CR)
    else:
        pdf.add_text_color(f"[图表 {chart_type} 不可用]", CGR)


def _add_technical_summary(pdf: StockReport, result: dict):
    """技术面总结"""
    analysis = result.get("analysis", {})
    tech_text = analysis.get("technical_analysis", "")
    if tech_text:
        pdf.add_sub("技术面简析")
        pdf.add_text(tech_text)


def _add_drawdown_details(pdf: StockReport, result: dict):
    """最大回撤详细分析"""
    dd = result.get("metrics", {}).get("max_drawdown", {})
    if dd:
        peak = dd.get("peak_price", "N/A")
        trough = dd.get("trough_price", "N/A")
        pct = dd.get("max_dd_pct", "N/A")
        duration = dd.get("duration_days", "N/A")

        lines = [
            f"  最高点价格: {peak} 元",
            f"  最低点价格: {trough} 元",
            f"  最大回撤幅度: {pct}%",
            f"  回撤持续天数: {duration} 天",
        ]
        for line in lines:
            pdf.add_text(line)

    # 当前回撤
    current_dd = result.get("metrics", {}).get("current_drawdown")
    if current_dd is not None:
        color = CG if current_dd > -5 else CY if current_dd > -15 else CR
        pdf.add_text_color(f"  当前距前高回撤: {current_dd:+.2f}%", color)


def _add_news_summary(pdf: StockReport, result: dict):
    """新闻情绪总结"""
    analysis = result.get("analysis", {})
    sentiment = analysis.get("news_sentiment", "")
    if sentiment:
        pdf.add_sub("消息面简析")
        pdf.add_text(sentiment)

    news = result.get("news", [])
    if news:
        pdf.add_sub("近期重要新闻")
        for n in news[:8]:
            t = str(n.get("title", ""))
            tm = str(n.get("time", ""))[:10]
            if t:
                pdf.add_text(f"  [{tm}] {t}")


def _add_ai_analysis(pdf: StockReport, result: dict):
    """AI 分析详情"""
    analysis = result.get("analysis", {})
    if not analysis:
        pdf.add_text("AI 分析数据不可用")
        return

    # 评分条
    score = analysis.get("score", 5)
    pdf.add_score_bar("综合评分", score * 10, max_score=100)

    # 摘要
    summary = analysis.get("summary", "")
    if summary:
        pdf.add_sub("核心观点")
        pdf.add_text(summary)

    # 技术面
    tech = analysis.get("technical_analysis", "")
    if tech:
        pdf.add_sub("技术面分析")
        pdf.add_text(tech)

    # 基本面
    fund = analysis.get("fundamental_analysis", "")
    if fund:
        pdf.add_sub("基本面分析")
        pdf.add_text(fund)

    # 新闻情绪
    sentiment = analysis.get("news_sentiment", "")
    if sentiment:
        pdf.add_sub("新闻情绪分析")
        pdf.add_text(sentiment)

    # 风险评估
    risk = analysis.get("risk_assessment", "")
    if risk:
        pdf.add_sub("风险评估")
        pdf.add_text(risk)

    # 后市展望
    outlook = analysis.get("outlook", "")
    if outlook:
        pdf.add_sub("后市展望")
        pdf.add_text(outlook)


def _add_investment_advice(pdf: StockReport, result: dict):
    """投资建议"""
    analysis = result.get("analysis", {})
    metrics = result.get("metrics", {})

    rating = analysis.get("rating", "中性观望")
    score = analysis.get("score", 5)
    confidence = analysis.get("confidence", "中")
    theme = analysis.get("investment_theme", "")
    position = analysis.get("position_suggestion", "")
    levels = analysis.get("key_levels", {})
    risks = analysis.get("risks_to_watch", [])

    # 评级
    rating_color = CG if rating in ("强烈推荐", "推荐买入") else CY if rating == "中性观望" else CR
    pdf.add_text_color(f"投资评级: {rating}  (评分: {score}/10, 置信度: {confidence})", rating_color)

    # 核心逻辑
    if theme:
        pdf.add_sub("核心投资逻辑")
        pdf.add_text(theme)

    # 关键价位
    if levels:
        pdf.add_sub("关键价位")
        pdf.add_text(f"  支撑位: {levels.get('support', 'N/A')}")
        pdf.add_text(f"  阻力位: {levels.get('resistance', 'N/A')}")
        stop_loss = levels.get("stop_loss")
        if stop_loss:
            pdf.add_text_color(f"  建议止损: {stop_loss} 元", CR)

    # 仓位建议
    if position:
        pdf.add_sub("仓位建议")
        bar_color = CG if "重仓" in position else CY if "半仓" in position else CGR
        pdf.add_text_color(f"  建议仓位: {position}", bar_color)

    # 风险提示
    if risks:
        pdf.add_sub("关注风险")
        for r in risks:
            pdf.add_text_color(f"  ⚠️ {r}", CR)

    # 支撑阻力详细
    sr = metrics.get("support_resistance", {})
    if sr:
        pdf.add_sub("技术面关键位")
        supports = sr.get("supports", [])
        resistances = sr.get("resistances", [])
        if supports:
            pdf.add_text("支撑位 (由近到远): " + " → ".join(
                f"{s['name']}({s['price']})" for s in supports
            ))
        if resistances:
            pdf.add_text("阻力位 (由近到远): " + " → ".join(
                f"{r['name']}({r['price']})" for r in resistances
            ))


def _add_disclaimer(pdf: StockReport):
    """风险提示"""
    warnings = [
        "1. 本报告由 AI 模型自动生成，仅供参考，不构成投资建议。",
        "2. 技术分析基于历史数据，历史表现不代表未来收益。",
        "3. 模型准确率约 60-65%，存在 35-40% 的误差空间。",
        "4. 请结合基本面分析、政策分析等做出综合判断。",
        "5. 股市有风险，投资需谨慎，请注意仓位控制。",
        f"6. 报告生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    for w in warnings:
        pdf.set_font(*pdf._ft("", 9.5))
        pdf.set_text_color(*CGR)
        pdf.cell(0, 8, w, new_x="LMARGIN", new_y="NEXT")


def _generate_error_report(result: dict, filename: Path):
    """生成错误报告"""
    pdf = StockReport()
    pdf.add_cover(
        title=f"{result.get('name', '?')} ({result.get('symbol', '?')})",
        subtitle="分析失败",
    )
    pdf.add_page()
    pdf.add_section("错误信息")
    pdf.add_text_color(f"分析失败: {result.get('error', '未知错误')}", CR)
    pdf.output(str(filename))
    print(f"\n  ⚠️ 错误报告已保存: {filename}")
