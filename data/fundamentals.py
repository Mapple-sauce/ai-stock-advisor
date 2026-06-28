"""基本面数据 —— 增强版：近4个季度财报 + 关键指标"""

from __future__ import annotations


def get_financial_summary(symbol: str) -> dict:
    """获取利润表摘要（增强版：近4个季度数据）"""
    try:
        import akshare as ak
        import pandas as pd

        income = ak.stock_financial_abstract(symbol=symbol)
        if income is None or income.empty:
            return {}

        # 最新一期
        latest = income.iloc[0]
        result = {
            "revenue": float(latest.get("营业收入", 0) or 0),
            "revenue_yoy": _parse_pct(str(latest.get("营业收入同比增长", "0"))),
            "net_profit": float(latest.get("净利润", 0) or 0),
            "profit_yoy": _parse_pct(str(latest.get("净利润同比增长", "0"))),
            "report_date": str(latest.get("报告期", "")),
            "report_period": "最新一期",
        }

        # 近4个季度数据
        quarters = []
        for i in range(min(4, len(income))):
            row = income.iloc[i]
            q = {
                "report_date": str(row.get("报告期", "")),
                "revenue": float(row.get("营业收入", 0) or 0),
                "revenue_yoy": _parse_pct(str(row.get("营业收入同比增长", "0"))),
                "net_profit": float(row.get("净利润", 0) or 0),
                "profit_yoy": _parse_pct(str(row.get("净利润同比增长", "0"))),
            }
            # 毛利率估算
            revenue = q["revenue"]
            cost = float(row.get("营业成本", 0) or 0)
            q["gross_margin"] = round((revenue - cost) / revenue * 100, 2) if revenue else 0
            # 净利率
            q["net_margin"] = round(q["net_profit"] / revenue * 100, 2) if revenue else 0
            quarters.append(q)

        result["quarters"] = quarters

        # 尝试获取ROE、资产负债率等
        try:
            # 用 ak.stock_financial_analysis_indicator 获取 ROE
            indicators = ak.stock_financial_analysis_indicator(symbol)
            if indicators is not None and not indicators.empty:
                latest_ind = indicators.iloc[0]
                result["roe"] = float(latest_ind.get("净资产收益率", 0) or 0)
                result["debt_ratio"] = float(latest_ind.get("资产负债率", 0) or 0)
                result["current_ratio"] = float(latest_ind.get("流动比率", 0) or 0)
                # 研发投入占营收比
                rd = float(latest_ind.get("研发投入占营业收入比例", 0) or 0)
                result["rd_ratio"] = rd
        except Exception:
            pass

        # 尝试获取现金流
        try:
            cf = ak.stock_cash_flow(symbol)
            if cf is not None and not cf.empty:
                latest_cf = cf.iloc[0]
                result["operating_cashflow"] = float(latest_cf.get("经营活动产生的现金流量净额", 0) or 0)
        except Exception:
            pass

        return result

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
