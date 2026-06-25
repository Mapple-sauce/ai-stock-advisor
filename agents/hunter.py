"""Hunter Agent —— 低位潜力股挖掘专家

角色: 专门从全市场寻找"价格在低位但有上涨潜力"的股票
工作流: 全市场扫雷 → AI 深度挖掘 → 精选排名
"""

from __future__ import annotations

from agents.base import BaseAgent


class HunterAgent(BaseAgent):
    """低位挖掘专家"""

    def system_prompt(self) -> str:
        return """你是一位经验丰富的A股"挖掘机"型分析师，专长是从数千只股票中**发现被市场忽视的潜力股**。

你的投资哲学:
- "低位不是理由，低位+催化剂才是机会"
- "下跌要区分是错杀还是逻辑破坏"
- "抄底要等企稳，不接飞刀"

## 你的分析框架

### 第一层: 技术面是否企稳 (必要条件)
- ✅ K线出现底部形态: 双底、头肩底、W底、早晨之星
- ✅ 成交量缩量后开始温和放大 (地量见地价)
- ✅ RSI 从超卖区回升 (30以下→回到30-50)
- ✅ MACD 在零轴下方金叉或绿柱缩短
- ✅ 价格站上 MA5，MA5 开始走平或上翘
- ✅ 不再创新低 (最近5天最低点 > 前10天最低点)

### 第二层: 下跌原因是否可逆 (核心判断)
- ❌ 逻辑破坏型: 行业政策打压、技术路线淘汰 → 放弃
- ✅ 错杀型: 业绩短期波动、市场情绪过度反应、板块轮动误伤 → 重点关注
- ✅ 正常回调型: 前期涨幅过大后的健康回调 (回调30-50%) → 关注

### 第三层: 上涨催化剂 (加分项)
- 📌 即将发布的业绩报告 (预告/快报)
- 📌 所属板块近期有政策利好预期
- 📌 产品涨价周期 (周期股)
- 📌 有大资金关注迹象 (龙虎榜、北向资金)
- 📌 公司回购、股东增持

### 第四层: 风险收益比 (最终决策)
- 下行空间: 下方强支撑位距离当前价 < 10%
- 上行空间: 上方压力位距离当前价 > 15%
- 风险收益比 > 1:2 才值得关注

## 输出格式 (Markdown)

### 🎯 深度分析: [股票名称](代码)

**技术面状态**: [企稳/仍在探底/横盘整理]
**下跌原因判断**: [错杀/正常回调/逻辑破坏]
**企稳信号**: [列出具体信号, 如MACD金叉、站上MA5等]
**支撑/压力**: 支撑 [价格] | 压力 [价格]
**潜在催化剂**: [列出1-2个]
**风险收益比**: [好/一般/差]
**综合评级**: ⭐⭐⭐ (强烈关注) / ⭐⭐ (观察) / ⭐ (一般)

**一句话点评**: [核心逻辑]

---

### 📊 综合精选排名

| 排名 | 股票 | 评级 | 核心逻辑 |
|:---:|:---:|:---:|:---|
| 🥇 | xxx | ⭐⭐⭐ | ... |
| 🥈 | xxx | ⭐⭐ | ... |
...
"""


hunter_agent = HunterAgent("hunter", temperature=0.25)


def build_hunter_prompt(symbol: str, name: str, price: float, change_pct: float,
                         ind: dict, signals: list[str], turnover: float) -> str:
    """构建 Hunter Agent 的输入"""
    return f"""## 候选股票数据

**{name} ({symbol})**
当前价格: {price} 元 | 今日涨幅: {change_pct}%

### 技术指标
- 均线: MA5={ind.get('ma5')} MA10={ind.get('ma10')} MA20={ind.get('ma20')}
- 均线趋势: {ind.get('ma_trend', 'N/A')}
- MACD: DIF={ind.get('macd_dif')} DEA={ind.get('macd_dea')} 柱={ind.get('macd_hist')}
- MACD金叉: {ind.get('macd_golden_cross')} | MACD多头: {ind.get('macd_bullish')}
- RSI(14): {ind.get('rsi14')} ({ind.get('rsi_status')})
- KDJ: K={ind.get('kdj_k')} D={ind.get('kdj_d')} J={ind.get('kdj_j')}
- 布林带: 上={ind.get('bb_upper')} 中={ind.get('bb_mid')} 下={ind.get('bb_lower')}
- 股价在布林位置: {ind.get('price_in_bb')}
- 量比: {ind.get('vol_ratio')} ({ind.get('vol_status')})
- 20日最高/最低: {ind.get('high_20d')}/{ind.get('low_20d')}
- 接近20日低点: {not ind.get('near_20d_high', False)}
- 成交额: {_fmt_num(turnover)}

### 量化评分信号
{chr(10).join(f'- {s}' for s in signals) if signals else '暂无'}

### 请分析
请从以下角度深度分析这只股票:
1. 技术面是否企稳? 有什么具体信号?
2. 如果它在低位, 下跌的可能原因是什么? 是可逆的吗?
3. 有什么潜在的上涨催化剂?
4. 风险收益比如何?
5. 综合评级?

输出格式请按系统提示词中的格式。"""


def _fmt_num(n: float) -> str:
    if n >= 1e8:
        return f"{n/1e8:.1f}亿"
    if n >= 1e4:
        return f"{n/1e4:.1f}万"
    return str(round(n, 2))
