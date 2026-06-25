# 🏗️ AI Stock Advisor 架构文档

> 本文档详细记录系统架构、各 Agent 分工、工作流程和影响因素权重体系。
> 维护者: 修改代码前请先阅读本文档确保理解整体架构。

---

## 📋 目录

1. [整体架构](#1-整体架构)
2. [多 Agent 分工](#2-多-agent-分工)
3. [工作流详解](#3-工作流详解)
4. [影响因素权重体系](#4-影响因素权重体系)
5. [数据依赖](#8-数据依赖)
6. [多因子评分模型](#6-多因子评分模型)
7. [业界参考模型](#7-业界参考模型)
8. [扩展指南](#9-扩展指南)
9. [回测验证](#10-回测验证)

---

## 1. 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                     main.py (入口)                        │
│     buy │ sell │ scan │ low │ mom │ hunt │ backtest      │
└────┬─────────────────────────────────────────────────┬───┘
     │                                                 │
     ▼                                                 ▼
┌──────────────────────┐              ┌──────────────────────────┐
│   chief/              │              │    data/                  │
│   orchestrator.py     │◄─────────────│    market.py              │
│   (流程编排器)         │   调用       │    fundamentals.py        │
│                      │              │    indicators.py          │
│   __init__.py         │              │    news.py                │
│   (Chief Agent 决策)  │              │                          │
└──────┬───────────────┘              └──────────────────────────┘
       │
       │ 协调 4 + 1 个 Agent
       ▼
┌──────────────────────────────────────────────────────────────┐
│  agents/                                                     │
│  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │Technical │  │Fundamental│  │Sentiment  │  │Risk       │  │
│  │技术分析   │  │基本面分析  │  │舆情分析   │  │风险评估   │  │
│  └──────────┘  └───────────┘  └───────────┘  └───────────┘  │
│  ┌──────────┐  ┌───────────┐                                │
│  │Scanner   │  │Hunter     │                                │
│  │市场扫描   │  │低位挖掘   │                                │
│  └──────────┘  └───────────┘                                │
└──────────────────────────────────────────────────────────────┘
```

### 核心设计原则

1. **每层职责分离**: 数据层 → Agent分析层 → 编排决策层
2. **多Agent独立分析**: 每个 Agent 从自己的专业视角分析相同的数据
3. **Chief 总决策**: 综合所有专业意见, 类似真实投资团队
4. **低随机性**: 固定 seed + 低 temperature, 保证结果可复现

---

## 2. 多 Agent 分工

### 2.1 Chief Agent (首席投资官) 👑

| 项目 | 说明 |
|---|---|
| **文件** | `chief/__init__.py` |
| **temperature** | 0.05 (接近确定性) |
| **seed** | 42 |
| **输出格式** | **JSON** (结构化决策) |
| **LLM调用方式** | `call_structured()` |

**职责**:
- 综合 4 位专业分析师的意见
- 识别各报告中的共识与分歧
- 对分歧点做出独立判断
- 给出最终决策 (结构化JSON)

**决策规则**:
- 买入: 至少 3/4 维度评分 > 5 分才买入, 任一维度 < 3 分一票否决
- 卖出: 技术面走坏或重大利空果断建议卖出
- 保护本金优先

**输出 JSON Schema** (`BUY_DECISION_SCHEMA`):
```json
{
  "final_score": 7,           // 1-10 综合评分
  "action": "推荐买入",        // 强烈推荐/推荐买入/观望/回避
  "confidence": "中",         // 高/中/低
  "entry_upper": 15.8,       // 买入上限
  "entry_lower": 15.2,       // 买入下限
  "stop_loss": 14.5,         // 止损位
  "position_suggestion": "半仓", // 仓位建议
  "time_horizon": "中期",     // 持有周期
  "key_reason": "...",        // 核心决策理由
  "risks_to_watch": []        // 风险监控
}
```

---

### 2.2 Technical Analyst (技术分析专家) 📊

| 项目 | 说明 |
|---|---|
| **文件** | `agents/technical.py` |
| **temperature** | 0.1 |
| **分析用时** | ~5-8 秒/只 (API调用) |
| **系统提示词** | ~800 tokens |

**分析维度**:
| 维度 | 权重 | 关键指标 |
|---|---|---|
| 趋势判断 | 高 | 均线排列 (MA5/MA10/MA20/MA60) |
| 动量指标 | 高 | MACD金叉/死叉, MACD柱方向 |
| 超买超卖 | 中 | RSI(14), KDJ |
| 通道位置 | 中 | 布林带上下轨 |
| 量价关系 | 高 | 量比, 量价配合 |
| 形态识别 | 中 | 突破/双底/头肩 |

**评分规则**:
```
8-10分: 强势上涨, 多头排列, 量价配合好
5-7分:  震荡偏多, 有待确认
3-4分:  偏弱, 建议观望
1-2分:  明显走坏, 强烈回避
```

---

### 2.3 Fundamental Analyst (基本面分析专家) 📋

| 项目 | 说明 |
|---|---|
| **文件** | `agents/fundamental.py` |
| **temperature** | 0.1 |

**分析维度**:
| 维度 | 权重 | 关键指标 |
|---|---|---|
| 估值水平 | 高 | PE/PB 行业分位, 历史分位 |
| 盈利能力 | 高 | ROE, 毛利率, 净利率 |
| 成长性 | 高 | 营收增速, 净利润增速 |
| 财务健康 | 中 | 资产负债率, 现金流 |

> ⚠️ 当前限制: 数据来源为 akshare, 财务数据更新有延迟。
> 部分分析可能因缺少数据而简略。

---

### 2.4 Sentiment Analyst (舆情分析专家) 📰

| 项目 | 说明 |
|---|---|
| **文件** | `agents/sentiment.py` |
| **temperature** | 0.1 |

**分析维度**:
| 维度 | 权重 | 来源 |
|---|---|---|
| 新闻情绪 | 高 | akshare 股票新闻 |
| 板块热度 | 中 | 板块联动效应 |
| 事件影响 | 高 | 业绩预告/重组/监管 |
| 风险事件 | 高 | 利空消息/黑天鹅 |

> ⚠️ 当前限制: 新闻来源有限。
> 未来扩展: Tavily API / SerpAPI 增强。

---

### 2.5 Risk Analyst (风险评估专家) ⚠️

| 项目 | 说明 |
|---|---|
| **文件** | `agents/risk.py` |
| **temperature** | 0.1 |

**分析维度**:
| 维度 | 权重 | 关注点 |
|---|---|---|
| 技术风险 | 高 | 高位超买, 顶背离, 量价背离 |
| 基本面风险 | 中 | 估值泡沫, 业绩下滑 |
| 市场风险 | 中 | 大盘系统性风险, 板块轮动 |
| 流动性风险 | 低 | 换手率, 成交量 |
| 关键价位 | 高 | 支撑位/压力位 |

**输出**: 止损建议 + 仓位建议

---

### 2.6 Scanner Agent (市场扫描) 🔍

| 项目 | 说明 |
|---|---|
| **文件** | `agents/scanner.py` |
| **temperature** | 0.1 |
| **职责** | 从候选股中精选 TOP 5 |

**三种扫描模式**:
| 模式 | 命令 | 侧重 |
|---|---|---|
| 涨幅榜 | `scan` | 今日涨幅前列 |
| 低位潜力 | `low` | 价格低位+企稳信号 |
| 追高跟强 | `mom` | 上升趋势+量价配合 |

---

### 2.7 Hunter Agent (低位挖掘专家) 💎

| 项目 | 说明 |
|---|---|
| **文件** | `agents/hunter.py` |
| **temperature** | 0.1 |
| **分析用时** | ~15-25 秒/只 (含API) |

**四层分析框架**:
```
第一层: 技术面是否企稳 (必要条件)
第二层: 下跌原因是否可逆 (核心判断)
第三层: 上涨催化剂 (加分项)
第四层: 风险收益比 (最终决策)
```

**完整工作流**:
```
全市场 5000+ 股票
    │ 新浪行情API
    ▼
过滤: ST/北交所/低价/低成交 → ~500 只
    │
    ▼
按成交额 TOP 80 → Baostock 批量下载 K 线
    │
    ▼
计算技术指标 → 量化评分系统打分
    │
    ▼
AI 深度分析 TOP 10 (每个股票一次API)
    ├─ 技术面企稳?  (MACD/RSI/均线)
    ├─ 下跌原因?    (错杀/回调/逻辑破坏)
    ├─ 催化剂?      (业绩/政策/资金)
    └─ 风险收益比?  (下行空间 vs 上行空间)
    │
    ▼
Hunter Agent 综合排名 → 推送报告
```

**判断标准**:
| 因素 | 买入加分 | 减分/放弃 |
|---|---|---|
| 下跌原因 | 错杀/正常回调 | 逻辑破坏/行业出清 |
| RSI位置 | 30-50 (超卖回升) | <20 (仍在探底) |
| 均线 | 站上MA5, MA5走平 | 均线空头发散 |
| 成交量 | 地量后温和放大 | 继续缩量 |
| 催化剂 | 业绩/政策/资金明确 | 无明显催化 |
| 风险收益比 | >1:2 | <1:1 |

---

## 3. 工作流详解

### 3.1 买入分析工作流

```
命令: python main.py buy
路径: main.py → orchestrator.analyze_buy(symbol)

for each symbol in STOCK_LIST:
    1. get_realtime_quote()     ← 新浪行情
    2. get_kline()              ← Baostock K线
    3. compute_indicators()     ← 指标计算 (纯Python)
    4. get_stock_news()         ← akshare 新闻
    5. technical_analyst.call() ← Agent① 技术分析
    6. fundamental_analyst.call() ← Agent② 基本面分析
    7. sentiment_analyst.call() ← Agent③ 舆情分析
    8. risk_analyst.call()      ← Agent④ 风险评估
    9. chief_agent.decide_buy() ← Chief 总决策
    10. format_report() + send() ← 报告 + 推送
```

### 3.2 卖出分析工作流

```
命令: python main.py sell
路径: main.py → orchestrator.analyze_sell(holding)

for each holding in portfolio.json:
    1. get_realtime_quote()
    2. get_kline()
    3. compute_indicators()
    4. get_stock_news()
    5. update_price() ← 更新持仓盈亏
    6. technical_analyst.call() ← Agent①
    7. sentiment_analyst.call() ← Agent③ (无基本面)
    8. risk_analyst.call()      ← Agent④
    9. chief_agent.decide_sell() ← Chief
    10. format_report() + send()
```

### 3.3 低位挖掘工作流 (Hunter)

```
命令: python main.py hunt
路径: main.py → orchestrator.hunter_deep_dive()

Phase 1: 量化筛选 (纯代码, 9秒)
  ├─ 新浪全市场 5000+
  ├─ 过滤 ST/北交所/低价/低流动性
  ├─ Baostock 80只 K线 + 指标计算
  └─ 量化打分排序

Phase 2: AI 深度分析 (~2-3分钟)
  ├─ TOP 10 每只逐一分析
  │  ├─ 技术面是否企稳
  │  ├─ 下跌原因判断
  │  ├─ 催化剂识别
  │  └─ 风险收益比评估
  └─ Hunter 综合排名

Phase 3: 报告输出
  ├─ 综合精选排名表格
  └─ 每只股票详细分析报告
```

---

## 4. 影响因素权重体系

### 4.1 综合权重矩阵 (影响股价的因素)

> 以下权重基于 A 股市场特征和历史回测经验设定。
> 各权重之和 = 100%

| 大类 | 权重 | 子因素 | 子权重 | 说明 |
|---|---|---|---|---|
| **📊 技术面** | **35%** | 均线趋势 | 12% | 多头/空头/缠绕, 最重要 |
| | | MACD | 8% | 金叉/死叉, 柱线变化 |
| | | RSI动能 | 5% | 超买超卖区间 |
| | | 量价关系 | 7% | 放量/缩量, 量价配合 |
| | | 布林带位置 | 3% | 通道位置, 开口方向 |
| **📋 基本面** | **20%** | 估值PE/PB | 8% | 行业分位, 历史分位 |
| | | ROE盈利 | 5% | 盈利能力, 稳定性 |
| | | 成长性 | 7% | 营收/利润增速 |
| **📰 舆情** | **15%** | 新闻情绪 | 6% | 正面/负面/中性 |
| | | 板块热度 | 5% | 所属板块近期表现 |
| | | 事件驱动 | 4% | 业绩/政策/公告 |
| **💰 资金面** | **15%** | 主力资金 | 6% | 大单净流入/流出 |
| | | 北向资金 | 4% | 外资流向 |
| | | 成交量能 | 5% | 成交额放大/缩小 |
| **🏛️ 宏观** | **10%** | 大盘走势 | 5% | 上证/创业板走势 |
| | | 政策面 | 3% | 行业政策, 货币 |
| | | 利率汇率 | 2% | 流动性环境 |
| **⚠️ 风险** | **5%** | 下行风险 | 3% | 支撑位距离 |
| | | 流动性风险 | 2% | 换手率/成交量 |

> ⚠️ 当前实现中已覆盖: 技术面(35%) + 基本面(20%) + 舆情(15%) + 风险(5%) = **75%**
> 
> 🚧 尚未实现 (未来扩展): 资金面(15%) + 宏观(10%)

### 4.2 量化评分计算公式

```
总评分 = Σ(因素得分 × 因素权重)

因素得分规则:
  +1.0 = 强利好信号 (如 MACD 金叉)
  +0.5 = 利好信号 (如 量比1.5)
   0.0 = 中性 (如 RSI在45-55)
  -0.5 = 利空信号 (如 均线死叉)
  -1.0 = 强利空信号 (如 放量下跌)
```

### 4.3 当前评分实现 (`scanner/screener.py`)

#### 低位潜力评分 (满分100)
| 因素 | 最高分 | 规则 |
|---|---|---|
| 价格与MA20关系 | 25 | 越靠近MA20越好 |
| RSI位置 | 20 | 30-50最佳 |
| 成交量变化 | 15 | 0.8-1.8倍温和放量 |
| MACD信号 | 20 | 金叉加分, 红柱加分 |
| 均线形态 | 10 | 站上MA5加分 |
| 当日涨幅 | 10 | -3%~+3%窄幅 |

#### 追高跟强评分 (满分100)
| 因素 | 最高分 | 规则 |
|---|---|---|
| 价格与MA20 | 20 | 在MA20上方加分 |
| RSI偏强 | 25 | 55-75最佳, >75减分 |
| 成交量放大 | 20 | 1.5x以上放量 |
| MACD | 30 | 多头+15, 金叉+15 |
| 均线排列 | 15 | 多头排列加分 |
| 接近20日高 | 10 | 突破形态加分 |
| 涨幅适中 | 15 | 3-7%最佳 |
| 换手率 | -10 | >20%减分 |

---

### 6.2 权重量化方法

```
总评分 = Σ(因子得分 × 因子权重)

每个因子得分范围: -1.0 (强利空) 到 +1.0 (强利好)
总分归一化: (原始分 / 总权重) + 50 → 0 ~ 100 分
```

权重以 `scanner/screener.py` 中的 `WEIGHTS_LOW` / `WEIGHTS_MOMENTUM` 字典为准。
修改权重直接编辑这两个字典即可。

---

## 7. 业界参考模型

### 7.1 Barra CNE6 因子模型 (行业标准)

Barra 是 MSCI 旗下的多因子风险模型, CNE6 是其针对中国 A 股的第 6 代版本。

**8 大类风格因子**:

| 因子类别 | 年化收益 | 说明 |
|---|---|---|
| Size (规模) | -2.75% | 小市值超额收益 (反向因子) |
| Volatility (波动) | +1.93% | 高波动高收益 (正向因子) |
| Liquidity (流动) | -5.90% | 低流动性的超额 (反向因子) |
| Momentum (动量) | -5.57% | A股动量反转效应强 (反向) |
| Quality (质量) | 阶段性 | ROE/盈利稳定性 |
| Value (价值) | +1.38% | 低估值保护 (正向因子) |
| Growth (成长) | 阶段性 | 营收/利润增速 |
| DividendYield (股息) | 阶段性 | 高股息防御属性 |

**对我们系统的启示**:
1. A股小市值因子和反转因子显著, 我们的 `low_position` 模式与之契合
2. 动量因子在A股表现稳定, 我们的 `momentum` 模式有理论支撑
3. 纯因子模型 R² ≈ 11.45%, 说明需要结合多维度信号 (我们的多Agent架构优势)

**Barra CNE6 vs 我们的因子映射**:

| Barra 因子 | 我们的对应因子 | 来源 |
|---|---|---|
| Momentum | ma_trend, macd_signal | 技术指标 |
| Volatility | rsi_position, bb_position | 技术指标 |
| Liquidity | volume_ratio | 量价分析 |
| Quality | score_ma5_stability | 技术指标 |
| Value | (未实现, 需基本面数据) | 未来扩展 |
| Growth | (未实现, 需财务数据) | 未来扩展 |

### 7.2 AlphaSift 多因子评分框架

由同作者 (ZhuLinsen) 开发的 AI 选股引擎, 提供可配置的多因子评分:

**8 个子评分维度**:
| 维度 | 说明 | 对应我们的 |
|---|---|---|
| factor_value_score | 估值评分 | 基本面Agent |
| factor_liquidity_score | 流动性评分 | volume_ratio |
| factor_momentum_score | 动量评分 | ma_trend, macd |
| factor_reversal_score | 反转评分 | RSI_position |
| factor_activity_score | 活跃度评分 | 量比 |
| factor_stability_score | 稳定性评分 | (未来) |
| factor_size_score | 市值评分 | (未来) |
| factor_theme_heat_score | 板块热度评分 | (未来) |

权重通过 YAML 配置, 支持等权和自定义两种方案。

### 7.3 华泰多维择时模型 (2026)

华泰证券最新研报, 将 26 个因子 → 12 子维度 → 4 大类:

**3 种模型**:
- **A1 (分层合成)**: 子维度 → 大类 → 最终评分 Sharpe 1.48
- **A2 (直接等权)**: 跳过大类聚合 Sharpe 1.50
- **B (路径优化)**: 动态选择最优子维度 Sharpe **1.72**

**核心洞察**: 不同因子在不同市场场景中表现不同:
- 追涨场景: 动量和资金流因子权重提高
- 抄底场景: 反转和估值因子权重提高
- 防御场景: 低波动和股息因子权重提高

**对我们的启示**: 我们的 `low_position` 和 `momentum` 两种模式本质上就是场景化因子选择, 与华泰模型B的思路一致。

### 7.4 未来可引入的改进

| 改进方向 | 参考来源 | 优先级 |
|---|---|---|
| 因子 ICIR 动态加权 (按历史表现调权重) | BigQuant ICIR | ⭐⭐⭐ |
| 场景化因子选择 (自适应切换权重) | 华泰 B 模型 | ⭐⭐⭐ |
| 机器学习因子合成 (LightGBM) | BigQuant | ⭐⭐ |
| 另类数据 (北向资金/主力流向) | Barra | ⭐⭐ |
| 因子绩效归因 (定期评估各因子有效性) | Barra CNE6 | ⭐⭐ |
| 行业中性化处理 | Barra | ⭐ |

---

## 8. 数据依赖

### 5.1 数据源一览

| 数据 | 来源 | 库 | 费用 | 稳定性 | 是否必需 |
|---|---|---|---|---|---|
| 实时行情 | 新浪财经 | akshare | 免费 | ⭐⭐⭐ | ✅ |
| K线历史 | 证券宝 | baostock | 免费 | ⭐⭐⭐⭐ | ✅ |
| 财务数据 | 证券宝 | baostock | 免费 | ⭐⭐⭐ | ⚠️ 可选 |
| 新闻 | 东方财富 | akshare | 免费 | ⭐⭐ | ⚠️ 可选 |
| 基本面 | akshare | akshare | 免费 | ⭐⭐ | ⚠️ 可选 |

### 5.2 数据获取策略

```python
# market.py: K线策略
get_kline():
  1. 尝试 Baostock (稳定, 官方数据)
  2. 失败 → 尝试 akshare (兜底)

# market.py: 行情策略
get_realtime_quote():
  1. 尝试 akshare 东方财富 (推荐)
  2. 失败 → 尝试 akshare 新浪 (兜底)
  3. 缓存全市场数据 (避免重复下载)
```

---

## 9. 扩展指南

### 6.1 如何添加新的 Agent

```python
# 1. 创建 Agent 文件
# agents/my_agent.py

from agents.base import BaseAgent

class MyAnalyst(BaseAgent):
    def system_prompt(self) -> str:
        return "你是一个XX专家..."

my_analyst = MyAnalyst("my", temperature=0.1)

# 2. 在编排器中集成
# chief/orchestrator.py
from agents.my_agent import my_analyst

class Orchestrator:
    def analyze_buy(self, symbol):
        # ... 现有流程 ...
        my_report = my_analyst.call(my_input)
        # ... 传给 Chief ...
```

### 6.2 如何添加新的数据源

```python
# data/your_source.py
def get_your_data(symbol: str) -> dict:
    """实现数据获取逻辑, 返回标准格式"""
    ...
    
# 在需要的 Agent 中调用
```

### 6.3 如何修改评分规则

编辑 `scanner/screener.py` 中的 `_compute_score()` 函数。
调整对应因素的加分/减分规则即可。

### 6.4 配置文件

```env
OPENAI_API_KEY=       # AI模型密钥
OPENAI_BASE_URL=      # API地址 (可换任意兼容OpenAI的服务)
OPENAI_MODEL=         # 模型名 (deepseek-chat / gpt-4o-mini 等)
STOCK_LIST=           # 股票代码, 逗号分隔
WECHAT_WEBHOOK_URL=   # 企业微信推送 (可选)
```

---

## 10. 回测验证

### 7.1 方案一: 历史回测 (已实现)

```
文件: backtest/
模块: backtest/engine.py, backtest/data.py

原理: 指定一个过去日期 → 只取该日期之前的数据 → 
     模拟当时决策 → 对比后续20天真实走势

用法:
  python main.py backtest            # 回测30天前
  python main.py backtest 2026-05-01 # 指定日期
  python main.py btmulti             # 多日期综合

输出指标:
  - 方向正确率 (%)
  - Score-收益相关性 (Pearson)
  - 推荐买入 vs 回避的收益差 (多空差)
  - 盈亏比
```

### 7.2 方案二: 实时跟踪 (日常使用)

每天运行的 `buy` / `hunt` 模式本身就是方案二:
- 记录今天的建议 → 30天后回顾验证
- 需要手动记录对比

---

## 附录

### A. 文件清单

```
ai-stock-advisor/
├── main.py                      # 入口
├── config.py                    # 配置
├── requirements.txt             # 依赖
├── .env.example                 # 环境变量模板
├── .gitignore                   # Git忽略
├── README.md                    # 项目简介
├── ARCHITECTURE.md              # 本文档
├── LICENSE                      # MIT协议
├──
├── agents/                      # Agent 层
│   ├── __init__.py
│   ├── base.py                  # Agent基类
│   ├── technical.py             # 技术分析
│   ├── fundamental.py           # 基本面
│   ├── sentiment.py             # 舆情
│   ├── risk.py                  # 风控
│   ├── scanner.py               # 扫描精选
│   └── hunter.py                # 低位挖掘
│
├── chief/                       # 决策层
│   ├── __init__.py              # Chief Agent
│   └── orchestrator.py          # 流程编排
│
├── data/                        # 数据层
│   ├── market.py                # 行情+K线
│   ├── fundamentals.py          # 基本面
│   ├── indicators.py            # 技术指标
│   └── news.py                  # 新闻
│
├── backtest/                    # 回测
│   ├── __init__.py
│   ├── data.py                  # 回测数据层
│   └── engine.py                # 回测引擎
│
├── scanner/                     # 量化筛选
│   ├── __init__.py
│   └── screener.py              # 筛选+评分
│
├── portfolio/                   # 持仓管理
│   ├── __init__.py
│   ├── storage.py
│   └── manager.py
│
├── report/                      # 报告推送
│   ├── __init__.py
│   ├── formatter.py
│   └── notifier.py
│
├── workflows/                   # GitHub Actions 模板
├── .github/workflows/           # 实际使用的workflow
│   ├── manual.yml               # 手动触发
│   ├── buy_analysis.yml         # 每日买入 (定时)
│   └── sell_analysis.yml        # 每日卖出 (定时)
│
└── data/
    └── portfolio.json           # 持仓数据 (本地)
```

### B. LLM Token 预算 (每只股票)

| Agent | Input Tokens | Output Tokens | 费用 (DeepSeek) |
|---|---|---|---|
| Technical | ~1,200 | ~400 | ¥0.0016 |
| Fundamental | ~700 | ~300 | ¥0.0010 |
| Sentiment | ~1,000 | ~300 | ¥0.0013 |
| Risk | ~900 | ~350 | ¥0.0012 |
| Chief | ~1,500 | ~300 | ¥0.0018 |
| **合计** | **~5,300** | **~1,650** | **¥0.0069/只** |

10只股票跑一次买入 ≈ ¥0.07 (7分钱)

### C. 版本记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-06 | v1.0 | 初始版本: 单Agent架构 |
| 2026-06 | v2.0 | 多Agent架构: 4专家+Chief |
| 2026-06 | v2.1 | 新增Hunter低位挖掘Agent |
| 2026-06 | v2.2 | 低随机性改进 (seed/temperature) |
| 2026-06 | v2.3 | 回测验证框架 (backtest) |
