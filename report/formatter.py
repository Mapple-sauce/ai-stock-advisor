"""报告格式化"""

from __future__ import annotations

from datetime import date


def format_buy_report(results: list[dict]) -> str:
    """格式化买入分析报告"""
    lines = [
        f"# 📈 AI 多Agent买入分析报告",
        f"**日期**: {date.today()}  |  **分析股票数**: {len(results)}",
        "",
        "---",
        "",
        "## 📊 综合决策汇总",
        "",
    ]

    for r in results:
        d = r.get("decision", {})
        score = d.get("final_score", "?")
        action = d.get("action", "?")
        reason = d.get("key_reason", "")
        position = d.get("position_suggestion", "")

        score_icon = "🟢" if score and isinstance(score, (int, float)) and score >= 7 else "🟡" if score and isinstance(score, (int, float)) and score >= 5 else "🔴"
        lines.append(f"### {score_icon} {r['name']} ({r['code']}) — **{action}** (评分: {score})")
        lines.append(f"- 核心理由: {reason}")
        lines.append(f"- 建议仓位: {position}")
        lines.append("")

    lines.append("---\n")

    # 详细报告
    for r in results:
        lines.append(f"\n## {r['name']} ({r['code']}) @ {r['price']}元")
        d = r.get("decision", {})

        lines.append(f"\n### 🎯 首席决策")
        lines.append(f"- **操作**: {d.get('action', '')}  |  **评分**: {d.get('final_score', '')}/10")
        lines.append(f"- **置信度**: {d.get('confidence', '')}")
        lines.append(f"- **核心理由**: {d.get('key_reason', '')}")
        lines.append(f"- **买入区间**: {d.get('entry_lower', '?')} - {d.get('entry_upper', '?')} 元")
        lines.append(f"- **止损位**: {d.get('stop_loss', '?')} 元")
        lines.append(f"- **建议仓位**: {d.get('position_suggestion', '')}")
        lines.append(f"- **持有周期**: {d.get('time_horizon', '')}")

        risks = d.get("risks_to_watch", [])
        if risks:
            lines.append(f"- **风险监控**: {', '.join(risks)}")

        lines.append(f"\n### 🔧 技术分析")
        lines.append(r.get('technical_report', ''))

        lines.append(f"\n### 📊 基本面分析")
        lines.append(r.get('fundamental_report', ''))

        lines.append(f"\n### 📰 舆情分析")
        lines.append(r.get('sentiment_report', ''))

        lines.append(f"\n### ⚠️ 风险评估")
        lines.append(r.get('risk_report', ''))

    lines.append("\n---\n*报告由 AI 多Agent系统自动生成, 仅供参考, 不构成投资建议*")
    return "\n".join(lines)


def format_sell_report(results: list[dict]) -> str:
    """格式化卖出分析报告"""
    lines = [
        f"# 📉 AI 多Agent持仓卖出分析报告",
        f"**日期**: {date.today()}  |  **持仓数**: {len(results)}",
        "",
        "---",
        "",
        "## 📊 综合决策汇总",
        "",
    ]

    for r in results:
        d = r.get("decision", {})
        score = d.get("final_score", "?")
        action = d.get("action", "")
        reason = d.get("sell_reason", "")
        pnl = r.get("pnl_pct", 0)

        pnl_icon = "🟢" if pnl >= 0 else "🔴"
        action_icon = "🟢" if action == "持有" else "🟡" if action == "减仓" else "🔴"
        lines.append(f"### {action_icon} {r['name']} ({r['code']}) — **{action}** (评分: {score})")
        lines.append(f"- {pnl_icon} 持仓盈亏: {pnl:.2f}%")
        lines.append(f"- 核心理由: {reason}")
        lines.append("")

    lines.append("---\n")

    for r in results:
        d = r.get("decision", {})
        lines.append(f"\n## {r['name']} ({r['code']})")
        lines.append(f"成本: {r.get('cost_price', '')} → 现价: {r['price']}  "
                      f"盈亏: {r.get('pnl_pct', 0):.2f}%")

        lines.append(f"\n### 🎯 首席决策")
        lines.append(f"- **操作**: {d.get('action', '')}  |  **评分**: {d.get('final_score', '')}/10")
        lines.append(f"- **核心理由**: {d.get('sell_reason', '')}")
        lines.append(f"- **止损价**: {d.get('stop_loss_updated', '?')} 元")
        lines.append(f"- **目标价**: {d.get('target_price', '?')} 元")
        if d.get("take_profit_now"):
            lines.append(f"- **⚠️ 建议止盈!**")

        risks = d.get("risks_to_watch", [])
        if risks:
            lines.append(f"- **风险信号**: {', '.join(risks)}")

        lines.append(f"\n### 🔧 技术分析")
        lines.append(r.get('technical_report', ''))
        lines.append(f"\n### 📰 舆情分析")
        lines.append(r.get('sentiment_report', ''))
        lines.append(f"\n### ⚠️ 风险评估")
        lines.append(r.get('risk_report', ''))

    lines.append("\n---\n*报告由 AI 多Agent系统自动生成, 仅供参考, 不构成投资建议*")
    return "\n".join(lines)


def format_scan_report(candidates: list[dict], ai_selection: str = "") -> str:
    """格式化扫描报告"""
    lines = [
        f"# 🔍 AI 选股扫描报告",
        f"**日期**: {date.today()}",
        "---",
        "",
    ]
    if ai_selection:
        lines.append(ai_selection)
        lines.append("")
    lines.append("### 候选股票池")
    for s in candidates[:15]:
        lines.append(f"- **{s.get('name', '')}** ({s.get('code', '')}) — "
                      f"涨幅: {s.get('change_pct', 0)}%  |  "
                      f"成交: {_fmt_num(s.get('turnover', 0))}")
    lines.append("")
    lines.append("---")
    lines.append("*报告由 AI 自动生成, 仅供参考, 不构成投资建议*")
    return "\n".join(lines)


def _fmt_num(num: float) -> str:
    if num >= 1e8:
        return f"{num/1e8:.1f}亿"
    if num >= 1e4:
        return f"{num/1e4:.1f}万"
    return str(num)
