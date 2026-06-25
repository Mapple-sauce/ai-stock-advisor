"""权重优化器 —— 自动尝试不同权重组合, 找到最优配置

运行: python -m backtest.weight_optimizer

流程:
  1. 生成多组随机权重配置
  2. 在多个历史时间段回测
  3. 评分每组配置 (按正确率+多空差)
  4. 输出最优配置
"""

from __future__ import annotations

import copy
import itertools
import json
import random
import sys
import time

from backtest.optimizer import backtest_factor_weights

# ── 测试用股票池 (不同板块, 不同市值, 分散) ──
TEST_STOCKS = [
    "600519",  # 贵州茅台 - 消费龙头
    "300750",  # 宁德时代 - 新能源龙头
    "000001",  # 平安银行 - 银行
    "300308",  # 中际旭创 - AI算力
    "002594",  # 比亚迪 - 新能源车
    "600036",  # 招商银行 - 银行
    "600276",  # 恒瑞医药 - 医药
    "002371",  # 北方华创 - 半导体设备
    "601318",  # 中国平安 - 保险
    "000333",  # 美的集团 - 家电
    "002415",  # 海康威视 - 安防
    "601012",  # 隆基绿能 - 光伏
    "600030",  # 中信证券 - 券商
    "300124",  # 汇川技术 - 工业自动化
    "688981",  # 中芯国际 - 芯片
]

# ── 回测日期: 随机抽取 (避免连续月份过拟合) ──
RANDOM_DATES = [
    "2024-01-15", "2024-02-19", "2024-03-18", "2024-04-15",
    "2024-05-20", "2024-06-17", "2024-07-15", "2024-08-19",
    "2024-09-16", "2024-10-21", "2024-11-18", "2024-12-16",
    "2025-01-13", "2025-02-17", "2025-03-17", "2025-04-14",
    "2025-05-19", "2025-06-16", "2025-07-14", "2025-08-18",
    "2025-09-15", "2025-10-20", "2025-11-17", "2025-12-15",
    "2026-01-12", "2026-02-17", "2026-03-16", "2026-04-13",
    "2026-05-18", "2026-06-01",
]

# 多空差权重: 综合考虑正确率、多空差、相关性
def score_config(result: dict) -> float:
    """综合评分一个配置的好坏"""
    if "error" in result:
        return -999

    accuracy = result.get("accuracy_pct", 0)
    spread = result.get("spread", 0)
    correlation = result.get("score_correlation", 0)
    total = result.get("total_tests", 0)

    if total < 30:
        return -500  # 测试样本太少

    # 综合评分 = 正确率优势 + 多空差 + 相关性 + 样本量奖励
    acc_score = (accuracy - 45) * 0.5  # 超过45%算正分
    spread_score = spread * 1.0        # 每1%多空差=1分
    corr_score = correlation * 20      # 相关性*20
    size_bonus = min(total / 100, 1.0)  # 样本越多越可信

    total_score = acc_score + spread_score + corr_score + size_bonus
    return round(total_score, 2)


