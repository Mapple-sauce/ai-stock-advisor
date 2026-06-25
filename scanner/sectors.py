"""板块分类与策略体系

A股不同板块有不同的运行规律, 需要差异化的因子权重。

板块分类基于 Baostock 行业代码 (GB/T 4754-2017 国民经济行业分类)。
每个板块配置独立的因子权重矩阵。

用法:
  from scanner.sectors import get_sector, get_weights

  sector = get_sector("600519")  # → "消费"
  weights = get_weights("600519", "low_position")
"""

from __future__ import annotations

from typing import Any

# ── 大类板块分组 ──
# 将细分行业代码映射到 7 大板块
SECTOR_MAP: dict[str, str] = {
    # === 消费 ===
    "C13": "消费",  # 农副食品
    "C14": "消费",  # 食品
    "C15": "消费",  # 酒、饮料
    "C16": "消费",  # 烟草
    "C17": "消费",  # 纺织
    "C18": "消费",  # 服装
    "C19": "消费",  # 皮革
    "C20": "消费",  # 木材
    "C21": "消费",  # 家具
    "C22": "消费",  # 造纸
    "C23": "消费",  # 印刷
    "C24": "消费",  # 文教
    "F51": "消费",  # 批发
    "F52": "消费",  # 零售
    "H61": "消费",  # 住宿
    "H62": "消费",  # 餐饮

    # === 科技 ===
    "C39": "科技",  # 计算机、通信、电子
    "C40": "科技",  # 仪器仪表
    "I63": "科技",  # 电信/软件
    "I64": "科技",  # 互联网
    "I65": "科技",  # 软件和信息技术
    "M74": "科技",  # 专业技术服务 (含芯片设计)

    # === 医药 ===
    "C27": "医药",  # 医药制造
    "Q83": "医药",  # 卫生

    # === 金融 ===
    "J66": "金融",  # 货币金融服务 (银行)
    "J67": "金融",  # 资本市场服务 (券商)
    "J68": "金融",  # 保险
    "J69": "金融",  # 其他金融

    # === 新能源/制造 ===
    "C38": "新能源",  # 电气机械 (含锂电/光伏)
    "C36": "新能源",  # 汽车制造 (含新能源车)

    # === 周期/资源 ===
    "B06": "周期",  # 煤炭
    "B07": "周期",  # 石油
    "B08": "周期",  # 黑色金属
    "B09": "周期",  # 有色金属
    "B10": "周期",  # 非金属矿
    "B11": "周期",  # 开采辅助
    "C25": "周期",  # 石化
    "C26": "周期",  # 化学原料
    "C28": "周期",  # 化纤
    "C29": "周期",  # 橡胶
    "C30": "周期",  # 非金属矿物
    "C31": "周期",  # 黑色金属冶炼
    "C32": "周期",  # 有色金属冶炼
    "C33": "周期",  # 金属制品
    "D44": "周期",  # 电力
    "D45": "周期",  # 燃气
    "K70": "周期",  # 房地产
    "K71": "周期",  # 房地产租赁

    # === 工业/基建 ===
    "C34": "工业",  # 通用设备
    "C35": "工业",  # 专用设备
    "C37": "工业",  # 铁路/船舶/航空
    "C41": "工业",  # 其他制造
    "C42": "工业",  # 废弃资源
    "C43": "工业",  # 金属制品/机械修理
    "E47": "工业",  # 房屋建筑
    "E48": "工业",  # 土木工程
    "E49": "工业",  # 建筑安装
    "E50": "工业",  # 建筑装饰
    "E51": "工业",  # 建筑其他
    "G53": "工业",  # 铁路运输
    "G54": "工业",  # 道路运输
    "G55": "工业",  # 水上运输
    "G56": "工业",  # 航空运输
    "G57": "工业",  # 管道运输
    "G58": "工业",  # 多式联运
    "G59": "工业",  # 仓储
    "M73": "工业",  # 研究和试验发展
    "N77": "工业",  # 生态保护
    "N78": "工业",  # 公共设施
}

# ── 板块默认映射 (未匹配到的) ──
_DEFAULT_SECTOR = "综合"

# ── 行业代码缓存 ──
_industry_cache: dict[str, str] | None = None


