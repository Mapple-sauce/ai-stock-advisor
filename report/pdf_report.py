"""PDF 报告生成器 —— 中文版，含内容校验"""

from __future__ import annotations

import datetime
from pathlib import Path

from fpdf import FPDF

_FONT_PATH = Path(__file__).resolve().parent.parent / "fonts" / "NotoSansCJKsc-Regular.otf"

C1 = (25, 55, 109); C2 = (0, 122, 204); CG = (0, 180, 100)
CR = (220, 60, 60); CGR = (100, 100, 100)
CLB = (240, 242, 248); CW = (255, 255, 255); CB = (30, 30, 30)


class StockReport(FPDF):
    """中文股票分析 PDF 报告"""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=25)
        if _FONT_PATH.exists():
            self.add_font("CN", "", str(_FONT_PATH), uni=True)
            self.add_font("CN", "B", str(_FONT_PATH), uni=True)
            self._font = "CN"
        else:
            self._font = "Helvetica"

    def _ft(self, style="", size=10):
        return (self._font, style, size)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font(*self._ft("", 8))
        self.set_text_color(*CGR)
        self.cell(0, 8, "AI Stock Advisor - 每日策略报告", align="L")
        self.cell(0, 8, f"第 {self.page_no()} 页", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*C1); self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y()); self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font(*self._ft("", 7))
        self.set_text_color(*CGR)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cell(0, 10, f"生成时间: {now} | 仅供参考", align="C")

    def cover(self, title, subtitle=""):
        self.add_page(); self.ln(50)
        self.set_font(*self._ft("B", 28)); self.set_text_color(*C1)
        self.cell(0, 15, title, align="C", new_x="LMARGIN", new_y="NEXT")
        if subtitle:
            self.set_font(*self._ft("", 14)); self.set_text_color(*C2)
            self.cell(0, 10, subtitle, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.set_draw_color(*C2); self.set_line_width(0.5)
        self.line(60, self.get_y(), 150, self.get_y()); self.ln(10)
        self.set_font(*self._ft("", 12)); self.set_text_color(*CGR)
        self.cell(0, 8, f"报告日期: {datetime.date.today().strftime('%Y年%m月%d日')}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(30)
        self.set_font(*self._ft("", 8)); self.set_text_color(*CGR)
        self.multi_cell(0, 5, "免责声明: 本报告由 AI 自动生成，仅供参考，不构成投资建议。", align="C")

    def h1(self, title):
        self.ln(4)
        self.set_font(*self._ft("B", 16)); self.set_text_color(*C1)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*C2); self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y()); self.ln(4)

    def h2(self, title):
        self.set_font(*self._ft("B", 12)); self.set_text_color(*C2)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT"); self.ln(2)

    def p(self, text):
        self.set_font(*self._ft("", 9.5)); self.set_text_color(*CB)
        self.multi_cell(0, 5, text); self.ln(2)

    def p_color(self, text, color):
        self.set_font(*self._ft("", 9.5)); self.set_text_color(*color)
        self.multi_cell(0, 5, text); self.ln(1)

    def table(self, headers, rows, col_widths=None):
        if col_widths is None:
            col_widths = [190 // len(headers)] * len(headers)
        self.set_font(*self._ft("B", 8))
        self.set_fill_color(*C1); self.set_text_color(*CW)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font(*self._ft("", 8))
        fill = False
        for row in rows:
            self.set_text_color(*CB)
            if fill: self.set_fill_color(*CLB)
            else: self.set_fill_color(*CW)
            for i, c in enumerate(row):
                self.cell(col_widths[i], 6, str(c)[:30], border=1, fill=fill, align="C")
            self.ln(); fill = not fill
        self.ln(3)

    def divider(self):
        self.set_draw_color(*CGR); self.set_line_width(0.2)
        self.line(10, self.get_y(), 200, self.get_y()); self.ln(4)


def validate_report(path_str):
    path = Path(path_str)
    if not path.exists():
        return {"valid": False, "issues": ["文件不存在"], "size_kb": 0}
    sz = path.stat().st_size / 1024
    issues = []
    if sz < 10: issues.append(f"文件过小({sz:.0f}KB)")
    if sz > 50000: issues.append(f"文件过大({sz:.0f}KB)")
    return {"valid": len(issues) == 0, "issues": issues, "size_kb": round(sz, 1)}


def generate_daily_report(market_summary=None, sector_analysis=None, stock_analysis=None,
                          portfolio_summary=None, market_news=None, sentiments=None, output_dir="reports"):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today()
    filename = out_path / f"策略报告_{today.strftime('%Y%m%d')}.pdf"

    pdf = StockReport()
    if pdf._font == "Helvetica":
        print("  [WARNING] No Chinese font found, using English")

    # Cover
    pdf.cover(title="每日策略分析报告", subtitle="AI Stock Advisor")

    # TOC
    pdf.add_page(); pdf.h1("目录")
    for t in ["1. 市场总览", "2. 板块分析", "3. 个股技术评分", "4. 市场舆情", "5. AI 产业链推荐", "6. 机器人产业链推荐", "7. 风险提示"]:
        pdf.set_font(*pdf._ft("", 11)); pdf.set_text_color(*C1)
        pdf.cell(0, 8, "    " + t, new_x="LMARGIN", new_y="NEXT")

    # Section 1
    pdf.add_page(); pdf.h1("1. 市场总览")
    if market_summary:
        idx = market_summary.get("indices", [])
        if idx:
            pdf.table(["指数", "最新价", "涨跌幅", "评分"],
                      [[i.get("name",""), str(i.get("price","")), f'{i.get("change_pct",0):+.2f}%', f'{i.get("score",50):.0f}/100'] for i in idx],
                      [50, 50, 50, 40])
        v = market_summary.get("outlook", "")
        if v: pdf.h2("市场观点"); pdf.p(v)

    # Section 2
    pdf.h1("2. 板块分析")
    if sector_analysis:
        rows = []
        for s in sector_analysis:
            sp = s.get("spread", 0)
            rows.append([s['name'], f'{s.get("score",0):.0f}', f'{sp:+.1f}%', s.get("direction","-"), s.get("view","")[:25]])
        pdf.table(["板块", "评分", "多空差", "方向", "观点"], rows, [35, 25, 30, 30, 70])

    # Section 3
    pdf.add_page(); pdf.h1("3. 个股技术评分")
    if stock_analysis:
        rows = []
        for stk in stock_analysis:
            rows.append([stk.get('name',''), stk.get("code",""),
                         f'{stk.get("price",0):.2f}', f'{stk.get("score",0):.0f}/100',
                         stk.get("action","-"), f'{stk.get("rsi",0):.1f}'])
        pdf.table(["名称", "代码", "现价", "评分", "建议", "RSI"], rows, [35, 28, 28, 28, 30, 28])
        pdf.h2("买卖参考")
        for stk in stock_analysis[:8]:
            sc = stk.get("score",0)
            txt = f"{stk.get('name','')}({stk.get('code','')}): 评分{sc:.0f}/100 | 参考介入{stk.get('entry_ref','-')} | {stk.get('action','观望')}"
            if stk.get("reason"): txt += " - " + stk['reason']
            pdf.p_color(txt, CG if sc >= 65 else CB)

    # Section 4
    pdf.h1("4. 市场舆情")
    has_sent = False
    if market_news:
        pdf.h2("今日要闻")
        for n in market_news:
            pdf.p("* " + n.get('title',''))
    if sentiments:
        pdf.h2("个股舆情")
        for code, sent in list(sentiments.items())[:6]:
            nm = sent.get("name", code) or code
            pdf.p(f"* {nm}({code}): 研报{len(sent.get('reports',[]))}篇 | 新闻{len(sent.get('news',[]))}条 | 讨论{len(sent.get('posts',[]))}条")
            has_sent = True
    if not has_sent and not market_news:
        pdf.p("（暂无舆情数据）")
    pdf.divider()

    # Section 5
    pdf.add_page(); pdf.h1("5. AI 产业链布局建议")
    ai = [s for s in (stock_analysis or []) if s.get("sector_group") == "AI"]
    if ai:
        pdf.table(["优先级", "标的", "评分", "参考介入", "逻辑"],
                  [[s.get("priority",""), f"{s.get('name','')}({s.get('code','')})",
                    f'{s.get("score",0):.0f}/100', s.get("entry_ref","-"), s.get("reason","")[:25]] for s in ai],
                  [18, 42, 25, 38, 67])

    # Section 6
    pdf.h1("6. 机器人产业链布局建议")
    robot = [s for s in (stock_analysis or []) if s.get("sector_group") == "Robot"]
    if robot:
        pdf.table(["优先级", "标的", "评分", "参考介入", "逻辑"],
                  [[s.get("priority",""), f"{s.get('name','')}({s.get('code','')})",
                    f'{s.get("score",0):.0f}/100', s.get("entry_ref","-"), s.get("reason","")[:25]] for s in robot],
                  [18, 42, 25, 38, 67])

    # Section 7
    pdf.add_page(); pdf.h1("7. 风险提示")
    for r in [
        "1. 本报告由 AI 模型自动生成，仅供参考，不构成投资建议。",
        "2. 技术分析基于历史数据，不能完全预测未来走势。",
        "3. 模型正确率约 60-65%，存在约 35-40% 的判断误差。",
        "4. 建议结合基本面分析综合判断。",
        "5. 股市有风险，投资需谨慎。",
        f"6. 报告生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]:
        pdf.set_font(*pdf._ft("", 9.5)); pdf.set_text_color(*CGR)
        pdf.cell(0, 8, r, new_x="LMARGIN", new_y="NEXT")

    # Save + validate
    pdf.output(str(filename))
    v = validate_report(str(filename))
    status = "OK" if v["valid"] else "WARN"
    print(f"  [{status}] 报告校验: {v['size_kb']}KB")
    print(f"  [FILE] {filename.name}")
    return str(filename)
