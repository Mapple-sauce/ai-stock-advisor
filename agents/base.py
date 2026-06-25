"""Agent 基类 —— 低随机性版本

降低随机性的策略:
  1. temperature=0.1 (接近确定性的输出)
  2. seed=42 (固定随机种子, 相同输入→相同输出)
  3. top_p=0.1 (只从概率最高的 token 中采样)
  4. call_structured() 强制 JSON Schema 约束输出格式
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from config import settings
from httpx import Client, Timeout


# 固定种子, 保证相同输入得到相同输出
_FIXED_SEED = 42


class BaseAgent(ABC):
    """所有 Agent 的基类 — 低随机性"""

    def __init__(self, name: str, model_override: str = "",
                 temperature: float = 0.1, top_p: float = 0.1):
        self.name = name
        self.model = model_override or settings.get_agent_model(name.lower()) or settings.openai_model
        self.temperature = temperature
        self.top_p = top_p

    @abstractmethod
    def system_prompt(self) -> str:
        ...

    def call(self, user_prompt: str, max_tokens: int = 4096) -> str:
        """调用 LLM (低随机性)"""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY 未配置")

        messages = [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": user_prompt},
        ]

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "seed": _FIXED_SEED,
            "max_tokens": max_tokens,
        }

        with Client(timeout=Timeout(180.0, connect=10.0)) as client:
            resp = client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def call_structured(self, user_prompt: str, output_schema: dict,
                        max_tokens: int = 4096) -> dict:
        """调用 LLM 并强制返回结构化 JSON (确定性最高)"""
        prompt = (
            f"{user_prompt}\n\n"
            f"## 输出要求\n"
            f"只返回 JSON，不要任何额外文字、markdown 或解释。\n"
            f"严格按照以下 JSON Schema 输出:\n"
            f"{json.dumps(output_schema, ensure_ascii=False, indent=2)}"
        )
        result = self.call(prompt, max_tokens=max_tokens)
        return self._parse_json(result)

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {"raw": text, "error": "JSON 解析失败"}
