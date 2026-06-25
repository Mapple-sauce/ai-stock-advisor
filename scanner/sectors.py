"""板块分类与策略体系

A股不同板块有不同的运行规律, 需要差异化的因子权重。
每个板块配置独立的因子权重矩阵和评分方向。

板块方向说明:
  _direction: 1  → 正向评分 (高分=好, 适合追趋势的板块如科技)
  _direction: -1 → 反向评分 (低分=好, 适合抄底的板块如工业)
"""

from __future__ import annotations

SECTOR_MAP: dict[str, str] = {
    "C13": "消费", "C14": "消费", "C15": "消费", "C16": "消费",
    "C17": "消费", "C18": "消费", "C19": "消费", "C20": "消费",
    "C21": "消费", "C22": "消费", "C23": "消费", "C24": "消费",
    "F51": "消费", "F52": "消费", "H61": "消费", "H62": "消费",
    "C39": "科技", "C40": "科技", "I63": "科技", "I64": "科技",
    "I65": "科技", "M74": "科技",
    "C27": "医药", "Q83": "医药",
    "J66": "金融", "J67": "金融", "J68": "金融", "J69": "金融",
    "C38": "新能源", "C36": "新能源",
    "B06": "周期", "B07": "周期", "B08": "周期", "B09": "周期",
    "B10": "周期", "B11": "周期", "C25": "周期", "C26": "周期",
    "C28": "周期", "C29": "周期", "C30": "周期", "C31": "周期",
    "C32": "周期", "C33": "周期", "D44": "周期", "D45": "周期",
    "K70": "周期", "K71": "周期",
    "C34": "工业", "C35": "工业", "C37": "工业", "C41": "工业",
    "C42": "工业", "C43": "工业", "E47": "工业", "E48": "工业",
    "E49": "工业", "E50": "工业", "E51": "工业",
    "G53": "工业", "G54": "工业", "G55": "工业", "G56": "工业",
    "G57": "工业", "G58": "工业", "G59": "工业",
    "M73": "工业", "N77": "工业", "N78": "工业",
}
_SECTOR_WEIGHTS_LOW: dict[str, dict] = {
    "消费": {
        "_direction": 1,  # 正向
        "ma_trend": (0.12, "均线趋势", ""), "macd_signal": (0.10, "MACD信号", ""),
        "rsi_position": (0.12, "RSI位置", "RSI反转"), "volume_ratio": (0.06, "量价关系", ""),
        "bb_position": (0.10, "布林位置", ""), "kdj_signal": (0.05, "KDJ信号", ""),
        "price_position": (0.12, "价格位置", "回调深度"), "near_high_low": (0.06, "高低位置", ""),
        "daily_change": (0.07, "当日涨幅", ""), "ma5_stability": (0.08, "MA5支撑", ""),
    },
    "科技": {
        "_direction": 1,
        "ma_trend": (0.18, "均线趋势", "趋势最重要"), "macd_signal": (0.15, "MACD信号", ""),
        "rsi_position": (0.06, "RSI位置", ""), "volume_ratio": (0.12, "量价关系", ""),
        "bb_position": (0.08, "布林位置", ""), "kdj_signal": (0.10, "KDJ信号", ""),
        "price_position": (0.05, "价格位置", ""), "near_high_low": (0.10, "高低位置", "突破"),
        "daily_change": (0.10, "当日涨幅", ""), "ma5_stability": (0.06, "MA5支撑", ""),
    },
    "医药": {
        "_direction": -1,
        "ma_trend": (0.14, "均线趋势", ""), "macd_signal": (0.12, "MACD信号", ""),
        "rsi_position": (0.08, "RSI位置", ""), "volume_ratio": (0.08, "量价关系", ""),
        "bb_position": (0.08, "布林位置", ""), "kdj_signal": (0.06, "KDJ信号", ""),
        "price_position": (0.10, "价格位置", "回调"), "near_high_low": (0.05, "高低位置", ""),
        "daily_change": (0.04, "当日涨幅", ""), "ma5_stability": (0.08, "MA5支撑", ""),
    },
    "金融": {
        "_direction": 1,
        "ma_trend": (0.10, "均线趋势", ""), "macd_signal": (0.08, "MACD信号", ""),
        "rsi_position": (0.12, "RSI位置", ""), "volume_ratio": (0.05, "量价关系", ""),
        "bb_position": (0.06, "布林位置", ""), "kdj_signal": (0.05, "KDJ信号", ""),
        "price_position": (0.12, "价格位置", "PB+技术"), "near_high_low": (0.04, "高低位置", ""),
        "daily_change": (0.04, "当日涨幅", ""), "ma5_stability": (0.08, "MA5支撑", ""),
    },
    "新能源": {
        "_direction": -1,
        "ma_trend": (0.16, "均线趋势", ""), "macd_signal": (0.14, "MACD信号", ""),
        "rsi_position": (0.05, "RSI位置", ""), "volume_ratio": (0.12, "量价关系", ""),
        "bb_position": (0.07, "布林位置", ""), "kdj_signal": (0.08, "KDJ信号", ""),
        "price_position": (0.05, "价格位置", ""), "near_high_low": (0.10, "高低位置", "突破"),
        "daily_change": (0.12, "当日涨幅", ""), "ma5_stability": (0.06, "MA5支撑", ""),
    },
    "周期": {
        "_direction": 1,
        "ma_trend": (0.18, "均线趋势", "趋势为王"), "macd_signal": (0.15, "MACD信号", ""),
        "rsi_position": (0.08, "RSI位置", ""), "volume_ratio": (0.10, "量价关系", "放量确认"),
        "bb_position": (0.05, "布林位置", ""), "kdj_signal": (0.07, "KDJ信号", ""),
        "price_position": (0.06, "价格位置", ""), "near_high_low": (0.08, "高低位置", "突破确认"),
        "daily_change": (0.10, "当日涨幅", ""), "ma5_stability": (0.05, "MA5支撑", ""),
    },
    "工业": {
        "_direction": -1,
        "ma_trend": (0.14, "均线趋势", ""), "macd_signal": (0.10, "MACD信号", ""),
        "rsi_position": (0.08, "RSI位置", ""), "volume_ratio": (0.08, "量价关系", ""),
        "bb_position": (0.06, "布林位置", ""), "kdj_signal": (0.06, "KDJ信号", ""),
        "price_position": (0.08, "价格位置", ""), "near_high_low": (0.06, "高低位置", ""),
        "daily_change": (0.05, "当日涨幅", ""), "ma5_stability": (0.07, "MA5支撑", ""),
    },
    "综合": {
        "_direction": 1,
        "ma_trend": (0.14, "均线趋势", ""), "macd_signal": (0.12, "MACD信号", ""),
        "rsi_position": (0.08, "RSI位置", ""), "volume_ratio": (0.10, "量价关系", ""),
        "bb_position": (0.06, "布林位置", ""), "kdj_signal": (0.05, "KDJ信号", ""),
        "price_position": (0.08, "价格位置", ""), "near_high_low": (0.06, "高低位置", ""),
        "daily_change": (0.05, "当日涨幅", ""), "ma5_stability": (0.05, "MA5支撑", ""),
    },
}