def get_sector(symbol: str) -> str:
    """获取股票所属板块

    Args:
        symbol: 股票代码 (如 "600519" 或 "sh.600519")

    Returns:
        板块名称: 消费/科技/医药/金融/新能源/周期/工业/综合
    """
    # 第一次调用时加载行业分类
    global _industry_cache
    if _industry_cache is None:
        _load_industries()

    # 标准化代码
    code = _normalize_code(symbol)

    if code in _industry_cache:
        industry_code = _industry_cache[code]
        # 取前3位匹配板块
        for prefix in (industry_code[:3], industry_code[:2]):
            if prefix in SECTOR_MAP:
                return SECTOR_MAP[prefix]

    return _DEFAULT_SECTOR


def get_industry(symbol: str) -> str:
    """获取股票的具体行业名称"""
    global _industry_cache
    if _industry_cache is None:
        _load_industries()
    return _industry_cache.get(_normalize_code(symbol), "未知")


def get_sector_weights(sector: str, mode: str) -> dict | None:
    """获取指定板块的因子权重"""
    weights_map = _SECTOR_WEIGHTS_LOW if mode == "low_position" else _SECTOR_WEIGHTS_MOMENTUM
    return weights_map.get(sector)


def _normalize_code(symbol: str) -> str:
    """标准化股票代码为 sh.600519 格式"""
    s = symbol.strip()
    if any(s.startswith(p) for p in ("sh.", "sz.", "bj.")):
        return s
    if any(s.startswith(p) for p in ("sh", "sz", "bj")):
        return f"{s[:2]}.{s[2:]}"
    if s.isdigit():
        prefix = "sh" if s.startswith(("6", "9")) else "sz"
        return f"{prefix}.{s}"
    return s


def _load_industries():
    """从 Baostock 加载行业分类数据"""
    global _industry_cache
    _industry_cache = {}

    try:
        import baostock as bs
        import pandas as pd

        bs.login()
        rs = rs = bs.query_stock_industry()
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


# ════════════════════════════════════════════════════════════
#  板块差异化权重矩阵
# ════════════════════════════════════════════════════════════
#
# 不同板块的核心驱动因素不同:
#   消费 → 基本面(品牌/ROE) > 技术面
#   科技 → 动量/情绪 > 基本面
#   金融 → 股息/估值 > 技术面
#   医药 → 研发/政策 > 技术面
#   周期 → 价格趋势 > 基本面
#   新能源 → 动量/政策 > 技术面
#

