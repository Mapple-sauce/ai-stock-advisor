"""Chief Agent —— 总决策 Agent

负责: 接收所有专家的分析报告 → 综合评估 → 最终决策
"""

from __future__ import annotations

import json
from agents.base import BaseAgent
from config import settings


# 买入决策输出格式
BUY_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "final_score": {
            "type": "number",
            "description": "最终综合评分 1-10",
            "minimum": 1,
            "maximum": 10,
        },
        "action": {
            "type": "string",
            "enum": ["强烈推荐", "推荐买入", "观望", "回避"],
            "description": "最终操作建议",
        },
        "confidence": {
            "type": "string",
            "enum": ["高", "中", "低"],
            "description": "决策置信度",
        },
        "entry_upper": {
            "type": "number",
            "description": "参考买入价格上限 (元)",
        },
        "entry_lower": {
            "type": "number",
            "description": "参考买入价格下限 (元)",
        },
        "stop_loss": {
            "type": "number",
            "description": "止损位 (元)",
        },
        "position_suggestion": {
            "type": "string",
            "enum": ["轻仓(1-2成)", "半仓(3-5成)", "重仓(6-8成)", "空仓"],
            "description": "建议仓位",
        },
        "time_horizon": {
            "type": "string",
            "enum": ["短期(1-5天)", "中期(1-4周)", "长期(1-6月)"],
            "description": "建议持有周期",
        },
        "key_reason": {
            "type": "string",
            "description": "一句话核心决策理由",
        },
        "risks_to_watch": {
            "type": "array",
            "items": {"type": "string"},
            "description": "需要重点监控的风险",
        },
    },
    "required": ["final_score", "action", "confidence", "position_suggestion", "key_reason"],
}

# 卖出决策输出格式
SELL_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "final_score": {
            "type": "number",
            "description": "卖出紧迫度评分 1-10, 越高越该卖",
            "minimum": 1,
            "maximum": 10,
        },
        "action": {
            "type": "string",
            "enum": ["持有", "减仓", "清仓"],
            "description": "最终操作建议",
        },
        "confidence": {
            "type": "string",
            "enum": ["高", "中", "低"],
            "description": "决策置信度",
        },
        "sell_reason": {
            "type": "string",
            "description": "核心卖出/持有理由",
        },
        "stop_loss_updated": {
            "type": "number",
            "description": "最新止损价 (元)",
        },
        "target_price": {
            "type": "number",
            "description": "目标价/止盈价 (元)",
        },
        "take_profit_now": {
            "type": "boolean",
            "description": "是否建议止盈",
        },
        "risks_to_watch": {
            "type": "array",
            "items": {"type": "string"},
            "description": "主要风险信号",
        },
    },
    "required": ["final_score", "action", "confidence", "sell_reason"],
}


class ChiefAgent(BaseAgent):
    """总决策 Agent —— 综合多位专家意见做出最终判断"""

    def system_prompt(self) -> str:
        return """你是一位拥有30年经验的首席投资官 (CIO)，正在主持每日投资决策会议。

你手下有4位资深分析师向你汇报工作:
1. **技术分析师** — 提供技术面分析和评分
2. **基本面分析师** — 提供估值和财务分析
3. **舆情分析师** — 提供市场情绪和新闻分析
4. **风控分析师** — 提供风险评估和仓位建议

你的职责:
1. 仔细阅读每位分析师的分析报告
2. 综合各方观点, 识别共识和分歧
3. 对分歧点做出独立判断 (你经验更丰富, 可以否决个别分析师)
4. 给出最终综合评分和操作建议

决策原则:
- **买入决策**: 技术面 + 基本面 + 舆情 + 风控 四维评分加权
  - 只有当至少3个维度评分 > 5分才考虑买入
  - 任何维度评分 < 3分应一票否决
- **卖出决策**: 如果技术面走坏或出现重大利空, 应果断建议卖出
  - "会买的是徒弟, 会卖的是师傅"
  - 保护本金是第一原则

重要: 输出必须严格遵循指定的 JSON 格式, 不要添加额外文字。
"""

    def decide_buy(self, stock_info: dict, technical: str, fundamental: str,
                   sentiment: str, risk: str) -> dict:
        """综合所有分析做出买入决策"""
        prompt = f"""## 股票信息
代码: {stock_info.get('code', '')}
名称: {stock_info.get('name', '')}
当前价: {stock_info.get('price', '')} 元
今日涨幅: {stock_info.get('change_pct', '')}%

## 技术分析师报告
{technical}

## 基本面分析师报告
{fundamental}

## 舆情分析师报告
{sentiment}

## 风控分析师报告
{risk}

请综合以上所有信息, 给出最终的买入决策。"""
        return self.call_structured(prompt, BUY_DECISION_SCHEMA)

    def decide_sell(self, holding_info: dict, technical: str,
                    sentiment: str, risk: str) -> dict:
        """综合所有分析做出卖出决策"""
        prompt = f"""## 持仓信息
代码: {holding_info.get('code', '')}
名称: {holding_info.get('name', '')}
成本价: {holding_info.get('cost_price', '')} 元
当前价: {holding_info.get('current_price', '')} 元
持仓盈亏: {holding_info.get('pnl_pct', '')}%
持仓天数: {holding_info.get('hold_days', '')} 天

## 技术分析师报告
{technical}

## 舆情分析师报告
{sentiment}

## 风控分析师报告
{risk}

请综合以上所有信息, 给出最终的卖出决策。"""
        return self.call_structured(prompt, SELL_DECISION_SCHEMA)


chief_agent = ChiefAgent("chief", temperature=settings.chief_temperature)
