"""新闻舆情获取"""

from __future__ import annotations


def get_stock_news(symbol: str, max_results: int = 5) -> list[dict]:
    """获取个股相关新闻"""
    results = []
    try:
        import akshare as ak

        news = ak.stock_info_news(symbol=symbol)
        if news is not None and not news.empty:
            for _, row in news.head(max_results).iterrows():
                results.append({
                    "title": str(row.get("标题", "")),
                    "time": str(row.get("发布时间", "")),
                    "content": str(row.get("内容", "")),
                })
    except Exception:
        pass
    return results


def get_market_news(max_results: 10) -> list[dict]:
    """获取市场要闻"""
    results = []
    try:
        import akshare as ak

        news = ak.stock_info_news(symbol="sh000001")
        if news is not None and not news.empty:
            for _, row in news.head(max_results).iterrows():
                results.append({
                    "title": str(row.get("标题", "")),
                    "time": str(row.get("发布时间", "")),
                })
    except Exception:
        pass
    return results