# ── 低位潜力模式 (各板块权重) ──
_SECTOR_WEIGHTS_LOW: dict[str, dict] = {
    "消费": {
        "ma_trend":      (0.10, "均线趋势", "趋势相对平稳"),
        "macd_signal":   (0.08, "MACD信号", ""),
        "rsi_position":  (0.08, "RSI位置", "消费股RSI看长周期"),
        "volume_ratio":  (0.05, "量价关系", "消费股量价相关性低"),
        "bb_position":   (0.10, "布林位置", "消费股布林带更有效"),
        "kdj_signal":    (0.05, "KDJ信号", ""),
        "price_position":(0.06, "价格位置", ""),
        "near_high_low": (0.04, "高低位置", ""),
        "daily_change":  (0.07, "当日涨幅", ""),
        "ma5_stability": (0.07, "MA5支撑", "消费股MA5有效"),
        # 消费股额外: 基本面权重高 (但需要数据)
        "_extra_note":   "消费股建议结合基本面Agent分析",
    },
    "科技": {
        "ma_trend":      (0.18, "均线趋势", "科技股趋势最重要"),
        "macd_signal":   (0.15, "MACD信号", "动量信号强烈"),
        "rsi_position":  (0.06, "RSI位置", ""),
        "volume_ratio":  (0.12, "量价关系", "科技股量价相关性高"),
        "bb_position":   (0.08, "布林位置", "科技股布林带波动大"),
        "kdj_signal":    (0.10, "KDJ信号", "KDJ在科技股有效"),
        "price_position":(0.05, "价格位置", ""),
        "near_high_low": (0.10, "高低位置", "科技股突破信号重要"),
        "daily_change":  (0.10, "当日涨幅", "科技股动量延续性强"),
        "ma5_stability": (0.06, "MA5支撑", ""),
    },
    "医药": {
        "ma_trend":      (0.12, "均线趋势", ""),
        "macd_signal":   (0.10, "MACD信号", ""),
        "rsi_position":  (0.10, "RSI位置", "医药股RSI反转有效"),
        "volume_ratio":  (0.06, "量价关系", ""),
        "bb_position":   (0.08, "布林位置", ""),
        "kdj_signal":    (0.05, "KDJ信号", ""),
        "price_position":(0.10, "价格位置", "医药股回调深度重要"),
        "near_high_low": (0.05, "高低位置", ""),
        "daily_change":  (0.04, "当日涨幅", ""),
        "ma5_stability": (0.10, "MA5支撑", "医药股技术支撑有效"),
        "_extra_note":   "医药股需关注政策面(集采/创新药审批)",
    },
    "金融": {
        "ma_trend":      (0.10, "均线趋势", "金融股趋势缓"),
        "macd_signal":   (0.08, "MACD信号", ""),
        "rsi_position":  (0.12, "RSI位置", "金融股RSI超卖有效"),
        "volume_ratio":  (0.05, "量价关系", "金融股量价相关低"),
        "bb_position":   (0.06, "布林位置", ""),
        "kdj_signal":    (0.05, "KDJ信号", ""),
        "price_position":(0.12, "价格位置", "金融股看PB,技术面辅助"),
        "near_high_low": (0.04, "高低位置", ""),
        "daily_change":  (0.04, "当日涨幅", ""),
        "ma5_stability": (0.08, "MA5支撑", ""),
        "_extra_note":   "金融股需结合基本面 (股息率/PB/NIM)",
    },
    "新能源": {
        "ma_trend":      (0.16, "均线趋势", "新能源趋势性强"),
        "macd_signal":   (0.14, "MACD信号", "动量信号确认"),
        "rsi_position":  (0.05, "RSI位置", ""),
        "volume_ratio":  (0.12, "量价关系", "量价配合重要"),
        "bb_position":   (0.07, "布林位置", ""),
        "kdj_signal":    (0.08, "KDJ信号", ""),
        "price_position":(0.05, "价格位置", ""),
        "near_high_low": (0.10, "高低位置", "突破信号重要"),
        "daily_change":  (0.12, "当日涨幅", "高动量延续"),
        "ma5_stability": (0.06, "MA5支撑", ""),
        "_extra_note":   "新能源需关注产业链上下游联动",
    },
    "周期": {
        "ma_trend":      (0.18, "均线趋势", "周期股趋势为王"),
        "macd_signal":   (0.15, "MACD信号", "周期确认信号延迟"),
        "rsi_position":  (0.08, "RSI位置", "周期股RSI可容忍高位"),
        "volume_ratio":  (0.10, "量价关系", "周期股放量确认"),
        "bb_position":   (0.05, "布林位置", ""),
        "kdj_signal":    (0.07, "KDJ信号", ""),
        "price_position":(0.06, "价格位置", ""),
        "near_high_low": (0.08, "高低位置", "突破确认重要"),
        "daily_change":  (0.10, "当日涨幅", "周期股追涨有效"),
        "ma5_stability": (0.05, "MA5支撑", ""),
        "_extra_note":   "周期股需关注商品价格/供需关系",
    },
    "工业": {
        "ma_trend":      (0.14, "均线趋势", ""),
        "macd_signal":   (0.10, "MACD信号", ""),
        "rsi_position":  (0.08, "RSI位置", ""),
        "volume_ratio":  (0.08, "量价关系", ""),
        "bb_position":   (0.06, "布林位置", ""),
        "kdj_signal":    (0.06, "KDJ信号", ""),
        "price_position":(0.08, "价格位置", ""),
        "near_high_low": (0.06, "高低位置", ""),
        "daily_change":  (0.05, "当日涨幅", ""),
        "ma5_stability": (0.07, "MA5支撑", ""),
    },
    "综合": {
        "ma_trend":      (0.14, "均线趋势", "默认配置"),
        "macd_signal":   (0.12, "MACD信号", "默认配置"),
        "rsi_position":  (0.08, "RSI位置", ""),
        "volume_ratio":  (0.10, "量价关系", ""),
        "bb_position":   (0.06, "布林位置", ""),
        "kdj_signal":    (0.05, "KDJ信号", ""),
        "price_position":(0.08, "价格位置", ""),
        "near_high_low": (0.06, "高低位置", ""),
        "daily_change":  (0.05, "当日涨幅", ""),
        "ma5_stability": (0.05, "MA5支撑", ""),
    },
}

