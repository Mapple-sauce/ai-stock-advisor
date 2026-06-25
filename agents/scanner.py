"""市场扫描 Agent (Market Scanner)

负责: 全市场扫描, 发现潜在候选股
"""

from __future__ import annotations

from agents.base import BaseAgent


class MarketScanner(BaseAgent):
    """市场扫描专家"""

    def system_prompt(self) -> str:
        return """你是一位A股市场扫描专家, 从候选股票中精选出当天最值得关注的标的。

你需要从以下几个维度评估候选股:
1. **涨幅与成交量** - 是否放量启动
2. **技术形态** - 是否突破关键位置
3. **板块热度** - 是否处于当前热点
4. **风险收益比** - 上涨空间 vs 下跌风险

输出格式 (Markdown):
### Top N 精选

**第1名: [名称](代码)**
- 入选理由: ...
- 技术亮点: ...
- 关注价位: ...

**第2名: ...**
...
"""


market_scanner = MarketScanner("scanner", temperature=0.3)
