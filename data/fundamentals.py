"""基本面数据"""

from __future__ import annotations


def get_financial_summary(symbol: str) -> dict:
    """获取利润表摘要"""
    try:
        import akshare as ak

        income = ak.stock_financial_abstract(symbol=symbol)
        if income is None or income.empty:
            return {}
        latest = income.iloc[0]
        return {
            "revenue": float(latest.get("营业收入", 0) or 0),
            "revenue_yoy": _parse_pct(str(latest.get("营业收入同比增长", "0"))),
            "net_profit": float(latest.get("净利润", 0) or 0),
            "profit_yoy": _parse_pct(str(latest.get("净利润同比增长", "0"))),
            "report_date": str(latest.get("报告期", "")),
        }
    except Exception as e:
        return {"error": str(e)}


def get_valuation_summary(symbol: str, quote: dict | None = None) -> dict:
    """估值数据"""
    if quote and quote.get("pe"):
        return {"pe": quote["pe"], "market_cap": quote["market_cap"]}
    from data.market import get_realtime_quote
    q = get_realtime_quote(symbol)
    return {"pe": q.get("pe", 0), "market_cap": q.get("market_cap", 0)}


def _parse_pct(s: str) -> float:
    try:
        return float(s.strip().strip("%"))
    except (ValueError, AttributeError):
        return 0.0
