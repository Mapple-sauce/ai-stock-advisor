"""资金面数据 —— 北向资金、个股大单流向"""

from __future__ import annotations


def get_money_flow(symbol: str) -> dict:
    """获取个股资金流向（大单/中单/小单）

    使用 akshare stock_individual_fund_flow
    返回最近 5 个交易日的资金流向汇总
    """
    try:
        import akshare as ak

        # 获取近 10 个交易日的个股资金流向
        df = ak.stock_individual_fund_flow(stock=symbol, market="sh")
        if df is None or df.empty:
            df = ak.stock_individual_fund_flow(stock=symbol, market="sz")
        if df is None or df.empty:
            return {}

        # 取最近 5 行
        recent = df.head(5)
        main_in = recent["主力净流入-净额"].astype(float).sum() if "主力净流入-净额" in recent.columns else 0
        main_ratio = recent["主力净流入-净占比"].astype(float).mean() if "主力净流入-净占比" in recent.columns else 0
        super_in = recent["超大单净流入-净额"].astype(float).sum() if "超大单净流入-净额" in recent.columns else 0
        large_in = recent["大单净流入-净额"].astype(float).sum() if "大单净流入-净额" in recent.columns else 0

        # 趋势判断
        daily_flows = recent["主力净流入-净额"].astype(float).tolist() if "主力净流入-净额" in recent.columns else []
        up_days = sum(1 for f in daily_flows if f > 0)
        if up_days >= 4:
            trend = "持续流入"
        elif up_days >= 3:
            trend = "流入为主"
        elif up_days >= 2:
            trend = "流入流出均衡"
        elif up_days >= 1:
            trend = "流出为主"
        else:
            trend = "持续流出"

        return {
            "main_net_inflow": round(main_in, 2),
            "main_inflow_ratio": round(main_ratio, 2),
            "super_large_net": round(super_in, 2),
            "large_net": round(large_in, 2),
            "flow_trend": trend,
            "up_days_5": up_days,
            "down_days_5": 5 - up_days,
        }
    except Exception:
        return {}


def get_northbound_flow(symbol: str) -> dict:
    """获取北向资金流向（沪股通/深股通）

    使用 akshare stock_hsgt_north_net_flow_in_em
    如果 akshare 接口不可用，返回空字典
    """
    try:
        import akshare as ak

        # 获取北向资金整体流向
        df = ak.stock_hsgt_north_net_flow_in_em(symbol=symbol)
        if df is None or df.empty:
            return {}

        recent = df.head(5)
        total_5d = recent["value"].astype(float).sum() if "value" in recent.columns else 0

        # 趋势判断
        vals = recent["value"].astype(float).tolist() if "value" in recent.columns else []
        up_days = sum(1 for v in vals if v > 0)

        if up_days >= 4:
            trend = "持续流入"
        elif up_days >= 2:
            trend = "流入为主"
        elif up_days >= 1:
            trend = "流入流出均衡"
        else:
            trend = "流出为主"

        return {
            "northbound_5d_flow": round(total_5d, 2),
            "northbound_trend": trend,
            "up_days_5": up_days,
        }
    except Exception:
        return {}
