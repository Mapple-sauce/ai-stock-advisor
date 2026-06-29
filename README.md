<div align="center">

# AI Stock Advisor 🤖📈

**AI 多 Agent 协作股票分析系统 — 深度个股分析 + 板块/供应链分析 + 价格预测**

A股专属 · 技术分析 · 基本面分析 · 行业地位分析 · 供应链分析 · 并行AI研判

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-orange)](https://github.com/ZhuLinsen/daily_stock_analysis)

</div>

---

## 📋 项目简介

AI Stock Advisor 是一个 **A 股专用的多 Agent 协作股票分析系统**。它通过多个 AI 专家并行工作，对每只个股进行全维度分析，并生成 **中文 PDF 报告**（含图表、价格预测、买卖建议）。

### 核心特色

| 特性 | 说明 |
|------|------|
| 🧠 **4 Agent 并行** | 主分析 + 板块分析 + 行业地位 + 供应链分析 同时运行 |
| 📊 **10 因子评分** | 均线/MACD/RSI/布林/KDJ/量价等 10 因子加权评分（百分制 1-100） |
| 📈 **价格预测** | 基于历史波动率的统计模拟，给出 1 周/1 月价格区间 |
| 📄 **中文 PDF 报告** | 自动生成带图表的 10 章节深度分析报告 |
| 🏭 **行业与供应链** | 板块趋势、同业排名、上下游产业链分析 |
| 📋 **财报深度分析** | 近 4 个季度营收/利润/毛利率趋势、ROE/负债率/现金流 |
| 📖 **指标参考手册** | 面向小白的投资指标科普 PDF |
| 🤖 **多 AI 模型** | 兼容 DeepSeek / OpenAI / Claude 等 API |
| ⚡ **自动化** | GitHub Actions 定时 + 手动触发，收盘后自动出报告 |

## ✨ 功能特性

### 📊 个股深度分析 (`analyze`)
对每只股票自动执行：
1. **数据采集** — 行情 / K线 / 技术指标 / 核心指标 / 基本面 / 新闻 / 资金流向
2. **行业数据** — 板块指数表现 / 同业可比公司 / 行业排名 / 供应链上下文
3. **图表生成** — 价格走势图 / 技术指标图（布林+MACD+KDJ）/ 回撤分析图
4. **4 Agent 并行 AI 分析**：
   - **主分析** — 技术面+基本面+情绪+风险+后市展望
   - **板块分析** — 板块趋势/驱动因素/热度/展望
   - **行业地位** — 市场地位/估值对比/竞争优势
   - **供应链分析** — 上下游依赖/产业链位置/风险
5. **PDF 报告生成** — 10 章节个股深度分析报告

### 🏢 市场扫描 (`scan` / `low` / `mom`)
- 全市场因子评分初筛 + AI 精选
- 板块感知权重系统（7 大板块分别配置）

### 📋 每日收盘报告 (`report`)
- 市场总览 / 板块分析 / 个股技术评分 / AI 热点追踪 / 风险提示

### 🎯 价格预测与买卖建议
- 基于波动率的蒙特卡洛模拟
- 买入区间 / 卖出区间 / 止损位
- 仓位建议（轻仓/半仓/重仓/空仓）

### 📖 指标参考手册 (`guide`)
- 独立 PDF，解释每个技术指标的定义、看法、小白速记
- 适合新手对照阅读

## 🔧 运行模式一览

| 命令 | 说明 | 输出 |
|------|------|------|
| `analyze` | 个股深度分析（多只逗号分隔） | PDF报告 + 图表 |
| `guide` | 投资指标参考手册 | PDF |
| `text` | 纯文本版分析（快速排错） | TXT |
| `scan` | 市场扫描 | 终端输出 |
| `report` | 每日收盘报告 | PDF |
| `buy` / `sell` | 买入/卖出分析 | 终端输出+推送 |
| `hunt` | 深度挖掘标的 | 终端输出 |
| `backtest` / `optimize` | 回测/权重优化 | 终端输出 |

## 🚀 快速开始

### 1. Fork 仓库

点击右上角 **Fork** 按钮，将仓库复制到你的 GitHub 账号下。

### 2. 配置 GitHub Secrets

在仓库 `Settings → Secrets and variables → Actions` 中添加：

| Secret | 说明 | 必填 |
|--------|------|------|
| `OPENAI_API_KEY` | DeepSeek / OpenAI API 密钥 | ✅ |
| `OPENAI_BASE_URL` | API 地址 (DeepSeek: `https://api.deepseek.com`) | ✅ |
| `OPENAI_MODEL` | 模型名 (`deepseek-chat`) | ✅ |
| `STOCK_LIST` | 股票代码列表，逗号分隔 | ✅ |
| `WECHAT_WEBHOOK_URL` | 企业微信群机器人 Webhook | 推送用 |

### 3. 启用 Actions

进入 **Actions** 标签页，点击启用按钮。

### 4. 手动触发

进入 **Actions → Manual Run → Run workflow**，选择模式运行：

| 模式 | 用途 |
|------|------|
| `analyze` | 分析个股，`stock_code` 填代码（逗号分隔） |
| `guide` | 生成投资指标参考手册 |
| `text` | 纯文本版分析（快速排错） |
| `report` | 每日收盘报告 |

### 5. 下载报告

运行完成后，在 Actions 运行结果页的 **Artifacts** 区下载 ZIP 文件，内含 PDF + 图表。

## 📁 项目结构

```
ai-stock-advisor/
├── agents/                  # AI Agent 定义
│   ├── base.py              # Agent 基类 (OpenAI 兼容 API 调用)
│   ├── sector.py            # 行业板块分析 Agent 🆕
│   ├── industry_position.py # 行业地位分析 Agent 🆕
│   ├── supply_chain.py      # 供应链分析 Agent 🆕
│   ├── technical.py         # 技术分析 Agent
│   ├── fundamental.py       # 基本面分析 Agent
│   ├── sentiment.py         # 舆情分析 Agent
│   ├── risk.py              # 风险评估 Agent
│   ├── scanner.py           # 市场扫描 Agent
│   └── hunter.py            # 深度挖掘 Agent
├── analysis/                # 个股深度分析
│   ├── analyst.py           # StockAnalyst（主入口，含并行执行）🔄
│   ├── industry.py          # 行业数据采集模块 🆕
│   ├── charts.py            # matplotlib 图表生成
│   └── metrics.py           # 核心指标计算
├── chief/                   # 总决策层
│   ├── __init__.py          # Chief Agent（综合买入/卖出决策）
│   └── orchestrator.py      # 流程编排器
├── data/                    # 数据获取层
│   ├── market.py            # 行情数据 (新浪 + Baostock + 东方财富)
│   ├── fundamentals.py      # 基本面数据（含近4个季度趋势）🔄
│   ├── indicators.py        # 技术指标计算
│   ├── news.py              # 新闻数据
│   ├── sentiment.py         # 舆情聚合
│   └── money_flow.py        # 资金流向
├── report/                  # 报告生成
│   ├── pdf_report.py        # PDF 基类 (中文)
│   ├── individual_report.py # 个股深度分析 PDF（10 章节）🔄
│   ├── indicator_guide.py   # 投资指标参考手册 PDF 🆕
│   ├── daily_report.py      # 每日收盘报告
│   ├── formatter.py         # 报告格式化
│   └── notifier.py          # 企业微信推送
├── scanner/                 # 市场扫描
│   ├── screener.py          # 10 因子量化评分
│   └── sectors.py           # 板块分类与权重系统
├── backtest/                # 回测引擎
│   ├── engine.py            # 回测核心
│   ├── optimizer.py         # 权重优化
│   └── weight_optimizer.py  # 优化器 UI
├── fonts/                   # 中文字体
├── .github/workflows/       # GitHub Actions
│   ├── manual.yml           # 手动触发（支持 analyze/guide/text 等）
│   └── daily_report.yml     # 每日定时报告
├── main.py                  # 入口
├── config.py                # 配置管理
├── test_analysis.py         # 纯文本版测试分析 🆕
└── requirements.txt         # 依赖
```

## 🖥️ 本地运行

```bash
# 克隆
git clone https://github.com/你的用户名/ai-stock-advisor.git
cd ai-stock-advisor

# 安装
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 运行
python main.py analyze 002594                # 分析比亚迪
python main.py analyze 512480,510880,002594  # 多只分析
python main.py buy                           # 买入分析
python main.py report                        # 每日报告
python -m report.indicator_guide             # 生成指标参考手册
```

## 🤖 AI 评分体系（百分制 1-100）

| 分数区间 | 评级 | 说明 |
|----------|------|------|
| 85-100 | 🟢 强烈推荐 | 技术面多头+基本面优秀+资金流入+情绪正面 |
| 65-84 | 🟢 推荐买入 | 整体偏多，少量瑕疵 |
| 45-64 | 🟡 中性观望 | 多空均衡，等待触发因素 |
| 25-44 | 🟡 谨慎回避 | 偏弱，多个风险点 |
| 1-24 | 🔴 回避 | 技术面/基本面明显恶化 |

### 10 因子权重分布

| 因子 | 权重 | 说明 |
|------|------|------|
| MA 趋势 | 10-18% | 均线排列方向（多头/空头） |
| MACD 信号 | 8-15% | 金叉/死叉 + 柱体强度 |
| RSI 位置 | 5-12% | 超买超卖 + 趋势 |
| 成交量比 | 5-12% | 量价配合程度 |
| 布林位置 | 5-12% | 在布林带中位置 |
| KDJ 信号 | 5-12% | K/D 线交叉信号 |
| 价格位置 | 5-12% | 在近期高低点的位置 |
| 距前高/低 | 4-10% | 接近压力位还是支撑位 |
| 日涨跌幅 | 4-12% | 当日涨跌幅度 |
| MA5 稳定性 | 5-10% | 5日均线的斜率平稳度 |

> 权重根据 **板块**（消费/科技/医药/金融/新能源/周期/工业）和 **模式**（低位/追高）动态调整。

## 💰 运营成本

使用 DeepSeek API，分析 5 只股票（4 个 Agent 并行）约 ¥0.15 元，每日自动运行约 ¥0.3 元。

## ⚡ GitHub Actions 工作流

### 手动触发 (`manual.yml`)
进入 **Actions → Manual Run → Run workflow**，选择模式：

| 模式 | stock_code 参数 | 输出 |
|------|----------------|------|
| `analyze` | `512480,510880,002594,601012`（逗号分隔） | `reports/` 下的个股 PDF + 图表 |
| `guide` | 不需要 | `reports/guide/` 下的指标参考手册 PDF |
| `text` | `512480,510880,002594`（纯文本快速排错） | `reports/` 下的 TXT 文件 |
| `report` | 不需要 | 每日收盘 PDF 报告 |
| `scan` / `low` / `mom` | 不需要 | 终端输出（在日志中查看） |
| `hunt` | 不需要 | 终端输出 |
| `optimize` | 不需要 | 权重优化结果 |

> `stock_code` 支持沪市（6/5/9开头）和深市（0/3开头）代码，ETF 代码自动识别。

### 定时触发 (`daily_report.yml`)
- 每个交易日 **17:00 北京时间** 自动生成每日收盘 PDF 报告
- 报告上传到 Actions 的 Artifacts 中

### 运行结果
每次运行完成后，在 Actions 运行结果页面的底部 **Artifacts** 区域：
- `reports` → 个股分析 PDF + 图表 PNG
- `daily-report` → 每日收盘 PDF 报告

点击即可下载 ZIP 文件。

## 📜 数据源

| 数据 | 来源 | 费用 |
|------|------|------|
| 实时行情 | 新浪财经 (akshare) | 免费 |
| K线/历史 | Baostock | 免费 |
| 行业分类 | Baostock | 免费 |
| 板块指数 | 东方财富 (akshare) | 免费 |
| 基本面 | akshare | 免费 |
| 新闻/研报 | akshare | 免费 |
| 资金流向 | akshare | 免费 |

## 🧩 技术栈

- **Python 3.12+** — 核心语言
- **akshare / Baostock** — 数据源
- **matplotlib** — 图表生成
- **fpdf2** — PDF 报告
- **DeepSeek / OpenAI 兼容 API** — AI 分析
- **concurrent.futures** — Agent 并行执行
- **GitHub Actions** — 自动化部署

## ⚠️ 免责声明

本项目仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。模型准确率约 60-65%，存在 35-40% 的判断误差。
