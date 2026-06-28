"""PDF 报告生成器 —— 中文版，含内容校验

字体策略（按优先级）:
  1. 系统 wqy-microhei.ttc (apt install fonts-wqy-microhei)
  2. 系统 NotoSansCJK OTF/TTC (apt install fonts-noto-cjk)
  3. 下载静态 TTF 兜底 (Google Fonts API)
"""

from __future__ import annotations

import datetime
from pathlib import Path

from fpdf import FPDF

# ── 中文字体搜索路径（按优先级） ──
_SYS_FONTS = [
    # 文泉驿微米黑 (TTC, fpdf2 2.7+ 支持)
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    # Noto CJK (TTC 合集)
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    # Noto CJK SC (CFF OTF)
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
]

_LOCAL_DIR = Path(__file__).resolve().parent.parent / "fonts"
_LOCAL_OTF = _LOCAL_DIR / "NotoSansCJKsc-Regular.otf"

# 兜底下载: CFF OTF (fpdf2 2.7.2+ 对 CFF OTF 编码已修复)
_OTF_URL = "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"

C1 = (25, 55, 109); C2 = (0, 122, 204); CG = (0, 180, 100)
CR = (220, 60, 60); CY = (255, 180, 0); CGR = (100, 100, 100)
CLB = (240, 242, 248); CW = (255, 255, 255); CB = (30, 30, 30)


