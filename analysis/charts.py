"""个股图表生成 —— matplotlib 图表，用于嵌入 PDF 报告

图表类型:
  1. generate_price_chart()     — 价格 + 均线 + 成交量 + 回撤（4面板）
  2. generate_technical_chart() — MACD + RSI 技术指标组合图
  3. generate_drawdown_chart()  — 最大回撤曲线图
  4. generate_news_timeline()   — 新闻时间线与股价叠加
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 非交互后端，服务器安全

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ── 中文字体配置 ──
_LOCAL_FONT = Path(__file__).resolve().parent.parent / "fonts" / "NotoSansCJKsc-Regular.otf"
_FONT_URL = "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
# 系统字体路径（安装 fonts-noto-cjk 后可用）
_SYS_FONTS = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
]

_CHART_DIR = Path(__file__).parent.parent / "reports" / "charts"


def _setup_chinese_font():
    """全局设置 matplotlib 中文字体"""
    # 1. 先找系统字体
    for fp in _SYS_FONTS:
        if Path(fp).exists() and Path(fp).stat().st_size > 100_000:
            try:
                import matplotlib.font_manager as fm
                fm.fontManager.addfont(fp)
                plt.rcParams["font.family"] = "sans-serif"
                plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK", "DejaVu Sans"]
                plt.rcParams["axes.unicode_minus"] = False
                print(f"  [FONT] 使用系统字体: {fp}")
                return True
            except Exception:
                continue

    # 2. 下载字体
    if not _LOCAL_FONT.exists() or _LOCAL_FONT.stat().st_size < 1_000_000:
        _LOCAL_FONT.parent.mkdir(parents=True, exist_ok=True)
        print("  [FONT] 下载图表中文字体...")
        try:
            import urllib.request
            urllib.request.urlretrieve(_FONT_URL, _LOCAL_FONT)
            sz = _LOCAL_FONT.stat().st_size
            print(f"  [FONT] 图表字体下载完成 ({sz/1024/1024:.1f}MB)")
        except Exception as e:
            print(f"  [FONT] 图表字体下载失败: {e}")

    if _LOCAL_FONT.exists() and _LOCAL_FONT.stat().st_size > 1_000_000:
        try:
            import matplotlib.font_manager as fm
            fm.fontManager.addfont(str(_LOCAL_FONT))
            fp = fm.FontProperties(fname=str(_LOCAL_FONT))
            font_name = fp.get_name()
            plt.rcParams["font.family"] = "sans-serif"
            plt.rcParams["font.sans-serif"] = [font_name, "Noto Sans CJK SC", "Noto Sans CJK", "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            print(f"  [FONT] 已设置全局中文字体: {font_name} ({_LOCAL_FONT.name})")
            return True
        except Exception as e:
            print(f"  [FONT] 注册字体失败: {e}")
    return False


_CN_SET = _setup_chinese_font()


def _use_cn():
    """返回是否使用中文的字体属性（备用方案，针对不支持全局的旧版 matplotlib）"""
    if _CN_SET:
        return {}
    return {}


# ── 颜色主题 ──
_C_GREEN = "#00b45a"
_C_RED = "#dc3c3c"
_C_BLUE = "#007acc"
_C_DARK = "#191929"
_C_GRAY = "#888888"
_C_LIGHT = "#f0f2f5"

# ════════════════════════════════════════════════════════════
#  公共接口
# ════════════════════════════════════════════════════════════


def generate_all_charts(
    df: pd.DataFrame,
    symbol: str,
    name: str,
    news: list[dict] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    """生成个股全套图表

    Args:
        df: K 线 DataFrame
        symbol: 股票代码
        name: 股票名称
        news: 新闻列表（可选，用于新闻时间线图）
        output_dir: 输出目录（默认 reports/charts/）

    Returns:
        {chart_type: file_path} 字典
    """
    out_dir = Path(output_dir) if output_dir else _CHART_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {}

    # 1. 价格走势综合图
    p1 = out_dir / f"{symbol}_price.png"
    generate_price_chart(df, str(p1))
    paths["price"] = str(p1)

    # 2. 技术指标图
    p2 = out_dir / f"{symbol}_technical.png"
    generate_technical_chart(df, str(p2))
    paths["technical"] = str(p2)

    # 3. 最大回撤图
    p3 = out_dir / f"{symbol}_drawdown.png"
    generate_drawdown_chart(df, str(p3))
    paths["drawdown"] = str(p3)

    # 4. 新闻时间线（如果有新闻数据）
    if news:
        p4 = out_dir / f"{symbol}_news.png"
        generate_news_timeline(news, df, str(p4))
        paths["news"] = str(p4)

    return paths


# ════════════════════════════════════════════════════════════
#  各图表生成函数
# ════════════════════════════════════════════════════════════


def generate_price_chart(df: pd.DataFrame, save_path: str):
    """价格走势综合图（4面板）

    ┌──────────────────────────────────┐
    │ ① 价格 + MA20/MA60/MA120/MA250  │
    │ ② 成交量柱状图                   │
    │ ③ 最大回撤曲线                   │
    │ ④ RSI 指标                      │
    └──────────────────────────────────┘
    """
    close = df["收盘"].values.astype(float)
    dates = pd.to_datetime(df["日期"].values)

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True,
                              gridspec_kw={"height_ratios": [3, 1, 1, 1]})
    fig.patch.set_facecolor("white")

    # ── ① 主图: 价格 + 均线 ──
    ax1 = axes[0]
    ax1.plot(dates, close, color=_C_DARK, linewidth=1.5, label="收盘价", zorder=3)

    # 均线
    colors = {"MA20": "#e67e22", "MA60": "#2980b9", "MA120": "#8e44ad", "MA250": "#c0392b"}
    for period, color in colors.items():
        n = int(period.replace("MA", ""))
        if len(close) >= n:
            ma = pd.Series(close).rolling(n).mean().values
            ax1.plot(dates, ma, color=color, linewidth=0.8, alpha=0.7, label=period)

    # 标注最大回撤区间
    peak = np.maximum.accumulate(close)
    drawdown = (close - peak) / peak * 100
    max_dd_idx = np.argmin(drawdown)
    ax1.axvspan(dates[max_dd_idx - 30] if max_dd_idx >= 30 else dates[0],
                dates[max_dd_idx], alpha=0.08, color=_C_RED)
    ax1.annotate(f"最大回撤\n{drawdown[max_dd_idx]:.1f}%",
                 xy=(dates[max_dd_idx], close[max_dd_idx]),
                 xytext=(dates[max_dd_idx], close[max_dd_idx] * 0.85),
                 fontsize=9, color=_C_RED,
                 arrowprops=dict(arrowstyle="->", color=_C_RED, alpha=0.6),
                 **_use_cn())

    ax1.set_ylabel("价格 (元)", fontsize=10, **_use_cn())
    ax1.legend(loc="upper left", fontsize=8, framealpha=0.8)
    ax1.grid(True, alpha=0.2)
    ax1.set_title(f"价格走势", fontsize=13, fontweight="bold", **_use_cn())

    # ── ② 成交量 ──
    ax2 = axes[1]
    if "成交量" in df.columns:
        volume = df["成交量"].values.astype(float)
        colors_bar = [_C_GREEN if close[i] >= close[i - 1] else _C_RED
                      for i in range(1, len(close))]
        colors_bar = [_C_GRAY] + colors_bar
        ax2.bar(dates, volume, color=colors_bar, alpha=0.6, width=1)
        ax2.set_ylabel("成交量", fontsize=10, **_use_cn())
        ax2.grid(True, alpha=0.2)
    else:
        ax2.set_visible(False)

    # ── ③ 最大回撤曲线 ──
    ax3 = axes[2]
    peaking = np.maximum.accumulate(close)
    dd = (close - peaking) / peaking * 100
    ax3.fill_between(dates, dd, 0, color=_C_RED, alpha=0.3)
    ax3.plot(dates, dd, color=_C_RED, linewidth=1)
    ax3.axhline(0, color=_C_DARK, linewidth=0.5)
    ax3.set_ylabel("回撤 %", fontsize=10, **_use_cn())
    ax3.grid(True, alpha=0.2)

    # ── ④ RSI ──
    ax4 = axes[3]
    rsi = _compute_rsi(close, 14)
    if rsi is not None:
        ax4.plot(dates[-len(rsi):], rsi, color=_C_BLUE, linewidth=1.2)
        ax4.axhline(80, color=_C_RED, linestyle="--", alpha=0.5, linewidth=0.8)
        ax4.axhline(20, color=_C_GREEN, linestyle="--", alpha=0.5, linewidth=0.8)
        ax4.fill_between(dates[-len(rsi):], 80, 100, alpha=0.05, color=_C_RED)
        ax4.fill_between(dates[-len(rsi):], 0, 20, alpha=0.05, color=_C_GREEN)
        ax4.set_ylabel("RSI(14)", fontsize=10, **_use_cn())
        ax4.set_ylim(0, 100)
    ax4.grid(True, alpha=0.2)

    # X 轴日期格式
    ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax4.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generate_technical_chart(df: pd.DataFrame, save_path: str):
    """技术指标组合图（MACD + 布林带 + 成交量）

    子图:
    ┌──────────────────────────────────┐
    │ ① 价格 + 布林带                  │
    │ ② MACD (DIF/DEA/柱线)            │
    │ ③ KDJ 指标                      │
    └──────────────────────────────────┘
    """
    close = df["收盘"].values.astype(float)
    high = df["最高"].values.astype(float)
    low = df["最低"].values.astype(float)
    dates = pd.to_datetime(df["日期"].values)

    fig, axes = plt.subplots(3, 1, figsize=(14, 9),
                              gridspec_kw={"height_ratios": [2.5, 1.5, 1]})
    fig.patch.set_facecolor("white")

    # ── ① 布林带 ──
    ax1 = axes[0]
    mid = pd.Series(close).rolling(20).mean().values
    std = pd.Series(close).rolling(20).std().values
    upper = mid + 2 * std
    lower = mid - 2 * std

    ax1.plot(dates, close, color=_C_DARK, linewidth=1.5, label="收盘价")
    ax1.plot(dates, mid, color="#e67e22", linewidth=0.8, alpha=0.7, label="中轨(MA20)")
    ax1.plot(dates, upper, color=_C_GRAY, linewidth=0.6, alpha=0.5, label="上轨")
    ax1.plot(dates, lower, color=_C_GRAY, linewidth=0.6, alpha=0.5, label="下轨")
    ax1.fill_between(dates, lower, upper, alpha=0.06, color=_C_BLUE)
    ax1.set_ylabel("价格", fontsize=10, **_use_cn())
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.2)
    ax1.set_title("布林带 + MACD + KDJ 技术指标", fontsize=13, fontweight="bold", **_use_cn())

    # ── ② MACD ──
    ax2 = axes[1]
    ema12 = pd.Series(close).ewm(span=12).mean().values
    ema26 = pd.Series(close).ewm(span=26).mean().values
    dif = ema12 - ema26
    dea = pd.Series(dif).ewm(span=9).mean().values
    macd_hist = dif - dea

    ax2.plot(dates, dif, color=_C_BLUE, linewidth=1, label="DIF")
    ax2.plot(dates, dea, color="#e67e22", linewidth=1, label="DEA")
    colors_macd = [_C_RED if v >= 0 else _C_GREEN for v in macd_hist]
    ax2.bar(dates, macd_hist, color=colors_macd, alpha=0.4, width=1, label="柱线")
    ax2.axhline(0, color=_C_DARK, linewidth=0.5)
    ax2.set_ylabel("MACD", fontsize=10, **_use_cn())
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, alpha=0.2)

    # ── ③ KDJ ──
    ax3 = axes[2]
    low9 = pd.Series(low).rolling(9).min().values
    high9 = pd.Series(high).rolling(9).max().values
    rsv = (close - low9) / (high9 - low9 + 1e-10) * 100
    k_val = pd.Series(rsv).ewm(com=2).mean().values
    d_val = pd.Series(k_val).ewm(com=2).mean().values
    j_val = 3 * k_val - 2 * d_val

    valid = ~np.isnan(k_val) & ~np.isnan(d_val) & ~np.isnan(j_val)
    if np.any(valid):
        ax3.plot(dates[valid], k_val[valid], color=_C_BLUE, linewidth=0.8, label="K")
        ax3.plot(dates[valid], d_val[valid], color="#e67e22", linewidth=0.8, label="D")
        ax3.plot(dates[valid], j_val[valid], color=_C_RED, linewidth=0.8, alpha=0.6, label="J")
        ax3.axhline(80, color=_C_RED, linestyle="--", alpha=0.3)
        ax3.axhline(20, color=_C_GREEN, linestyle="--", alpha=0.3)
    ax3.set_ylabel("KDJ", fontsize=10, **_use_cn())
    ax3.legend(loc="upper left", fontsize=8)
    ax3.grid(True, alpha=0.2)

    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generate_drawdown_chart(df: pd.DataFrame, save_path: str):
    """最大回撤曲线图

    显示从每个峰值到谷底的回撤路径
    """
    close = df["收盘"].values.astype(float)
    dates = pd.to_datetime(df["日期"].values)

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor("white")

    peak = np.maximum.accumulate(close)
    drawdown = (close - peak) / peak * 100

    # 填充回撤区域（分颜色深浅）
    ax.fill_between(dates, drawdown, 0,
                    where=(drawdown < -20), color=_C_RED, alpha=0.4, label="深度回撤 (>20%)")
    ax.fill_between(dates, drawdown, 0,
                    where=(drawdown >= -20) & (drawdown < -10),
                    color=_C_RED, alpha=0.2, label="中度回撤 (10-20%)")
    ax.fill_between(dates, drawdown, 0,
                    where=(drawdown >= -10) & (drawdown < 0),
                    color=_C_RED, alpha=0.08, label="轻度回撤 (<10%)")

    ax.plot(dates, drawdown, color=_C_RED, linewidth=1.2)
    ax.axhline(0, color=_C_DARK, linewidth=0.8)

    # 标注最大回撤点
    min_idx = np.argmin(drawdown)
    ax.scatter(dates[min_idx], drawdown[min_idx], color=_C_RED, s=50, zorder=5)
    ax.annotate(f"最大回撤: {drawdown[min_idx]:.1f}%",
                xy=(dates[min_idx], drawdown[min_idx]),
                xytext=(dates[min_idx], drawdown[min_idx] * 1.3),
                fontsize=11, color=_C_RED, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=_C_RED),
                **_use_cn())

    ax.set_ylabel("回撤 (%)", fontsize=11, **_use_cn())
    ax.set_title("历史回撤分析", fontsize=13, fontweight="bold", **_use_cn())
    ax.legend(loc="lower left", fontsize=9)
    ax.grid(True, alpha=0.2)

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generate_news_timeline(news: list[dict], df: pd.DataFrame, save_path: str):
    """新闻时间线与股价叠加图

    在股价走势上标注新闻事件:
    - 正面新闻: 绿色三角标记
    - 负面新闻: 红色倒三角标记
    - 重大新闻: 大号标记
    """
    close = df["收盘"].values.astype(float)
    dates = pd.to_datetime(df["日期"].values)
    price_range = np.max(close) - np.min(close)

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("white")

    # 股价线
    ax.plot(dates, close, color=_C_DARK, linewidth=2, label="收盘价", zorder=2)
    ax.fill_between(dates, close.min() * 0.98, close, alpha=0.05, color=_C_BLUE)

    # 新闻标注
    news_colors = {"正面": _C_GREEN, "负面": _C_RED, "中性": _C_GRAY}
    markers = {"正面": "^", "负面": "v", "中性": "o"}

    parsed = 0
    for n in news:
        try:
            time_str = str(n.get("time", "")).strip()
            if not time_str or len(time_str) < 10:
                continue
            dt = pd.to_datetime(time_str[:10])
            title = str(n.get("title", ""))
            sentiment = "正面"  # 默认
            for kw in ["负面", "利空", "跌", "减持", "处罚", "亏损"]:
                if kw in title:
                    sentiment = "负面"
                    break
            for kw in ["正面", "利好", "涨", "增持", "中标", "突破"]:
                if kw in title:
                    sentiment = "正面"
                    break

            # 找最近的交易日
            idx = np.argmin(np.abs((pd.to_datetime(df["日期"]) - dt).days))
            if idx >= len(close):
                continue
            price_at = close[idx]
            is_major = any(kw in title for kw in ["业绩", "预增", "预减", "重组",
                                                   "监管", "处罚", "退市", "中标"])
            size = 120 if is_major else 60

            ax.scatter(dates[idx], price_at,
                       color=news_colors.get(sentiment, _C_GRAY),
                       marker=markers.get(sentiment, "o"),
                       s=size, zorder=5, edgecolors="white", linewidth=0.5)

            # 显示新闻标题摘要
            short_title = title[:30] + "…" if len(title) > 30 else title
            offset_y = price_range * 0.03
            ax.annotate(short_title,
                        xy=(dates[idx], price_at),
                        xytext=(dates[idx], price_at + offset_y * (
                            1 if sentiment == "正面" else -2)),
                        fontsize=7, color=news_colors.get(sentiment, _C_GRAY),
                        ha="center",
                        arrowprops=dict(arrowstyle="-", color=_C_GRAY, alpha=0.3))
            parsed += 1
            if parsed >= 20:  # 最多显示 20 条新闻
                break
        except Exception:
            continue

    ax.set_ylabel("价格 (元)", fontsize=11, **_use_cn())
    ax.set_title("股价走势 + 新闻事件时间线", fontsize=13, fontweight="bold", **_use_cn())
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.2)

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ════════════════════════════════════════════════════════════
#  内部辅助
# ════════════════════════════════════════════════════════════


def _compute_rsi(close: np.ndarray, period: int = 14) -> np.ndarray | None:
    """RSI 计算"""
    if len(close) < period + 1:
        return None
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return np.full(len(close) - 1, 100)
    rs = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)
    return np.full(len(close) - 1, rsi)
