"""Agent 基类"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from config import settings
from httpx import Client, Timeout


class BaseAgent(ABC):
    """所有 Agent 的基类"""

    def __init__(self, name: str, model_override: str = "", temperature: float = 0.3):
        self.name = name
        self.model = model_override or settings.get_agent_model(name.lower()) or settings.openai_model
        self.temperature = temperature

    @abstractmethod
    def system_prompt(self) -> str:
        """返回该 Agent 的系统提示词"""
        ...

    def call(self, user_prompt: str, max_tokens: int = 4096) -> str:
        """调用 LLM"""
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

    def call_structured(self, user_prompt: str, output_schema: dict, max_tokens: int = 4096) -> dict:
        """调用 LLM 并返回结构化 JSON"""
        prompt = (
            f"{user_prompt}\n\n"
            f"请严格按照以下 JSON Schema 输出，只返回 JSON，不要加额外说明:\n"
            f"{json.dumps(output_schema, ensure_ascii=False, indent=2)}"
        )
        result = self.call(prompt, max_tokens=max_tokens)
        return self._parse_json(result)

    @staticmethod
    def _parse_json(text: str) -> dict:
        """从 LLM 输出中提取 JSON"""
        # 尝试直接解析
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试找到 {...} 或 [{...}]
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {"raw": text, "error": "JSON 解析失败"}
