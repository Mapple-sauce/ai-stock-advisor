# 📊 项目架构流程图

> 此流程图由 `tools/generate_flowchart.py` 自动生成，项目变更后重新运行即可同步。

## 整体架构

```mermaid
graph TB
    %% 样式定义
    classDef cmd fill:#e2a76f,stroke:#333,stroke-width:2px,color:#fff;
    classDef data fill:#16213e,stroke:#4a6fa5,stroke-width:1.5px,color:#ddd;
    classDef agent fill:#0f3460,stroke:#4a6fa5,stroke-width:2px,color:#fff;
    classDef chief fill:#e94560,stroke:#fff,stroke-width:2px,color:#fff;
    classDef output fill:#533483,stroke:#c77dff,stroke-width:2px,color:#fff;
    classDef backtest fill:#2d3436,stroke:#636e72,stroke-width:2px,color:#b2bec3;

    %% 命令行入口
    CLI["⚡ CLI: python main.py [buy|sell|scan|low|mom|hunt|report|backtest]"]
    class CLI cmd;

    %% 数据层
    subgraph DATA_LAYER["📦 数据层"]
        MARKET["行情数据<br/>新浪财经(实时) + Baostock(K线/分红)"]
        FUND["基本面数据<br/>akshare(财务/新闻)"]
        SECTOR["板块分类<br/>scanner/sectors.py<br/>7大板块×方向控制"]
    end
    class MARKET,FUND,SECTOR data;

    %% 量化筛选层
    SCREENER["🔬 量化筛选引擎 scanner/screener.py<br/>全市场5000+ → 过滤 → TOP80 → 10因子评分<br/>板块感知权重 + 方向控制(正向/反向)"]
    class SCREENER agent;

    %% Agent层
    subgraph AGENT_LAYER["🤖 Agent 分析层"]
        TA["📊 Technical Analyst<br/>均线/MACD/RSI/布林带"]
        FA["📋 Fundamental Analyst<br/>估值/ROE/成长性"]
        SA["📰 Sentiment Analyst<br/>新闻情绪/板块热度"]
        RA["⚠️ Risk Analyst<br/>止损/仓位/关键价位"]
        HA["💎 Hunter Agent<br/>四层框架纵深挖掘"]
    end
    class TA,FA,SA,RA,HA agent;

    %% Chief Agent
    CHIEF["🧠 Chief Agent (首席投资官)<br/>综合4专家意见 → 结构化JSON决策<br/>temperature=0.05 / seed=42"]
    class CHIEF chief;

    %% 输出层
    subgraph OUTPUT_LAYER["📤 输出层"]
        BUY[("📈 买入/卖出分析<br/>Agent报告 + JSON决策<br/>企业微信推送")]
        SCAN[("📊 市场扫描<br/>涨幅榜/低位/追高<br/>AI精选TOP 5")]
        HUNT[("💎 低位挖掘<br/>全市场→量化→AI深度<br/>精选排名+数据")]
        PDF[("📄 PDF报告<br/>每日收盘分析报告<br/>含产业链布局建议")]
    end
    class BUY,SCAN,HUNT,PDF output;

    %% 回测系统
    BT["🧪 回测验证 backtest/<br/>历史回测 | 权重优化 | 分红数据"]
    class BT backtest;

    %% 数据流连接
    CLI --> MARKET
    CLI --> SCREENER
    MARKET --> SCREENER
    FUND --> SCREENER
    SECTOR --> SCREENER
    SECTOR --> TA
    SECTOR --> RA
    SECTOR --> HA

    SCREENER --> TA
    SCREENER --> FA
    SCREENER --> SA
    SCREENER --> RA
    SCREENER --> HA

    TA --> CHIEF
    FA --> CHIEF
    SA --> CHIEF
    RA --> CHIEF
    HA --> CHIEF

    CHIEF --> BUY
    CHIEF --> SCAN
    CHIEF --> HUNT
    CHIEF --> PDF

    BUY -.-> BT
    SCAN -.-> BT
    HUNT -.-> BT
```

## 板块策略权重矩阵

```mermaid
graph LR
    %% 样式
    classDef sector fill:#0f3460,stroke:#4a6fa5,color:#fff;
    classDef dir_pos fill:#2ecc71,stroke:#fff,color:#fff;
    classDef dir_neg fill:#e94560,stroke:#fff,color:#fff;

    S["板块感知权重体系"] --> T["科技 🖥️"]
    S --> M["医药 💊"]
    S --> I["工业 ⚙️"]
    S --> F["金融 🏦"]
    S --> N["新能源 ⚡"]
    S --> C["周期 ⛏️"]
    S --> CON["消费 🍶"]

    T --> T1["方向: 正向(高分=好)"]
    T --> T2["均线18%  MACD15%  量价12%"]

    M --> M1["方向: 正向(高分=好)"]
    M --> M2["均线14%  MACD12%  价格位置10%"]

    I --> I1["方向: 反向(低分=好)"]
    I --> I2["均线14%  MACD10%  MA5支撑7%"]

    F --> F1["方向: 正向(高分=好)"]
    F --> F2["RSI12%  价格位置12%  均线10%"]

    N --> N1["方向: 反向(低分=好)"]
    N --> N2["均线16%  MACD14%  量价12%"]

    C --> C1["方向: 正向(高分=好)"]
    C --> C2["均线18%  MACD15%  涨幅10%"]

    CON --> CON1["方向: 正向(高分=好)"]
    CON --> CON2["RSI12%  布林10%  价格位置12%"]

    class T,M,I,F,N,C,CON sector;
    class T1,M1,F1,C1,CON1 dir_pos;
    class I1,N1 dir_neg;
```

## 数据流全景

```mermaid
sequenceDiagram
    participant User as 用户
    participant CLI as CLI入口
    participant Data as 数据层
    participant Quant as 量化筛选
    participant Agents as Agents
    participant Chief as Chief Agent
    participant Output as 输出

    User->>CLI: python main.py hunt
    CLI->>Data: 获取全市场行情
    Data-->>CLI: 5000+股票实时数据
    CLI->>Quant: 过滤+计算技术指标
    Quant-->>CLI: TOP80候选股+评分
    CLI->>Agents: 逐一深度分析(TOP10)
    Agents-->>Chief: 4份分析报告
    Chief-->>Chief: 综合评分+决策
    Chief-->>Output: 最终报告
    Output-->>User: 企业微信/PDF推送
```

## 命令参考速查

| 命令 | 功能 | 耗时 |
|------|------|------|
| `python main.py buy` | 买入分析（4 Agent + Chief） | ~3-5分钟/10只 |
| `python main.py sell` | 持仓卖出分析 | ~2-3分钟/5只 |
| `python main.py scan` | 涨幅榜扫描 | ~20秒 |
| `python main.py low` | 低位潜力股筛选 | ~30秒 |
| `python main.py mom` | 追高跟强筛选 | ~30秒 |
| `python main.py hunt` | 低位挖掘深度分析 | ~3-5分钟 |
| `python main.py report` | 生成每日PDF报告 | ~2分钟 |
| `python main.py backtest` | 单次回测验证 | ~1分钟 |
| `python main.py btmulti` | 多日期综合回测 | ~5分钟 |

---

> **流程图自动生成**: 运行 `python tools/generate_flowchart.py` 更新 PNG 图表
> **最后更新**: 项目 git 提交记录
