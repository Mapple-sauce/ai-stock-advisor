"""行情数据获取

数据源策略:
  - K线/历史数据: Baostock (免费, 稳定, 无需注册)
  - 实时行情: 新浪 (akshare stock_zh_a_spot)
  - 兜底: akshare 其他接口
"""

from __future__ import annotations

import pandas as pd

# ── 新浪行情缓存 (避免重复下载) ──
_sina_cache: pd.DataFrame | None = None


def get_realtime_quote(symbol: str) -> dict:
    """获取实时行情 (新浪, 带缓存)"""
    global _sina_cache

    try:
        import akshare as ak

        # 缓存全市场数据 (首次下载后复用)
        if _sina_cache is None:
            df = ak.stock_zh_a_spot()
            df = df[~df["代码"].str.startswith("bj")]
            df = df[~df["名称"].str.contains("ST|\\*")]
            _sina_cache = df

        df = _sina_cache

        # 匹配股票 (新浪代码带 sh/sz 前缀)
        row = _find_row(df, symbol)
        if row is None:
            return {"error": f"未找到 {symbol}", "code": symbol}

        return {
            "code": symbol,
            "name": str(row.get("名称", "")),
            "price": _float(row.get("最新价", 0)),
            "change_pct": _float(row.get("涨跌幅", 0)),
            "change_amount": _float(row.get("涨跌额", 0)),
            "open": _float(row.get("今开", 0)),
            "pre_close": _float(row.get("昨收", 0)),
            "high": _float(row.get("最高", 0)),
            "low": _float(row.get("最低", 0)),
            "volume": _float(row.get("成交量", 0)),
            "turnover": _float(row.get("成交额", 0)),
            "amplitude": 0.0,
            "pe": 0.0,
            "market_cap": 0.0,
            "turnover_rate": 0.0,
        }
    except Exception as e:
        return {"error": str(e), "code": symbol}


def _find_row(df: pd.DataFrame, symbol: str):
    """在 DataFrame 中查找股票行"""
    # 直接匹配
    match = df[df["代码"] == symbol]
    if not match.empty:
        return match.iloc[0]

    # 加 sh/sz 前缀
    if symbol.isdigit():
        for prefix in ("sh", "sz"):
            match = df[df["代码"] == f"{prefix}{symbol}"]
            if not match.empty:
                return match.iloc[0]

    return None


def get_kline(symbol: str, period: str = "daily", count: int = 120) -> pd.DataFrame:
    """获取历史 K 线 (Baostock → akshare 兜底)

    Baostock 规范格式:
      - 沪市: sh.600519
      - 深市: sz.000001 / sz.300308
    """
    df = _try_baostock_kline(symbol, count)
    if df is not None and not df.empty and len(df) >= 10:
        return df

    # 兜底: akshare
    df = _try_akshare_kline(symbol)
    if df is not None and not df.empty:
        return df.tail(count).reset_index(drop=True)

    print(f"  ⚠️ {symbol} K线获取失败 (所有数据源)")
    return pd.DataFrame()


def _try_baostock_kline(symbol: str, count: int = 120) -> pd.DataFrame | None:
    """尝试 Baostock 获取 K 线"""
    try:
        import baostock as bs

        bs.login()

        # 转换代码格式
        bs_code = _to_baostock_code(symbol)

        # 根据 count 推算起始日期 (约 6 个月)
        import datetime
        end = datetime.date.today()
        start = end - datetime.timedelta(days=180)

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume,amount",
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            frequency="d",
            adjustflag="3",  # 前复权
        )

        bs.logout()

        if rs.error_code != "0":
            return None

        df = rs.get_data()
        if df is None or df.empty:
            return None

        # 重命名列为中文 (兼容 indicators.py)
        df = df.rename(columns={
            "date": "日期",
            "open": "开盘",
            "high": "最高",
            "low": "最低",
            "close": "收盘",
            "volume": "成交量",
            "amount": "成交额",
        })

        # 转数值类型
        for col in ["开盘", "最高", "最低", "收盘", "成交量", "成交额"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.tail(count).reset_index(drop=True)
        return df

    except Exception as e:
        print(f"  ⚠️ Baostock K线失败: {e}")
        try:
            bs.logout()
        except Exception:
            pass
        return None


def _try_akshare_kline(symbol: str) -> pd.DataFrame | None:
    """尝试 akshare 获取 K 线 (兜底)"""
    try:
        import akshare as ak

        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        if df is None or df.empty:
            return None
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception:
        return None


def get_batch_quotes(symbols: list[str]) -> dict[str, dict]:
    """批量获取行情"""
    results = {}
    for s in symbols:
        results[s] = get_realtime_quote(s)
    return results


def _float(v) -> float:
    try:
        return round(float(v), 2)
    except (ValueError, TypeError):
        return 0.0


def _to_baostock_code(symbol: str) -> str:
    """转为 Baostock 格式 (sh.600519 / sz.000001)"""
    s = symbol.strip()
    if s.startswith(("sh.", "sz.", "bj.")):
        return s
    if s.startswith(("sh", "sz", "bj")):
        return f"{s[:2]}.{s[2:]}"
    if s.isdigit():
        prefix = "sh" if s.startswith(("5", "6", "9")) else "sz"
        return f"{prefix}.{s}"
    return s
