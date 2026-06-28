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
    """市场扫描 (从命令行读取模式)"""
    scan_mode = "top_gainers"
    if len(sys.argv) > 2:
        scan_mode = sys.argv[2]
    _do_scan(scan_mode)


def run_scan_with_mode(mode: str):
    """市场扫描 (指定模式)"""
    _do_scan(mode)


def _do_scan(scan_mode: str):
    """执行扫描 (内部函数)"""
    mode_labels = {
        "top_gainers": "📈 今日涨幅榜",
        "low_position": "💎 低位潜力股",
        "momentum": "🔥 追高跟强",
    }
    label = mode_labels.get(scan_mode, scan_mode)

    print("\n" + "█" * 60)
    print(f"   🔍 AI 多 Agent 市场扫描 [{label}]")
    print("█" * 60)

    candidates = screen_market(mode=scan_mode, max_candidates=20)
    if not candidates:
        print("⚠️ 扫描结果为空")
        return

    # AI 精选
    orchestrator = Orchestrator()
    selection = orchestrator.scan_market(candidates, mode=scan_mode)

    report = format_scan_report(candidates, selection)
    print(f"\n✅ 市场扫描完成 [{label}]")
    send_report(report, f"🔍 AI 市场扫描 - {label}")


def run_report():
    """生成每日PDF报告"""
    from report.daily_report import run_daily_report

    output_dir = "reports"
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    print(f"\n{'█'*60}")
    print(f"   📊 生成每日 PDF 分析报告")
    print(f"{'█'*60}\n")

    pdf_path = run_daily_report(output_dir=output_dir)

    from report.notifier import send_wechat_markdown
    import datetime as dt
    send_wechat_markdown(
        f"## 📊 每日收盘分析报告已生成\n\n"
        f"**日期**: {dt.date.today()}\n\n"
        f"📄 文件: `{pdf_path}`\n\n"
        f"包含: 市场总览 / 板块分析 / 个股评分 / AI链 / 机器人链\n\n"
        f"> 请查看仓库 `reports/` 目录获取完整 PDF"
    )

    print(f"\n✅ PDF 报告已生成: {pdf_path}")
    return pdf_path


def run_hunter():
    """低位挖掘: Hunter Agent 深度分析"""
    scan_mode = "low_position"
    from scanner.screener import screen_market

    print("\n" + "█" * 60)
    print("   💎 AI 低位挖掘 Hunter Agent")
    print("   [全市场扫雷 → 量化初筛 → AI深度分析 → 精选排名]")
    print("█" * 60)

    candidates = screen_market(mode=scan_mode, max_candidates=20)
    if not candidates:
        print("⚠️ 扫描结果为空")
        return

    orchestrator = Orchestrator()
    report = orchestrator.hunter_deep_dive(candidates)

    print(f"\n✅ 低位挖掘完成")
    send_report(report, "💎 AI 低位挖掘深度报告")


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



def run_optimize():
    """动态权重优化: P1 方案 - 自动寻找最优因子权重"""
    mode = "low_position"
    if len(sys.argv) > 2:
        mode = sys.argv[2]

    print("\n" + "█" * 60)
    print("   ⚡ P1 优化方案: 动态权重矩阵")
    print("   扫描最近6个月数据, 搜索20000组权重配置")
    print("█" * 60 + "\n")

    from backtest.optimizer import find_optimal_weights
    from scanner.screener import refresh_weights_file

    print(f"  模式: {mode}")
    print(f"  样本: 15只龙头股, 最近6个月数据")
    print(f"  搜索: 20000组随机权重配置\n")

    result = find_optimal_weights(
        symbols=None,
        mode=mode,
        lookback_months=6,
        hold_days=20,
        iterations=20000,
    )

    if "error" in result:
        print(f"\n  ❌ 优化失败: {result['error']}")
        return

    print(f"\n  ✅ 优化完成!")
    print(f"  准确率: {result['accuracy_pct']}%")
    print(f"  多空差: {result['spread']:+.1f}%")
    print(f"  测试次数: {result['total_tests']}次")
    print(f"  买入/回避: {result['buy_count']}/{result['avoid_count']}次")
    print(f"\n  最优权重配置:")

    weights = result["weights"]
    for f, (w, name, _) in sorted(weights.items(), key=lambda x: x[1][0], reverse=True):
        print(f"    {f:20s} = {w:.4f}  ({name})")

    saved = refresh_weights_file(mode, weights)
    if saved:
        print(f"\n  ✅ 权重已保存到 weights/{mode}.json")
    else:
        print(f"\n  ⚠️ 权重保存失败, 使用硬编码权重")

    old_acc = 61.5
    new_acc = result['accuracy_pct']
    diff = new_acc - old_acc
    arrow = "↑" if diff > 0 else "↓" if diff < 0 else "="
    print(f"\n  对比: 旧权重正确率 {old_acc}%  →  新权重正确率 {new_acc}%  ({arrow} {abs(diff):.1f}%)")


