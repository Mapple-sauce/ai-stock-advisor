#!/usr/bin/env python3
"""纯文本版个股分析报告——测试数据流和中文显示"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analysis.analyst import stock_analyst
from datetime import datetime

symbols = sys.argv[1:] if len(sys.argv) > 1 else ["512480", "510880", "002594"]
output_lines = []

for symbol in symbols:
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  {symbol} 分析报告 (纯文本版)")
    lines.append(f"{'='*60}")

    result = stock_analyst.analyze(symbol)

    if result.get("status") == "error":
        lines.append(f"  ❌ 失败: {result.get('error')}")
    else:
        name = result.get("name", symbol)
        price = result.get("price", "?")
        lines.append(f"  名称: {name}")
        lines.append(f"  价格: {price}")

        metrics = result.get("metrics", {})
        lines.append(f"\n  📊 核心指标:")
        lines.append(f"    最大回撤: {metrics.get('max_drawdown', {}).get('max_dd_pct', 'N/A')}%")
        lines.append(f"    夏普比率: {metrics.get('sharpe_ratio', 'N/A')}")
        lines.append(f"    年化波动率: {metrics.get('volatility_1y', 'N/A')}%")
        lines.append(f"    近1月: {metrics.get('return_1m', 'N/A')}")

        analysis = result.get("analysis", {})
        lines.append(f"\n  🤖 AI 研判:")
        lines.append(f"    评分: {analysis.get('score', '?')}/10")
        lines.append(f"    评级: {analysis.get('rating', '?')}")
        lines.append(f"    置信度: {analysis.get('confidence', '?')}")

        for key, label in [("summary","核心观点"),("technical_analysis","技术面"),
                           ("fundamental_analysis","基本面"),("outlook","后市")]:
            txt = analysis.get(key, "")
            if txt:
                lines.append(f"\n    {label}:")
                lines.append(f"      {txt[:300]}")

    lines.append(f"\n  {'='*50}")
    lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  {'='*50}")
    output_lines.extend(lines)

# 打印到控制台
print('\n'.join(output_lines))

# 保存到文件
save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(save_dir, exist_ok=True)
save_path = os.path.join(save_dir, f"text_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
with open(save_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))
print(f"\n  [FILE] 报告已保存: {save_path}")
