"""回测数据层 —— 支持按时间回溯查询数据

核心功能: 在指定时间点查询"当时能看到的数据"
"""

from __future__ import annotations

import datetime
import pandas as pd


def get_realtime_quote_as_of(symbol: str, as_of_date: str) -> dict:
    """获取指定日期的收盘行情 (模拟当时的实时数据)

    回测思路: 用 Baostock 获取当天的收盘价作为"实时价格"
    """
    try:
        import baostock as bs
        bs.login()

        code = _to_bs_code(symbol)
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume,amount",
            start_date=as_of_date, end_date=as_of_date,
            frequency="d", adjustflag="3",
        )
        bs.logout()

        if rs.error_code != "0":
            return {"error": f"Baostock查询失败: {rs.error_msg}", "code": symbol}

        df = rs.get_data()
        if df is None or df.empty:
            return {"error": f"无 {as_of_date} 数据", "code": symbol}

        r = df.iloc[0]
        return {
            "code": symbol,
            "name": _get_name(symbol, as_of_date),
            "price": _f(r.get("close", 0)),
            "open": _f(r.get("open", 0)),
            "high": _f(r.get("high", 0)),
            "low": _f(r.get("low", 0)),
            "volume": _f(r.get("volume", 0)),
            "turnover": _f(r.get("amount", 0)),
            "change_pct": 0.0,
            "change_amount": 0.0,
            "amplitude": 0.0,
            "pe": 0.0,
            "market_cap": 0.0,
            "turnover_rate": 0.0,
            "pre_close": 0.0,
            "_as_of_date": as_of_date,
        }
    except Exception as e:
        return {"error": str(e), "code": symbol}


def get_kline_as_of(symbol: str, as_of_date: str, count: int = 120) -> pd.DataFrame:
    """获取指定日期之前的 K 线 (不含当天)"""
    try:
        import baostock as bs
        import datetime as dt

        bs.login()

        code = _to_bs_code(symbol)
        end = dt.date.fromisoformat(as_of_date)
        start = end - dt.timedelta(days=180)

        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume,amount",
            start_date=start.strftime("%Y-%m-%d"),
            end_date=as_of_date,
            frequency="d", adjustflag="3",
        )
        bs.logout()

        if rs.error_code != "0":
            return pd.DataFrame()

        df = rs.get_data()
        if df is None or df.empty:
            return pd.DataFrame()

        # 去掉当天数据 (回测时当天数据不可用)
        df = df[df["date"] < as_of_date]

        df = df.rename(columns={
            "date": "日期", "open": "开盘", "high": "最高",
            "low": "最低", "close": "收盘", "volume": "成交量", "amount": "成交额",
        })
        for col in ["开盘", "最高", "最低", "收盘", "成交量", "成交额"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df.tail(count).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def get_actual_return(symbol: str, start_date: str, hold_days: int = 30) -> dict:
    """获取指定时间段后的真实涨跌 (用于验证预测)"""
    try:
        import baostock as bs
        import datetime as dt

        bs.login()
        code = _to_bs_code(symbol)

        start = dt.date.fromisoformat(start_date)
        end = start + dt.timedelta(days=hold_days + 10)

        rs = bs.query_history_k_data_plus(
            code, "date,close",
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            frequency="d", adjustflag="3",
        )
        bs.logout()

        if rs.error_code != "0":
            return {"error": rs.error_msg}

        df = rs.get_data()
        if df is None or df.empty or len(df) < 2:
            return {"error": "数据不足"}

        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna()

        if len(df) < 2:
            return {"error": "有效数据不足"}

        entry = float(df.iloc[0]["close"])
        # 取30天内最高/最低/收盘
        if len(df) > hold_days:
            df_period = df.iloc[1:hold_days+1]
        else:
            df_period = df.iloc[1:]

        if df_period.empty:
            return {"error": "无后续数据"}

        exit_price = float(df_period.iloc[-1]["close"])
        high_price = float(df_period["close"].max())
        low_price = float(df_period["close"].min())

        return {
            "entry_price": round(entry, 2),
            "exit_price": round(exit_price, 2),
            "return_pct": round((exit_price - entry) / entry * 100, 2),
            "high_pct": round((high_price - entry) / entry * 100, 2),
            "low_pct": round((low_price - entry) / entry * 100, 2),
            "best_return": round((high_price - entry) / entry * 100, 2),
            "worst_return": round((low_price - entry) / entry * 100, 2),
            "days_in_data": len(df_period),
            "start_date": start_date,
        }
    except Exception as e:
        return {"error": str(e)}


def _to_bs_code(symbol: str) -> str:
    s = symbol.strip()
    if s.startswith(("sh.", "sz.", "bj.")):
        return s
    if s.startswith(("sh", "sz", "bj")):
        return f"{s[:2]}.{s[2:]}"
    if s.isdigit():
        prefix = "sh" if s.startswith(("6", "9")) else "sz"
        return f"{prefix}.{s}"
    return s


def _get_name(symbol: str, as_of_date: str) -> str:
    """获取股票名称 (回测时用)"""
    try:
        import baostock as bs
        bs.login()
        rs = bs.query_stock_basic(code=_to_bs_code(symbol))
        bs.logout()
        if rs.error_code == "0":
            data = rs.get_data()
            if data is not None and not data.empty:
                return str(data.iloc[0].get("code_name", symbol))
    except Exception:
        pass
    return symbol


def _f(v) -> float:
    try:
        return round(float(v), 2)
    except (ValueError, TypeError):
        return 0.0
