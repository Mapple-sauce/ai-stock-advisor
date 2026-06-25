<div align="center">

# AI Stock Advisor 🤖📈

**AI 多 Agent 协作股票分析系统**

技术分析 · 基本面分析 · 舆情分析 · 风险评估 · Chief Agent 总决策

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek%20%7C%20Claude%20%7C%20Gemini-orange)](https://github.com/ZhuLinsen/daily_stock_analysis)

</div>

---

## 📋 项目简介

AI Stock Advisor 是一个基于**多 Agent 协作架构**的智能股票分析系统。它模拟一个投资分析团队的工作流程：

| Agent | 角色 | 职责 |
|-------|------|------|
| **Chief Agent** 🧠 | 首席投资官 | 综合所有专家意见，做出最终决策 |
| **Technical Analyst** 📊 | 技术分析专家 | K线形态、均线、MACD、RSI、KDJ、布林带 |
| **Fundamental Analyst** 📋 | 基本面分析专家 | 估值分析、盈利能力、成长性 |
| **Sentiment Analyst** 📰 | 舆情分析专家 | 新闻情绪、市场热度、事件驱动 |
| **Risk Analyst** ⚠️ | 风险评估专家 | 技术风险、仓位建议、止损位 |

## ✨ 功能特性

- ✅ **买入分析** — 4 位 Agent 并行分析 + Chief 综合决策
- ✅ **持仓卖出分析** — 技术面 + 舆情 + 风险评估 + 首席决策
- ✅ **市场扫描** — 全市场初筛 + AI 精选
- ✅ **多AI模型** — 支持 DeepSeek / Claude / Gemini / OpenAI 兼容接口
- ✅ **自动化运行** — GitHub Actions 定时触发，每天收盘后自动分析
- ✅ **企业微信推送** — 分析结果自动推送到企业微信群

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
| `STOCK_LIST` | 股票代码列表，逗号分隔，如 `600519,300750,000001` | ✅ |
| `WECHAT_WEBHOOK_URL` | 企业微信群机器人 Webhook | 推送用 |

### 3. 启用 Actions

进入 **Actions** 标签页，点击启用按钮。

### 4. 手动触发

进入 **Actions → Manual Run → Run workflow**，选择模式运行。

## 📁 项目结构

```
ai-stock-advisor/
├── agents/                # Agent 定义
│   ├── base.py            # Agent 基类 (LLM 调用)
│   ├── technical.py       # 技术分析 Agent
│   ├── fundamental.py     # 基本面分析 Agent
│   ├── sentiment.py       # 舆情分析 Agent
│   ├── risk.py            # 风险评估 Agent
│   └── scanner.py         # 市场扫描 Agent
├── chief/                 # 总决策层
│   ├── __init__.py        # Chief Agent (综合决策)
│   └── orchestrator.py    # 流程编排器
├── data/                  # 数据获取层
│   ├── market.py          # 行情数据 (新浪 + Baostock)
│   ├── fundamentals.py    # 基本面数据
│   ├── indicators.py      # 技术指标计算
│   ├── news.py            # 新闻舆情
│   └── portfolio.json     # 持仓样本数据
├── report/                # 报告与通知
│   ├── formatter.py       # 报告格式化
│   └── notifier.py        # 企业微信推送
├── portfolio/             # 持仓管理
│   ├── storage.py         # 持久化
│   └── manager.py         # CRUD操作
├── scanner/               # 市场扫描
│   └── screener.py        # 量化初筛
├── workflows/             # GitHub Actions
├── main.py                # 入口
├── config.py              # 配置管理
└── requirements.txt       # 依赖
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
python main.py buy    # 买入分析
python main.py sell   # 卖出分析
python main.py scan   # 市场扫描
python main.py all    # 全流程
```

## 💰 运营成本

使用 DeepSeek API，每日分析 10 只股票约 ¥0.1 元，每月约 ¥2.5 元。

## 📜 数据源

| 数据 | 来源 | 费用 |
|------|------|------|
| 实时行情 | 新浪财经 | 免费 |
| K线/历史 | Baostock | 免费 |
| 基本面 | akshare | 免费 |
| 新闻 | akshare | 免费 |

## ⚠️ 免责声明

本项目仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
