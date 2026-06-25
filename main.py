"""
AI Stock Advisor — 多Agent协作股票分析系统

架构:
  Chief Agent (总决策) ─┬── Technical Analyst (技术分析)
                        ├── Fundamental Analyst (基本面)
                        ├── Sentiment Analyst (舆情分析)
                        └── Risk Analyst (风险评估)

使用:
  python main.py buy             # 买入分析
  python main.py sell            # 卖出分析
  python main.py scan            # 市场扫描
  python main.py all             # 全部执行
  python main.py add 000001 10   # 添加持仓
  python main.py list            # 查看持仓
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from chief.orchestrator import Orchestrator
from portfolio.manager import PortfolioManager
from report.formatter import format_buy_report, format_sell_report, format_scan_report
from report.notifier import send_report
from scanner.screener import screen_market


def run_buy_analysis():
    """买入分析: 多Agent协作"""
    print("\n" + "█" * 60)
    print("   📈 AI 多 Agent 买入分析")
    print("█" * 60)

    symbols = settings.stock_list or settings.watch_list
    if not symbols:
        print("⚠️ 未配置 STOCK_LIST 或 WATCH_LIST")
        return

    orchestrator = Orchestrator()
    results = []
    for i, symbol in enumerate(symbols, 1):
        print(f"\n{'─'*50}")
        print(f"  [{i}/{len(symbols)}]")
        result = orchestrator.analyze_buy(symbol)
        if result:
            results.append(result)

    if results:
        report = format_buy_report(results)
        print("\n✅ 买入分析完成, 推送报告中...")
        send_report(report, "📈 AI 买入分析报告")
    else:
        print("⚠️ 没有成功分析任何股票")


def run_sell_analysis():
    """卖出分析: 多Agent协作"""
    print("\n" + "█" * 60)
    print("   📉 AI 多 Agent 持仓卖出分析")
    print("█" * 60)

    pm = PortfolioManager()
    holdings = pm.get_all()
    if not holdings:
        print("📭 当前没有持仓")
        print("  提示: python main.py add <代码> <成本价> [名称]")
        return

    orchestrator = Orchestrator()
    results = []
    for i, h in enumerate(holdings, 1):
        print(f"\n{'─'*50}")
        print(f"  [{i}/{len(holdings)}]")
        result = orchestrator.analyze_sell(h)
        if result:
            results.append(result)

    if results:
        report = format_sell_report(results)
        print("\n✅ 卖出分析完成, 推送报告中...")
        send_report(report, "📉 AI 持仓卖出分析报告")
    else:
        print("⚠️ 没有成功分析任何持仓")


def run_scan():
    """市场扫描"""
    print("\n" + "█" * 60)
    print("   🔍 AI 多 Agent 市场扫描")
    print("█" * 60)

    candidates = screen_market()
    if not candidates:
        print("⚠️ 扫描结果为空")
        return

    print(f"\n📊 初步筛选出 {len(candidates)} 只候选股:\n")
    for s in candidates[:10]:
        print(f"  {s['code']} {s['name']} 涨幅:{s.get('change_pct', 0)}%")

    # AI 精选
    orchestrator = Orchestrator()
    selection = orchestrator.scan_market(candidates)

    report = format_scan_report(candidates, selection)
    print(f"\n✅ 市场扫描完成")
    send_report(report, "🔍 AI 市场扫描报告")


def add_holding():
    """添加持仓"""
    if len(sys.argv) < 4:
        print("用法: python main.py add <代码> <成本价> [名称] [数量]")
        return
    symbol = sys.argv[2]
    cost = float(sys.argv[3])
    name = sys.argv[4] if len(sys.argv) > 4 else symbol
    quantity = int(sys.argv[5]) if len(sys.argv) > 5 else 100

    pm = PortfolioManager()
    h = pm.add(symbol, name, cost, quantity)
    print(f"✅ 已添加持仓: {h['name']} ({h['symbol']}) 成本 {h['cost_price']} 数量 {h['quantity']}")


def list_holdings():
    """查看持仓"""
    pm = PortfolioManager()
    s = pm.get_summary()
    if not s["holdings"]:
        print("📭 暂无持仓")
        return
    pnl_icon = "🟢" if s["total_pnl_pct"] >= 0 else "🔴"
    print(f"\n📊 持仓总览: {s['total']} 只  {pnl_icon} {s['total_pnl_pct']}%\n")
    for h in s["holdings"]:
        pnl = h.get("pnl_pct", 0)
        icon = "🟢" if pnl >= 0 else "🔴"
        print(f"  {icon} {h['name']} ({h['symbol']})  "
              f"成本:{h['cost_price']} 现价:{h.get('current_price', 'N/A')}  "
              f"盈亏:{pnl}% 持仓:{h.get('hold_days', '?')}天")


def main():
    if not settings.is_ready:
        sys.exit(1)

    mode = settings.run_mode
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    modes = {
        "buy": run_buy_analysis,
        "买入": run_buy_analysis,
        "sell": run_sell_analysis,
        "卖出": run_sell_analysis,
        "scan": run_scan,
        "扫描": run_scan,
        "add": add_holding,
        "添加": add_holding,
        "list": list_holdings,
        "持仓": list_holdings,
        "all": lambda: [run_scan(), run_buy_analysis(), run_sell_analysis()],
    }

    fn = modes.get(mode)
    if fn:
        fn()
    else:
        print(f"未知模式: {mode}")
        print("用法: python main.py [buy|sell|scan|add|list|all]")


if __name__ == "__main__":
    main()