def run_optimization(
    symbols: list[str] | None = None,
    dates: list[str] | None = None,
    mode: str = "low_position",
    hold_days: int = 20,
    max_configs: int = 30,
    top_k: int = 5,
):
    """运行权重优化

    Args:
        symbols: 测试股票池 (None=使用默认)
        dates: 回测日期 (None=使用默认)
        mode: 扫描模式 (low_position / momentum)
        hold_days: 持有天数
        max_configs: 最多测试的配置数
        top_k: 返回前k个最优配置
    """
    if symbols is None:
        symbols = TEST_STOCKS
    if dates is None:
        dates = RANDOM_DATES

    print(f"{'='*70}")
    print(f"  🔬 权重优化器启动")
    print(f"  {'='*70}")
    print(f"  📊 股票池: {len(symbols)} 只  |  回测日期: {len(dates)} 天")
    print(f"  ⚙️  模式: {mode}  |  持有: {hold_days} 天")
    print(f"  🎯 尝试配置数: {max_configs}")
    print(f"{'='*70}\n")

    # 生成不同的权重配置
    configs = _generate_weight_configs(max_configs)
    print(f"  生成了 {len(configs)} 种权重配置, 开始回测...\n")

    results = []
    for i, (name, weights) in enumerate(configs, 1):
        print(f"  [{i}/{len(configs)}] {name}...", end=" ", flush=True)
        start = time.time()

        result = backtest_factor_weights(
            symbols=symbols[:10],  # 每轮选10只加速
            dates=dates[:15],       # 选前15个日期
            weights=weights,
            mode=mode,
            hold_days=hold_days,
        )

        elapsed = time.time() - start
        if "error" in result:
            print(f"❌ {result['error']}")
            continue

        config_score = score_config(result)
        results.append((config_score, name, weights, result))
        print(f"正确率:{result['accuracy_pct']:.1f}% "
              f"多空差:{result['spread']:+.2f}% "
              f"score:{config_score:.1f} "
              f"({elapsed:.0f}s)")

    # 排序
    results.sort(key=lambda x: x[0], reverse=True)

    print(f"\n{'='*70}")
    print(f"  📊 优化结果 TOP {top_k}")
    print(f"{'='*70}\n")

    for i, (score, name, weights, result) in enumerate(results[:top_k], 1):
        print(f"  {'─'*50}")
        print(f"  [{i}] {name}")
        print(f"      综合评分: {score}")
        print(f"      正确率: {result['accuracy_pct']}%")
        print(f"      多空差: {result['spread']:+.2f}% 推荐买({result['buy_count']}) vs 回避({result['avoid_count']})")
        print(f"      相关性: {result['score_correlation']}")
        print(f"      平均收益: {result['avg_return']:+.2f}%  (测试{result['total_tests']}次)")
        print(f"      权重配置:")
        for factor, (w, desc, _) in sorted(weights.items(), key=lambda x: x[1][0], reverse=True):
            print(f"        {factor:20s} = {w:5.2f}  ({desc})")

    # 横向对比
    print(f"\n  {'='*50}")
    print(f"  📈 横向对比")
    print(f"  {'='*50}")
    print(f"  {'配置名':<20} {'正确率':<8} {'多空差':<10} {'相关性':<8} {'测试数':<8}")
    print(f"  {'─'*54}")
    for score, name, _, result in results[:top_k]:
        print(f"  {name:<20} {result['accuracy_pct']:<8.1f}% "
              f"{result['spread']:<+9.2f}% {result['score_correlation']:<8.3f} "
              f"{result['total_tests']:<8}")

    # 输出最佳配置 (可直接复制到 screener.py)
    print(f"\n  {'='*50}")
    print(f"  📝 最优权重配置 (可复制到 screener.py)")
    print(f"  {'='*50}\n")

    if results:
        best_score, best_name, best_weights, best_result = results[0]
        print(f"  # 最佳配置: {best_name}")
        print(f"  # 正确率: {best_result['accuracy_pct']}%  多空差: {best_result['spread']:+.2f}%")
        print(f"  WEIGHTS_BEST = {{")
        for factor, (w, desc, note) in sorted(best_weights.items(), key=lambda x: x[1][0], reverse=True):
            print(f"      \"{factor}\": ({w:.2f}, \"{desc}\", \"{note}\"),")
        print(f"  }}")

    print(f"\n  ✅ 优化完成!\n")
    return results


