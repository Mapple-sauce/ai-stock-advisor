"""量化筛选器 —— 技术面初筛"""

from __future__ import annotations

from config import settings


def screen_market() -> list[dict]:
    """全市场初筛, 返回候选股票列表"""
    try:
        import akshare as ak

        # 使用新浪接口 (更稳定)
        df = ak.stock_zh_a_spot()
        # 过滤北交所
        df = df[~df["代码"].str.startswith("bj")]
        # 排除 ST
        df = df[~df["名称"].str.contains("ST|\\*")]
        # 按涨幅降序
        df = df.sort_values("涨跌幅", ascending=False).head(100)

        candidates = []
        for _, row in df.iterrows():
            candidates.append({
                "code": str(row["代码"]),
                "name": str(row["名称"]),
                "price": round(float(row.get("最新价", 0) or 0), 2),
                "change_pct": round(float(row.get("涨跌幅", 0) or 0), 2),
                "turnover": float(row.get("成交额", 0) or 0),
                "volume": float(row.get("成交量", 0) or 0),
            })

        return candidates[: settings.scan_top_n]
    except Exception as e:
        print(f"  ⚠️ 市场扫描失败: {e}")
        return []