def _download_font(url: str, dest: Path) -> bool:
    """下载字体文件"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [FONT] 下载字体 -> {dest.name} ...")
    import urllib.request
    try:
        urllib.request.urlretrieve(url, dest)
        sz = dest.stat().st_size
        print(f"  [FONT] 完成 ({sz/1024/1024:.1f}MB)")
        return sz > 100_000
    except Exception as e:
        print(f"  [FONT] 下载失败: {e}")
        return False


def _find_font() -> str | None:
    """查找可用中文字体，返回字体路径"""
    # 1. 扫描系统字体
    for fp in _SYS_FONTS:
        p = Path(fp)
        if p.exists() and p.stat().st_size > 50_000:
            print(f"  [FONT] 找到系统字体: {p.name} ({p.stat().st_size/1024:.0f}KB)")
            return str(p)

    # 2. 尝试下载 OTF
    if _download_font(_OTF_URL, _LOCAL_OTF):
        return str(_LOCAL_OTF)

    return None


def _load_font(pdf: FPDF, font_path: str) -> bool:
    """尝试用 fpdf2 加载字体，返回是否成功"""
    try:
        pdf.add_font("CN", "", font_path, uni=True)
        pdf.add_font("CN", "B", font_path, uni=True)
        ext = Path(font_path).suffix.lower()
        sz = Path(font_path).stat().st_size / 1024
        print(f"  [FONT] ✅ 加载成功: {Path(font_path).name} ({sz:.0f}KB)")
        return True
    except Exception as e:
        print(f"  [FONT] ❌ 加载失败 ({Path(font_path).name}): {e}")
        return False


class StockReport(FPDF):
    """中文股票分析 PDF 报告"""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=25)
        font_path = _find_font()
        if font_path and _load_font(self, font_path):
            self._font = "CN"
        else:
            print("  [FONT] ⚠️ 无中文字体可用，使用英文")
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
        self.add_page()
        if self._font != "Helvetica":
            self.ln(50)
        self.set_font(*self._ft("B", 28)); self.set_text_color(*C1)
        self.cell(0, 15, title, align="C", new_x="LMARGIN", new_y="NEXT")
        if subtitle:
            self.set_font(*self._ft("", 14)); self.set_text_color(*C2)
            self.cell(0, 10, subtitle, align="C", new_x="LMARGIN", new_y="NEXT")
        if self._font != "Helvetica":
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


def validate_content(market_summary, sector_analysis, stock_analysis, market_news, sentiments):
    """生成前校验数据完整性"""
    checks = {"市场总览": bool(market_summary and market_summary.get("indices")),
              "板块分析": bool(sector_analysis and len(sector_analysis) > 0),
              "个股评分": bool(stock_analysis and len(stock_analysis) > 0),
              "市场舆情": bool(market_news and len(market_news) > 0),
              "个股舆情": bool(sentiments and len(sentiments) > 0)}
    missing = [k for k, v in checks.items() if not v]
    print(f"  [DATA] 有数据: {len([v for v in checks.values() if v])}/5 | 缺失: {', '.join(missing) if missing else '无'}")
    return checks


def validate_report(path_str):
    """校验 PDF 文件完整性"""
    path = Path(path_str)
    if not path.exists():
        return {"valid": False, "issues": ["文件不存在"], "size_kb": 0}
    sz = path.stat().st_size / 1024
    issues = []
    if sz < 30: issues.append(f"文件偏小({sz:.0f}KB) — 部分内容可能缺失")
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

    print("  [CHECK] Pre-validating content integrity...")
    validate_content(market_summary, sector_analysis, stock_analysis, market_news, sentiments)

    pdf.cover(title="每日策略分析报告", subtitle="AI Stock Advisor")
    pdf.add_page(); pdf.h1("目录")
    for t in ["1. 市场总览", "2. 板块分析", "3. 个股技术评分", "4. 市场舆情",
              "5. AI 产业链推荐", "6. 机器人产业链推荐", "7. 风险提示"]:
        pdf.set_font(*pdf._ft("", 11)); pdf.set_text_color(*C1)
        pdf.cell(0, 8, "    " + t, new_x="LMARGIN", new_y="NEXT")
    pdf.add_page(); pdf.h1("1. 市场总览")
    if market_summary:
        idx = market_summary.get("indices", [])
        if idx:
            pdf.table(["指数", "最新价", "涨跌幅", "评分"],
                      [[i.get("name",""), str(i.get("price","")), f'{i.get("change_pct",0):+.2f}%', f'{i.get("score",50):.0f}/100'] for i in idx],
                      [50, 50, 50, 40])
        v = market_summary.get("outlook", "")
        if v: pdf.h2("市场观点"); pdf.p(v)
    pdf.h1("2. 板块分析")
    if sector_analysis:
        rows = [[s['name'], f'{s.get("score",0):.0f}', f'{s.get("spread",0):+.1f}%', s.get("direction","-"), s.get("view","")[:25]] for s in sector_analysis]
        pdf.table(["板块", "评分", "多空差", "方向", "观点"], rows, [35, 25, 30, 30, 70])
    pdf.add_page(); pdf.h1("3. 个股技术评分")
    if stock_analysis:
        rows = [[stk.get('name',''), stk.get("code",""),
                 f'{stk.get("price",0):.2f}', f'{stk.get("score",0):.0f}/100',
                 stk.get("action","-"), f'{stk.get("rsi",0):.1f}'] for stk in stock_analysis]
        pdf.table(["名称", "代码", "现价", "评分", "建议", "RSI"], rows, [35, 28, 28, 28, 30, 28])
        pdf.h2("买卖参考")
        for stk in stock_analysis[:8]:
            sc = stk.get("score",0)
            txt = f"{stk.get('name','')}({stk.get('code','')}): 评分{sc:.0f}/100 | 参考介入{stk.get('entry_ref','-')} | {stk.get('action','观望')}"
            pdf.p_color(txt, CG if sc >= 65 else CB)
    pdf.h1("4. 市场舆情")
    has_news = market_news and len(market_news) > 0
    has_sent = sentiments and len(sentiments) > 0
    if has_news:
        pdf.h2("今日要闻")
        for n in market_news: pdf.p("* " + n.get('title',''))
    if has_sent:
        pdf.h2("个股舆情")
        for code, sent in list(sentiments.items())[:6]:
            pdf.p(f"* {sent.get('name',code)}({code}): 研报{len(sent.get('reports',[]))}篇 | 新闻{len(sent.get('news',[]))}条")
    if not has_news and not has_sent: pdf.p("（暂无舆情数据）")
    pdf.add_page(); pdf.h1("5. AI 产业链布局建议")
    ai = [s for s in (stock_analysis or []) if s.get("sector_group") == "AI"]
    if ai:
        pdf.table(["优先级", "标的", "评分", "参考介入", "逻辑"],
                  [[s.get("priority",""), f"{s.get('name','')}({s.get('code','')})", f'{s.get("score",0):.0f}/100', s.get("entry_ref","-"), s.get("reason","")[:25]] for s in ai],
                  [18, 42, 25, 38, 67])
    pdf.h1("6. 机器人产业链布局建议")
    robot = [s for s in (stock_analysis or []) if s.get("sector_group") == "Robot"]
    if robot:
        pdf.table(["优先级", "标的", "评分", "参考介入", "逻辑"],
                  [[s.get("priority",""), f"{s.get('name','')}({s.get('code','')})", f'{s.get("score",0):.0f}/100', s.get("entry_ref","-"), s.get("reason","")[:25]] for s in robot],
                  [18, 42, 25, 38, 67])
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

    pdf.output(str(filename))
    v = validate_report(str(filename))
    status = "OK" if v["valid"] else "WARN"
    print(f"  [{status}] 报告校验: {v['size_kb']}KB")
    print(f"  [FILE] {filename.name}")
    return str(filename)