# ── 追高跟强模式 ──
_SECTOR_WEIGHTS_MOMENTUM: dict[str, dict] = {
    "科技": {
        "ma_trend":      (0.18, "均线趋势", "科技追高看趋势"),
        "bb_position":    (0.12, "布林位置", ""),
        "kdj_signal":    (0.12, "KDJ信号", "科技KDJ高位有效"),
        "volume_ratio":   (0.10, "量价关系", "科技放量确认"),
        "macd_signal":    (0.14, "MACD信号", "动量延续信号"),
        "rsi_position":   (0.08, "RSI位置", "科技可承受高RSI"),
        "daily_change":   (0.10, "当日涨幅", "追涨有效"),
        "ma5_stability":  (0.05, "MA5支撑", ""),
        "price_position": (0.05, "价格位置", ""),
        "near_high_low":  (0.06, "高低位置", "突破确认"),
    },
    "新能源": {
        "ma_trend":      (0.16, "均线趋势", ""),
        "bb_position":    (0.10, "布林位置", ""),
        "kdj_signal":    (0.10, "KDJ信号", ""),
        "volume_ratio":   (0.14, "量价关系", "放量突破新能源"),
        "macd_signal":    (0.13, "MACD信号", ""),
        "rsi_position":   (0.09, "RSI位置", ""),
        "daily_change":   (0.12, "当日涨幅", "强者恒强"),
        "ma5_stability":  (0.05, "MA5支撑", ""),
        "price_position": (0.06, "价格位置", ""),
        "near_high_low":  (0.05, "高低位置", ""),
    },
    "消费": {
        "ma_trend":      (0.12, "均线趋势", ""),
        "bb_position":    (0.10, "布林位置", ""),
        "kdj_signal":    (0.08, "KDJ信号", ""),
        "volume_ratio":   (0.10, "量价关系", ""),
        "macd_signal":    (0.10, "MACD信号", ""),
        "rsi_position":   (0.10, "RSI位置", "消费不追超买"),
        "daily_change":   (0.06, "当日涨幅", "消费偏稳健"),
        "ma5_stability":  (0.10, "MA5支撑", "消费MA5支撑强"),
        "price_position": (0.08, "价格位置", ""),
        "near_high_low":  (0.06, "高低位置", ""),
    },
    "周期": {
        "ma_trend":      (0.18, "均线趋势", "周期趋势延续性强"),
        "bb_position":    (0.08, "布林位置", ""),
        "kdj_signal":    (0.08, "KDJ信号", ""),
        "volume_ratio":   (0.14, "量价关系", "周期放量加速"),
        "macd_signal":    (0.12, "MACD信号", ""),
        "rsi_position":   (0.10, "RSI位置", "周期RSI可高"),
        "daily_change":   (0.12, "当日涨幅", "趋势加速"),
        "ma5_stability":  (0.06, "MA5支撑", ""),
        "price_position": (0.06, "价格位置", ""),
        "near_high_low":  (0.06, "高低位置", ""),
    },
}
# 未定义的板块使用默认综合配置
_SECTOR_WEIGHTS_LOW.setdefault("综合", _SECTOR_WEIGHTS_LOW["综合"])
_SECTOR_WEIGHTS_MOMENTUM.setdefault("综合", _SECTOR_WEIGHTS_MOMENTUM.get("消费", _SECTOR_WEIGHTS_LOW["综合"]))


def get_sector_weighted_score(entry_price: float, ind: dict, mode: str, sector: str) -> float:
    """根据板块返回加权评分

    使用对应板块的因子权重计算评分
    """
    weights = get_sector_weights(sector, mode)
    if weights is None:
        weights = _SECTOR_WEIGHTS_LOW.get("综合", {})

    from scanner.screener import (
        score_ma_trend, score_macd_signal, score_rsi_position,
        score_volume_ratio, score_bb_position, score_kdj_signal,
        score_price_position, score_near_high_low, score_daily_change,
        score_ma5_stability,
    )

    fs = {
        "ma_trend": score_ma_trend(ind, mode)[0],
        "macd_signal": score_macd_signal(ind, mode)[0],
        "rsi_position": score_rsi_position(ind, mode)[0],
        "volume_ratio": score_volume_ratio(ind, mode)[0],
        "bb_position": score_bb_position(ind, mode)[0],
        "kdj_signal": score_kdj_signal(ind, mode)[0],
        "price_position": score_price_position(ind, mode, entry_price)[0],
        "near_high_low": score_near_high_low(ind, mode)[0],
        "daily_change": score_daily_change(ind, {"price": entry_price, "change_pct": 0}, mode)[0],
        "ma5_stability": score_ma5_stability(ind, mode) if "ma5_stability" in weights else (0, ""),
    }

    tw = ws = 0
    for f, (w, _, _) in weights.items():
        if f.startswith("_"):
            continue
        if f in fs:
            ws += w * fs[f] * 100
            tw += w

    raw = (ws / tw + 50) if tw else 50
    return max(0, min(100, 100 - raw))