def run_backtest_mode():
    """回测验证 (方案一): 单日期回测"""
    from backtest.engine import run_backtest

    symbols = settings.stock_list or settings.watch_list
    if not symbols:
        print("⚠️ 未配置 STOCK_LIST")
        return

    import datetime
    as_of = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    if len(sys.argv) > 2:
        as_of = sys.argv[2]

    print("\n" + "█" * 60)
    print(f"  🧪 方案一: AI 分析回测验证")
    print(f"  📅 回测日期: {as_of}  |  持有天数: 20")
    print(f"  📊 测试 {len(symbols)} 只股票")
    print("█" * 60)

    result = run_backtest(symbols, as_of_date=as_of, hold_days=20)
    summary = result["summary"]
    buy_avg = summary.get("buy_avg_return", 0)
    avoid_avg = summary.get("avoid_avg_return", 0)
    diff = buy_avg - avoid_avg
    print(f"  🟢 推荐买入平均: {buy_avg:+.2f}% vs 回避平均: {avoid_avg:+.2f}% (差: {diff:+.2f}%)")
    print(f"  {'✅ 模型有效' if diff > 0 else '❌ 模型待优化'}")


def run_backtest_multi():
    """多日期综合回测"""
    from backtest.engine import run_multi_backtest

    symbols = settings.stock_list or settings.watch_list
    if not symbols:
        print("⚠️ 未配置 STOCK_LIST")
        return

    import datetime
    dates = []
    today = datetime.date.today()
    for m in range(1, 6):
        d = today.replace(day=1) - datetime.timedelta(days=m * 30)
        dates.append(d.strftime("%Y-%m-%d"))

    print("\n" + "█" * 60)
    print(f"  🧪 方案一: 多日期综合回测")
    print(f"  📅 {len(dates)} 个时间点 x {len(symbols)} 只股票")
    print("█" * 60)

    result = run_multi_backtest(symbols, dates, hold_days=20)
    summary = result["summary"]
    buy_avg = summary.get("buy_avg_return", 0)
    avoid_avg = summary.get("avoid_avg_return", 0)
    diff = buy_avg - avoid_avg
    accuracy = summary.get("accuracy_pct", 0)

    print(f"\n  🏆 模型综合评估:")
    if accuracy > 55 and diff > 2:
        print(f"  🟢 有参考价值 (正确率{accuracy}%, 多空差{diff:+.2f}%)")
    elif accuracy > 50 and diff > 0:
        print(f"  🟡 略有参考价值 (正确率{accuracy}%, 多空差{diff:+.2f}%)")
    else:
        print(f"  🔴 需优化 (正确率{accuracy}%, 多空差{diff:+.2f}%)")