_SECTOR_WEIGHTS_MOMENTUM: dict[str, dict] = {
    "科技": {
        "_direction": 1,
        "ma_trend": (0.18, "均线趋势", ""), "bb_position": (0.12, "布林位置", ""),
        "kdj_signal": (0.12, "KDJ信号", ""), "volume_ratio": (0.10, "量价关系", ""),
        "macd_signal": (0.14, "MACD信号", ""), "rsi_position": (0.08, "RSI位置", ""),
        "daily_change": (0.10, "当日涨幅", ""), "ma5_stability": (0.05, "MA5支撑", ""),
        "price_position": (0.05, "价格位置", ""), "near_high_low": (0.06, "高低位置", ""),
    },
    "新能源": {
        "_direction": -1,
        "ma_trend": (0.16, "均线趋势", ""), "bb_position": (0.10, "布林位置", ""),
        "kdj_signal": (0.10, "KDJ信号", ""), "volume_ratio": (0.14, "量价关系", ""),
        "macd_signal": (0.13, "MACD信号", ""), "rsi_position": (0.09, "RSI位置", ""),
        "daily_change": (0.12, "当日涨幅", ""), "ma5_stability": (0.05, "MA5支撑", ""),
        "price_position": (0.06, "价格位置", ""), "near_high_low": (0.05, "高低位置", ""),
    },
    "周期": {
        "_direction": 1,
        "ma_trend": (0.18, "均线趋势", ""), "bb_position": (0.08, "布林位置", ""),
        "kdj_signal": (0.08, "KDJ信号", ""), "volume_ratio": (0.14, "量价关系", ""),
        "macd_signal": (0.12, "MACD信号", ""), "rsi_position": (0.10, "RSI位置", ""),
        "daily_change": (0.12, "当日涨幅", ""), "ma5_stability": (0.06, "MA5支撑", ""),
        "price_position": (0.06, "价格位置", ""), "near_high_low": (0.06, "高低位置", ""),
    },
    "消费": {
        "_direction": 1,
        "ma_trend": (0.12, "均线趋势", ""), "bb_position": (0.10, "布林位置", ""),
        "kdj_signal": (0.08, "KDJ信号", ""), "volume_ratio": (0.10, "量价关系", ""),
        "macd_signal": (0.10, "MACD信号", ""), "rsi_position": (0.10, "RSI位置", ""),
        "daily_change": (0.06, "当日涨幅", ""), "ma5_stability": (0.10, "MA5支撑", ""),
        "price_position": (0.08, "价格位置", ""), "near_high_low": (0.06, "高低位置", ""),
    },
}