def _generate_weight_configs(n: int) -> list[tuple[str, dict]]:
    """生成不同的权重配置

    策略:
      1. 等权配置 (baseline)
      2. 随机扰动配置 (在等权基础上加随机扰动)
      3. 极端配置 (某些因子极端高/低)
    """
    # 因子列表
    factors = {
        "ma_trend":      ("均线趋势", "趋势指标"),
        "macd_signal":   ("MACD信号", "动量指标"),
        "rsi_position":  ("RSI位置", "反转指标"),
        "volume_ratio":  ("量价关系", "资金指标"),
        "bb_position":   ("布林位置", "波动指标"),
        "kdj_signal":    ("KDJ信号", "辅助指标"),
        "price_position":("价格位置", "趋势指标"),
        "near_high_low": ("高低位置", "突破指标"),
        "daily_change":  ("当日涨幅", "动能指标"),
        "ma5_stability": ("MA5支撑", "支撑指标"),
    }

    configs = []
    seed = 42

    # 1. 等权配置 (baseline)
    equal_w = {f: (1.0 / len(factors), name, note) for f, (name, note) in factors.items()}
    configs.append(("等权基线", equal_w))

    # 2. 当前默认配置
    default_weights = {
        "ma_trend": (0.14, "均线趋势", "趋势指标"),
        "macd_signal": (0.10, "MACD信号", "动量指标"),
        "rsi_position": (0.08, "RSI位置", "反转指标"),
        "volume_ratio": (0.10, "量价关系", "资金指标"),
        "bb_position": (0.05, "布林位置", "波动指标"),
        "kdj_signal": (0.05, "KDJ信号", "辅助指标"),
        "price_position": (0.08, "价格位置", "趋势指标"),
        "near_high_low": (0.06, "高低位置", "突破指标"),
        "daily_change": (0.04, "当日涨幅", "动能指标"),
        "ma5_stability": (0.05, "MA5支撑", "支撑指标"),
    }
    configs.append(("当前默认", default_weights))

    # 3. 趋势优先 (均线+MACD权重翻倍)
    trend_favored = copy.deepcopy(equal_w)
    for f in ["ma_trend", "macd_signal", "price_position"]:
        w, name, note = trend_favored[f]
        trend_favored[f] = (w * 2.5, name, note)
    _normalize(trend_favored)
    configs.append(("趋势优先", trend_favored))

    # 4. 反转优先 (RSI+布林权重翻倍)
    reversal_favored = copy.deepcopy(equal_w)
    for f in ["rsi_position", "bb_position", "ma5_stability"]:
        w, name, note = reversal_favored[f]
        reversal_favored[f] = (w * 2.5, name, note)
    _normalize(reversal_favored)
    configs.append(("反转优先", reversal_favored))

    # 5. 量价优先 (量比+涨幅权重翻倍)
    volume_favored = copy.deepcopy(equal_w)
    for f in ["volume_ratio", "daily_change", "near_high_low"]:
        w, name, note = volume_favored[f]
        volume_favored[f] = (w * 2.5, name, note)
    _normalize(volume_favored)
    configs.append(("量价优先", volume_favored))

    # 6-15. 随机配置 (带不同随机种子)
    rng = random.Random(seed)
    for i in range(10):
        w = {f: (rng.uniform(0.5, 2.0), name, note) for f, (name, note) in factors.items()}
        _normalize(w)
        configs.append((f"随机{i+1:02d}", w))

    # 16-25. 极端配置 (一个因子权重极高)
    factor_list = list(factors.keys())
    for i, dominant_factor in enumerate(factor_list[:10]):
        extreme_w = {f: (0.3, name, note) for f, (name, note) in factors.items()}
        dominant_name = factors[dominant_factor][0]
        extreme_w[dominant_factor] = (3.0, dominant_name, factors[dominant_factor][1])
        _normalize(extreme_w)
        configs.append((f"极端-{dominant_name}", extreme_w))

    # 截取前n个
    return configs[:n]


def _normalize(weights: dict) -> None:
    """归一化权重, 使总和为1.0"""
    total = sum(w for w, _, _ in weights.values())
    if total == 0:
        return
    for f in weights:
        w, name, note = weights[f]
        weights[f] = (w / total, name, note)


if __name__ == "__main__":
    run_optimization()
