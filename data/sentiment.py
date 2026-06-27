"""舆情采集器 —— 从主流财经平台采集文本观点

数据源:
  1. akshare 股票新闻 (东方财富)
  2. akshare 股吧帖子 (东方财富)
  3. akshare 研报摘要
  4. akshare 新闻快讯

输出: 结构化的舆情数据, 用于 AI 观点汇总
"""

from __future__ import annotations

import datetime
import json
from typing import Any


def collect_sentiment(symbol: str, name: str = "", max_sources: int = 3) -> dict:
    """采集个股全渠道舆情

    Args:
        symbol: 股票代码
        name: 股票名称
        max_sources: 最大来源数

    Returns:
        {"news": [...], "posts": [...], "reports": [...], "summary": ""}
    """
    result = {
        "symbol": symbol,
        "name": name or symbol,
        "collected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "news": [],
        "posts": [],
        "reports": [],
        "total_items": 0,
    }

    # 1. 股票新闻
    try:
        import akshare as ak
        news = ak.stock_info_news(symbol=symbol)
        if news is not None and not news.empty:
            for _, row in news.head(10).iterrows():
                title = str(row.get("标题", "") or "")
                content = str(row.get("内容", "") or "")
                time = str(row.get("发布时间", "") or "")[:10]
                if title.strip():
                    result["news"].append({
                        "title": title.strip(),
                        "content": content.strip()[:200],
                        "time": time,
                        "source": "东方财富",
                    })
    except Exception as e:
        print(f"    ⚠️ 新闻获取失败: {e}")

    # 2. 股吧帖子
    try:
        import akshare as ak
        posts = ak.stock_board_comment_em(symbol=symbol)
        if posts is not None and not posts.empty:
            for _, row in posts.head(10).iterrows():
                title = str(row.get("标题", "") or "")
                content = str(row.get("内容", "") or "")
                if title.strip():
                    result["posts"].append({
                        "title": title.strip()[:100],
                        "content": content.strip()[:200],
                        "source": "股吧",
                    })
    except Exception:
        pass

    # 3. 研报摘要
    try:
        import akshare as ak
        reports = ak.stock_research_report_em(symbol=symbol)
        if reports is not None and not reports.empty:
            for _, row in reports.head(5).iterrows():
                title = str(row.get("标题", "") or "")
                org = str(row.get("机构", "") or "")
                rating = str(row.get("评级", "") or "")
                if title.strip():
                    result["reports"].append({
                        "title": title.strip()[:100],
                        "org": org.strip(),
                        "rating": rating.strip(),
                        "source": "券商研报",
                    })
    except Exception:
        pass

    result["total_items"] = len(result["news"]) + len(result["posts"]) + len(result["reports"])
    return result


def summarize_sentiment(sentiment_data: dict) -> str:
    """AI 汇总舆情观点

    使用 LLM 分析采集到的舆情，输出:
      - 市场整体情绪 (看多/看空/中性)
      - 核心观点摘要
      - 多空分歧点
      - 关键风险提示

    Args:
        sentiment_data: collect_sentiment() 的输出

    Returns:
        AI 汇总的分析文本
    """
    from agents.base import BaseAgent

    name = sentiment_data.get("name", sentiment_data.get("symbol", ""))
    news = sentiment_data.get("news", [])
    posts = sentiment_data.get("posts", [])
    reports = sentiment_data.get("reports", [])

    if not news and not posts and not reports:
        return "(暂无舆情数据)"

    # 构建输入文本
    lines = [f"# {name} 舆情汇总分析", f"采集时间: {sentiment_data.get('collected_at', '')}", ""]

    if reports:
        lines.append(f"## 券商研报 ({len(reports)} 篇)")
        for r in reports:
            lines.append(f"- [{r.get('org','')}] {r.get('title','')} 评级:{r.get('rating','N/A')}")
        lines.append("")

    if news:
        lines.append(f"## 新闻 ({len(news)} 条)")
        for n in news:
            lines.append(f"- [{n.get('time','')}] {n.get('title','')}")
        lines.append("")

    if posts:
        lines.append(f"## 股吧讨论 ({len(posts)} 条)")
        for p in posts[:5]:
            lines.append(f"- {p.get('title','')}")
        lines.append("")

    lines.append(
        "请根据以上信息，输出以下内容(中文):\n"
        "1. **市场情绪**: 看多/看空/中性\n"
        "2. **核心观点**: 用2-3句话概括市场主要观点\n"
        "3. **多空分歧**: 看多vs看空的核心逻辑\n"
        "4. **关键信号**: 值得关注的事件或数据\n"
        "5. **风险提示**: 潜在的利空因素"
    )

    agent = BaseAgent("sentiment_summarizer", temperature=0.05)
    try:
        result = agent.call("\n".join(lines), max_tokens=2048)
        return result
    except Exception as e:
        return f"(AI 汇总失败: {e})"


def get_market_news_snapshot(max_items: int = 5) -> list[dict]:
    """获取市场要闻快照"""
    results = []
    try:
        import akshare as ak
        news = ak.stock_info_news(symbol="sh000001")
        if news is not None and not news.empty:
            for _, row in news.head(max_items).iterrows():
                title = str(row.get("标题", "") or "")
                if title.strip():
                    results.append({
                        "title": title.strip(),
                        "time": str(row.get("发布时间", "") or "")[:10],
                    })
    except Exception:
        pass
    return results