_industry_cache: dict[str, str] | None = None


def get_sector(symbol: str) -> str:
    global _industry_cache
    if _industry_cache is None:
        _load_industries()
    code = _normalize_code(symbol)
    if code in _industry_cache:
        industry_code = _industry_cache[code]
        for prefix in (industry_code[:3], industry_code[:2]):
            if prefix in SECTOR_MAP:
                return SECTOR_MAP[prefix]
    return "综合"


def get_sector_weights(sector: str, mode: str) -> dict | None:
    weights_map = _SECTOR_WEIGHTS_LOW if mode == "low_position" else _SECTOR_WEIGHTS_MOMENTUM
    w = weights_map.get(sector)
    if w is None:
        w = weights_map.get("综合")
    return w


def get_sector_weighted_score(entry_price: float, ind: dict, mode: str, sector: str) -> float:
    from scanner.screener import (
        score_ma_trend, score_macd_signal, score_rsi_position,
        score_volume_ratio, score_bb_position, score_kdj_signal,
        score_price_position, score_near_high_low, score_daily_change,
        score_ma5_stability,
    )
    weights = get_sector_weights(sector, mode)
    if weights is None:
        weights = _SECTOR_WEIGHTS_LOW.get("综合", {})
    fs = {
        "ma_trend": score_ma_trend(ind, mode)[0], "macd_signal": score_macd_signal(ind, mode)[0],
        "rsi_position": score_rsi_position(ind, mode)[0], "volume_ratio": score_volume_ratio(ind, mode)[0],
        "bb_position": score_bb_position(ind, mode)[0], "kdj_signal": score_kdj_signal(ind, mode)[0],
        "price_position": score_price_position(ind, mode, entry_price)[0],
        "near_high_low": score_near_high_low(ind, mode)[0],
        "daily_change": score_daily_change(ind, {"price": entry_price, "change_pct": 0}, mode)[0],
        "ma5_stability": score_ma5_stability(ind, mode)[0] if "ma5_stability" in weights else 0,
    }
    tw = ws = 0
    for f in weights:
        if f.startswith("_"):
            continue
        w, _, _ = weights[f]
        if f in fs:
            ws += w * fs[f] * 100
            tw += w
    raw = (ws / tw + 50) if tw else 50
    direction = weights.get("_direction", -1)
    if isinstance(direction, (int, float)):
        return max(0, min(100, raw if direction == 1 else 100 - raw))
    return max(0, min(100, 100 - raw))


def _normalize_code(symbol: str) -> str:
    s = symbol.strip()
    for p in ("sh.", "sz.", "bj."):
        if s.startswith(p):
            return s
    for p in ("sh", "sz", "bj"):
        if s.startswith(p):
            return f"{s[:2]}.{s[2:]}"
    if s.isdigit():
        return f"{'sh' if s.startswith(('6','9')) else 'sz'}.{s}"
    return s


def _load_industries():
    global _industry_cache
    _industry_cache = {}
    try:
        import baostock as bs
        import pandas as pd
        bs.login()
        rs = bs.query_stock_industry()
        rows = []
        while (rs.error_code == '0') & rs.next():
            rows.append(rs.get_row_data())
        df = pd.DataFrame(rows, columns=rs.fields)
        bs.logout()
        for _, row in df.iterrows():
            code = str(row.get("code", "")).strip()
            industry = str(row.get("industry", "")).strip()
            if code and industry:
                _industry_cache[code] = industry
    except Exception as e:
        print(f"  ⚠️ 行业分类加载失败: {e}")
