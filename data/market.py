"""行情数据获取 (akshare 免费接口)"""

from __future__ import annotations

import pandas as pd

# 新浪接口列名映射
_SINA_COLUMNS = {
    "代码": "code",
    "名称": "name",
    "最新价": "price",
    "涨跌幅": "change_pct",
    "涨跌额": "change_amount",
    "今开": "open",
    "昨收": "pre_close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "turnover",
    "买入": "bid",
    "卖出": "ask",
    "时间戳": "time",
}

# 东方财富接口列名
_EM_COLUMNS = {
    "代码": "code",
    "名称": "name",
    "最新价": "price",
    "涨跌幅": "change_pct",
    "涨跌额": "change_amount",
    "今开": "open",
    "昨收": "pre_close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "turnover",
    "振幅": "amplitude",
    "市盈率-动态": "pe",
    "总市值": "market_cap",
    "换手率": "turnover_rate",
}


def _df_to_dict(df: pd.DataFrame, symbol: str, column_map: dict) -> dict:
    """将 DataFrame 行转为统一格式的字典"""
    row = df[df["代码"] == symbol]
    if row.empty:
        return {"error": f"未找到 {symbol}", "code": symbol}

    r = row.iloc[0]
    result = {"code": symbol, "name": str(r.get("名称", ""))}

    for sina_key, unified_key in column_map.items():
        if sina_key in r:
            v = r[sina_key]
            try:
                result[unified_key] = round(float(v), 2)
            except (ValueError, TypeError):
                result[unified_key] = v

    # 补充字段
    if "pe" not in result:
        result["pe"] = 0.0
    if "market_cap" not in result:
        result["market_cap"] = 0.0
    if "amplitude" not in result:
        result["amplitude"] = 0.0
    if "turnover_rate" not in result:
        result["turnover_rate"] = 0.0

    return result


def get_realtime_quote(symbol: str) -> dict:
    """获取实时行情 (自动尝试多个数据源)"""
    result = _try_em(symbol)
    if result:
        return result
    result = _try_sina(symbol)
    if result:
        return result
    return {"error": f"所有数据源均无法获取 {symbol}", "code": symbol}


def _try_em(symbol: str) -> dict | None:
    """尝试东方财富接口"""
    try:
        import akshare as ak

        if symbol.isdigit() and symbol.startswith(("51", "15", "16", "18", "56", "58")):
            df = ak.fund_etf_spot_em()
        else:
            df = ak.stock_zh_a_spot_em()
        return _df_to_dict(df, symbol, _EM_COLUMNS)
    except Exception:
        return None


def _try_sina(symbol: str) -> dict | None:
    """尝试新浪接口 (代码带 sh/sz 前缀)"""
    try:
        import akshare as ak

        df = ak.stock_zh_a_spot()  # 新浪
        df = df[~df["代码"].str.startswith("bj")]

        # 新浪接口代码有前缀 (sh600519, sz000001)
        # 先尝试用原始代码匹配
        result = _df_to_dict(df, symbol, _SINA_COLUMNS)
        if "error" not in result:
            return result

        # 再尝试加 sh/sz 前缀
        if symbol.isdigit():
            if symbol.startswith(("6", "9")):
                result = _df_to_dict(df, f"sh{symbol}", _SINA_COLUMNS)
            else:
                result = _df_to_dict(df, f"sz{symbol}", _SINA_COLUMNS)
            if "error" not in result:
                return result

        return None
    except Exception:
        return None


def get_kline(symbol: str, period: str = "daily", count: int = 120) -> pd.DataFrame:
    """获取历史 K 线 (用于技术指标计算)"""
    try:
        import akshare as ak

        df = ak.stock_zh_a_hist(symbol=symbol, period=period, adjust="qfq")
        df = df.tail(count).reset_index(drop=True)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        print(f"  ⚠️ {symbol} K线获取失败: {e}")
        return pd.DataFrame()


def get_batch_quotes(symbols: list[str]) -> dict[str, dict]:
    """批量获取行情"""
    result = {}
    for s in symbols:
        result[s] = get_realtime_quote(s)
    return result
