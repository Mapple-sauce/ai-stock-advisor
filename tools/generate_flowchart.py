"""项目流程图生成器

每次项目有重大更新后运行: python tools/generate_flowchart.py
自动生成 docs/architecture_flowchart.png 图表

依赖: matplotlib, numpy (已包含在 requirements.txt)
"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保项目根目录在路径中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ── 颜色方案 ──
C_BG = "#1a1a2e"           # 深色背景
C_CHIEF = "#e94560"         # Chief Agent 红色
C_AGENT = "#0f3460"         # Agent 深蓝
C_DATA = "#16213e"          # 数据层 深蓝黑
C_OUTPUT = "#533483"        # 输出层 紫色
C_CMD = "#e2a76f"           # 命令 金色
C_WHITE = "#ffffff"
C_TEXT = "#e8e8e8"
C_GREEN = "#2ecc71"
C_YELLOW = "#f1c40f"


def create_flowchart(output_path: str = "docs/architecture_flowchart.png"):
    """生成项目架构流程图"""
    fig, ax = plt.subplots(1, 1, figsize=(18, 22))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 22)
    ax.set_facecolor(C_BG)
    fig.patch.set_facecolor(C_BG)
    ax.axis("off")

    # ══════════════════════════════════════════════════════════════
    #  绘制节点函数
    # ══════════════════════════════════════════════════════════════

    def box(x, y, w, h, text, color=C_AGENT, text_color=C_WHITE, fontsize=9, alpha=0.9):
        """绘制圆角矩形框"""
        bb = FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle="round,pad=0.15",
            facecolor=color, edgecolor="white", linewidth=1.2,
            alpha=alpha,
        )
        ax.add_patch(bb)
        ax.text(x, y, text, ha="center", va="center",
                fontsize=fontsize, color=text_color, fontweight="bold",
                family="sans-serif")

    def arrow(x1, y1, x2, y2, color=C_TEXT, lw=1.5, style="-"):
        """绘制箭头"""
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=color,
                                    lw=lw, linestyle=style, alpha=0.7))

    def title(text, y, size=20):
        """绘制标题"""
        ax.text(9, y, text, ha="center", va="center",
                fontsize=size, color=C_WHITE, fontweight="bold",
                family="sans-serif")

    def label(text, x, y, size=10, color=C_TEXT):
        """绘制标签"""
        ax.text(x, y, text, ha="center", va="center",
                fontsize=size, color=color, family="sans-serif")

    # ══════════════════════════════════════════════════════════════
    #  绘制流程图
    # ══════════════════════════════════════════════════════════════

    # ── 标题 ──
    title("AI Stock Advisor", 21.2, 22)
    label("Multi-Agent Stock Analysis System", 9, 20.5, 12, C_YELLOW)

    # ── 命令行入口 ──
    box(9, 19.2, 14, 0.8, "⚡ 命令入口  python main.py [buy|sell|scan|low|mom|hunt|report|backtest]",
        C_CMD, fontsize=10)

    # ── 数据层 ──
    box(3, 17.2, 4.5, 1.0, "📦 数据层\ndata/\n行情(K线/实时) | 基本面 | 新闻 | 技术指标",
        C_DATA, fontsize=7.5)
    box(9, 17.2, 4.5, 1.0, "📦 数据源\na. 新浪财经(实时行情)\nb. Baostock(K线/分红)\nc. akshare(新闻/基本面)",
        C_DATA, fontsize=7.5)
    box(15, 17.2, 4.5, 1.0, "📦 板块分类\nscanner/sectors.py\n7大板块权重矩阵\n方向控制(_direction)",
        C_DATA, fontsize=7.5)

    # 数据流向
    arrow(9, 18.7, 9, 18.0, C_TEXT)
    arrow(3, 16.7, 3, 15.3, C_TEXT)
    arrow(9, 16.7, 9, 15.3, C_TEXT)
    arrow(15, 16.7, 15, 15.3, C_TEXT)

    # ── 量化筛选层 ──
    box(9, 14.5, 12, 1.2, "🔬 量化筛选引擎  scanner/screener.py\n全市场5000+ → 过滤ST/北交所 → TOP80 → 10因子评分\n低分=好(反转) / 高分=好(正向)  板块感知权重",
        C_AGENT, fontsize=7.5)

    arrow(9, 13.9, 9, 12.3, C_TEXT)

    # ── Agent 层 ──
    # 上方: 5个专业Agent
    agents = [
        (2.5, 10.5, "Technical\nAnalyst\n📊 技术分析\n均线/MACD/RSI"),
        (5.9, 10.5, "Fundamental\nAnalyst\n📋 基本面\n估值/ROE/成长"),
        (9, 10.5, "Sentiment\nAnalyst\n📰 舆情分析\n新闻/情绪/事件"),
        (12.1, 10.5, "Risk\nAnalyst\n⚠️ 风险评估\n止损/仓位/风控"),
        (15.5, 10.5, "Hunter\nAgent\n💎 低位挖掘\n四层分析框架"),
    ]
    for x, y, text in agents:
        box(x, y, 2.6, 1.6, text, C_AGENT, fontsize=6.5)

    # 中间: Chief Agent
    box(9, 7.5, 4.5, 1.8, "🧠  Chief Agent (首席投资官)\nchief/__init__.py\n综合4专家意见 → 结构化JSON决策\ntemperature=0.05 (确定性最高)",
        C_CHIEF, fontsize=7.5)

    # Agent → Chief 连线
    for x in [2.5, 5.9, 9, 12.1, 15.5]:
        arrow(x, 9.7, x, 8.4, C_TEXT)

    # Chief → 输出
    arrow(9, 6.6, 9, 5.2, C_TEXT)

    # ── 输出层 ──
    outputs = [
        (2.5, 3.8, "📈 买卖分析\nbuy/sell\nAgent报告+JSON决策\n推送到企业微信"),
        (6.5, 3.8, "📊 市场扫描\nscan/low/mom\n涨幅榜/低位/追高\nAI精选TOP 5"),
        (11.5, 3.8, "💎 低位挖掘\nhunt\n全市场→量化→AI深度\n精选排名+报告"),
        (15.5, 3.8, "📄 PDF报告\nreport\n每日收盘分析\n含产业链布局建议"),
    ]
    for x, y, text in outputs:
        box(x, y, 3.2, 1.6, text, C_OUTPUT, fontsize=6.5)

    # ── 底层: 回测系统 ──
    box(6, 1.2, 5, 1.2, "🧪 回测验证 backtest/\n历史回测 | 权重优化 | 分红数据",
        "#2d3436", fontsize=7.5)
    box(12, 1.2, 5, 1.2, "⚙️ 自动化 .github/workflows/\n每天收盘后自动运行\n手动触发可选模式",
        "#2d3436", fontsize=7.5)

    arrow(9, 4.6, 6, 1.8, C_TEXT, 1.0, "--")
    arrow(9, 4.6, 12, 1.8, C_TEXT, 1.0, "--")

    # ── 左侧: 板块策略说明 ──
    sector_info = (
        "┌───────── 板块感知策略 ─────────┐\n"
        "│ 科技(+1)  重趋势  | 工业(-1)  回调买入│\n"
        "│ 医药(+1)  趋势为主 | 新能源(-1) 低分好 │\n"
        "│ 消费(+1)  MA20关键 | 金融(+1) RSI有效 │\n"
        "│ 周期(+1)  趋势为王                    │\n"
        "└──────────────────────────────────────┘"
    )
    ax.text(0.5, 3.5, sector_info, ha="left", va="center",
            fontsize=6.5, color=C_YELLOW, fontfamily="monospace",
            transform=ax.transData)

    # ── 右侧: 模型效果 ──
    result_info = (
        "┌──────── 回测效果 ────────┐\n"
        "│ 科技: +16.5% ✅          │\n"
        "│ 医药: +10.7% ✅          │\n"
        "│ 工业: +6.2%  ✅          │\n"
        "│ 金融: +1.3%  🟡          │\n"
        "│ 平均多空差: +5.1%       │\n"
        "└──────────────────────────┘"
    )
    ax.text(17.5, 3.5, result_info, ha="right", va="center",
            fontsize=6.5, color=C_GREEN, fontfamily="monospace",
            transform=ax.transData)

    # ── 保存 ──
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight",
                facecolor=C_BG, edgecolor="none")
    plt.close()
    print(f"  ✅ 流程图已生成: {output_path} ({Path(output_path).stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    create_flowchart()