def run_individual_analysis():
    """个股深度分析"""
    if len(sys.argv) < 3:
        print("\n" + "█" * 60)
        print("   📋 个股深度分析")
        print("█" * 60)
        print("\n用法: python main.py analyze <股票代码>")
        print("示例:")
        print("  python main.py analyze 002594    # 比亚迪")
        print("  python main.py analyze 601012    # 隆基绿能")
        print("  python main.py analyze 510880    # 红利ETF")
        print("  python main.py analyze 512480    # 半导体ETF")
        print("  # 逗号分隔, 一次分析多个:")
        print("  python main.py analyze 512480,510880,516360,002594,601012")
        return

    symbols_raw = sys.argv[2]
    symbols = symbols_raw.replace("，", ",").split(",")

    for i, symbol in enumerate(symbols, 1):
        symbol = symbol.strip()
        print(f"\n{'█'*60}")
        print(f"   📋 [{i}/{len(symbols)}] 个股深度分析: {symbol}")
        print(f"{'█'*60}")

        from analysis.analyst import stock_analyst
        result = stock_analyst.analyze(symbol)

        if result.get("status") == "error":
            print(f"\n  ❌ 分析失败: {result.get('error', '未知错误')}")
            continue

        from report.individual_report import generate_individual_report
        pdf_path = generate_individual_report(result)
        print(f"\n  ✅ 分析完成: {result.get('name', '')} ({symbol})")

        # 汇总
        analysis = result.get("analysis", {})
        if analysis:
            print(f"  📊 评分: {analysis.get('score', '?')}/10 | "
                  f"评级: {analysis.get('rating', '?')} | "
                  f"置信度: {analysis.get('confidence', '?')}")

    print(f"\n{'✅'*10}")
    print(f"  全部分析完成")
    print(f"{'✅'*10}\n")


def run_monitor():
    """启动新闻监控"""
    print("\n" + "█" * 60)
    print("   🔔 个股新闻监控")
    print("█" * 60)

    symbols = settings.stock_list or settings.watch_list
    if not symbols:
        symbols = ["002594", "601012", "510880", "512480"]
        print(f"  📌 使用默认监控列表: {', '.join(symbols)}")

    print(f"  📡 监控股票: {', '.join(symbols)}")
    print(f"  ⏱ 每 60 分钟检查一次")

    from analysis.monitor import NewsMonitor
    monitor = NewsMonitor()
    monitor.start_monitoring(symbols)


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
        "low": lambda: run_scan_with_mode("low_position"),
        "低位": lambda: run_scan_with_mode("low_position"),
        "mom": lambda: run_scan_with_mode("momentum"),
        "追高": lambda: run_scan_with_mode("momentum"),
        "hunt": run_hunter,
        "挖掘": run_hunter,
        "backtest": run_backtest_mode,
        "bt": run_backtest_mode,
        "btmulti": run_backtest_multi,
        "report": run_report,
        "报告": run_report,
        "optimize": run_optimize,
        "优化": run_optimize,
        "add": add_holding,
        "添加": add_holding,
        "list": list_holdings,
        "持仓": list_holdings,
        "analyze": run_individual_analysis,
        "分析": run_individual_analysis,
        "guide": lambda: __import__("report.indicator_guide", fromlist=[""]).generate_indicator_guide(),
        "monitor": run_monitor,
        "监控": run_monitor,
        "all": lambda: [run_scan(), run_buy_analysis(), run_sell_analysis()],
    }

    fn = modes.get(mode)
    if fn:
        fn()
    else:
        print(f"未知模式: {mode}")
        print("用法: python main.py [command]")
        print("  scan [mode]  市场扫描 (low/mom/top_gainers)")
        print("  low          低位潜力股 (量化筛选)")
        print("  mom          追高跟强")
        print("  hunt         低位挖掘 (AI深度分析) 💎")
        print("  buy          买入分析")
        print("  sell         卖出分析")
        print("  analyze <code>  个股深度分析 (新) 📋")
        print("  monitor      新闻监控 (新) 🔔")
        print("  report       生成每日PDF报告 📄")
        print("  backtest     回测验证")
        print("  btmulti      多日期综合回测")


if __name__ == "__main__":
    main()
